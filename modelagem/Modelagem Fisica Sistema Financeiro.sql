CREATE TABLE pessoa (
	id_pessoa SERIAL PRIMARY KEY
	, nome VARCHAR(100) NOT NULL
	, tipo VARCHAR(20) NOT NULL CHECK(tipo IN('fisica', 'juridica'))
);

CREATE TABLE moeda(
	id_moeda SERIAL PRIMARY KEY
	, moeda VARCHAR(10) UNIQUE NOT NULL
);

CREATE TABLE conta(
	id_conta SERIAL PRIMARY KEY
	, tipo_conta VARCHAR(50) NOT NULL
	, banco VARCHAR(100) NOT NULL
	, id_pessa INT NOT NULL REFERENCEs pessoa(id_pessoa)
	, id_moeda INT NOT NULL REFERENCES moeda(id_moeda)
);

CREATE TABLE tipo_movimentacao(
	id_tipo SERIAL PRIMARY KEY
	, nome VARCHAR(50) NOT NULL UNIQUE
	, natureza VARCHAR(20) NOT NULL CHECK(natureza IN('entrada', 'saida'))
	, categoria_funcional VARCHAR(50) NOT NULL
	, descricao VARCHAR(250)
);

CREATE TABLE categoria(
	id_categoria SERIAL PRIMARY KEY
	, nome VARCHAR(50) NOT NULL
	, categoria_pai INT REFERENCES categoria(id_categoria)
);

CREATE TABLE planejado(
	id_planejado SERIAL PRIMARY KEY
	, recorrencia VARCHAR(30) NOT NULL CHECK(recorrencia IN('diaria','semanal', 'mensal', 'bimestral', 'semestral', 'anual' ))
	, dia INT CHECK(dia BETWEEN 1 AND 31)
	, valor NUMERIC(14, 2) NOT NULL
	, dt_inicial DATE
	, dt_final DATE
	, id_moeda INT NOT NULL REFERENCES moeda(id_moeda)
	, id_categoria INT REFERENCES categoria(id_categoria)
	, id_tipo INT REFERENCES tipo_movimentacao(id_tipo)
);

CREATE TABLE cambio(
	id_cambio SERIAL PRIMARY KEY
	, data DATE NOT NULL
	, conta_venda INT NOT NULL REFERENCES conta(id_conta)
	, valor_vendido NUMERIC(14, 2) NOT NULL
	, conta_compra INT NOT NULL REFERENCES conta(id_conta)
	, valor_comprado NUMERIC(14, 2) NOT NULL
);

CREATE TABLE movimentacao(
	id_mov SERIAL PRIMARY KEY
	, data DATE NOT NULL
	, descricao VARCHAR(250)
	, valor NUMERIC(14, 2) NOT NULL
	, status VARCHAR(20) DEFAULT 'pendente' CHECK(status IN('pendente', 'confirmado', 'cancelado'))
	, id_conta INT REFERENCES conta(id_conta)
	, id_categoria INT REFERENCES categoria(id_categoria) NOT NULL
	, id_tipo INT REFERENCES tipo_movimentacao(id_tipo) NOT NULL
	, id_cambio INT REFERENCES cambio(id_cambio)
);

CREATE TABLE saldo(
	id_saldo SERIAL PRIMARY KEY
	, data DATE NOT NULL
	, saldo NUMERIC(14, 2) NOT NULL
	, id_conta INT NOT NULL REFERENCES conta(id_conta)
	, id_mov INT UNIQUE NOT NULL REFERENCES movimentacao(id_mov)
);


ALTER TABLE planejado
ALTER COLUMN descricao TYPE VARCHAR(100);

ALTER TABLE conta
ADD COLUMN nome_conta VARCHAR(50) UNIQUE;

ALTER TABLE categoria
DROP COLUMN categoria_pai;

ALTER TABLE categoria
ADD COLUMN categoria_estrategica VARCHAR(50)
	CHECK (categoria_estrategica IN ('ESTILO_DE_VIDA', 'VIVER_O_AGORA', 'VIVER_O_DEPOIS', 'SAUDE_EMPRESARIAL'));

ALTER TABLE conta
RENAME COLUMN id_pessa TO id_pessoa;
