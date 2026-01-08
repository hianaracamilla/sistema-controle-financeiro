-- Criar os tipos ENUM primeiro
CREATE TYPE tipo_recorrencia AS ENUM ('MENSAL', 'SEMANAL', 'UNICO');
CREATE TYPE tipo_origem AS ENUM ('PLANEJADO', 'EXTRATO_BANCO', 'MANUAL');
CREATE TYPE tipo_status_mov AS ENUM ('PENDENTE', 'CONFIRMADO', 'CONCILIADO');
CREATE TYPE tipo_caixinha AS ENUM ('ENTRADA', 'SAIDA');
CREATE TYPE tipo_status_meta AS ENUM ('EM ANDAMENTO', 'ATINGIDA', 'CANCELADA');

-- Tabela CATEGORIA (sem dependências)
CREATE TABLE CATEGORIA (
    id_categoria SERIAL PRIMARY KEY,
    categoria VARCHAR(100) NOT NULL
);

-- Tabela CAIXINHA (depende de CATEGORIA)
CREATE TABLE CAIXINHA (
    id_caixinha SERIAL PRIMARY KEY,
    caixinha VARCHAR(100) NOT NULL,
    tipo_caixinha tipo_caixinha NOT NULL,
    FK_CATEGORIA_Id INTEGER NOT NULL,
    CONSTRAINT FK_CAIXINHA_CATEGORIA 
        FOREIGN KEY (FK_CATEGORIA_Id)
        REFERENCES CATEGORIA (id_categoria)
        ON DELETE CASCADE
);

-- Tabela PLANEJADO (depende de CAIXINHA)
CREATE TABLE PLANEJADO (
    id_plan SERIAL PRIMARY KEY,
    recorrencia_plan tipo_recorrencia NOT NULL,
    dia_plan INTEGER NOT NULL,
    valor_plan NUMERIC(10,2) NOT NULL,
    dt_inicio_plan DATE NOT NULL,
    dt_final_plan DATE,
    descricao_plan VARCHAR(255) NOT NULL,
    plan_ativo BOOLEAN DEFAULT TRUE,
    FK_CAIXINHA_Id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT FK_PLANEJADO_CAIXINHA
        FOREIGN KEY (FK_CAIXINHA_Id)
        REFERENCES CAIXINHA (id_caixinha)
        ON DELETE CASCADE
);

-- Tabela MOVIMENTACAO (depende de CAIXINHA e PLANEJADO)
CREATE TABLE MOVIMENTACAO (
    id_mov SERIAL PRIMARY KEY,
    dt_mov DATE NOT NULL,
    descricao_mov VARCHAR(255),
    valor_mov NUMERIC(10,2) NOT NULL,
    origem_mov tipo_origem NOT NULL,
    status_mov tipo_status_mov DEFAULT 'PENDENTE',
    desc_extrato TEXT,
    FK_CAIXINHA_Id INTEGER NOT NULL,
    FK_PLANEJADO_Id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT FK_MOVIMENTACAO_CAIXINHA
        FOREIGN KEY (FK_CAIXINHA_Id)
        REFERENCES CAIXINHA (id_caixinha)
        ON DELETE RESTRICT,
    CONSTRAINT FK_MOVIMENTACAO_PLANEJADO
        FOREIGN KEY (FK_PLANEJADO_Id)
        REFERENCES PLANEJADO (id_plan)
        ON DELETE CASCADE
);

-- Tabela METAS (depende de CAIXINHA)
CREATE TABLE METAS (
    id_meta SERIAL PRIMARY KEY,
    meta VARCHAR(255) NOT NULL,
    valor_alvo NUMERIC(10,2) NOT NULL,
    status tipo_status_meta NOT NULL,
    FK_CAIXINHA_Id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT FK_METAS_CAIXINHA
        FOREIGN KEY (FK_CAIXINHA_Id)
        REFERENCES CAIXINHA (id_caixinha)
        ON DELETE CASCADE
);

-- Tabela DICIONARIO_CLASSIFICACAO (depende de CAIXINHA)
CREATE TABLE DICIONARIO_CLASSIFICACAO (
    id_dicio SERIAL PRIMARY KEY,
    palavra_chave VARCHAR(255) NOT NULL,
    dt_ultima_atualizacao DATE DEFAULT CURRENT_DATE,
    confianca_dicionario INTEGER CHECK (confianca_dicionario >= 0 AND confianca_dicionario <= 100),
    FK_CAIXINHA_Id INTEGER NOT NULL,
    CONSTRAINT FK_DICIONARIO_CAIXINHA
        FOREIGN KEY (FK_CAIXINHA_Id)
        REFERENCES CAIXINHA (id_caixinha)
        ON DELETE RESTRICT
);

-- Criar índices para melhor performance
CREATE INDEX idx_movimentacao_dt ON MOVIMENTACAO(dt_mov);
CREATE INDEX idx_movimentacao_caixinha ON MOVIMENTACAO(FK_CAIXINHA_Id);
CREATE INDEX idx_planejado_caixinha ON PLANEJADO(FK_CAIXINHA_Id);
CREATE INDEX idx_dicionario_palavra ON DICIONARIO_CLASSIFICACAO(palavra_chave);

CREATE OR REPLACE VIEW dim_caixinhas_e_categorias AS 
SELECT
    c.id_caixinha,
    c.caixinha,
    c.tipo_caixinha,
    cat.categoria
FROM caixinha c
LEFT JOIN categoria cat ON c.fk_categoria_id = cat.id_categoria;

CREATE OR REPLACE VIEW dim_metas AS
SELECT
    m.id_meta,
    m.meta,
    m.valor_alvo,
    c.caixinha,
    cat.categoria
FROM metas m
LEFT JOIN caixinha c ON m.fk_caixinha_id = c.id_caixinha
LEFT JOIN categoria cat ON c.fk_categoria_id = cat.id_categoria;

CREATE OR REPLACE VIEW dim_planejamento AS 
SELECT
    p.id_plan,
    p.recorrencia_plan as recorrencia,
    p.dia_plan as dia,
    p.valor_plan as valor,
    p.dt_inicio_plan as data_inicio,
    p.dt_final_plan as data_final,
    p.descricao_plan as descricao,
    c.caixinha,
    c.tipo_caixinha
FROM planejado p
LEFT JOIN caixinha c ON p.fk_caixinha_id = c.id_caixinha;

CREATE OR REPLACE VIEW dim_mov AS
SELECT
    mov.id_mov,
    mov.dt_mov as data,
    mov.desc_extrato as descricao,
    mov.valor_mov as valor,
    c.tipo_caixinha as tipo,
    c.caixinha,
    cat.categoria as categoria_geral,
    mov.origem_mov as origem,
    mov.status_mov as status
FROM movimentacao mov
LEFT JOIN caixinha c ON mov.fk_caixinha_id = c.id_caixinha
LEFT JOIN categoria cat ON c.fk_categoria_id = cat.id_categoria;

-- =========================================
-- A) Criar entidade PESSOA
-- =========================================
CREATE TABLE PESSOA (
    id_pessoa SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO pessoa (nome) VALUES
('Casal'),
('PJ Stefane'),
('PJ Hianara'),
('Stefane'),
('Hianara');

-- =========================================
-- B) Adicionar FK_PESSOA em PLANEJADO e MOVIMENTACAO
-- =========================================
ALTER TABLE planejado
ADD COLUMN fk_pessoa_id INTEGER;

ALTER TABLE movimentacao
ADD COLUMN fk_pessoa_id INTEGER;

ALTER TABLE planejado
ADD CONSTRAINT fk_planejado_pessoa
FOREIGN KEY (fk_pessoa_id)
REFERENCES pessoa (id_pessoa)
ON DELETE RESTRICT;

ALTER TABLE movimentacao
ADD CONSTRAINT fk_movimentacao_pessoa
FOREIGN KEY (fk_pessoa_id)
REFERENCES pessoa (id_pessoa)
ON DELETE RESTRICT;

-- =========================================
-- C) Atribuir todos os lançamentos existentes para "Casal"
-- =========================================
UPDATE planejado
SET fk_pessoa_id = (SELECT id_pessoa FROM pessoa WHERE nome = 'Casal')
WHERE fk_pessoa_id IS NULL;

UPDATE movimentacao
SET fk_pessoa_id = (SELECT id_pessoa FROM pessoa WHERE nome = 'Casal')
WHERE fk_pessoa_id IS NULL;

-- (Opcional, mas recomendado) tornar obrigatório daqui pra frente:
ALTER TABLE planejado
ALTER COLUMN fk_pessoa_id SET NOT NULL;

ALTER TABLE movimentacao
ALTER COLUMN fk_pessoa_id SET NOT NULL;

-- Índices para filtro por pessoa
CREATE INDEX idx_planejado_pessoa ON planejado(fk_pessoa_id);
CREATE INDEX idx_movimentacao_pessoa ON movimentacao(fk_pessoa_id);

-- =========================================
-- D) Ajuste PLANEJADO: remover dt_final_plan e criar repeticoes_plan
-- =========================================
-- 1) Adiciona repeticoes_plan
ALTER TABLE planejado
ADD COLUMN repeticoes_plan INTEGER NOT NULL DEFAULT -1;

-- 2) (Opcional) Normalizar UNICO para 1 repetição
UPDATE planejado
SET repeticoes_plan = 1
WHERE recorrencia_plan = 'UNICO';

-- 3) Remove a coluna dt_final_plan
-- ATENÇÃO: isso vai quebrar views/queries que usam dt_final_plan; ajuste abaixo.
ALTER TABLE planejado
DROP COLUMN dt_final_plan;

-- =========================================
-- E) Atualizar views afetadas (recriar)
-- =========================================
DROP VIEW IF EXISTS dim_planejamento;

CREATE OR REPLACE VIEW dim_planejamento AS 
SELECT
    p.id_plan,
    p.recorrencia_plan as recorrencia,
    p.repeticoes_plan as repeticoes,
    p.dia_plan as dia,
    p.valor_plan as valor,
    p.dt_inicio_plan as data_inicio,
    p.descricao_plan as descricao,
    c.caixinha,
    c.tipo_caixinha,
    pes.nome as pessoa
FROM planejado p
LEFT JOIN caixinha c ON p.fk_caixinha_id = c.id_caixinha
LEFT JOIN pessoa pes ON p.fk_pessoa_id = pes.id_pessoa;

DROP VIEW IF EXISTS dim_mov;

CREATE OR REPLACE VIEW dim_mov AS
SELECT
    mov.id_mov,
    mov.dt_mov as data,
    COALESCE(mov.descricao_mov, mov.desc_extrato) as descricao,
    mov.valor_mov as valor,
    c.tipo_caixinha as tipo,
    c.caixinha,
    cat.categoria as categoria_geral,
    mov.origem_mov as origem,
    mov.status_mov as status,
    pes.nome as pessoa
FROM movimentacao mov
LEFT JOIN caixinha c ON mov.fk_caixinha_id = c.id_caixinha
LEFT JOIN categoria cat ON c.fk_categoria_id = cat.id_categoria
LEFT JOIN pessoa pes ON mov.fk_pessoa_id = pes.id_pessoa;



