import argparse
import csv
import ssl
from pathlib import Path

import requests

try:
    from publicsuffixlist import PublicSuffixList
except ModuleNotFoundError:
    PublicSuffixList = None

CRTSH_BASE_URL = "https://crt.sh/"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
REQUEST_TIMEOUT = 60

STATE_DIR = Path("state")  # store pem files (cache)
STATE_DIR.mkdir(exist_ok=True)
CERT_ID_CACHE_FILE = STATE_DIR / "seen_cert_ids.txt"
PSL = PublicSuffixList() if PublicSuffixList else None
_PSL_WARNING_SHOWN = False


def normalize_domain(value):
    """Normalize DNS names found in certificates."""
    if not value:
        return ""
    value = value.strip().lower()
    if value.startswith("*."):
        value = value[2:]
    return value.strip(".")


def load_seen_cert_ids():
    """Load cached certificate IDs used by --uncached mode."""
    if not CERT_ID_CACHE_FILE.exists():
        return set()

    try:
        return {line.strip() for line in CERT_ID_CACHE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()}
    except OSError:
        return set()


def save_seen_cert_ids(seen_ids):
    """Persist processed certificate IDs for --uncached mode."""
    try:
        CERT_ID_CACHE_FILE.write_text("\n".join(str(cert_id) for cert_id in sorted(seen_ids)) + "\n", encoding="utf-8")
    except OSError as err:
        print(f"Warning: could not save cert ID cache: {err}")


def get_cert_ids(domain, args, extended=None):
    """Find all certificate IDs for the given domain query."""
    r_params = {"output": "json"}

    if args.exclude_expired:
        r_params["exclude"] = "expired"

    if (extended is None or extended is True) and args.extended:
        r_params["q"] = f"{get_domain_private_suffix(domain)}.%.%"
    else:
        r_params["Identity"] = domain

    headers = {"User-Agent": USER_AGENT}

    try:
        req = requests.get(CRTSH_BASE_URL, params=r_params, headers=headers, timeout=REQUEST_TIMEOUT)
        print(req.url)
        req.raise_for_status()
        certs = req.json()
    except requests.RequestException as err:
        print(f"Error retrieving certificates: {err}")
        return
    except ValueError:
        print("Error decoding crt.sh JSON response.")
        return

    seen = set()
    for cert in certs:
        cert_id = cert.get("min_cert_id") or cert.get("id")
        if cert_id is not None and cert_id not in seen:
            seen.add(cert_id)
            yield cert_id


def get_cert_entries(domain, args, extended=None):
    """Return deduplicated crt.sh JSON entries for a domain query."""
    r_params = {"output": "json"}

    if args.exclude_expired:
        r_params["exclude"] = "expired"

    if (extended is None or extended is True) and args.extended:
        r_params["q"] = f"{get_domain_private_suffix(domain)}.%.%"
    else:
        r_params["Identity"] = domain

    headers = {"User-Agent": USER_AGENT}

    try:
        req = requests.get(CRTSH_BASE_URL, params=r_params, headers=headers, timeout=REQUEST_TIMEOUT)
        print(req.url)
        req.raise_for_status()
        certs = req.json()
    except requests.RequestException as err:
        print(f"Error retrieving certificates: {err}")
        return []
    except ValueError:
        print("Error decoding crt.sh JSON response.")
        return []

    dedup = {}
    for cert in certs:
        cert_id = cert.get("min_cert_id") or cert.get("id")
        if cert_id is not None and cert_id not in dedup:
            dedup[cert_id] = cert

    return list(dedup.values())


def iter_domains_from_entry(entry):
    """Yield normalized domains from a crt.sh JSON entry."""
    name_value = entry.get("name_value", "")
    if name_value:
        for candidate in str(name_value).splitlines():
            normalized = normalize_domain(candidate)
            if normalized:
                yield normalized

    common_name = entry.get("common_name", "")
    if common_name:
        normalized = normalize_domain(common_name)
        if normalized:
            yield normalized


def get_cert(cert_id, args):
    """Download and cache PEM certificate for processing."""
    pem_file = STATE_DIR / f"{cert_id}.pem"
    if pem_file.exists():
        if args.uncached:
            return None
        return pem_file

    url = f"{CRTSH_BASE_URL}?d={cert_id}"

    try:
        req = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        req.raise_for_status()
        with pem_file.open("wb") as fd:
            fd.write(req.content)
        return pem_file
    except requests.RequestException as err:
        print(f"Error retrieving PEM for cert ID {cert_id}: {err}")
    except OSError as err:
        print(f"Error saving PEM for cert ID {cert_id}: {err}")

    return None


def get_subjectaltname(cert_path):
    """Extract DNS names from the subjectAltName or commonName fields."""
    if cert_path is None:
        return

    try:
        # Undocumented but convenient for parsing PEM in stdlib.
        pem = ssl._ssl._test_decode_cert(cert_path.as_posix())
    except Exception as err:
        print(f"Error decoding certificate {cert_path.name}: {err}")
        return

    san_items = pem.get("subjectAltName", [])
    yielded = False
    for name_type, value in san_items:
        if name_type == "DNS":
            norm = normalize_domain(value)
            if norm:
                yielded = True
                yield norm

    if yielded:
        return

    for subject_item in pem.get("subject", []):
        for key, value in subject_item:
            if key == "commonName":
                norm = normalize_domain(value)
                if norm:
                    yield norm
                return


def matches_private_suffix(subject, private_suffix):
    """Filter extended results to names related to the private suffix."""
    labels = [label for label in normalize_domain(subject).split(".") if label]
    return private_suffix in labels


def get_subdomains(domain, args, extended=None):
    """Extract domain names from certificate SAN/CN fields."""
    if extended is None:
        extended = args.extended

    subdomains = set()
    count = 0
    private_suffix = get_domain_private_suffix(domain) if extended else ""
    known_ids = load_seen_cert_ids() if args.uncached else set()
    processed_ids = set(known_ids)

    for entry in get_cert_entries(domain, args, extended):
        cert_id = entry.get("min_cert_id") or entry.get("id")
        if cert_id is None:
            continue

        cert_id = str(cert_id)

        if args.uncached and cert_id in known_ids:
            continue

        processed_ids.add(cert_id)
        for subject in iter_domains_from_entry(entry):
            if not extended or matches_private_suffix(subject, private_suffix):
                subdomains.add(subject)

        new_count = len(subdomains) - count
        if new_count > 0:
            print(f"New domains found: {new_count}.  Total: {count + new_count}")
        count = len(subdomains)

    if args.uncached:
        save_seen_cert_ids(processed_ids)

    return subdomains


def get_domain_private_suffix(domain):
    """Return private part of a domain (e.g. 'www.google' for 'www.google.com')."""
    global _PSL_WARNING_SHOWN

    domain = normalize_domain(domain)
    if not domain:
        return ""

    if PSL is None:
        if not _PSL_WARNING_SHOWN:
            print("Warning: 'publicsuffixlist' not installed. Using simplified domain parsing.")
            _PSL_WARNING_SHOWN = True
        labels = domain.split(".")
        return ".".join(labels[:-1]) if len(labels) > 1 else domain

    public_suffix = PSL.publicsuffix(domain)
    if not public_suffix:
        return domain

    suffix_token = f".{public_suffix}"
    if domain.endswith(suffix_token):
        return domain[: -len(suffix_token)]
    return domain


def save_domains_csv(domains, csv_path):
    """Save discovered domains to a CSV file."""
    output_path = Path(csv_path)
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["domain"])
        for domain in sorted(domains):
            writer.writerow([domain])

    return output_path


def main(args):
    print(
        "Domain: %s, Extended: %s, Exclude Expired: %s, Uncached: %s"
        % (args.domain, args.extended, args.exclude_expired, args.uncached)
    )

    all_domains = set()
    for domain in args.domain:
        if args.extended:
            results = get_subdomains(domain, args, extended=False).union(get_subdomains(domain, args))
        else:
            results = get_subdomains(domain, args, extended=False)
        all_domains.update(results)
        print(results)

    if args.csv:
        output_path = save_domains_csv(all_domains, args.csv)
        print(f"CSV saved to: {output_path} ({len(all_domains)} domains)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover domains using crt.sh.")
    parser.add_argument(
        "--domain",
        "-d",
        required=True,
        metavar="N",
        type=str,
        nargs="+",
        help="crt.sh domain query. Specify multiple using --domain <domain>",
    )
    parser.add_argument(
        "--extended",
        required=False,
        default=False,
        action="store_true",
        help="include wildcard searches with domain private suffix ('google.%%.%%' for 'google.com').",
    )
    parser.add_argument(
        "--exclude_expired",
        required=False,
        default=False,
        action="store_true",
        help="Exclude expired certificates.",
    )
    parser.add_argument(
        "--uncached",
        required=False,
        default=False,
        action="store_true",
        help="Only return domains not previously discovered (not in PEM cache).",
    )
    parser.add_argument(
        "--csv",
        required=False,
        default=None,
        metavar="FILE",
        type=str,
        help="Save discovered domains to CSV (e.g. --csv domains.csv).",
    )
    parser.set_defaults(func=main)

    try:
        args = parser.parse_args()
        args.func(args)
    except Exception as err:
        print(err)
        parser.print_help()
