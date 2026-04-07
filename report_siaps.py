#!/usr/bin/env python3
"""
Script para gerar relatórios e gráficos a partir dos dados do SIAPS
Lê configurações do arquivo equipes_indicadores.json
"""

import json
import sys
import re
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Backend para salvar arquivos sem display

# Diretório base
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
CSV_DIR = DOWNLOADS_DIR / "csv"
REPORTS_DIR = BASE_DIR / "reports"


def ensure_directories():
    """Cria diretórios se não existirem"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    """Carrega configurações do arquivo equipes_indicadores.json"""
    config_path = BASE_DIR / "equipes_indicadores.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text: str) -> str:
    """Converte texto para slug (lowercase, hífens)"""
    acentos = {
        "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "õ": "o", "ô": "o", "ö": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "ñ": "n",
        "Á": "a", "À": "a", "Ã": "a", "Â": "a", "Ä": "a",
        "É": "e", "È": "e", "Ê": "e", "Ë": "e",
        "Í": "i", "Ì": "i", "Î": "i", "Ï": "i",
        "Ó": "o", "Ò": "o", "Õ": "o", "Ô": "o", "Ö": "o",
        "Ú": "u", "Ù": "u", "Û": "u", "Ü": "u",
        "Ç": "c", "Ñ": "n",
    }
    for char, replacement in acentos.items():
        text = text.replace(char, replacement)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" ", "-")
    return text


def format_equipes_name(equipes: list) -> str:
    """Formata lista de equipes para nome do arquivo"""
    return "-".join(equipes)


def format_competencia_display(competencia: str) -> str:
    """Converte 2025-04 para ABR/25"""
    meses = {
        "01": "JAN", "02": "FEV", "03": "MAR", "04": "ABR",
        "05": "MAI", "06": "JUN", "07": "JUL", "08": "AGO",
        "09": "SET", "10": "OUT", "11": "NOV", "12": "DEZ",
    }
    parts = competencia.split("-")
    ano = parts[0][2:4]
    mes = parts[1]
    return f"{meses[mes]}/{ano}"


def read_csv_siaps(filepath: Path) -> pd.DataFrame:
    """Lê CSV do SIAPS pulando as linhas de cabeçalho"""
    # Os CSVs têm 17 linhas de cabeçalho antes dos dados
    # Linha 18 é o cabeçalho das colunas
    df = pd.read_csv(
        filepath,
        sep=";",
        encoding="utf-8-sig",
        skiprows=17,
        dtype=str
    )

    # Limpar valores (remover tabs e aspas)
    for col in df.columns:
        df[col] = df[col].str.replace('\t', '').str.replace('"', '').str.strip()

    # Converter PONTUAÇÃO para float
    # Trata formato brasileiro: "2.300,00" -> "2300.00"
    def parse_brazilian_number(val):
        if pd.isna(val) or val == "":
            return 0.0
        # Remove pontos de milhar e troca vírgula por ponto
        val = str(val).replace(".", "").replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return 0.0

    df["PONTUAÇÃO"] = df["PONTUAÇÃO"].apply(parse_brazilian_number)

    return df


def load_data_for_indicator(equipes: list, indicador: dict, competencias: list) -> dict:
    """Carrega dados de todas as competências para um indicador"""
    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    data = {}
    for comp in competencias:
        filename = f"{equipes_name}-{indicador_slug}-{comp}-relatorio-competencia.csv"
        filepath = CSV_DIR / filename

        if filepath.exists():
            df = read_csv_siaps(filepath)
            data[comp] = df
        else:
            print(f"  Aviso: Arquivo não encontrado: {filename}")

    return data


def calculate_growth(val_anterior, val_atual):
    """Calcula percentual de crescimento"""
    if val_anterior == 0:
        if val_atual == 0:
            return 0.0
        return 100.0  # Crescimento infinito -> 100%
    return ((val_atual - val_anterior) / val_anterior) * 100


def generate_report_for_indicator(equipes: list, indicador: dict, competencias: list, data: dict) -> pd.DataFrame:
    """Gera relatório consolidado para um indicador"""
    if len(data) == 0:
        return None

    # Criar DataFrame consolidado
    all_teams = set()
    for comp, df in data.items():
        teams = df[["ESTABELECIMENTO", "INE", "NOME DA EQUIPE"]].drop_duplicates()
        for _, row in teams.iterrows():
            all_teams.add((row["ESTABELECIMENTO"], row["INE"], row["NOME DA EQUIPE"]))

    rows = []
    for estabelecimento, ine, nome_equipe in all_teams:
        row = {
            "ESTABELECIMENTO": estabelecimento,
            "INE": ine,
            "NOME DA EQUIPE": nome_equipe,
        }

        # Pontuações por competência
        pontuacoes = []
        for comp in competencias:
            if comp in data:
                df = data[comp]
                match = df[(df["INE"] == ine) & (df["NOME DA EQUIPE"] == nome_equipe)]
                if not match.empty:
                    pont = match["PONTUAÇÃO"].values[0]
                else:
                    pont = 0.0
            else:
                pont = 0.0

            col_name = f"PONT_{format_competencia_display(comp).replace('/', '_')}"
            row[col_name] = pont
            pontuacoes.append(pont)

        # Calcular variações
        if len(pontuacoes) >= 2:
            var_1_2 = calculate_growth(pontuacoes[0], pontuacoes[1])
            row["VAR_1_2_%"] = var_1_2
        else:
            row["VAR_1_2_%"] = 0.0

        if len(pontuacoes) >= 3:
            var_2_3 = calculate_growth(pontuacoes[1], pontuacoes[2])
            row["VAR_2_3_%"] = var_2_3
        else:
            row["VAR_2_3_%"] = 0.0

        # Crescimento total (primeira para última)
        if len(pontuacoes) >= 2:
            total_growth = calculate_growth(pontuacoes[0], pontuacoes[-1])
            row["CRESCIMENTO_TOTAL_%"] = total_growth
        else:
            row["CRESCIMENTO_TOTAL_%"] = 0.0

        rows.append(row)

    df_report = pd.DataFrame(rows)
    return df_report


def get_top_and_bottom(df: pd.DataFrame, n: int = 5) -> tuple:
    """Retorna top N que mais cresceram e top N que menos cresceram"""
    df_sorted = df.sort_values("CRESCIMENTO_TOTAL_%", ascending=False)
    top_cresceram = df_sorted.head(n)
    menos_cresceram = df_sorted.tail(n).iloc[::-1]  # Inverter para mostrar do menor para maior
    return top_cresceram, menos_cresceram


def generate_growth_chart(equipes: list, indicador: dict, df_report: pd.DataFrame):
    """Gera gráfico de barras com crescimento de TODAS as equipes"""
    if df_report is None or df_report.empty:
        return

    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    # Ordenar por crescimento (maior para menor)
    df_sorted = df_report.sort_values("CRESCIMENTO_TOTAL_%", ascending=True)

    # Criar labels com nome + INE
    labels = [f"{row['NOME DA EQUIPE'][:30]} ({row['INE']})" for _, row in df_sorted.iterrows()]
    valores = df_sorted["CRESCIMENTO_TOTAL_%"].values

    # Cores: verde para positivo, vermelho para negativo
    colors = ['green' if v >= 0 else 'red' for v in valores]

    # Ajustar tamanho da figura baseado na quantidade de equipes
    num_equipes = len(df_sorted)
    fig_height = max(8, num_equipes * 0.4)

    fig, ax = plt.subplots(figsize=(14, fig_height))

    bars = ax.barh(labels, valores, color=colors, alpha=0.7)
    ax.set_xlabel("Crescimento Total (%)", fontsize=12)
    ax.set_ylabel("Equipe (INE)", fontsize=12)
    ax.set_title(f"Crescimento Total por Equipe - {indicador['nome']}\nEquipes: {equipes_name}", fontsize=14)
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.grid(True, axis='x', alpha=0.3)

    # Adicionar valores nas barras
    for bar, val in zip(bars, valores):
        offset = 2 if val >= 0 else -2
        ha = 'left' if val >= 0 else 'right'
        ax.text(bar.get_width() + offset, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}%', va='center', ha=ha, fontsize=8)

    plt.tight_layout()

    output_path = REPORTS_DIR / f"{equipes_name}-{indicador_slug}-crescimento.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"    Gráfico salvo: {output_path.name}")


def save_report(df: pd.DataFrame, equipes: list, indicador: dict, top_cresceram: pd.DataFrame, menos_cresceram: pd.DataFrame, competencias: list):
    """Salva relatório em CSV"""
    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    output_path = REPORTS_DIR / f"{equipes_name}-{indicador_slug}-report.csv"

    with open(output_path, "w", encoding="utf-8-sig") as f:
        # Cabeçalho
        f.write(f"RELATÓRIO DE EVOLUÇÃO - {indicador['nome']}\n")
        f.write(f"Equipes: {', '.join(equipes)}\n")
        f.write(f"Competências: {', '.join([format_competencia_display(c) for c in competencias])}\n")
        f.write("\n")

        # Resumo de variação
        f.write("=" * 50 + "\n")
        f.write("RESUMO DAS VARIAÇÕES\n")
        f.write("=" * 50 + "\n")

        comp_cols = [c for c in df.columns if c.startswith("PONT_")]
        for col in comp_cols:
            media = df[col].mean()
            f.write(f"{col.replace('PONT_', '')}: Média de pontuação = {media:.2f}\n")

        if "VAR_1_2_%" in df.columns:
            media_var1 = df["VAR_1_2_%"].mean()
            f.write(f"\n% de crescimento entre {competencias[0]} e {competencias[1]}: {media_var1:.2f}%\n")

        if "VAR_2_3_%" in df.columns:
            media_var2 = df["VAR_2_3_%"].mean()
            f.write(f"% de crescimento entre {competencias[1]} e {competencias[2]}: {media_var2:.2f}%\n")

        media_total = df["CRESCIMENTO_TOTAL_%"].mean()
        f.write(f"\nCrescimento total médio: {media_total:.2f}%\n")

        f.write("\n")
        f.write("=" * 50 + "\n")
        f.write("TOP 5 - MAIOR CRESCIMENTO\n")
        f.write("=" * 50 + "\n")
        for _, row in top_cresceram.iterrows():
            f.write(f"  {row['NOME DA EQUIPE']} (INE: {row['INE']}): {row['CRESCIMENTO_TOTAL_%']:.2f}%\n")

        f.write("\n")
        f.write("=" * 50 + "\n")
        f.write("TOP 5 - MENOR CRESCIMENTO\n")
        f.write("=" * 50 + "\n")
        for _, row in menos_cresceram.iterrows():
            f.write(f"  {row['NOME DA EQUIPE']} (INE: {row['INE']}): {row['CRESCIMENTO_TOTAL_%']:.2f}%\n")

        f.write("\n\n")
        f.write("=" * 50 + "\n")
        f.write("DADOS COMPLETOS\n")
        f.write("=" * 50 + "\n\n")

    # Append DataFrame com 2 casas decimais
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if df_formatted[col].dtype in ['float64', 'float32']:
            df_formatted[col] = df_formatted[col].round(2)
    df_formatted.to_csv(output_path, mode="a", sep=";", index=False, encoding="utf-8-sig")

    print(f"    Relatório salvo: {output_path.name}")


def get_top_and_bottom_by_score(df: pd.DataFrame, score_col: str, n: int = 5) -> tuple:
    """Retorna top N maiores notas e top N menores notas"""
    df_sorted = df.sort_values(score_col, ascending=False)
    top_notas = df_sorted.head(n)
    menores_notas = df_sorted.tail(n).iloc[::-1]
    return top_notas, menores_notas


def save_score_report(equipes: list, indicador: dict, competencias: list, data: dict):
    """Salva relatório de notas por competência"""
    if len(data) == 0:
        return

    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    output_path = REPORTS_DIR / f"{equipes_name}-{indicador_slug}-notas-competencia.csv"

    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write(f"RELATÓRIO DE NOTAS POR COMPETÊNCIA - {indicador['nome']}\n")
        f.write(f"Equipes: {', '.join(equipes)}\n")
        f.write("\n")

        for comp in competencias:
            if comp not in data:
                continue

            df = data[comp]
            comp_display = format_competencia_display(comp)

            f.write("=" * 60 + "\n")
            f.write(f"COMPETÊNCIA: {comp_display}\n")
            f.write("=" * 60 + "\n\n")

            top_notas, menores_notas = get_top_and_bottom_by_score(df, "PONTUAÇÃO")

            f.write("TOP 5 - MAIORES NOTAS\n")
            f.write("-" * 40 + "\n")
            for _, row in top_notas.iterrows():
                f.write(f"  {row['NOME DA EQUIPE']} (INE: {row['INE']}): {row['PONTUAÇÃO']:.2f}\n")

            f.write("\n")
            f.write("TOP 5 - MENORES NOTAS\n")
            f.write("-" * 40 + "\n")
            for _, row in menores_notas.iterrows():
                f.write(f"  {row['NOME DA EQUIPE']} (INE: {row['INE']}): {row['PONTUAÇÃO']:.2f}\n")

            f.write("\n\n")

    print(f"    Relatório notas salvo: {output_path.name}")


def generate_score_chart_by_competencia(equipes: list, indicador: dict, competencia: str, df: pd.DataFrame):
    """Gera gráfico de barras com pontuação de TODAS as equipes para uma competência"""
    if df is None or df.empty:
        return

    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])
    comp_display = format_competencia_display(competencia)
    comp_slug = competencia.replace("-", "")

    # Ordenar por pontuação (maior para menor, mas ascending=True para barh)
    df_sorted = df.sort_values("PONTUAÇÃO", ascending=True)

    # Criar labels com nome + INE
    labels = [f"{row['NOME DA EQUIPE'][:30]} ({row['INE']})" for _, row in df_sorted.iterrows()]
    valores = df_sorted["PONTUAÇÃO"].values

    # Cores baseadas na pontuação
    max_val = valores.max() if len(valores) > 0 else 1
    colors = plt.cm.RdYlGn([v / max_val if max_val > 0 else 0 for v in valores])

    # Ajustar tamanho da figura baseado na quantidade de equipes
    num_equipes = len(df_sorted)
    fig_height = max(8, num_equipes * 0.4)

    fig, ax = plt.subplots(figsize=(14, fig_height))

    bars = ax.barh(labels, valores, color=colors, alpha=0.8)
    ax.set_xlabel("Pontuação", fontsize=12)
    ax.set_ylabel("Equipe (INE)", fontsize=12)
    ax.set_title(f"Pontuação por Equipe - {indicador['nome']}\nCompetência: {comp_display} | Equipes: {equipes_name}", fontsize=14)
    ax.grid(True, axis='x', alpha=0.3)

    # Adicionar valores nas barras
    for bar, val in zip(bars, valores):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}', va='center', ha='left', fontsize=8)

    plt.tight_layout()

    output_path = REPORTS_DIR / f"{equipes_name}-{indicador_slug}-notas-{comp_slug}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"    Gráfico notas {comp_display} salvo: {output_path.name}")


def process_indicator(equipes: list, indicador: dict, competencias: list):
    """Processa um indicador completo"""
    print(f"\n  Processando indicador: {indicador['nome']}")

    # Carregar dados
    data = load_data_for_indicator(equipes, indicador, competencias)

    if len(data) == 0:
        print(f"    Nenhum dado encontrado para o indicador")
        return

    # Gerar relatório
    df_report = generate_report_for_indicator(equipes, indicador, competencias, data)

    if df_report is None or df_report.empty:
        print(f"    Nenhum dado para gerar relatório")
        return

    # Top e bottom
    top_cresceram, menos_cresceram = get_top_and_bottom(df_report)

    # Salvar relatório de evolução
    save_report(df_report, equipes, indicador, top_cresceram, menos_cresceram, competencias)

    # Gerar gráfico de evolução
    generate_growth_chart(equipes, indicador, df_report)

    # Salvar relatório de notas por competência
    save_score_report(equipes, indicador, competencias, data)

    # Gerar gráficos de notas por competência
    for comp in competencias:
        if comp in data:
            generate_score_chart_by_competencia(equipes, indicador, comp, data[comp])


def generate_reports(equipes_filter: list = None):
    """Gera relatórios para todos os indicadores filtrados"""
    ensure_directories()
    config = load_config()

    competencias = config.get("competencias", [])
    equipes_config = config.get("equipes", [])

    if equipes_filter:
        def grupo_matches(grupo):
            sg = {s.upper() for s in grupo.get("sgEquipes", [])}
            for group_set in equipes_filter:
                if all(e.upper() in sg for e in group_set):
                    return True
            return False

        equipes_config = [g for g in equipes_config if grupo_matches(g)]
        if not equipes_config:
            filtro_display = ', '.join('&'.join(gs) for gs in equipes_filter)
            print(f"Nenhum grupo encontrado para o filtro: {filtro_display}")
            return

    print("=" * 70)
    print("Geração de Relatórios - SIAPS")
    print("=" * 70)
    print(f"Competências: {', '.join(competencias)}")
    print(f"Grupos de equipes: {len(equipes_config)}")
    if equipes_filter:
        filtro_display = ', '.join('&'.join(gs) for gs in equipes_filter)
        print(f"Filtro de equipes: {filtro_display}")
    print(f"Saída: {REPORTS_DIR}")
    print("=" * 70)

    for grupo in equipes_config:
        equipes = grupo.get("sgEquipes", [])
        indicadores = grupo.get("indicadores", [])

        print(f"\n{'='*70}")
        print(f"EQUIPES: {', '.join(equipes)}")
        print(f"Indicadores: {len(indicadores)}")
        print(f"{'='*70}")

        for indicador in indicadores:
            process_indicator(equipes, indicador, competencias)

    print("\n" + "=" * 70)
    print("Relatórios gerados com sucesso!")
    print(f"Arquivos salvos em: {REPORTS_DIR}")
    print("=" * 70)


def main():
    equipes_filter = [arg.split('&') for arg in sys.argv[1:]] if len(sys.argv) > 1 else None
    generate_reports(equipes_filter)


if __name__ == "__main__":
    main()
