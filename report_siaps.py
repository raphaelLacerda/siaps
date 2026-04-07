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
GRAFICOS_DIR = BASE_DIR / "graficos"


def ensure_directories():
    """Cria diretórios se não existirem"""
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)


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
    df["PONTUAÇÃO"] = df["PONTUAÇÃO"].str.replace(",", ".").astype(float)

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


def generate_line_chart(equipes: list, indicador: dict, competencias: list, data: dict):
    """Gera gráfico de linha para evolução das pontuações"""
    if len(data) == 0:
        return

    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    # Coletar todas as equipes e suas pontuações
    teams_data = {}

    for comp, df in data.items():
        for _, row in df.iterrows():
            key = (row["INE"], row["NOME DA EQUIPE"])
            if key not in teams_data:
                teams_data[key] = {"nome": row["NOME DA EQUIPE"], "pontuacoes": {}}
            teams_data[key]["pontuacoes"][comp] = row["PONTUAÇÃO"]

    # Preparar dados para o gráfico
    comp_labels = [format_competencia_display(c) for c in competencias]

    # Criar figura
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plotar cada equipe
    colors = plt.cm.tab20(np.linspace(0, 1, len(teams_data)))

    for idx, (key, team_info) in enumerate(teams_data.items()):
        ponts = [team_info["pontuacoes"].get(c, 0) for c in competencias]
        nome_curto = team_info["nome"][:30] + "..." if len(team_info["nome"]) > 30 else team_info["nome"]
        ax.plot(comp_labels, ponts, marker='o', label=nome_curto, color=colors[idx], linewidth=2)

    ax.set_xlabel("Competência", fontsize=12)
    ax.set_ylabel("Pontuação", fontsize=12)
    ax.set_title(f"Evolução da Pontuação - {indicador['nome']}\nEquipes: {equipes_name}", fontsize=14)
    ax.grid(True, alpha=0.3)

    # Legenda
    if len(teams_data) <= 15:
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    else:
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=6, ncol=2)

    plt.tight_layout()

    # Salvar
    output_path = GRAFICOS_DIR / f"{equipes_name}-{indicador_slug}-evolucao.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"    Gráfico salvo: {output_path.name}")


def generate_top_bottom_chart(equipes: list, indicador: dict, top_cresceram: pd.DataFrame, menos_cresceram: pd.DataFrame):
    """Gera gráfico de barras com top 5 que mais e menos cresceram"""
    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Top 5 que mais cresceram
    if not top_cresceram.empty:
        nomes_top = [n[:25] + "..." if len(n) > 25 else n for n in top_cresceram["NOME DA EQUIPE"]]
        valores_top = top_cresceram["CRESCIMENTO_TOTAL_%"].values
        bars1 = ax1.barh(nomes_top, valores_top, color='green', alpha=0.7)
        ax1.set_xlabel("Crescimento Total (%)")
        ax1.set_title("Top 5 - Maior Crescimento")
        ax1.invert_yaxis()
        for bar, val in zip(bars1, valores_top):
            ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f'{val:.1f}%', va='center', fontsize=9)

    # Top 5 que menos cresceram
    if not menos_cresceram.empty:
        nomes_bottom = [n[:25] + "..." if len(n) > 25 else n for n in menos_cresceram["NOME DA EQUIPE"]]
        valores_bottom = menos_cresceram["CRESCIMENTO_TOTAL_%"].values
        colors = ['red' if v < 0 else 'orange' for v in valores_bottom]
        bars2 = ax2.barh(nomes_bottom, valores_bottom, color=colors, alpha=0.7)
        ax2.set_xlabel("Crescimento Total (%)")
        ax2.set_title("Top 5 - Menor Crescimento")
        ax2.invert_yaxis()
        for bar, val in zip(bars2, valores_bottom):
            offset = 1 if val >= 0 else -5
            ax2.text(bar.get_width() + offset, bar.get_y() + bar.get_height()/2,
                    f'{val:.1f}%', va='center', fontsize=9)

    plt.suptitle(f"Análise de Crescimento - {indicador['nome']}\nEquipes: {equipes_name}", fontsize=14)
    plt.tight_layout()

    output_path = GRAFICOS_DIR / f"{equipes_name}-{indicador_slug}-top-bottom.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"    Gráfico top/bottom salvo: {output_path.name}")


def save_report(df: pd.DataFrame, equipes: list, indicador: dict, top_cresceram: pd.DataFrame, menos_cresceram: pd.DataFrame, competencias: list):
    """Salva relatório em CSV"""
    equipes_name = format_equipes_name(equipes)
    indicador_slug = slugify(indicador["nome"])

    output_path = GRAFICOS_DIR / f"{equipes_name}-{indicador_slug}-report.csv"

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
            f.write(f"  {row['NOME DA EQUIPE']}: {row['CRESCIMENTO_TOTAL_%']:.2f}%\n")

        f.write("\n")
        f.write("=" * 50 + "\n")
        f.write("TOP 5 - MENOR CRESCIMENTO\n")
        f.write("=" * 50 + "\n")
        for _, row in menos_cresceram.iterrows():
            f.write(f"  {row['NOME DA EQUIPE']}: {row['CRESCIMENTO_TOTAL_%']:.2f}%\n")

        f.write("\n\n")
        f.write("=" * 50 + "\n")
        f.write("DADOS COMPLETOS\n")
        f.write("=" * 50 + "\n\n")

    # Append DataFrame
    df.to_csv(output_path, mode="a", sep=";", index=False, encoding="utf-8-sig")

    print(f"    Relatório salvo: {output_path.name}")


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

    # Salvar relatório
    save_report(df_report, equipes, indicador, top_cresceram, menos_cresceram, competencias)

    # Gerar gráficos
    generate_line_chart(equipes, indicador, competencias, data)
    generate_top_bottom_chart(equipes, indicador, top_cresceram, menos_cresceram)


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
    print(f"Saída: {GRAFICOS_DIR}")
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
    print(f"Arquivos salvos em: {GRAFICOS_DIR}")
    print("=" * 70)


def main():
    equipes_filter = [arg.split('&') for arg in sys.argv[1:]] if len(sys.argv) > 1 else None
    generate_reports(equipes_filter)


if __name__ == "__main__":
    main()
