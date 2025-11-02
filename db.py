# Copyright (c) 2025 Hianara Camilla
# Licensed under CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/)


import psycopg2
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="sistema_financeiro",
        user="postgres",
        password="postgre",
        port="5432"
    )

 
# ----- MOVIMENTACÕES -----
def inserir_movimentacao(data, descricao, valor, id_conta, id_tipo, id_categoria, status):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO movimentacao (
            data_mov,
            descricao,
            valor,
            id_conta,
            id_tipo,
            id_categoria,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id_mov
    """
    try:
        # Executa o INSERT e já pega o id_mov inserido
        cur.execute(query, (
            data,
            descricao,
            valor,
            id_conta,
            id_tipo,
            id_categoria,
            status
        ))
        id_mov = cur.fetchone()[0]

        conn.commit()

        # Se status for 'confirmado', atualiza o saldo
        if status == "confirmado":
            cur.execute("SELECT natureza FROM tipo_movimentacao WHERE id_tipo = %s", (id_tipo,))
            natureza = cur.fetchone()[0]
            atualizar_saldo_apos_movimentacao(id_conta, id_mov, valor, natureza)

        return True, "Movimentação inserida com sucesso."

    except Exception as e:
        conn.rollback()
        return False, f"Erro ao inserir movimentação: {e}"

    finally:
        cur.close()
        conn.close()

        
def atualizar_movimentacao(id_mov, data, descricao, valor, id_conta, id_tipo, status):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE movimentacao
        SET data_mov = %s,
            descricao = %s,
            valor = %s,
            id_conta = %s,
            id_tipo = %s,
            status = %s
        WHERE id_mov = %s
    """

    try:
        # Busca status anterior
        cur.execute("SELECT status FROM movimentacao WHERE id_mov = %s", (id_mov,))
        status_anterior = cur.fetchone()[0]

        # Executa o UPDATE
        cur.execute(query, (
            data,
            descricao,
            valor,
            id_conta,
            id_tipo,
            status,
            id_mov
        ))

        # Atualiza o saldo apenas se o novo status for "confirmado"
        if status == "confirmado":
            # Remove saldo anterior (se existia)
            if status_anterior == "confirmado":
                cur.execute("DELETE FROM saldo WHERE id_mov = %s", (id_mov,))

            # Pega a natureza e atualiza o saldo
            cur.execute("SELECT natureza FROM tipo_movimentacao WHERE id_tipo = %s", (id_tipo,))
            natureza = cur.fetchone()[0]
            atualizar_saldo_apos_movimentacao(id_conta, id_mov, valor, natureza)

        conn.commit()
        return True, "Movimentação atualizada com sucesso."
    
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao atualizar movimentação: {e}"
    
    finally:
        cur.close()
        conn.close()


def carregar_movimentacoes():
    conn = get_connection()
    query = """
        SELECT 
            m.id_mov,
            m.data_mov AS data,
            m.descricao AS descricao,
            m.valor AS valor,
            mo.moeda    AS moeda,
            c.nome_conta AS conta,
            m.id_tipo AS id_tipo,
            tm.nome     AS tipo,
            tm.natureza AS natureza,
            cat.nome    AS categoria,
            m.status AS status
        FROM movimentacao m
        JOIN conta c             ON c.id_conta = m.id_conta
        JOIN moeda mo            ON mo.id_moeda = c.id_moeda
        JOIN tipo_movimentacao tm ON tm.id_tipo = m.id_tipo
        JOIN categoria cat       ON cat.id_categoria = m.id_categoria
        ORDER BY m.data_mov, m.id_mov
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def movimentacao_existe(data, descricao, id_categoria):
    """
    Retorna True se já existe uma movimentação com
    mesma data, mesma descrição e mesma categoria.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1
          FROM movimentacao
         WHERE data_mov       = %s
           AND descricao  = %s
           AND id_categoria = %s
         LIMIT 1
    """, (data, descricao, id_categoria))
    existe = cur.fetchone() is not None
    cur.close()
    conn.close()
    return existe

def deletar_movimentacao(id_mov):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM saldo WHERE id_mov = %s", (id_mov,))
        cur.execute("DELETE FROM movimentacao WHERE id_mov = %s", (id_mov,))
        conn.commit()
        return True, "Movimentação deletada com sucesso."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao deletar movimentação: {e}"
    finally:
        cur.close()
        conn.close()

def inserir_transferencia_entre_contas(data, descricao, valor, id_moeda):
    """
    Insere duas movimentações (saída e entrada) quando a categoria for 'Transferência entre contas'.
    Ambas serão salvas com status 'pendente' e contas padrão da moeda.
    """

    DEFAULT_CONTA_POR_MOEDA = {
    1: 97,   # ARS → id_conta 97
    2: 98,   # BRL → id_conta 98
    3: 99,   # USD → id_conta 99
    }
    
    try:
        id_categoria_transferencia = 28
        id_tipo_saida = 16
        id_tipo_entrada = 17
        status = "pendente"

        conta_origem = DEFAULT_CONTA_POR_MOEDA.get(id_moeda)
        conta_destino = DEFAULT_CONTA_POR_MOEDA.get(id_moeda)

        if not conta_origem or not conta_destino:
            return False, "❗ Conta padrão não definida para esta moeda."

        # Saída
        sucesso1, msg1 = inserir_movimentacao(
            data=data,
            descricao=descricao,
            valor=valor,
            id_conta=conta_origem,
            id_tipo=id_tipo_saida,
            id_categoria=id_categoria_transferencia,
            status=status
        )

        # Entrada
        sucesso2, msg2 = inserir_movimentacao(
            data=data,
            descricao=descricao,
            valor=valor,
            id_conta=conta_destino,
            id_tipo=id_tipo_entrada,
            id_categoria=id_categoria_transferencia,
            status=status
        )

        if sucesso1 and sucesso2:
            return True, "✅ Transferência entre contas registrada com sucesso."
        else:
            return False, msg1 if not sucesso1 else msg2

    except Exception as e:
        return False, f"❌ Erro ao registrar transferência entre contas: {e}"


# ----- PLANEJAMENTOS -----

def inserir_planejado(recorrencia, dia, valor, id_moeda, descricao,
                      id_categoria, dt_inicial, dt_final, id_tipo):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO planejado (
                recorrencia, dia, valor, id_moeda,
                descricao, id_categoria, dt_inicial,
                dt_final, id_tipo
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (recorrencia.lower(), dia, valor, id_moeda, descricao,
              id_categoria, dt_inicial, dt_final, id_tipo))
        conn.commit()
        return True, "Planejado inserido com sucesso."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao inserir planejado: {e}"
    finally:
        cur.close()
        conn.close()

def atualizar_planejado(id_planejado, recorrencia, dia, valor, id_moeda,
                        descricao, id_categoria, dt_inicial, dt_final, id_tipo):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE planejado
               SET recorrencia   = %s,
                   dia           = %s,
                   valor         = %s,
                   id_moeda      = %s,
                   descricao     = %s,
                   id_categoria  = %s,
                   dt_inicial    = %s,
                   dt_final      = %s,
                   id_tipo       = %s
             WHERE id_planejado = %s
        """, (recorrencia, dia, valor, id_moeda, descricao,
              id_categoria, dt_inicial, dt_final, id_tipo, id_planejado))
        conn.commit()
        return True, "Planejado atualizado com sucesso."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao atualizar planejado: {e}"
    finally:
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

# ----- CÂMBIOS -----

def inserir_cambio(data, id_conta_origem, id_conta_destino, valor_vendido, valor_comprado):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1. Inserir o câmbio na tabela 'cambio'
        cur.execute("""
            INSERT INTO cambio (
                data_cambio, conta_venda, valor_vendido,
                conta_compra, valor_comprado
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id_cambio
        """, (data, id_conta_origem, valor_vendido, id_conta_destino, valor_comprado))
        id_cambio = cur.fetchone()[0]

        # 2. Inserir movimentação de saída (venda da moeda)
        cur.execute("""
            INSERT INTO movimentacao (
                data_mov, descricao, valor, id_conta,
                id_tipo, id_categoria, status, id_cambio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data,
            f"Venda de moeda cambio id #{id_cambio}",
            valor_vendido,
            id_conta_origem,
            13,            # id_tipo = 13 (saída)
            22,            # id_categoria = 22 (Câmbio)
            "pendente",
            id_cambio
        ))

        # 3. Inserir movimentação de entrada (compra da moeda)
        cur.execute("""
            INSERT INTO movimentacao (
                data_mov, descricao, valor, id_conta,
                id_tipo, id_categoria, status, id_cambio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data,
            f"Compra de moeda cambio id #{id_cambio}",
            valor_comprado,
            id_conta_destino,
            14,            # id_tipo = 14 (entrada)
            22,            # id_categoria = 22 (Câmbio)
            "pendente",
            id_cambio
        ))

        conn.commit()
        return True, f"Câmbio #{id_cambio} registrado com sucesso."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao registrar câmbio: {e}"
    finally:
        cur.close()
        conn.close()

def carregar_cambios():
    conn = get_connection()
    query = """
        SELECT
            c.data_cambio AS data,
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
        ORDER BY c.data_cambio DESC
    """
    return pd.read_sql(query, conn)

def buscar_ultima_cotacao_por_conta(id_conta_compra, data_movimentacao):
    """
    Retorna a cotação ARS→BRL ou USD→BRL da conta COMPRA,
    quando BRL foi a conta_venda.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT valor_vendido / valor_comprado AS cotacao
    FROM cambio
    WHERE 
        conta_compra = %s
        AND data_cambio <= %s
    ORDER BY data_cambio DESC
    LIMIT 1
    """
    cur.execute(query, (id_conta_compra, data_movimentacao))
    resultado = cur.fetchone()
    conn.close()

    if resultado:
        return float(resultado[0])
    else:
        return None


# ----- RECEBIDO PJ -----

def inserir_recebido_pj(data, valor_total, id_conta_padrao, id_tipo):
    # garante que é Decimal
    valor = Decimal(valor_total)

    # define quantizador para 2 casas
    quant = Decimal('0.01')

    parte_empresa = (valor * Decimal('0.15')).quantize(quant, rounding=ROUND_HALF_UP)
    parte_pessoa  = (valor * Decimal('0.765')).quantize(quant, rounding=ROUND_HALF_UP)
    parte_reserva = (valor * Decimal('0.085')).quantize(quant, rounding=ROUND_HALF_UP)

    conn = get_connection()
    cur = conn.cursor()
    try:
    # 1) Caixa da empresa
        cur.execute("""
            INSERT INTO movimentacao (
                data_mov, descricao, valor, id_conta,
                id_tipo, id_categoria, status
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data,
            f"Caixa da empresa: retido 15% de R${valor:.2f} ;;pj_auto",
            parte_empresa,
            id_conta_padrao,
            id_tipo,
            25,
            "pendente"
        ))

        # 2) Recebimento de salário em conta
        cur.execute("""
            INSERT INTO movimentacao (data_mov,descricao,valor,id_conta,id_tipo,id_categoria,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data,
            f"Recebimento de salário: R${parte_pessoa:.2f} de R${valor:.2f} ;;pj_auto",
            parte_pessoa,
            id_conta_padrao,
            id_tipo,
            24,
            "pendente"
        ))

        # 3) Reserva de emergência
        cur.execute("""
            INSERT INTO movimentacao (data_mov,descricao,valor,id_conta,id_tipo,id_categoria,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data,
            f"Reserva de emergência: 8.5% de R${valor:.2f} = R${parte_reserva:.2f} ;;pj_auto",
            parte_reserva,
            id_conta_padrao,
            15,  # id_tipo = 15 (reserva de emergência)
            23,
            "pendente"
        ))

        conn.commit()
        return True, "Recebimento PJ processado e 3 movimentações criadas."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao processar Recebido PJ: {e}"
    finally:
        cur.close()
        conn.close()


def movimentacoes_pj_ja_existem(data_mov):
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT COUNT(*) FROM movimentacao
        WHERE data_mov = %s
        AND id_categoria IN (23, 24, 25)
        AND descricao LIKE '%%;;pj_auto'
    """
    cur.execute(query, (data_mov,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count >= 3  # se as 3 já existem, não recriar

# ---- LOOKUPS ----

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
    cur.execute("""
        SELECT c.id_conta, c.nome_conta, mo.moeda 
        FROM conta c
        JOIN moeda mo ON mo.id_moeda = c.id_moeda
    """)
    dados = cur.fetchall()  
    cur.close()
    conn.close()
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


# ------ SALDOS ------

def get_ultimo_saldo(id_conta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT saldo 
        FROM saldo 
        WHERE id_conta = %s 
        ORDER BY data_atualizacao DESC, id_saldo DESC 
        LIMIT 1
    """, (id_conta,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else Decimal("0.00")


def atualizar_saldo_apos_movimentacao(id_conta, id_mov, valor, natureza):
    saldo_anterior = get_ultimo_saldo(id_conta)

    if natureza == "entrada":
        saldo_novo = saldo_anterior + Decimal(valor)
    else:
        saldo_novo = saldo_anterior - Decimal(valor)


    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO saldo (data_atualizacao, saldo, id_conta, id_mov)
        VALUES (CURRENT_DATE, %s, %s, %s)
    """, (saldo_novo, id_conta, id_mov))
    conn.commit()
    cur.close()
    conn.close()


