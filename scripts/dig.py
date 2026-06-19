#!/usr/bin/env python3
import argparse
from toolkit_utils import fail, now_iso, validate_host_target, ensure_command, run_command, get_targets, print_csv

ALLOWED_DNS_TYPES = {"A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "PTR"}

def run_dig(target: str, record_type: str):
    try:
        host = validate_host_target(target)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    dns_type = record_type.upper().strip()
    if dns_type not in ALLOWED_DNS_TYPES:
        return {"ok": False, "error": "Tipo DNS no permitido"}

    ensure_command("dig")
    cmd = ["dig", "+noall", "+answer", host, dns_type]
    result = run_command(cmd, timeout=20)
    
    if result["ok"]:
        answers = []
        for line in result["stdout"].splitlines():
            parts = line.split()
            if len(parts) >= 5:
                answers.append({
                    "record_name": parts[0],
                    "ttl": parts[1],
                    "class": parts[2],
                    "type": parts[3],
                    "value": " ".join(parts[4:])
                })
        return {"ok": True, "answers": answers}
    else:
        return {"ok": False, "error": result["stderr"]}

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
        out = run_dig(t, args.record_type)
        payload = {
            "timestamp": now_iso(),
            "action": "dig",
            "target": t,
            "ok": out.get("ok", False),
            "status": "0" if out.get("ok") else "1",
            "error": out.get("error", "")
        }
        
        if payload["ok"]:
            answers = out.get("answers", [])
            if not answers:
                payload["ok"] = False
                payload["error"] = "Sin registros de respuesta"
                results.append(payload)
            else:
                for ans in answers:
                    row = payload.copy()
                    row.update({
                        "dig_record_name": ans["record_name"],
                        "dig_ttl": ans["ttl"],
                        "dig_class": ans["class"],
                        "dig_type": ans["type"],
                        "dig_value": ans["value"]
                    })
                    results.append(row)
        else:
            results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
