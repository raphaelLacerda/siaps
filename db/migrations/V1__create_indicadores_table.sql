-- Tabela principal para dados do SIAPS (indicadores por competência)
CREATE TABLE indicadores (
    id SERIAL PRIMARY KEY,
    cnes VARCHAR(20),
    estabelecimento VARCHAR(255),
    tipo_estabelecimento VARCHAR(100),
    ine VARCHAR(20),
    nome_equipe VARCHAR(255),
    sigla_equipe VARCHAR(20),
    atendimentos_programada INTEGER,
    atendimentos_total INTEGER,
    pontuacao DECIMAL(10,2),
    indicador VARCHAR(100),
    competencia DATE,
    tipo_equipe VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimizar consultas
CREATE INDEX idx_indicadores_competencia ON indicadores(competencia);
CREATE INDEX idx_indicadores_indicador ON indicadores(indicador);
CREATE INDEX idx_indicadores_sigla_equipe ON indicadores(sigla_equipe);
CREATE INDEX idx_indicadores_ine ON indicadores(ine);
