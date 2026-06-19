import argparse
import csv
import datetime
import json
import random
import ssl
import time
from pathlib import Path

import requests

try:
    import psycopg2
except ModuleNotFoundError:
    psycopg2 = None

try:
    from publicsuffixlist import PublicSuffixList
except ModuleNotFoundError:
    PublicSuffixList = None

CRTSH_BASE_URL = "https://crt.sh/"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
REQUEST_TIMEOUT = 60

ALL_CERTS_JSON = []
DOMAIN_ANALYSIS = {}

def get_state_dir(args):
    d = Path(getattr(args, "state_dir", "state"))
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_cert_id_cache_file(args):
    return get_state_dir(args) / "seen_cert_ids.txt"

def update_domain_analysis(domain_name, not_before, not_after):
    if not domain_name: return
    
    if isinstance(not_before, str):
        try:
            not_before = datetime.datetime.fromisoformat(not_before.replace("Z", "+00:00"))
        except:
            not_before = None
    elif isinstance(not_before, datetime.datetime) and not_before.tzinfo is None:
        not_before = not_before.replace(tzinfo=datetime.timezone.utc)
            
    if isinstance(not_after, str):
        try:
            not_after = datetime.datetime.fromisoformat(not_after.replace("Z", "+00:00"))
        except:
            not_after = None
    elif isinstance(not_after, datetime.datetime) and not_after.tzinfo is None:
        not_after = not_after.replace(tzinfo=datetime.timezone.utc)

    if domain_name not in DOMAIN_ANALYSIS:
        DOMAIN_ANALYSIS[domain_name] = {'first_seen': not_before, 'last_seen': not_after, 'level': domain_name.count(".")}
    else:
        current = DOMAIN_ANALYSIS[domain_name]
        if not_before and (not current['first_seen'] or not_before < current['first_seen']):
            current['first_seen'] = not_before
        if not_after and (not current['last_seen'] or not_after > current['last_seen']):
            current['last_seen'] = not_after
PSL = PublicSuffixList() if PublicSuffixList else None
_PSL_WARNING_SHOWN = False

DB_CONFIG = {
    "dbname": "certwatch",
    "user": "guest",
    "password": "",
    "host": "crt.sh",
    "port": "5432",
    "sslmode": "disable",
    "connect_timeout": 60,
    "keepalives": 1,
    "keepalives_idle": 60,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}


def build_connection():
    if not psycopg2:
        raise SystemExit("Missing dependency: psycopg2. Install it with 'pip install psycopg2-binary'.")
    return psycopg2.connect(**DB_CONFIG)


def get_subdomains_by_keyword_db(keyword, args):
    if not psycopg2:
        print("Error: psycopg2 is not installed. Please install it to use --use-db.")
        return set()

    subdomains = set()
    pattern = f"%{keyword}%"
    
    query = """
        SELECT cai.CERTIFICATE_ID, cai.NAME_VALUE AS dominio, x509_notBefore(cai.CERTIFICATE) AS NOT_BEFORE, x509_notAfter(cai.CERTIFICATE) AS NOT_AFTER, ca.NAME AS ISSUER_NAME
        FROM certificate_and_identities cai
        LEFT JOIN ca ON cai.ISSUER_CA_ID = ca.ID
        WHERE plainto_tsquery('certwatch', %s) @@ identities(cai.CERTIFICATE)
          AND (cai.NAME_VALUE ILIKE %s OR cai.NAME_VALUE = %s)
        LIMIT %s;
    """
    known_ids = load_seen_cert_ids(args) if getattr(args, "uncached", False) else set()
    processed_ids = set(known_ids)

    
    retries = 5
    for attempt in range(1, retries + 1):
        conn = None
        cursor = None
        try:
            print(f"--- [DB Query Attempt {attempt}/{retries}] querying keyword {keyword} ---")
            conn = build_connection()
            conn.autocommit = True
            cursor = conn.cursor()
            limit_val = getattr(args, "db_limit", 30000)
            cursor.execute(query, (keyword, pattern, keyword, limit_val))
            records = cursor.fetchall()
            
            count_before = len(subdomains)
            for record in records:
                cert_id = str(record[0])
                name_value = record[1]
                not_before = record[2]
                not_after = record[3]
                issuer_name = record[4]
                
                if getattr(args, "uncached", False) and cert_id in known_ids:
                    continue

                processed_ids.add(cert_id)
                
                ALL_CERTS_JSON.append({
                    "name_value": name_value,
                    "not_before": not_before,
                    "not_after": not_after,
                    "issuer_name": issuer_name
                })
                
                if name_value:
                    for candidate in str(name_value).splitlines():
                        norm = normalize_domain(candidate)
                        if norm:
                            update_domain_analysis(norm, not_before, not_after)
                            subdomains.add(norm)
            
            new_count = len(subdomains) - count_before
            if new_count > 0:
                print(f"New domains found via DB: {new_count}. Total: {len(subdomains)}")
                
            if getattr(args, "uncached", False):
                save_seen_cert_ids(args, processed_ids)
                
            return subdomains
            
        except Exception as exc:
            error_msg = str(exc).splitlines()[0] if str(exc) else "Unknown error"
            print(f"   [Fallo Intento {attempt}] {error_msg}")
            if attempt < retries:
                time.sleep(random.randint(15, 30))
            else:
                print("   [DB Query] Capacidad agotada.")
                return subdomains
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
                
    return subdomains


def get_subdomains_db(domain, args, extended=None):
    """Extract domain names by querying the crt.sh PostgreSQL DB directly."""
    if not psycopg2:
        print("Error: psycopg2 is not installed. Please install it to use --use-db.")
        return set()

    if getattr(args, "exclude_expired", False):
        print("Warning: --exclude_expired is not supported with --use-db yet. Returning all certificates.")

    subdomains = set()
    known_ids = load_seen_cert_ids(args) if getattr(args, "uncached", False) else set()
    processed_ids = set(known_ids)
    private_suffix = get_domain_private_suffix(domain) if extended else ""
    
    query_domain = private_suffix if extended else domain
    if not query_domain:
        query_domain = domain

    pattern = f"%.{query_domain}"
    
    limit_val = getattr(args, "db_limit", 30000)
    
    if getattr(args, "levels", None) is not None:
        points_base = query_domain.count(".")
        points_max = points_base + args.levels
        query = """
            SELECT cai.CERTIFICATE_ID, cai.NAME_VALUE AS dominio, x509_notBefore(cai.CERTIFICATE) AS NOT_BEFORE, x509_notAfter(cai.CERTIFICATE) AS NOT_AFTER, ca.NAME AS ISSUER_NAME
            FROM certificate_and_identities cai
            LEFT JOIN ca ON cai.ISSUER_CA_ID = ca.ID
            WHERE plainto_tsquery('certwatch', %s) @@ identities(cai.CERTIFICATE)
              AND (cai.NAME_VALUE ILIKE %s OR cai.NAME_VALUE = %s)
              AND (LENGTH(cai.NAME_VALUE) - LENGTH(REPLACE(cai.NAME_VALUE, '.', ''))) <= %s
            LIMIT %s;
        """
        query_params = (query_domain, pattern, query_domain, points_max, limit_val)
    else:
        query = """
            SELECT cai.CERTIFICATE_ID, cai.NAME_VALUE AS dominio, x509_notBefore(cai.CERTIFICATE) AS NOT_BEFORE, x509_notAfter(cai.CERTIFICATE) AS NOT_AFTER, ca.NAME AS ISSUER_NAME
            FROM certificate_and_identities cai
            LEFT JOIN ca ON cai.ISSUER_CA_ID = ca.ID
            WHERE plainto_tsquery('certwatch', %s) @@ identities(cai.CERTIFICATE)
              AND (cai.NAME_VALUE ILIKE %s OR cai.NAME_VALUE = %s)
            LIMIT %s;
        """
        query_params = (query_domain, pattern, query_domain, limit_val)

    retries = 5
    for attempt in range(1, retries + 1):
        conn = None
        cursor = None
        try:
            print(f"--- [DB Query Attempt {attempt}/{retries}] querying {query_domain} ---")
            conn = build_connection()
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(query, query_params)
            records = cursor.fetchall()
            
            count_before = len(subdomains)
            for record in records:
                cert_id = str(record[0])
                name_value = record[1]
                not_before = record[2]
                not_after = record[3]
                issuer_name = record[4]
                
                if getattr(args, "uncached", False) and cert_id in known_ids:
                    continue

                processed_ids.add(cert_id)
                
                ALL_CERTS_JSON.append({
                    "name_value": name_value,
                    "not_before": not_before,
                    "not_after": not_after,
                    "issuer_name": issuer_name
                })
                
                if name_value:
                    for candidate in str(name_value).splitlines():
                        norm = normalize_domain(candidate)
                        if norm:
                            if not extended or matches_private_suffix(norm, private_suffix):
                                update_domain_analysis(norm, not_before, not_after)
                                subdomains.add(norm)
            
            new_count = len(subdomains) - count_before
            if new_count > 0:
                print(f"New domains found via DB: {new_count}. Total: {len(subdomains)}")
                
            if getattr(args, "uncached", False):
                save_seen_cert_ids(args, processed_ids)
                
            return subdomains
            
        except Exception as exc:
            error_msg = str(exc).splitlines()[0] if str(exc) else "Unknown error"
            print(f"   [Fallo Intento {attempt}] {error_msg}")
            if attempt < retries:
                time.sleep(random.randint(15, 30))
            else:
                print("   [DB Query] Capacidad agotada.")
                return subdomains
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
                
    return subdomains


import re

def normalize_domain(value):
    """Normalize DNS names found in certificates."""
    if not value:
        return ""
    value = value.strip().lower()
    if value.startswith("*."):
        value = value[2:]
    value = value.strip(".")
    
    # Check for invalid characters (only allow alphanumeric, dash, dot, and asterisk)
    if not re.match(r'^[a-z0-9\.\-\*]+$', value):
        return ""
        
    return value


def load_seen_cert_ids(args):
    """Load cached certificate IDs used by --uncached mode."""
    cache_file = get_cert_id_cache_file(args)
    if not cache_file.exists():
        return set()

    try:
        return {line.strip() for line in cache_file.read_text(encoding="utf-8").splitlines() if line.strip()}
    except OSError:
        return set()


def save_seen_cert_ids(args, seen_ids):
    """Persist processed certificate IDs for --uncached mode."""
    cache_file = get_cert_id_cache_file(args)
    try:
        cache_file.write_text("\n".join(str(cert_id) for cert_id in sorted(seen_ids)) + "\n", encoding="utf-8")
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
        ALL_CERTS_JSON.extend(certs)
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
    pem_file = get_state_dir(args) / f"{cert_id}.pem"
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


def get_subdomains_by_keyword(keyword, args):
    if getattr(args, "use_db", False):
        return get_subdomains_by_keyword_db(keyword, args)

    subdomains = set()
    count = 0
    known_ids = load_seen_cert_ids(args) if args.uncached else set()
    processed_ids = set(known_ids)

    r_params = {"output": "json", "q": f"%{keyword}%"}
    if getattr(args, "exclude_expired", False):
        r_params["exclude"] = "expired"

    headers = {"User-Agent": USER_AGENT}

    try:
        req = requests.get(CRTSH_BASE_URL, params=r_params, headers=headers, timeout=REQUEST_TIMEOUT)
        print(req.url)
        req.raise_for_status()
        certs = req.json()
        ALL_CERTS_JSON.extend(certs)
    except requests.RequestException as err:
        print(f"Error retrieving certificates: {err}")
        return subdomains
    except ValueError:
        print("Error decoding crt.sh JSON response.")
        return subdomains

    dedup = {}
    for cert in certs:
        cert_id = cert.get("min_cert_id") or cert.get("id")
        if cert_id is not None and cert_id not in dedup:
            dedup[cert_id] = cert

    for entry in dedup.values():
        cert_id = str(entry.get("min_cert_id") or entry.get("id"))
        if args.uncached and cert_id in known_ids:
            continue

        processed_ids.add(cert_id)
        for subject in iter_domains_from_entry(entry):
            update_domain_analysis(subject, entry.get("not_before"), entry.get("not_after"))
            subdomains.add(subject)

        new_count = len(subdomains) - count
        if new_count > 0:
            print(f"New domains found: {new_count}.  Total: {count + new_count}")
        count = len(subdomains)

    if args.uncached:
        save_seen_cert_ids(args, processed_ids)

    return subdomains


def get_subdomains(domain, args, extended=None):
    """Extract domain names from certificate SAN/CN fields."""
    if extended is None:
        extended = args.extended

    if getattr(args, "use_db", False):
        return get_subdomains_db(domain, args, extended)

    subdomains = set()
    count = 0
    private_suffix = get_domain_private_suffix(domain) if extended else ""
    known_ids = load_seen_cert_ids(args) if args.uncached else set()
    processed_ids = set(known_ids)

    levels_max = None
    if getattr(args, "levels", None) is not None:
        query_domain = private_suffix if extended else domain
        if not query_domain:
            query_domain = domain
        levels_max = query_domain.count(".") + args.levels

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
                if levels_max is not None and subject.count(".") > levels_max:
                    continue
                update_domain_analysis(subject, entry.get("not_before"), entry.get("not_after"))
                subdomains.add(subject)

        new_count = len(subdomains) - count
        if new_count > 0:
            print(f"New domains found: {new_count}.  Total: {count + new_count}")
        count = len(subdomains)

    if args.uncached:
        save_seen_cert_ids(args, processed_ids)

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

def save_analysis_csv(analysis_data, csv_path):
    output_path = Path(csv_path)
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["domain", "level", "first_seen", "last_seen", "is_active"])
        for domain, data in sorted(analysis_data.items()):
            fs = data['first_seen'].date().isoformat() if data['first_seen'] else ""
            ls = data['last_seen'].date().isoformat() if data['last_seen'] else ""
            active = "Vigente" if data['last_seen'] and data['last_seen'] > now else "Expirado"
            writer.writerow([domain, data['level'], fs, ls, active])

    return output_path

def save_jsonl(data, jsonl_path):
    output_path = Path(jsonl_path)
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, default=str) + "\n")


def main(args):
    print(
        "Domain: %s, Keyword: %s, Extended: %s, Levels: %s, Exclude Expired: %s, Uncached: %s, Use DB: %s"
        % (args.domain, args.keyword, args.extended, args.levels, args.exclude_expired, args.uncached, getattr(args, "use_db", False))
    )

    all_domains = set()
    
    if args.domain:
        for domain in args.domain:
            if args.extended:
                results = get_subdomains(domain, args, extended=False).union(get_subdomains(domain, args))
            else:
                results = get_subdomains(domain, args, extended=False)
            all_domains.update(results)
            print(results)
            
    if args.keyword:
        for keyword in args.keyword:
            results = get_subdomains_by_keyword(keyword, args)
            all_domains.update(results)
            print(results)

    if args.csv:
        output_path = save_domains_csv(all_domains, args.csv)
        print(f"CSV saved to: {output_path} ({len(all_domains)} domains)")
        
    if getattr(args, "jsonl", None):
        output_path = save_jsonl(ALL_CERTS_JSON, args.jsonl)
        print(f"JSONL saved to: {args.jsonl} ({len(ALL_CERTS_JSON)} cert records)")
        
    if getattr(args, "analyze_csv", None):
        output_path = save_analysis_csv(DOMAIN_ANALYSIS, args.analyze_csv)
        print(f"Analysis CSV saved to: {output_path} ({len(DOMAIN_ANALYSIS)} domains)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover domains using crt.sh.")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--domain",
        "-d",
        metavar="N",
        type=str,
        nargs="+",
        help="crt.sh domain query. Specify multiple using --domain <domain>",
    )
    group.add_argument(
        "--keyword",
        "-k",
        metavar="K",
        type=str,
        nargs="+",
        help="crt.sh keyword query (e.g., 'bolivia'). Specify multiple using --keyword <keyword>",
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
    parser.add_argument(
        "--use-db",
        required=False,
        default=False,
        action="store_true",
        help="Query the crt.sh PostgreSQL database directly instead of the HTTP API.",
    )
    parser.add_argument(
        "--db-limit",
        required=False,
        type=int,
        default=30000,
        help="Maximum number of records to retrieve when using --use-db.",
    )
    parser.add_argument(
        "--levels",
        required=False,
        type=int,
        default=None,
        help="Extra subdomain levels to allow when querying by domain (e.g. 1, 2).",
    )
    parser.add_argument(
        "--jsonl",
        required=False,
        default=None,
        metavar="FILE",
        type=str,
        help="Save raw certificate JSON data to file as JSON Lines (JSONL).",
    )
    parser.add_argument(
        "--analyze-csv",
        required=False,
        default=None,
        metavar="FILE",
        type=str,
        help="Save subdomain analysis (first seen, last seen, status, level) to CSV.",
    )
    parser.add_argument(
        "--state-dir",
        required=False,
        default="state",
        metavar="DIR",
        type=str,
        help="Directory to save state (seen certs cache). Default: state",
    )
    parser.set_defaults(func=main)

    try:
        args = parser.parse_args()
        args.func(args)
    except Exception as err:
        print(err)
        parser.print_help()
