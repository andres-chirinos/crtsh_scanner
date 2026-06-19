# DNS Lookup Script (`dnslookup.py`)

## Descripción
Este script realiza consultas simplificadas de registros DNS para obtener respuestas rápidas. Intenta usar el comando `dig +short` y, si no se encuentra disponible en el sistema, hace un respaldo con `nslookup`.

## Uso
```bash
./scripts/dnslookup.py --target <DOMINIO> [--record-type TIPO]
```

## Argumentos
- `--target` (Requerido): El dominio o subdominio a consultar.
- `--record-type` (Opcional): El tipo de registro DNS a consultar. Valores permitidos: `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `SOA`, `PTR`. Por defecto es `A`.

## Ejemplo de salida
Devuelve un JSON con un listado limpio de los registros, ideal para extraer direcciones IP, servidores de correo (MX) u otros registros puntuales de forma automatizada (ya que suprime las cabeceras).
