-- View para resumo de indicadores por competência
CREATE VIEW v_indicadores_resumo AS
SELECT
    indicador,
    competencia,
    tipo_equipe,
    COUNT(*) as total_equipes,
    AVG(pontuacao) as media_pontuacao,
    MIN(pontuacao) as min_pontuacao,
    MAX(pontuacao) as max_pontuacao
FROM indicadores
GROUP BY indicador, competencia, tipo_equipe;

-- View para evolução temporal
CREATE VIEW v_evolucao_temporal AS
SELECT
    indicador,
    competencia,
    sigla_equipe,
    AVG(pontuacao) as media_pontuacao,
    COUNT(*) as total_equipes
FROM indicadores
GROUP BY indicador, competencia, sigla_equipe
ORDER BY competencia;

-- View para ranking de crescimento
CREATE VIEW v_ranking_crescimento AS
SELECT
    indicador,
    tipo_equipe,
    nome_equipe,
    ine,
    crescimento_total_pct,
    pontuacao_comp1,
    pontuacao_comp3,
    RANK() OVER (PARTITION BY indicador ORDER BY crescimento_total_pct DESC) as rank_crescimento
FROM crescimento
ORDER BY indicador, crescimento_total_pct DESC;

-- View para equipes com queda de desempenho
CREATE VIEW v_equipes_em_queda AS
SELECT
    indicador,
    tipo_equipe,
    nome_equipe,
    ine,
    estabelecimento,
    crescimento_total_pct,
    pontuacao_comp1,
    pontuacao_comp3
FROM crescimento
WHERE crescimento_total_pct < 0
ORDER BY crescimento_total_pct ASC;
