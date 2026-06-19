# Traceroute Script (`traceroute.py`)

## Descripción
Este script mapea la ruta que toman los paquetes en la red para llegar a un servidor objetivo utilizando el comando del sistema `traceroute` (o como segunda alternativa, `tracepath` si el primero no está instalado).

## Uso
```bash
./scripts/traceroute.py --target <IP_O_DOMINIO> [--max-hops N]
```

## Argumentos
- `--target` (Requerido): La dirección IP o dominio de destino.
- `--max-hops` (Opcional): Número máximo de saltos (hops) permitidos para llegar al destino. Por defecto es `20`. Debe estar entre `1` y `64`.

## Ejemplo de salida
Devuelve un JSON con los detalles de los diferentes saltos o nodos de la red intermedios reportados por el subproceso, junto con sus tiempos de respuesta.

## Esquema CSV
Genera una sola fila por objetivo. Contiene las columnas estándar y agrega:
- `raw_output`: El texto íntegro (`stdout`) del comando traceroute, listando todos los saltos de red, IPs intermedias y tiempos de respuesta hasta llegar al objetivo.

## Esquema CSV
Genera una sola fila por objetivo. Contiene las columnas estándar y agrega:
- `raw_output`: El texto íntegro (`stdout`) del comando traceroute, listando todos los saltos de red, IPs intermedias y tiempos de respuesta hasta llegar al objetivo.
