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
    return {"ok": True, "command": " ".join(cmd), "result": result}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    if args.count < 1 or args.count > 10:
        fail("count debe estar entre 1 y 10")

    results = []
    for t in targets:
        out = run_ping(t, args.count)
        ok = out.get("ok", False) and out.get("result", {}).get("ok", False)
        
        payload = {
            "timestamp": now_iso(),
            "action": "ping",
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
