#!/usr/bin/env python3
import argparse
import os
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from dotenv import load_dotenv

from toolkit_utils import fail, now_iso, get_targets, print_csv, flatten_json

load_dotenv()

API_URL = 'https://openpagerank.com/api/v1.0/getPageRank'
API_KEY = os.getenv('OPEN_RANK_API_KEY', 'YOUR-API-KEY-HERE')

def lookup_openrank(query: str):
    safe_query = query.strip()
    if not safe_query:
        return {"ok": False, "error": "El parametro target es requerido"}

    params = urlencode({"domains[]": safe_query})
    req = Request(
        url=f"{API_URL}?{params}",
        headers={"API-OPR": API_KEY, "accept": "application/json"}
    )

    try:
        with urlopen(req, timeout=12) as response:
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
    parser = argparse.ArgumentParser(description="Consulta OpenPageRank")
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    results = []
    for t in targets:
        out = lookup_openrank(t)
        payload = {
            "timestamp": now_iso(),
            "action": "open_rank",
            "target": t,
            "ok": out.get("ok", False),
            "status": out.get("status_code", ""),
            "error": out.get("error", "")
        }
        if payload["ok"]:
            data = out.get("data", {})
            resp_list = data.get("response", [])
            if resp_list and isinstance(resp_list, list):
                # Extraer la metadata principal de OPR
                flat = flatten_json(resp_list[0], prefix="opr_")
                payload.update(flat)
            else:
                payload["opr_raw_data"] = json.dumps(data)
        results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
