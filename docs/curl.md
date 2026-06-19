# Curl Script (`curl.py`)

## Descripción
Este script actúa como un envoltorio simplificado para el comando del sistema `curl`. Realiza solicitudes web directas a los objetivos indicados, ideal para probar que una URL o endpoint responda y capturar su salida en crudo o los códigos de estado dentro de nuestra infraestructura estandarizada.

## Uso
```bash
./scripts/curl.py --target <URL>
```

## Argumentos
- `--target` (Requerido): Una o múltiples URLs u objetivos a los que se enviará la petición (ej. `http://example.com`).
- `--file` (Opcional): Un archivo de texto con un listado de URLs a consultar (una por línea).

## Ejemplo de salida
Devuelve un CSV estandarizado (compatible con el resto de la suite de red) que incluye una columna `raw_output` con el contenido del cuerpo de la respuesta o mensaje de error HTTP si no fuera accesible.
