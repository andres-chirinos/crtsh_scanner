#!/usr/bin/env python3
import argparse
from toolkit_utils import fail, now_iso, validate_host_target, ensure_command, run_command, get_targets, print_csv

def run_ping(target: str, count: int):
    try:
        host = validate_host_target(target)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    ensure_command("ping")
    cmd = ["ping", "-c", str(count), host]
    result = run_command(cmd, timeout=max(8, count * 4))
    
    if result["ok"]:
        stdout = result["stdout"]
        import re
        match = re.search(r"rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms", stdout)
        if match:
            return {
                "ok": True,
                "ping_min": match.group(1),
                "ping_avg": match.group(2),
                "ping_max": match.group(3),
                "ping_mdev": match.group(4)
            }
        else:
            return {"ok": False, "error": "100% packet loss o no responde a ping"}
    else:
        return {"ok": False, "error": result["stderr"] or "100% packet loss"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    if args.count < 1 or args.count > 20:
        fail("count debe estar entre 1 y 20")

    results = []
    for t in targets:
        out = run_ping(t, args.count)
        ok = out.get("ok", False)
        
        payload = {
            "timestamp": now_iso(),
            "action": "ping",
            "target": t,
            "ok": ok,
            "status": "0" if ok else "1",
            "error": out.get("error", "") if not ok else ""
        }
        if ok:
            payload.update({
                "ping_avg": out.get("ping_avg"),
                "ping_max": out.get("ping_max"),
                "ping_min": out.get("ping_min"),
                "ping_mdev": out.get("ping_mdev")
            })
            
        results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
