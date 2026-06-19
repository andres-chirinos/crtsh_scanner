#!/usr/bin/env python3
import argparse
import shutil
from toolkit_utils import fail, now_iso, validate_host_target, run_command, get_targets, print_csv

def run_traceroute(target: str, max_hops: int):
    try:
        host = validate_host_target(target)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    traceroute_bin = shutil.which("traceroute")
    if traceroute_bin:
        cmd = ["traceroute", "-m", str(max_hops), host]
    else:
        tracepath_bin = shutil.which("tracepath")
        if not tracepath_bin:
            fail("No se encontro traceroute ni tracepath")
        cmd = ["tracepath", host]

    result = run_command(cmd, timeout=50)
    return {"ok": True, "command": " ".join(cmd), "result": result}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    parser.add_argument("--max-hops", type=int, default=20)
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    if args.max_hops < 1 or args.max_hops > 64:
        fail("max-hops debe estar entre 1 y 64")

    results = []
    for t in targets:
        out = run_traceroute(t, args.max_hops)
        ok = out.get("ok", False) and out.get("result", {}).get("ok", False)
        
        payload = {
            "timestamp": now_iso(),
            "action": "traceroute",
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
