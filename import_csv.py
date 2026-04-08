#!/usr/bin/env python3
"""
Script para importar CSVs do SIAPS para PostgreSQL.
Verifica quais arquivos já foram importados e importa apenas os novos.

Uso: pipenv run python import_csv.py
"""

import os
import re
import csv
import hashlib
import psycopg2
from pathlib import Path

# Configuração do banco
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "siaps"),
    "user": os.getenv("DB_USER", "alyne"),
    "password": os.getenv("DB_PASSWORD", "alyne123"),
}

CSV_DIR = Path(os.getenv("CSV_DIR", "/app/downloads/csv"))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "/app/reports"))

# Fallback para execução local
if not CSV_DIR.exists():
    CSV_DIR = Path(__file__).parent / "downloads" / "csv"
if not REPORTS_DIR.exists():
    REPORTS_DIR = Path(__file__).parent / "reports"


def get_file_hash(filepath: str) -> str:
    """Calcula SHA256 do arquivo."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def is_file_imported(conn, filename: str, file_hash: str) -> bool:
    """Verifica se arquivo já foi importado (mesmo nome e hash)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_hash FROM import_control WHERE filename = %s",
        (filename,)
    )
    result = cursor.fetchone()
    cursor.close()

    if result is None:
        return False
    return result[0] == file_hash


def register_import(conn, filename: str, file_type: str, records: int, file_hash: str):
    """Registra arquivo como importado."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO import_control (filename, file_type, records_count, file_hash)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (filename) DO UPDATE SET
            records_count = EXCLUDED.records_count,
            file_hash = EXCLUDED.file_hash,
            imported_at = CURRENT_TIMESTAMP
    """, (filename, file_type, records, file_hash))
    conn.commit()
    cursor.close()


def parse_filename(filename: str) -> dict:
    """Extrai metadados do nome do arquivo de indicadores."""
    name = filename.replace(".csv", "")
    pattern = r"^(.+?)-(.+?)-(\d{4})-(\d{2})-relatorio-competencia$"
    match = re.match(pattern, name)

    if not match:
        return None

    return {
        "tipo_equipe": match.group(1),
        "indicador": match.group(2).replace("-", " ").title(),
        "competencia": f"{match.group(3)}-{match.group(4)}-01",
    }


def parse_crescimento_filename(filename: str) -> dict:
    """Extrai metadados do nome do arquivo de crescimento."""
    name = filename.replace(".csv", "")
    pattern = r"^(.+?)-(.+?)-crescimento$"
    match = re.match(pattern, name)

    if not match:
        return None

    return {
        "tipo_equipe": match.group(1),
        "indicador": match.group(2).replace("-", " ").title(),
    }


def find_data_start(filepath: str, marker: str = "CNES;") -> int:
    """Encontra a linha onde começam os dados."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if line.startswith(marker):
                return i
    return -1


def clean_value(value: str) -> str:
    """Limpa valores do CSV."""
    return value.strip().replace("\t", "").strip('"')


def parse_number(value: str) -> float | None:
    """Converte string para número."""
    if not value:
        return None
    value = clean_value(value).replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def import_indicadores(conn, filepath: str, metadata: dict) -> int:
    """Importa arquivo de indicadores."""
    data_start = find_data_start(filepath, "CNES;")
    if data_start == -1:
        return 0

    inserted = 0
    cursor = conn.cursor()

    with open(filepath, "r", encoding="utf-8-sig") as f:
        for _ in range(data_start):
            next(f)

        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            try:
                cnes = clean_value(row.get("CNES", ""))
                if not cnes:
                    continue

                cursor.execute("""
                    INSERT INTO indicadores (
                        cnes, estabelecimento, tipo_estabelecimento, ine,
                        nome_equipe, sigla_equipe, atendimentos_programada,
                        atendimentos_total, pontuacao, indicador, competencia, tipo_equipe
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    cnes,
                    clean_value(row.get("ESTABELECIMENTO", "")),
                    clean_value(row.get("TIPO DO ESTABELECIMENTO", "")),
                    clean_value(row.get("INE", "")),
                    clean_value(row.get("NOME DA EQUIPE", "")),
                    clean_value(row.get("SIGLA DA EQUIPE", "")),
                    parse_number(row.get("NÚMERO TOTAL DE ATENDIMENTOS POR DEMANDA PROGRAMADA", "")),
                    parse_number(row.get("NÚMERO TOTAL DE ATENDIMENTOS POR TODOS OS TIPOS DE DEMANDAS (ESPONTÂNEAS E PROGRAMADAS)", "")),
                    parse_number(row.get("PONTUAÇÃO", "")),
                    metadata["indicador"],
                    metadata["competencia"],
                    metadata["tipo_equipe"],
                ))
                inserted += 1
            except Exception as e:
                print(f"  Erro ao inserir linha: {e}")

    conn.commit()
    cursor.close()
    return inserted


def extract_competencias_from_header(filepath: str) -> list:
    """Extrai competências do cabeçalho do arquivo de crescimento."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for line in f:
            if line.startswith("ESTABELECIMENTO;INE;"):
                parts = line.strip().split(";")
                return [p.replace("PONT_", "") for p in parts if p.startswith("PONT_")]
    return []


def import_crescimento(conn, filepath: str, metadata: dict) -> int:
    """Importa arquivo de crescimento."""
    data_start = find_data_start(filepath, "ESTABELECIMENTO;INE;")
    if data_start == -1:
        return 0

    competencias = extract_competencias_from_header(filepath)
    if len(competencias) < 3:
        return 0

    inserted = 0
    cursor = conn.cursor()

    with open(filepath, "r", encoding="utf-8-sig") as f:
        for _ in range(data_start):
            next(f)

        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            try:
                ine = clean_value(row.get("INE", ""))
                if not ine:
                    continue

                cursor.execute("""
                    INSERT INTO crescimento (
                        estabelecimento, ine, nome_equipe,
                        pontuacao_comp1, pontuacao_comp2, pontuacao_comp3,
                        variacao_1_2_pct, variacao_2_3_pct, crescimento_total_pct,
                        indicador, tipo_equipe,
                        competencia_1, competencia_2, competencia_3
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    clean_value(row.get("ESTABELECIMENTO", "")),
                    ine,
                    clean_value(row.get("NOME DA EQUIPE", "")),
                    parse_number(row.get(f"PONT_{competencias[0]}", "")),
                    parse_number(row.get(f"PONT_{competencias[1]}", "")),
                    parse_number(row.get(f"PONT_{competencias[2]}", "")),
                    parse_number(row.get("VAR_1_2_%", "")),
                    parse_number(row.get("VAR_2_3_%", "")),
                    parse_number(row.get("CRESCIMENTO_TOTAL_%", "")),
                    metadata["indicador"],
                    metadata["tipo_equipe"],
                    competencias[0], competencias[1], competencias[2],
                ))
                inserted += 1
            except Exception as e:
                print(f"  Erro ao inserir linha: {e}")

    conn.commit()
    cursor.close()
    return inserted


def main():
    print("Importador de CSVs SIAPS")
    print("=" * 50)

    # Conecta ao banco
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"Conectado ao PostgreSQL ({DB_CONFIG['host']}:{DB_CONFIG['port']})")
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return 1

    # Importa indicadores
    print(f"\nBuscando CSVs em {CSV_DIR}")
    if CSV_DIR.exists():
        csv_files = sorted(CSV_DIR.glob("*.csv"))
        print(f"Encontrados {len(csv_files)} arquivos de indicadores")

        imported = 0
        skipped = 0

        for csv_file in csv_files:
            metadata = parse_filename(csv_file.name)
            if not metadata:
                continue

            file_hash = get_file_hash(str(csv_file))

            if is_file_imported(conn, csv_file.name, file_hash):
                skipped += 1
                continue

            records = import_indicadores(conn, str(csv_file), metadata)
            register_import(conn, csv_file.name, "indicadores", records, file_hash)
            print(f"  + {csv_file.name}: {records} registros")
            imported += 1

        print(f"Indicadores: {imported} importados, {skipped} ja existiam")
    else:
        print(f"Pasta {CSV_DIR} nao encontrada")

    # Importa crescimento
    print(f"\nBuscando reports em {REPORTS_DIR}")
    if REPORTS_DIR.exists():
        cresc_files = sorted(REPORTS_DIR.glob("*-crescimento.csv"))
        print(f"Encontrados {len(cresc_files)} arquivos de crescimento")

        imported = 0
        skipped = 0

        for cresc_file in cresc_files:
            metadata = parse_crescimento_filename(cresc_file.name)
            if not metadata:
                continue

            file_hash = get_file_hash(str(cresc_file))

            if is_file_imported(conn, cresc_file.name, file_hash):
                skipped += 1
                continue

            records = import_crescimento(conn, str(cresc_file), metadata)
            register_import(conn, cresc_file.name, "crescimento", records, file_hash)
            print(f"  + {cresc_file.name}: {records} registros")
            imported += 1

        print(f"Crescimento: {imported} importados, {skipped} ja existiam")
    else:
        print(f"Pasta {REPORTS_DIR} nao encontrada")

    conn.close()
    print("\nImportacao concluida!")
    return 0


if __name__ == "__main__":
    exit(main())
