import argparse
import random
import time
from pathlib import Path

import pandas as pd

try:
    import psycopg2
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: psycopg2. Install it with 'pip install -r requirements.txt'."
    ) from exc

DB_CONFIG = {
    "dbname": "certwatch",
    "user": "guest",
    "password": "",
    "host": "crt.sh",
    "port": "5432",
    "sslmode": "disable",
    "connect_timeout": 60,
    "keepalives": 1,
    "keepalives_idle": 60,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}


def build_connection():
    return psycopg2.connect(**DB_CONFIG)


def run_query(query, params):
    conn = None
    cursor = None
    try:
        conn = build_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(query, params)
        records = cursor.fetchall()
        if not records:
            return pd.DataFrame()

        col_names = [desc[0] for desc in cursor.description]
        return pd.DataFrame(records, columns=col_names)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def save_csv(df, output_path):
    output_file = Path(output_path)
    if output_file.parent and not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    return output_file


def deduplicate_domains(df, column_name="dominio"):
    if df.empty or column_name not in df.columns:
        return df
    return df.drop_duplicates(subset=[column_name])


def query_by_domain(domain, levels_extra=1, limit=30000):
    """Extract subdomains by base domain and depth."""
    points_base = domain.count(".")
    points_max = points_base + levels_extra
    pattern = f"%.{domain}"

    query = """
        SELECT cai.NAME_VALUE AS dominio
        FROM certificate_and_identities cai
        WHERE plainto_tsquery('certwatch', %s) @@ identities(cai.CERTIFICATE)
          AND (cai.NAME_VALUE ILIKE %s OR cai.NAME_VALUE = %s)
          AND (LENGTH(cai.NAME_VALUE) - LENGTH(REPLACE(cai.NAME_VALUE, '.', ''))) <= %s
        LIMIT %s;
    """

    return run_query(query, (domain, pattern, domain, points_max, limit))


def query_by_keyword(keyword, limit=30000):
    """Extract domain-like values containing a keyword anywhere in the name."""
    pattern = f"%{keyword}%"

    query = """
        SELECT cai.NAME_VALUE AS dominio
        FROM certificate_and_identities cai
        WHERE plainto_tsquery('certwatch', %s) @@ identities(cai.CERTIFICATE)
          AND (cai.NAME_VALUE ILIKE %s OR cai.NAME_VALUE = %s)
        LIMIT %s;
    """

    return run_query(query, (keyword, pattern, keyword, limit))


def retry_with_backoff(action, retries=5, min_wait=5, max_wait=12):
    for attempt in range(1, retries + 1):
        try:
            print(f"--- [INTENTO {attempt}/{retries}] Ejecutando consulta ---")
            return action()
        except Exception as exc:
            error_msg = str(exc).splitlines()[0]
            print(f"   [FALLO Intento {attempt}] {error_msg}")
            if attempt < retries:
                time.sleep(random.randint(min_wait, max_wait))
            else:
                print("   [RENDICIÓN] Capacidad agotada.")
                return pd.DataFrame()


def execute_domain_mode(args):
    print("=" * 60)
    print(
        f"Modo dominio: base={args.domain} niveles_extra={args.levels} limite={args.limit}"
    )

    df = retry_with_backoff(
        lambda: query_by_domain(
            args.domain, levels_extra=args.levels, limit=args.limit),
        retries=args.retries,
        min_wait=args.min_wait,
        max_wait=args.max_wait,
    )

    df = deduplicate_domains(df)
    if df.empty:
        print("No se encontraron registros.")
        return 1

    print(f"[RESULTADO] {len(df)} dominios únicos.")
    print(df.head(args.preview_rows))

    if args.output:
        output_file = save_csv(df, args.output)
        print(f"Datos guardados en: {output_file}")

    return 0


def execute_keyword_mode(args):
    print("=" * 60)
    print(f"Modo palabra: palabra={args.keyword} limite={args.limit}")

    df = retry_with_backoff(
        lambda: query_by_keyword(args.keyword, limit=args.limit),
        retries=args.retries,
        min_wait=args.min_wait,
        max_wait=args.max_wait,
    )

    df = deduplicate_domains(df)
    if df.empty:
        print("No se encontraron registros.")
        return 1

    print(f"[RESULTADO] {len(df)} dominios únicos.")
    print(df.head(args.preview_rows))

    if args.output:
        output_file = save_csv(df, args.output)
        print(f"Datos guardados en: {output_file}")

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extrae dominios desde crt.sh por dominio o por palabra clave."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--limit",
        type=int,
        default=30000,
        help="Número máximo de registros a recuperar.",
    )
    common.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta del CSV de salida.",
    )
    common.add_argument(
        "--retries",
        type=int,
        default=5,
        help="Cantidad de reintentos ante fallos temporales.",
    )
    common.add_argument(
        "--min-wait",
        type=int,
        default=5,
        help="Espera mínima entre reintentos.",
    )
    common.add_argument(
        "--max-wait",
        type=int,
        default=12,
        help="Espera máxima entre reintentos.",
    )
    common.add_argument(
        "--preview-rows",
        type=int,
        default=5,
        help="Cantidad de filas a mostrar por pantalla.",
    )

    domain_parser = subparsers.add_parser(
        "domain",
        parents=[common],
        help="Busca a partir de un dominio base.",
    )
    domain_parser.add_argument(
        "domain",
        type=str,
        help="Dominio base, por ejemplo gob.bo.",
    )
    domain_parser.add_argument(
        "--levels",
        type=int,
        default=1,
        help="Niveles extra permitidos sobre el dominio base.",
    )
    domain_parser.set_defaults(func=execute_domain_mode)

    keyword_parser = subparsers.add_parser(
        "keyword",
        parents=[common],
        help="Busca a partir de una palabra.",
    )
    keyword_parser.add_argument(
        "keyword",
        type=str,
        help="Palabra clave, por ejemplo bolivia.",
    )
    keyword_parser.set_defaults(func=execute_keyword_mode)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
