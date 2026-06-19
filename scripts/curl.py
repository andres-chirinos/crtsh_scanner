#!/usr/bin/env python3
import argparse
from toolkit_utils import fail, now_iso, ensure_command, run_command, get_targets, print_csv

def run_curl(target: str):
    ensure_command("curl")
    url = target if target.startswith("http") else f"http://{target}"
    cmd = [
        "curl", "-o", "/dev/null", "-s", "-w", "%{http_code},%{time_total}", 
        "-L", "--max-time", "15", url
    ]
    result = run_command(cmd, timeout=20)
    
    if result.get("ok"):
        try:
            code, time = result["stdout"].strip().split(",")
            return {"ok": True, "curl_http_code": code, "curl_latency_seconds": time}
        except Exception:
            return {"ok": False, "error": "Fallo al parsear curl output"}
    else:
        return {"ok": False, "error": result.get("stderr", "Error de red en curl")}

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
        ok = out.get("ok", False)
        
        payload = {
            "timestamp": now_iso(),
            "action": "curl",
            "target": t,
            "ok": ok,
            "status": out.get("curl_http_code", "") if ok else "",
            "error": out.get("error", "") if not ok else ""
        }
        if ok:
            payload["curl_http_code"] = out.get("curl_http_code")
            payload["curl_latency_seconds"] = out.get("curl_latency_seconds")
            
        results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
