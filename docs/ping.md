# Ping Script (`ping.py`)

## Descripción
Este script ejecuta una prueba de conectividad ICMP (`ping`) contra un objetivo especificado utilizando el binario nativo del sistema operativo.

## Uso
```bash
./scripts/ping.py --target <IP_O_DOMINIO> [--count N]
```

## Argumentos
- `--target` (Requerido): La dirección IP o dominio al que se enviarán los paquetes ICMP.
- `--count` (Opcional): Número de paquetes a enviar. Por defecto es `4`. Debe estar entre `1` y `10`.

## Ejemplo de salida
Devuelve un JSON con el estado de la ejecución, código de salida, además de la salida estándar (`stdout`) que contiene las estadísticas de pérdida de paquetes y latencia, así como la salida de error (`stderr`) del comando.
