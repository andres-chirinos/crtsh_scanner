import ipaddress
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z0-9-]{1,63}(?<!-)$"
)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def fail(message: str, code: int = 1) -> None:
    payload = {
        "ok": False,
        "error": message,
        "timestamp": now_iso(),
    }
    print(json.dumps(payload, ensure_ascii=True))
    sys.exit(code)

def validate_host_target(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("El target es requerido")

    if value.startswith(("http://", "https://")):
        raise ValueError("Usa solo host/IP, no URL completa")

    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass

    # Permitir ASNs y rangos CIDR para ipguide y otros, o dejar que la herramienta falle naturalmente
    if re.match(r"^AS\d+$", value, re.IGNORECASE):
        return value

    if not DOMAIN_PATTERN.match(value):
        raise ValueError("Target invalido")

    return value

def ensure_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        fail(f"No se encontro el comando requerido: {name}")
    return path

def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": "Tiempo de espera agotado",
        }

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }

def get_targets(args) -> list[str]:
    targets = []
    if getattr(args, "target", None):
        targets.extend(args.target)
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as f:
            targets.extend([line.strip() for line in f if line.strip()])
    return targets

def flatten_json(y, prefix=''):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '_')
        elif isinstance(x, list):
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x
    flatten(y, prefix)
    return out

def print_csv(results: list[dict]):
    import csv
    if not results:
        return
        
    keys = []
    for r in results:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
                
    writer = csv.DictWriter(sys.stdout, fieldnames=keys)
    writer.writeheader()
    for res in results:
        writer.writerow(res)
