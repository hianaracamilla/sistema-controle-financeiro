# db_crud.py - Adaptado para o schema com Pessoa + enums corretos + repeticoes_plan

import os
import pandas as pd
from supabase import create_client, Client
import streamlit as st


# --- ENUMS (valores exatos do banco) ---
STATUS_MOV_OPTIONS = ["PENDENTE", "CONFIRMADO", "CONCILIADO"]
ORIGEM_MOV_OPTIONS = ["PLANEJADO", "EXTRATO_BANCO", "MANUAL"]
RECORRENCIA_OPTIONS = ["MENSAL", "SEMANAL", "UNICO"]


# --- CONEXÃO ---
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except FileNotFoundError:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    except Exception:
        url = None
        key = None

    if not url or not key:
        raise ValueError("❌ Erro: Chaves do Supabase não encontradas.")

    return create_client(url, key)


try:
    supabase = get_supabase_client()
except Exception as e:
    supabase = None
    print(f"Erro init supabase: {e}")


# --- LOOKUPS ---
def buscar_caixinhas():
    """Retorna { 'NomeCaixinha': id_caixinha }"""
    try:
        response = supabase.table("caixinha").select("id_caixinha, caixinha").execute()
        if not response.data:
            return {}
        return {item["caixinha"]: item["id_caixinha"] for item in response.data}
    except Exception as e:
        print(f"Erro buscar caixinhas: {e}")
        return {}


def buscar_pessoas():
    """Retorna { 'NomePessoa': id_pessoa }"""
    try:
        response = supabase.table("pessoa").select("id_pessoa, nome").order("id_pessoa").execute()
        if not response.data:
            return {}
        return {item["nome"]: item["id_pessoa"] for item in response.data}
    except Exception as e:
        print(f"Erro buscar pessoas: {e}")
        return {}


# --- CRUD MOVIMENTACAO ---
def inserir_movimentacao(
    dt_mov,
    descricao_mov,
    valor_mov,
    fk_caixinha_id,
    fk_pessoa_id,
    status_mov="PENDENTE",
    origem_mov="MANUAL",
    desc_extrato=None,
    fk_planejado_id=None,
):
    # normaliza enums
    if status_mov not in STATUS_MOV_OPTIONS:
        status_mov = "PENDENTE"
    if origem_mov not in ORIGEM_MOV_OPTIONS:
        origem_mov = "MANUAL"

    payload = {
        "dt_mov": str(dt_mov),
        "descricao_mov": descricao_mov,
        "valor_mov": valor_mov,
        "fk_caixinha_id": fk_caixinha_id,
        "fk_pessoa_id": fk_pessoa_id,
        "status_mov": status_mov,
        "origem_mov": origem_mov,
        "desc_extrato": desc_extrato,
        "fk_planejado_id": fk_planejado_id,
    }

    # remove chaves None para não sobrescrever campos default
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        supabase.table("movimentacao").insert(payload).execute()
        return True, "Movimentação inserida com sucesso!"
    except Exception as e:
        return False, f"Erro ao inserir: {e}"


def atualizar_movimentacao(id_mov, dt_mov, descricao_mov, valor_mov, fk_caixinha_id, fk_pessoa_id, status_mov):
    if status_mov not in STATUS_MOV_OPTIONS:
        return False, f"Status inválido: {status_mov}"

    payload = {
        "dt_mov": str(dt_mov),
        "descricao_mov": descricao_mov,
        "valor_mov": valor_mov,
        "fk_caixinha_id": fk_caixinha_id,
        "fk_pessoa_id": fk_pessoa_id,
        "status_mov": status_mov,
    }

    try:
        supabase.table("movimentacao").update(payload).eq("id_mov", id_mov).execute()
        return True, "Movimentação atualizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def deletar_movimentacao(id_mov):
    try:
        supabase.table("movimentacao").delete().eq("id_mov", id_mov).execute()
        return True, "Movimentação deletada com sucesso!"
    except Exception as e:
        return False, f"Erro ao deletar: {e}"


def carregar_movimentacoes():
    """
    Carrega movimentacoes com join em caixinha + pessoa.
    """
    try:
        query = """
            id_mov, dt_mov, descricao_mov, desc_extrato, valor_mov, status_mov, origem_mov,
            fk_caixinha_id, fk_pessoa_id,
            caixinha:fk_caixinha_id (caixinha),
            pessoa:fk_pessoa_id (nome)
        """
        response = supabase.table("movimentacao").select(query).order("dt_mov", desc=True).execute()
        data = response.data

        if not data:
            return pd.DataFrame()

        flat_data = []
        for row in data:
            flat_row = row.copy()

            cx = flat_row.pop("caixinha", None)
            pes = flat_row.pop("pessoa", None)

            flat_row["nome_caixinha"] = cx["caixinha"] if cx else ""
            flat_row["nome_pessoa"] = pes["nome"] if pes else ""

            # descrição “melhor” para exibir
            if not flat_row.get("descricao_mov") and flat_row.get("desc_extrato"):
                flat_row["descricao_mov"] = flat_row["desc_extrato"]

            flat_data.append(flat_row)

        return pd.DataFrame(flat_data)

    except Exception as e:
        print(f"Erro carregar movimentacoes: {e}")
        return pd.DataFrame()


# --- CRUD PLANEJADO ---
def inserir_planejado(recorrencia, dia, valor, descricao, fk_caixinha_id, fk_pessoa_id, dt_inicio, repeticoes_plan=-1, ativo=True):
    if recorrencia not in RECORRENCIA_OPTIONS:
        return False, f"Recorrência inválida: {recorrencia}"

    payload = {
        "recorrencia_plan": recorrencia,
        "dia_plan": dia,
        "valor_plan": valor,
        "descricao_plan": descricao,
        "fk_caixinha_id": fk_caixinha_id,
        "fk_pessoa_id": fk_pessoa_id,
        "dt_inicio_plan": str(dt_inicio) if dt_inicio else None,
        "repeticoes_plan": repeticoes_plan,
        "plan_ativo": ativo,
    }

    try:
        supabase.table("planejado").insert(payload).execute()
        return True, "Planejamento inserido com sucesso!"
    except Exception as e:
        return False, f"Erro ao inserir planejado: {e}"


def atualizar_planejado(id_plan, recorrencia, dia, valor, descricao, fk_caixinha_id, fk_pessoa_id, dt_inicio, repeticoes_plan, ativo):
    if recorrencia not in RECORRENCIA_OPTIONS:
        return False, f"Recorrência inválida: {recorrencia}"

    payload = {
        "recorrencia_plan": recorrencia,
        "dia_plan": dia,
        "valor_plan": valor,
        "descricao_plan": descricao,
        "fk_caixinha_id": fk_caixinha_id,
        "fk_pessoa_id": fk_pessoa_id,
        "dt_inicio_plan": str(dt_inicio) if dt_inicio else None,
        "repeticoes_plan": repeticoes_plan,
        "plan_ativo": ativo,
    }

    try:
        supabase.table("planejado").update(payload).eq("id_plan", id_plan).execute()
        return True, "Planejamento atualizado com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar planejado: {e}"


def buscar_planejados():
    try:
        query = """
            id_plan, recorrencia_plan, dia_plan, valor_plan, descricao_plan, dt_inicio_plan,
            repeticoes_plan, plan_ativo, fk_caixinha_id, fk_pessoa_id,
            caixinha:fk_caixinha_id (caixinha),
            pessoa:fk_pessoa_id (nome)
        """
        response = supabase.table("planejado").select(query).order("id_plan").execute()
        data = response.data or []

        flat_data = []
        for row in data:
            flat_row = row.copy()
            cx = flat_row.pop("caixinha", None)
            pes = flat_row.pop("pessoa", None)
            flat_row["nome_caixinha"] = cx["caixinha"] if cx else ""
            flat_row["nome_pessoa"] = pes["nome"] if pes else ""
            flat_data.append(flat_row)

        return flat_data
    except Exception as e:
        print(f"Erro buscar planejados: {e}")
        return []
