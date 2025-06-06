import psycopg2
import pandas as pd
import streamlit as st

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="sistema_financeiro",
        user="postgres",
        password="postgre",
        port="5432"
    )

def inserir_movimentacao(data, descricao, valor, id_conta, id_tipo, id_categoria, status):
    """
    Insere uma nova movimentação na tabela movimentacao.
    Parâmetros esperados (7 no total):
      - data: DATE
      - descricao: TEXT
      - valor: NUMERIC
      - id_conta: INT (FK para conta)
      - id_tipo: INT (FK para tipo_movimentacao)
      - id_categoria: INT (FK para categoria)
      - status: VARCHAR ('pendente', 'confirmado' ou 'cancelado')
    """

    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO movimentacao (
            data,
            descricao,
            valor,
            id_conta,
            id_tipo,
            id_categoria,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    cur.execute(query, (
        data,
        descricao,
        valor,
        id_conta,
        id_tipo,
        id_categoria,
        status
    ))

    conn.commit()
    cur.close()
    conn.close()

def buscar_planejados_periodo():
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            p.id_planejado,
            p.recorrencia,
            p.dia,
            p.valor,       
            mo.moeda,
            p.descricao,
            cat.nome AS categoria,
            cat.categoria_estrategica,
            tm.nome AS tipo,
            p.dt_inicial,
            p.dt_final,
            p.id_moeda,  -- ✅ adicionado para uso interno
            p.id_categoria,
            p.id_tipo
        FROM planejado p
        JOIN moeda mo ON mo.id_moeda = p.id_moeda
        JOIN categoria cat ON cat.id_categoria = p.id_categoria
        JOIN tipo_movimentacao tm ON tm.id_tipo = p.id_tipo
    """

    cur.execute(query)
    colunas = [desc[0] for desc in cur.description]
    dados = cur.fetchall()
    cur.close()
    conn.close()

    return [dict(zip(colunas, linha)) for linha in dados]


def buscar_opcoes_moeda():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id_moeda, moeda FROM moeda")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return {nome: id for id, nome in dados}

def buscar_opcoes_conta():
    conn = get_connection()
    cur = conn.cursor()
    # Buscamos também a sigla da moeda (“BRL”, “USD” ou “ARS”) através do JOIN com tabela moeda
    cur.execute("""
        SELECT c.id_conta, c.nome_conta, mo.moeda 
        FROM conta c
        JOIN moeda mo ON mo.id_moeda = c.id_moeda
    """)
    dados = cur.fetchall()  
    # dados será algo como [(1, 'Nubank', 'BRL'), (2, 'Bradesco', 'USD'), …]
    cur.close()
    conn.close()
    # Construímos um dicionário: { 'Nubank': (1, 'BRL'), 'Bradesco': (2, 'USD'), … }
    return {nome: (id_conta, moeda_sigla) for id_conta, nome, moeda_sigla in dados}


def buscar_opcoes_tipo():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id_tipo, nome FROM tipo_movimentacao")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return {nome: id for id, nome in dados}

def buscar_opcoes_categoria():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id_categoria, nome FROM categoria")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return {nome: id for id, nome in dados}

def inserir_cambio(data, id_conta_origem, id_conta_destino, valor_vendido, valor_comprado):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1. Inserir o câmbio na tabela 'cambio'
        cur.execute("""
            INSERT INTO cambio (
                data, conta_venda, valor_vendido,
                conta_compra, valor_comprado
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id_cambio
        """, (data, id_conta_origem, valor_vendido, id_conta_destino, valor_comprado))
        id_cambio = cur.fetchone()[0]

        # 2. Inserir movimentação de saída (venda da moeda)
        cur.execute("""
            INSERT INTO movimentacao (
                data, descricao, valor, id_conta,
                id_tipo, id_categoria, status, id_cambio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data,
            f"Venda de moeda cambio id #{id_cambio}",
            valor_vendido,
            id_conta_origem,
            13,            # id_tipo = 13 (saída)
            22,            # id_categoria = 22 (Câmbio)
            "confirmado",
            id_cambio
        ))

        # 3. Inserir movimentação de entrada (compra da moeda)
        cur.execute("""
            INSERT INTO movimentacao (
                data, descricao, valor, id_conta,
                id_tipo, id_categoria, status, id_cambio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data,
            f"Compra de moeda cambio id #{id_cambio}",
            valor_comprado,
            id_conta_destino,
            14,            # id_tipo = 14 (entrada)
            22,            # id_categoria = 22 (Câmbio)
            "confirmado",
            id_cambio
        ))

        conn.commit()
        st.success("✅ Câmbio registrado com movimentações.")
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao registrar câmbio: {e}")
    finally:
        cur.close()
        conn.close()


def carregar_cambios():
    conn = get_connection()
    query = """
        SELECT
            c.data,
            cv.nome_conta AS conta_venda,
            mv.moeda AS moeda_venda,
            c.valor_vendido,
            cc.nome_conta AS conta_compra,
            mc.moeda AS moeda_compra,
            c.valor_comprado,
            ROUND(c.valor_comprado / c.valor_vendido, 3) AS taxa_cambio
        FROM cambio c
        JOIN conta cv ON cv.id_conta = c.conta_venda
        JOIN conta cc ON cc.id_conta = c.conta_compra
        JOIN moeda mv ON mv.id_moeda = cv.id_moeda
        JOIN moeda mc ON mc.id_moeda = cc.id_moeda
        ORDER BY c.data DESC
    """
    return pd.read_sql(query, conn)
