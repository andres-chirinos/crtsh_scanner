# Whois NIC.BO Script (`whois_bo.py`)

## Descripción
Este script se conecta al sitio web oficial del registro boliviano `nic.bo` y mediante *scraping* extrae información sobre los dominios y subdominios registrados bajo terminaciones bolivianas (`.bo`, `.com.bo`, `.edu.bo`, etc.). Esta herramienta es clave para encontrar a quién pertenece un dominio y validar la existencia de infraestructuras web en Bolivia.

## Uso
```bash
./scripts/whois_bo.py --target <DOMINIO_RAIZ>
```

## Argumentos
- `--target` (Requerido): Una o múltiples palabras raíz a buscar en nic.bo (ej. `umsa` buscará en `umsa.bo`, `umsa.edu.bo`, etc).
- `--file` (Opcional): Archivo de texto con lista de objetivos.

## Esquema CSV
Genera múltiples filas por objetivo (una por cada dominio/subdominio descubierto). Las columnas estándar generadas son:
- `timestamp`: Fecha ISO de la petición.
- `action`: `whois_bo`.
- `target`: La palabra raíz consultada.
- `ok`: `True` si la búsqueda tuvo éxito.
- `status`: Código HTTP o de estado (ej. 200).
- `error`: Mensaje de error, si existe.

Además, crea dinámicamente columnas con prefijo `whois_` para cada detalle recuperado:
- `whois_dominio`: Nombre del subdominio en nic.bo (ej. `umsa.bo`).
- `whois_estado`: Estado del dominio (ej. `Registrado`).
- `whois_precio`: Costo asociado al dominio (si aplica).
- `whois_detalles_General_Titular`: Nombre del propietario.
- `whois_detalles_General_Fecha de Registro`: Fecha de registro en nic.bo.
- `whois_detalles_Contacto...`: Datos de contacto aplanados si están disponibles.
