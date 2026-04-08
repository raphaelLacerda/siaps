#!/usr/bin/env python3
"""
Migration runner minimalista — substitui o Flyway.
Lê arquivos V<N>__*.sql de db/migrations/ em ordem e aplica ao banco.
Rastreia migrations aplicadas na tabela schema_migrations.
"""
import os
import re
import psycopg2
from pathlib import Path

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "siaps"),
    "user": os.getenv("DB_USER", "alyne"),
    "password": os.getenv("DB_PASSWORD", "alyne123"),
}

MIGRATIONS_DIR = Path(__file__).parent / "db" / "migrations"


def ensure_migrations_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     INTEGER PRIMARY KEY,
                filename    VARCHAR(255) NOT NULL,
                applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def get_applied_versions(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def run_migrations():
    print("Conectando ao banco de dados...")
    conn = psycopg2.connect(**DB_CONFIG)
    ensure_migrations_table(conn)
    applied = get_applied_versions(conn)

    sql_files = sorted(
        MIGRATIONS_DIR.glob("V*.sql"),
        key=lambda f: int(re.match(r"V(\d+)__", f.name).group(1))
    )

    if not sql_files:
        print("Nenhum arquivo de migration encontrado.")
        conn.close()
        return

    for sql_file in sql_files:
        match = re.match(r"V(\d+)__", sql_file.name)
        if not match:
            continue
        version = int(match.group(1))

        if version in applied:
            print(f"  [skip] {sql_file.name} (já aplicada)")
            continue

        print(f"  [apply] {sql_file.name}...")
        sql = sql_file.read_text()
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                (version, sql_file.name),
            )
        conn.commit()
        print(f"  [ok] {sql_file.name}")

    conn.close()
    print("Migrations concluídas.")


if __name__ == "__main__":
    run_migrations()
