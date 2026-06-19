# Crt.sh Script (`crtsh.py`)

## Descripción
Este script se conecta a la API web pública de `crt.sh` para obtener todos los certificados SSL/TLS emitidos asociados a un dominio. Extrae todos los nombres de subdominios únicos declarados en los certificados (`Subject Alternative Names`), siendo una herramienta potente para el reconocimiento y enumeración de infraestructuras expuestas.

## Uso
```bash
./scripts/crtsh.py --target <DOMINIO>
```

## Argumentos
- `--target` (Requerido): Uno o múltiples dominios base a investigar (ej. `google.com`).
- `--file` (Opcional): Un archivo de texto con un listado de dominios a consultar.

## Ejemplo de salida
Devuelve un CSV estandarizado con los resultados de la enumeración, añadiendo las columnas exclusivas `crt_unique_subdomains_count` y `crt_subdomains`, donde se listan todos los subdominios únicos encontrados separados por comas.

## Esquema CSV
A diferencia de otros scripts, crtsh puede generar **múltiples filas** para un solo objetivo.
Para un objetivo consultado, extraerá todos los subdominios únicos de los certificados SSL y creará una fila independiente por cada subdominio encontrado en la columna agregada:
- `crt_subdomain`: El nombre de un subdominio descubierto (ej. `mail.google.com`).
Esta separación por fila permite integrar directamente este dataset como listado de objetivos para las demás herramientas (ping, dig, curl, etc.).

## Esquema CSV
A diferencia de otros scripts, crtsh puede generar **múltiples filas** para un solo objetivo.
Para un objetivo consultado, extraerá todos los subdominios únicos de los certificados SSL y creará una fila independiente por cada subdominio encontrado en la columna agregada:
- `crt_subdomain`: El nombre de un subdominio descubierto (ej. `mail.google.com`).
Esta separación por fila permite integrar directamente este dataset como listado de objetivos para las demás herramientas (ping, dig, curl, etc.).
