# Dig Script (`dig.py`)

## Descripción
Este script efectúa una consulta completa al sistema de nombres de dominio utilizando el comando del sistema `dig`. Es ideal para cuando se necesita todo el nivel de detalle y verbosidad (como tiempos de TTL o servidores autoritativos) que ofrece el protocolo DNS.

## Uso
```bash
./scripts/dig.py --target <DOMINIO> [--record-type TIPO]
```

## Argumentos
- `--target` (Requerido): El dominio a consultar.
- `--record-type` (Opcional): El tipo de registro DNS que se solicita. Valores permitidos: `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `SOA`, `PTR`. Por defecto es `A`.

## Ejemplo de salida
Devuelve un JSON con la salida exhaustiva (`stdout`) del comando `dig`, incluyendo las secciones de "QUESTION SECTION", "ANSWER SECTION", "AUTHORITY SECTION" y los metadatos de los tiempos de petición del servidor.

## Esquema CSV
Genera una sola fila por objetivo. Contiene las columnas estándar y agrega:
- `raw_output`: Todo el texto exhaustivo de la respuesta del protocolo DNS (Sección QUESTION, ANSWER, tiempos de TTL, servidores DNS autoritativos, etc).

## Esquema CSV
Genera una sola fila por objetivo. Contiene las columnas estándar y agrega:
- `raw_output`: Todo el texto exhaustivo de la respuesta del protocolo DNS (Sección QUESTION, ANSWER, tiempos de TTL, servidores DNS autoritativos, etc).
