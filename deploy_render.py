#!/usr/bin/env python3
"""
Script para deploy no Render Free Tier.
Conecta ao banco PostgreSQL remoto do Render e executa:
1. Migrations (migrate.py)
2. Importação de CSVs (import_csv.py)

Uso:
    # Exportar a connection string do Render (External Database URL)
    export DATABASE_URL="postgres://user:pass@host:port/dbname"

    # Rodar o script
    pipenv run python deploy_render.py
"""
import os
import sys
import subprocess
from urllib.parse import urlparse

def parse_database_url(url: str) -> dict:
    """Converte DATABASE_URL para variáveis individuais."""
    parsed = urlparse(url)
    return {
        "DB_HOST": parsed.hostname,
        "DB_PORT": str(parsed.port or 5432),
        "DB_NAME": parsed.path.lstrip("/"),
        "DB_USER": parsed.username,
        "DB_PASSWORD": parsed.password,
    }

def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("=" * 60)
        print("ERRO: DATABASE_URL não configurada!")
        print("=" * 60)
        print()
        print("Passos para obter a URL do banco no Render:")
        print()
        print("1. Acesse https://dashboard.render.com")
        print("2. Vá em 'Databases' → seu banco PostgreSQL")
        print("3. Copie 'External Database URL'")
        print("4. Execute:")
        print()
        print('   export DATABASE_URL="postgres://..."')
        print("   pipenv run python deploy_render.py")
        print()
        sys.exit(1)

    # Parse e exporta variáveis
    db_vars = parse_database_url(database_url)
    os.environ.update(db_vars)

    print("=" * 60)
    print("Deploy para Render - Plano Free")
    print("=" * 60)
    print(f"Host: {db_vars['DB_HOST']}")
    print(f"Database: {db_vars['DB_NAME']}")
    print(f"User: {db_vars['DB_USER']}")
    print()

    # 1. Rodar migrations
    print("[1/2] Executando migrations...")
    result = subprocess.run([sys.executable, "migrate.py"], env=os.environ)
    if result.returncode != 0:
        print("ERRO nas migrations!")
        sys.exit(1)
    print()

    # 2. Importar CSVs
    print("[2/2] Importando CSVs...")
    result = subprocess.run([sys.executable, "import_csv.py"], env=os.environ)
    if result.returncode != 0:
        print("ERRO na importação!")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Deploy concluído com sucesso!")
    print("=" * 60)
    print()
    print("Próximo passo: Configure o Metabase no Render")
    print("URL do seu banco (para configurar no Metabase):")
    print(f"  Host: {db_vars['DB_HOST']}")
    print(f"  Port: {db_vars['DB_PORT']}")
    print(f"  Database: {db_vars['DB_NAME']}")
    print(f"  User: {db_vars['DB_USER']}")
    print()

if __name__ == "__main__":
    main()
