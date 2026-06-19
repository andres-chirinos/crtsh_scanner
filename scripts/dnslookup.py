#!/usr/bin/env python3
import argparse
import shutil
from toolkit_utils import fail, now_iso, validate_host_target, run_command, get_targets, print_csv

ALLOWED_DNS_TYPES = {"A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "PTR"}

def run_dnslookup(target: str, record_type: str):
    try:
        host = validate_host_target(target)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    dns_type = record_type.upper().strip()
    if dns_type not in ALLOWED_DNS_TYPES:
        return {"ok": False, "error": "Tipo DNS no permitido"}

    dig_bin = shutil.which("dig")
    if dig_bin:
        cmd = ["dig", "+short", host, dns_type]
    else:
        nslookup_bin = shutil.which("nslookup")
        if not nslookup_bin:
            fail("No se encontro dig ni nslookup")
        cmd = ["nslookup", f"-type={dns_type}", host]

    result = run_command(cmd, timeout=20)
    return {"ok": True, "command": " ".join(cmd), "result": result}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    parser.add_argument("--record-type", default="A")
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    results = []
    for t in targets:
        out = run_dnslookup(t, args.record_type)
        ok = out.get("ok", False) and out.get("result", {}).get("ok", False)
        
        payload = {
            "timestamp": now_iso(),
            "action": "dnslookup",
            "target": t,
            "ok": ok,
            "status": out.get("result", {}).get("returncode", ""),
            "raw_output": out.get("result", {}).get("stdout", "").strip() if ok else out.get("result", {}).get("stderr", "").strip(),
            "error": out.get("error", "") if not out.get("ok", False) else ""
        }
        results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
