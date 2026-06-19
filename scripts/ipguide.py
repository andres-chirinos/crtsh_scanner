#!/usr/bin/env python3
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from toolkit_utils import fail, now_iso, get_targets, print_csv

def lookup_ipguide(query: str):
    safe_query = query.strip()
    if not safe_query:
        return {"ok": False, "error": "El parametro target/query es requerido"}

    req = Request(
        url=f"https://ip.guide/{safe_query}",
        headers={"accept": "application/json", "user-agent": "ipguide-toolkit/0.1"},
    )

    try:
        with urlopen(req, timeout=12) as response:
            raw = response.read().decode("utf-8")
            content_type = response.getheader("Content-Type", "")
            
            if "application/json" in content_type or raw.strip().startswith("{"):
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = raw
            else:
                data = raw
                
            return {"ok": True, "status_code": response.status, "data": data}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status_code": exc.code, "error": body}
    except URLError as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}

def main():
    parser = argparse.ArgumentParser(description="IP Guide lookup")
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    results = []
    for t in targets:
        out = lookup_ipguide(t)
        payload = {
            "timestamp": now_iso(),
            "action": "ipguide",
            "target": t,
            "ok": out.get("ok", False),
            "status": out.get("status_code", ""),
            "error": out.get("error", "")
        }
        if payload["ok"]:
            data = out.get("data", "")
            if isinstance(data, dict):
                from toolkit_utils import flatten_json
                flat = flatten_json(data, prefix="ipg_")
                payload.update(flat)
            else:
                payload["ipg_raw_data"] = data
        results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
