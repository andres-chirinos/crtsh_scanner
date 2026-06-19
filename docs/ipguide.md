# IP Guide Script (`ipguide.py`)

## Descripción
Este script se conecta a la API de `ip.guide` para obtener información detallada de red. Soporta direcciones IPv4, IPv6, rangos CIDR (ej: `2800:cd0::/32`), Sistemas Autónomos (ASN, ej: `AS6568`), y descargas masivas en CSV (ej: `bulk/asns.csv`). Devuelve información geográfica, datos del ASN y rutas asociadas.

## Uso
```bash
./scripts/ipguide.py --target <IP | DOMINIO | CIDR | ASN | bulk/...>
```

## Argumentos
- `--target` (Requerido): El objetivo a consultar. Puede ser una IP, dominio, bloque CIDR, ASN, o un endpoint de bulk.

## Ejemplo de salida
Devuelve un JSON con el resultado de la acción, el objetivo y los datos obtenidos de la API, incluyendo el código de estado HTTP o cualquier error de conexión en caso de que ocurra.

## Esquema CSV
El CSV generado contiene las columnas estándar (, , , , , ) y aplana todo el JSON de ip.guide dinámicamente creando columnas con el prefijo `ipg_`:
- `ipg_ip`: La IP consultada o resuelta.
- `ipg_network_cidr`: Bloque CIDR.
- `ipg_network_autonomous_system_asn`: El número ASN (ej. 6568).
- `ipg_location_country`: País (ej. Bolivia).
- `ipg_location_city`: Ciudad.

## Esquema CSV
El CSV generado contiene las columnas estándar (`timestamp`, `action`, `target`, `ok`, `status`, `error`) y aplana todo el JSON de ip.guide dinámicamente creando columnas con el prefijo `ipg_`:
- `ipg_ip`: La IP consultada o resuelta.
- `ipg_network_cidr`: Bloque CIDR.
- `ipg_network_autonomous_system_asn`: El número ASN (ej. 6568).
- `ipg_location_country`: País (ej. Bolivia).
- `ipg_location_city`: Ciudad.
