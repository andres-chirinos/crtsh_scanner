# Toolkit Utilities (`toolkit_utils.py`)

## Descripción
Es un submódulo interno en Python que provee funciones y utilidades comunes (DRY) para el resto de los scripts de la carpeta `scripts/`. Este archivo no está diseñado para ser ejecutado directamente en la consola.

## Funciones principales
- `fail(message, code)`: Muestra un mensaje JSON de error estructurado (`{"ok": false, ...}`) y finaliza la ejecución del script con un código de error específico.
- `validate_host_target(raw)`: Verifica que la entrada no sea una URL completa (`http://...`) y valida mediante Expresiones Regulares y la librería `ipaddress` que cumpla con el estándar RFC para direcciones IP válidas o nombres de dominio.
- `ensure_command(name)`: Comprueba si un ejecutable o binario existe en el entorno actual del sistema (p. ej. evalúa si `ping` o `dig` están instalados), y corta la ejecución controladamente si faltan.
- `run_command(command, timeout)`: Ejecuta un binario utilizando la librería interna `subprocess`, capturando su `stdout`, `stderr`, gestionando correctamente eventos de *Timeout* (tiempo de espera agotado) y encapsulando el resultado en un diccionario.
