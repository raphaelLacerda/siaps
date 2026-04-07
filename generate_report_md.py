#!/usr/bin/env python3
"""Gera REPORT.MD a partir dos CSVs de crescimento em `reports/`"""
from pathlib import Path
import glob, re
from io import StringIO
import pandas as pd

REPORTS_DIR = Path('reports')

def read_crescimento_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        lines = f.read().splitlines()
    # find start of CSV table
    start = 0
    for i,l in enumerate(lines):
        if l.startswith('ESTABELECIMENTO') or l.startswith('ESTABELECIMENTO;'):
            start = i
            break
    csv_text = '\n'.join(lines[start:])
    if not csv_text.strip():
        return None, None
    try:
        df = pd.read_csv(StringIO(csv_text), sep=';', dtype=str)
    except Exception:
        df = pd.read_csv(StringIO(csv_text), sep=';', engine='python', dtype=str)
    # normalize numeric columns
    for col in df.columns:
        if col.startswith('PONT_') or col == 'PONTUAÇÃO' or 'CRESCIMENTO' in col or col.endswith('%'):
            df[col] = df[col].astype(str).str.replace('%','').str.replace(',','.')
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass
    return df, lines

def main():
    files = sorted(glob.glob(str(REPORTS_DIR / '*-crescimento.csv')))
    data = {}
    for fp in files:
        name = Path(fp).name
        m = re.match(r'(?P<group>.+)-(?P<slug>.+)-crescimento.csv', name)
        group = m.group('group') if m else name
        df, lines = read_crescimento_csv(fp)
        if df is None:
            continue
        # get indicator name from header if possible
        indicador = None
        for l in lines[:10]:
            if l.upper().startswith('RELAT') and '-' in l:
                indicador = l.split('-')[-1].strip()
                break
        if not indicador:
            indicador = m.group('slug') if m else name
        data.setdefault(group, {})[indicador] = df

    # aggregate per INE
    ines = {}
    for group, inds in data.items():
        for ind_name, df in inds.items():
            pont_cols = [c for c in df.columns if c.startswith('PONT_') or c=='PONTUAÇÃO']
            if pont_cols:
                df['MEAN_SCORE'] = df[pont_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
            else:
                df['MEAN_SCORE'] = pd.to_numeric(df.get('PONTUAÇÃO', pd.Series([0]*len(df))), errors='coerce')
            cres_col = None
            for c in df.columns:
                if 'CRESCIMENTO' in c:
                    cres_col = c
                    break
            if not cres_col:
                cres_col = 'CRESCIMENTO_TOTAL_%'
                if cres_col not in df.columns:
                    df[cres_col] = 0.0
            df[cres_col] = pd.to_numeric(df[cres_col], errors='coerce')
            for _, r in df.iterrows():
                ine_raw = str(r.get('INE',''))
                ine_norm = ine_raw.lstrip('0')
                ine_key = (ine_raw, r.get('NOME DA EQUIPE',''))
                entry = ines.setdefault(ine_key, {'group': group, 'indicators': {}})
                entry['indicators'][ind_name] = {'growth': float(r.get(cres_col, 0.0) or 0.0), 'mean_score': float(r.get('MEAN_SCORE', 0.0) or 0.0)}

    # write REPORT.MD
    out = []
    out.append('# Relatório Analítico — Crescimento e Notas por INE')
    out.append('\n> Gerado automaticamente a partir dos CSVs em `reports/`.')
    out.append('\n---\n')

    for group, inds in data.items():
        out.append(f'## Grupo: {group}\n')
        for ind_name, df in inds.items():
            out.append(f'### Indicador: {ind_name}')
            cres_col = next((c for c in df.columns if 'CRESCIMENTO' in c), 'CRESCIMENTO_TOTAL_%')
            df[cres_col] = pd.to_numeric(df[cres_col], errors='coerce')
            pont_cols = [c for c in df.columns if c.startswith('PONT_') or c=='PONTUAÇÃO']
            if pont_cols:
                df['MEAN_SCORE'] = df[pont_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
            df_sorted = df.sort_values(cres_col, ascending=False)
            out.append('\n**Top 5 maiores crescimentos**')
            for _,r in df_sorted.head(5).iterrows():
                out.append(f"- {r.get('NOME DA EQUIPE','')} (INE: {r.get('INE','')}) — Crescimento: {r.get(cres_col,0):.2f}%, Média nota: {r.get('MEAN_SCORE',0):.2f}")
            out.append('\n**Top 5 menores crescimentos**')
            for _,r in df_sorted.tail(5).iterrows():
                out.append(f"- {r.get('NOME DA EQUIPE','')} (INE: {r.get('INE','')}) — Crescimento: {r.get(cres_col,0):.2f}%, Média nota: {r.get('MEAN_SCORE',0):.2f}")
            out.append('\n')

    out.append('\n---\n')
    out.append('# Análise por INE (visão geral)')
    for (ine,name), info in sorted(ines.items(), key=lambda x: x[0][0]):
        inds = info['indicators']
        growths = [v['growth'] for v in inds.values()]
        scores = [v['mean_score'] for v in inds.values()]
        avg_growth = sum(growths)/len(growths) if growths else 0
        avg_score = sum(scores)/len(scores) if scores else 0
        out.append(f'## {name} (INE: {ine}) — Grupo: {info.get("group")}')
        out.append(f'- Indicadores avaliados: {len(inds)}')
        out.append(f'- Crescimento médio: {avg_growth:.2f}%')
        out.append(f'- Nota média (média das competências nos indicadores): {avg_score:.2f}')
        out.append('\n**Detalhes por indicador:**')
        for ind,vals in inds.items():
            out.append(f"- {ind}: Crescimento = {vals['growth']:.2f}%, Média nota = {vals['mean_score']:.2f}")
        # assessment
        assessment = []
        if avg_growth > 20 and avg_score >= 60:
            assessment.append('Equipe com crescimento forte e notas boas — resultado robusto (bom desempenho).')
        if avg_growth > 20 and avg_score < 50:
            assessment.append('Crescimento expressivo mas notas baixas — provavelmente partiu de baseline baixo; merecem atenção para consolidar qualidade.')
        if avg_growth <=20 and avg_score < 50:
            assessment.append('Baixo crescimento e notas baixas — equipe possivelmente com desempenho deficiente, precisa plano de melhoria.')
        if avg_growth <=20 and avg_score >= 60:
            assessment.append('Notas boas com pouco crescimento — equipe está estável e performando bem; pode haver teto de melhoria.')
        if not assessment:
            assessment.append('Desempenho misto — analisar indicadores específicos.')
        out.append('\n**Avaliação resumida:**')
        for a in assessment:
            out.append(f'- {a}')
        out.append('\n**Sugestões de melhoria / pontos fortes:**')
        if avg_score < 50:
            out.append('- Foco em capacitação técnica e revisão de processos; monitorar indicadores-chave.')
        else:
            out.append('- Manter boas práticas; compartilhar experiências com equipes que têm notas melhores.')
        if avg_growth > 20 and avg_score < 50:
            out.append('- Investigar causas do aumento (campanhas, mudanças operacionais) e garantir qualidade nas ações.')
        out.append('\n')

    Path('REPORT.MD').write_text('\n'.join(out), encoding='utf-8')
    print('REPORT.MD gerado')

if __name__ == '__main__':
    main()
