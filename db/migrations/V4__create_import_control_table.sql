-- Tabela de controle de arquivos importados
CREATE TABLE import_control (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    file_type VARCHAR(20) NOT NULL, -- 'indicadores' ou 'crescimento'
    records_count INTEGER NOT NULL,
    file_hash VARCHAR(64), -- SHA256 do arquivo para detectar mudanças
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_control_filename ON import_control(filename);
CREATE INDEX idx_import_control_file_type ON import_control(file_type);
