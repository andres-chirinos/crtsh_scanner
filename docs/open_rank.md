# OpenRank Script (`open_rank.py`)

## Descripción
Este script se conecta a la API de `openpagerank.com` para obtener el PageRank y métricas de popularidad de un dominio. Es fundamental para evaluar el peso o tráfico estimado de los subdominios y dominios detectados.
Nota: Se requiere tener configurada la variable de entorno `OPEN_RANK_API_KEY` (por ejemplo, mediante un archivo `.env`).

## Uso
```bash
./scripts/open_rank.py --target <DOMINIO>
```

## Argumentos
- `--target` (Requerido): Una o múltiples URLs u objetivos a los que se enviará la petición (ej. `google.com`).
- `--file` (Opcional): Un archivo de texto con un listado de dominios a consultar.

## Ejemplo de salida
Devuelve un CSV estandarizado que incluye columnas generadas de forma dinámica con el prefijo `opr_` aplanando las métricas internas devueltas por la API (ej. `opr_page_rank_integer`, `opr_rank`, etc.).

## Esquema CSV
Genera una sola fila por dominio. Contiene las columnas estándar y aplana la métrica de OpenPageRank agregando columnas con prefijo `opr_`:
- `opr_status_code`: El código HTTP que retornó el dominio al ser evaluado.
- `opr_page_rank_integer`: Puntuación entera del PageRank (0 a 10).
- `opr_rank`: Posición de popularidad global.
- `opr_error`: Mensaje si el dominio no tiene métricas disponibles.

## Esquema CSV
Genera una sola fila por dominio. Contiene las columnas estándar y aplana la métrica de OpenPageRank agregando columnas con prefijo `opr_`:
- `opr_status_code`: El código HTTP que retornó el dominio al ser evaluado.
- `opr_page_rank_integer`: Puntuación entera del PageRank (0 a 10).
- `opr_rank`: Posición de popularidad global.
- `opr_error`: Mensaje si el dominio no tiene métricas disponibles.
