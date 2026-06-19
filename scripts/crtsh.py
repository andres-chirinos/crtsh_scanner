#!/usr/bin/env python3
import argparse
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from toolkit_utils import fail, now_iso, get_targets, print_csv

def lookup_crtsh(query: str):
    safe_query = query.strip()
    if not safe_query:
        return {"ok": False, "error": "El parametro target es requerido"}

    params = urlencode({"q": f"%.{safe_query}", "output": "json"})
    req = Request(
        url=f"https://crt.sh/?{params}",
        headers={"accept": "application/json", "user-agent": "crtsh-toolkit/0.1"}
    )

    try:
        # crt.sh es notoriamente lento a veces, así que usamos un timeout alto
        with urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            return {"ok": True, "status_code": response.status, "data": data}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status_code": exc.code, "error": body}
    except URLError as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}
    except json.JSONDecodeError:
        return {"ok": False, "status_code": 200, "error": "Respuesta no JSON"}

def main():
    parser = argparse.ArgumentParser(description="Consulta de subdominios en crt.sh")
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    results = []
    for t in targets:
        out = lookup_crtsh(t)
        payload = {
            "timestamp": now_iso(),
            "action": "crtsh",
            "target": t,
            "ok": out.get("ok", False),
            "status": out.get("status_code", ""),
            "error": out.get("error", "")
        }
        
        if payload["ok"]:
            data = out.get("data", [])
            if isinstance(data, list):
                subdomains = set()
                for cert in data:
                    name_value = cert.get("name_value", "")
                    for name in name_value.split("\n"):
                        clean_name = name.strip().lower()
                        if clean_name:
                            subdomains.add(clean_name)
                
                if not subdomains:
                    results.append(payload)
                else:
                    for sub in sorted(subdomains):
                        row = payload.copy()
                        row["crt_subdomain"] = sub
                        results.append(row)
            else:
                payload["crt_raw_data"] = json.dumps(data)
                results.append(payload)
        else:
            results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
