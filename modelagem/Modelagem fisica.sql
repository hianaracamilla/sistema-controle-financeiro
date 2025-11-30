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


SELECT * FROM caixinha;

SELECT * FROM categoria;

SELECT * FROM movimentacao;