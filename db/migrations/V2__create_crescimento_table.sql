-- Tabela para dados de crescimento (relatórios de evolução)
CREATE TABLE crescimento (
    id SERIAL PRIMARY KEY,
    estabelecimento VARCHAR(255),
    ine VARCHAR(20),
    nome_equipe VARCHAR(255),
    pontuacao_comp1 DECIMAL(10,2),
    pontuacao_comp2 DECIMAL(10,2),
    pontuacao_comp3 DECIMAL(10,2),
    variacao_1_2_pct DECIMAL(10,2),
    variacao_2_3_pct DECIMAL(10,2),
    crescimento_total_pct DECIMAL(10,2),
    indicador VARCHAR(100),
    tipo_equipe VARCHAR(50),
    competencia_1 VARCHAR(10),
    competencia_2 VARCHAR(10),
    competencia_3 VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para tabela de crescimento
CREATE INDEX idx_crescimento_indicador ON crescimento(indicador);
CREATE INDEX idx_crescimento_ine ON crescimento(ine);
CREATE INDEX idx_crescimento_tipo_equipe ON crescimento(tipo_equipe);
