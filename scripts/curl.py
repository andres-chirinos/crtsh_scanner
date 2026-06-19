#!/usr/bin/env python3
import argparse
from toolkit_utils import fail, now_iso, ensure_command, run_command, get_targets, print_csv

def run_curl(target: str):
    # No usamos validate_host_target aquí porque curl espera URLs completas a menudo
    ensure_command("curl")
    cmd = ["curl", "-sL", target]
    result = run_command(cmd, timeout=30)
    return {"ok": True, "command": " ".join(cmd), "result": result}

def main():
    parser = argparse.ArgumentParser(description="Script para hacer fetch a URLs usando curl")
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets (URLs)")
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    results = []
    for t in targets:
        out = run_curl(t)
        ok = out.get("ok", False) and out.get("result", {}).get("ok", False)
        
        payload = {
            "timestamp": now_iso(),
            "action": "curl",
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
