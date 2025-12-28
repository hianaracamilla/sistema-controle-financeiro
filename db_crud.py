# db_crud.py - Supabase CRUD (Financeiro + Rico Zen) - com Calendário Anual e conversão para Planejado

import os
import datetime as dt
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- ENUMS (valores exatos do banco) ---
STATUS_MOV_OPTIONS = ["PENDENTE", "CONFIRMADO", "CONCILIADO"]
ORIGEM_MOV_OPTIONS = ["PLANEJADO", "EXTRATO_BANCO", "MANUAL"]
RECORRENCIA_OPTIONS = ["MENSAL", "SEMANAL", "UNICO"]

TIPO_EVENTO_CALENDARIO = ["PESSOAL", "FINANCEIRO", "SAUDE", "VIAGEM", "RAIZES", "OUTRO"]


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
        raise ValueError("❌ Erro: Chaves do Supabase não encontradas (secrets/env).")

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


# --- MOVIMENTACAO ---
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
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        supabase.table("movimentacao").insert(payload).execute()
        return True, "Movimentação inserida com sucesso!"
    except Exception as e:
        return False, f"Erro ao inserir movimentação: {e}"


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
        return False, f"Erro ao atualizar movimentação: {e}"


def deletar_movimentacao(id_mov):
    try:
        supabase.table("movimentacao").delete().eq("id_mov", id_mov).execute()
        return True, "Movimentação deletada com sucesso!"
    except Exception as e:
        return False, f"Erro ao deletar movimentação: {e}"


def carregar_movimentacoes():
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

            if not flat_row.get("descricao_mov") and flat_row.get("desc_extrato"):
                flat_row["descricao_mov"] = flat_row["desc_extrato"]

            flat_data.append(flat_row)

        return pd.DataFrame(flat_data)

    except Exception as e:
        print(f"Erro carregar movimentacoes: {e}")
        return pd.DataFrame()


# --- PLANEJADO ---
def inserir_planejado(recorrencia, dia, valor, descricao, fk_caixinha_id, fk_pessoa_id, dt_inicio, repeticoes_plan=-1, ativo=True):
    if recorrencia not in RECORRENCIA_OPTIONS:
        return False, f"Recorrência inválida: {recorrencia}"

    payload = {
        "recorrencia_plan": recorrencia,
        "dia_plan": int(dia),
        "valor_plan": float(valor),
        "descricao_plan": descricao,
        "fk_caixinha_id": fk_caixinha_id,
        "fk_pessoa_id": fk_pessoa_id,
        "dt_inicio_plan": str(dt_inicio) if dt_inicio else None,
        "repeticoes_plan": int(repeticoes_plan),
        "plan_ativo": bool(ativo),
    }

    try:
        resp = supabase.table("planejado").insert(payload).execute()
        # resp.data geralmente retorna lista com a linha inserida
        return True, resp.data[0] if resp.data else "Planejamento inserido com sucesso!"
    except Exception as e:
        return False, f"Erro ao inserir planejado: {e}"


def atualizar_planejado(id_plan, recorrencia, dia, valor, descricao, fk_caixinha_id, fk_pessoa_id, dt_inicio, repeticoes_plan, ativo):
    if recorrencia not in RECORRENCIA_OPTIONS:
        return False, f"Recorrência inválida: {recorrencia}"

    payload = {
        "recorrencia_plan": recorrencia,
        "dia_plan": int(dia),
        "valor_plan": float(valor),
        "descricao_plan": descricao,
        "fk_caixinha_id": fk_caixinha_id,
        "fk_pessoa_id": fk_pessoa_id,
        "dt_inicio_plan": str(dt_inicio) if dt_inicio else None,
        "repeticoes_plan": int(repeticoes_plan),
        "plan_ativo": bool(ativo),
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


# ======================================================================================
# CALENDÁRIO ANUAL
# ======================================================================================
def carregar_eventos_calendario(ano: int) -> pd.DataFrame:
    """
    Retorna DataFrame dos eventos do ano com join em caixinha.
    """
    try:
        dt_ini = dt.date(ano, 1, 1)
        dt_fim = dt.date(ano + 1, 1, 1)

        query = """
            id_evento, data_evento, titulo, descricao, tipo, valor_previsto,
            fk_caixinha_id, fk_planejado_id,
            caixinha:fk_caixinha_id (caixinha)
        """
        resp = (
            supabase.table("calendario_evento")
            .select(query)
            .gte("data_evento", str(dt_ini))
            .lt("data_evento", str(dt_fim))
            .order("data_evento", desc=False)
            .execute()
        )
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = []
        for r in data:
            rr = r.copy()
            cx = rr.pop("caixinha", None)
            rr["nome_caixinha"] = cx["caixinha"] if cx else ""
            rows.append(rr)

        df = pd.DataFrame(rows)
        df["data_evento"] = pd.to_datetime(df["data_evento"]).dt.date
        return df
    except Exception as e:
        print(f"Erro carregar_eventos_calendario: {e}")
        return pd.DataFrame()


def inserir_evento_calendario(data_evento, titulo, descricao, tipo, valor_previsto, fk_caixinha_id):
    if tipo not in TIPO_EVENTO_CALENDARIO:
        tipo = "OUTRO"
    payload = {
        "data_evento": str(data_evento),
        "titulo": titulo,
        "descricao": descricao,
        "tipo": tipo,
        "valor_previsto": float(valor_previsto) if valor_previsto is not None else None,
        "fk_caixinha_id": fk_caixinha_id,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        supabase.table("calendario_evento").insert(payload).execute()
        return True, "Evento criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao criar evento: {e}"


def atualizar_evento_calendario(id_evento, data_evento, titulo, descricao, tipo, valor_previsto, fk_caixinha_id):
    if tipo not in TIPO_EVENTO_CALENDARIO:
        return False, f"Tipo inválido: {tipo}"

    payload = {
        "data_evento": str(data_evento),
        "titulo": titulo,
        "descricao": descricao,
        "tipo": tipo,
        "valor_previsto": float(valor_previsto) if valor_previsto is not None else None,
        "fk_caixinha_id": fk_caixinha_id,
    }
    try:
        supabase.table("calendario_evento").update(payload).eq("id_evento", id_evento).execute()
        return True, "Evento atualizado com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar evento: {e}"


def deletar_evento_calendario(id_evento: int):
    try:
        supabase.table("calendario_evento").delete().eq("id_evento", id_evento).execute()
        return True, "Evento deletado com sucesso!"
    except Exception as e:
        return False, f"Erro ao deletar evento: {e}"


def _get_id_pessoa_casal() -> int | None:
    """
    Retorna id da pessoa 'Casal' (obrigatório para conversão).
    """
    try:
        resp = supabase.table("pessoa").select("id_pessoa").eq("nome", "Casal").limit(1).execute()
        if resp.data:
            return resp.data[0]["id_pessoa"]
        return None
    except Exception:
        return None


def converter_evento_para_planejado(id_evento: int) -> tuple[bool, str]:
    """
    Cria um PLANEJADO (UNICO, repeticoes=1) baseado no evento e salva fk_planejado_id no evento.
    Regras:
      - evento precisa ter valor_previsto e fk_caixinha_id
      - evento não pode já ter fk_planejado_id
      - pessoa padrão: 'Casal'
    """
    try:
        resp = (
            supabase.table("calendario_evento")
            .select("id_evento, data_evento, titulo, descricao, tipo, valor_previsto, fk_caixinha_id, fk_planejado_id")
            .eq("id_evento", id_evento)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return False, "Evento não encontrado."

        ev = resp.data[0]

        if ev.get("fk_planejado_id"):
            return False, "Este evento já está vinculado a um Planejado."

        if ev.get("valor_previsto") is None:
            return False, "Evento sem valor_previsto. Preencha um valor para converter."

        if ev.get("fk_caixinha_id") is None:
            return False, "Evento sem caixinha. Selecione uma caixinha para converter."

        id_pessoa_casal = _get_id_pessoa_casal()
        if not id_pessoa_casal:
            return False, "Não encontrei a pessoa 'Casal' na tabela pessoa."

        data_evento = pd.to_datetime(ev["data_evento"]).date()
        dia = data_evento.day

        descricao = ev.get("descricao") or ""
        titulo = ev.get("titulo") or "Evento"
        desc_plan = f"[Calendário] {titulo}" if not descricao else f"[Calendário] {titulo} - {descricao}"

        ok, inserted = inserir_planejado(
            recorrencia="UNICO",
            dia=dia,
            valor=float(ev["valor_previsto"]),
            descricao=desc_plan[:255],
            fk_caixinha_id=ev["fk_caixinha_id"],
            fk_pessoa_id=id_pessoa_casal,
            dt_inicio=data_evento,
            repeticoes_plan=1,
            ativo=True,
        )
        if not ok:
            return False, f"Falha ao criar Planejado: {inserted}"

        # inserted pode ser dict do planejado
        if isinstance(inserted, dict) and inserted.get("id_plan"):
            id_plan = inserted["id_plan"]
        else:
            # fallback: buscar o último planejado parecido (último recurso)
            # (normalmente não cai aqui)
            id_plan = None

        if not id_plan:
            return False, "Planejado criado, mas não consegui capturar id_plan para vincular no evento."

        supabase.table("calendario_evento").update({"fk_planejado_id": id_plan}).eq("id_evento", id_evento).execute()
        return True, f"Convertido! Planejado #{id_plan} criado e vinculado ao evento."

    except Exception as e:
        return False, f"Erro ao converter: {e}"

# ==========================
# METAS & METINHAS (SEMESTRE)
# ==========================

STATUS_META_OPTIONS = ["EM ANDAMENTO", "ATINGIDA", "CANCELADA"]
HORIZONTE_OPTIONS = ["SEMESTRE", "ANO"]  # você pode usar "MES" depois se quiser
TIPO_META_OPTIONS = ["FINANCEIRA", "COMPORTAMENTO", "OUTRA"]


def _periodo_semestre(ano: int, semestre: int):
    # semestre: 1 => Jan-Jun, 2 => Jul-Dez
    if semestre == 1:
        ini = dt.date(ano, 1, 1)
        fim = dt.date(ano, 6, 30)
    else:
        ini = dt.date(ano, 7, 1)
        fim = dt.date(ano, 12, 31)
    return ini, fim


def carregar_metas_semestre(ano: int, semestre: int) -> pd.DataFrame:
    """
    Retorna metas do semestre (mães + metinhas).
    Critério: dt_inicio/dt_fim dentro do intervalo OU nulos (compatibilidade).
    """
    try:
        ini, fim = _periodo_semestre(ano, semestre)

        query = """
            id_meta, meta, valor_alvo, status, fk_caixinha_id, created_at,
            horizonte, dt_inicio, dt_fim, tipo, meta_pai_id,
            caixinha:fk_caixinha_id (caixinha)
        """
        resp = (
            supabase.table("metas")
            .select(query)
            .order("meta_pai_id", desc=False)  # mães primeiro (nulls first costuma vir)
            .order("id_meta", desc=False)
            .execute()
        )
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = []
        for r in data:
            rr = r.copy()
            cx = rr.pop("caixinha", None)
            rr["nome_caixinha"] = cx["caixinha"] if cx else ""
            rows.append(rr)

        df = pd.DataFrame(rows)

        # Normalizar datas
        if "dt_inicio" in df.columns:
            df["dt_inicio"] = pd.to_datetime(df["dt_inicio"], errors="coerce").dt.date
        if "dt_fim" in df.columns:
            df["dt_fim"] = pd.to_datetime(df["dt_fim"], errors="coerce").dt.date

        # Filtrar para o semestre:
        # - se dt_inicio/dt_fim nulos: assume que vale (não bloqueia)
        # - se preenchidos: tem que intersectar o semestre
        def intersects(row):
            di = row.get("dt_inicio")
            dfim = row.get("dt_fim")
            if di is None and dfim is None:
                return True
            if di is None:
                di = ini
            if dfim is None:
                dfim = fim
            return not (dfim < ini or di > fim)

        df = df[df.apply(intersects, axis=1)].copy()
        return df

    except Exception as e:
        print(f"Erro carregar_metas_semestre: {e}")
        return pd.DataFrame()


def inserir_meta(
    meta: str,
    valor_alvo: float | None,
    status: str,
    horizonte: str,
    dt_inicio: dt.date | None,
    dt_fim: dt.date | None,
    tipo: str,
    fk_caixinha_id: int | None,
    meta_pai_id: int | None,
):
    if status not in STATUS_META_OPTIONS:
        status = "EM ANDAMENTO"
    if horizonte not in HORIZONTE_OPTIONS:
        horizonte = "SEMESTRE"
    if tipo not in TIPO_META_OPTIONS:
        tipo = "FINANCEIRA"

    payload = {
        "meta": meta[:255],
        "valor_alvo": float(valor_alvo) if valor_alvo is not None else None,
        "status": status,
        "horizonte": horizonte,
        "dt_inicio": str(dt_inicio) if dt_inicio else None,
        "dt_fim": str(dt_fim) if dt_fim else None,
        "tipo": tipo,
        "fk_caixinha_id": fk_caixinha_id,
        "meta_pai_id": meta_pai_id,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        resp = supabase.table("metas").insert(payload).execute()
        return True, resp.data[0] if resp.data else "Meta inserida"
    except Exception as e:
        return False, f"Erro ao inserir meta: {e}"


def atualizar_meta(
    id_meta: int,
    meta: str,
    valor_alvo: float | None,
    status: str,
    horizonte: str,
    dt_inicio: dt.date | None,
    dt_fim: dt.date | None,
    tipo: str,
    fk_caixinha_id: int | None,
):
    if status not in STATUS_META_OPTIONS:
        return False, f"Status inválido: {status}"
    if horizonte not in HORIZONTE_OPTIONS:
        return False, f"Horizonte inválido: {horizonte}"
    if tipo not in TIPO_META_OPTIONS:
        return False, f"Tipo inválido: {tipo}"

    payload = {
        "meta": meta[:255],
        "valor_alvo": float(valor_alvo) if valor_alvo is not None else None,
        "status": status,
        "horizonte": horizonte,
        "dt_inicio": str(dt_inicio) if dt_inicio else None,
        "dt_fim": str(dt_fim) if dt_fim else None,
        "tipo": tipo,
        "fk_caixinha_id": fk_caixinha_id,
    }

    try:
        supabase.table("metas").update(payload).eq("id_meta", id_meta).execute()
        return True, "Meta atualizada"
    except Exception as e:
        return False, f"Erro ao atualizar meta: {e}"


def deletar_meta(id_meta: int):
    """
    Atenção: se for meta mãe, metinhas (filhas) serão apagadas por ON DELETE CASCADE.
    """
    try:
        supabase.table("metas").delete().eq("id_meta", id_meta).execute()
        return True, "Meta deletada"
    except Exception as e:
        return False, f"Erro ao deletar meta: {e}"

# ==========================
# PRIORIDADES (SEMESTRE / ANO)
# ==========================

STATUS_PRIORIDADE_OPTIONS = ["ATIVA", "CONCLUIDA", "PAUSADA"]
HORIZONTE_PRIORIDADE_OPTIONS = ["SEMESTRE", "ANO"]


def carregar_prioridades(ano: int, horizonte: str) -> pd.DataFrame:
    """
    Carrega prioridades filtrando por ano (periodo_inicio dentro do ano) e horizonte.
    """
    try:
        if horizonte not in HORIZONTE_PRIORIDADE_OPTIONS:
            horizonte = "SEMESTRE"

        dt_ini = dt.date(ano, 1, 1)
        dt_fim = dt.date(ano + 1, 1, 1)

        resp = (
            supabase.table("prioridade")
            .select("id_prioridade, titulo, descricao, horizonte, periodo_inicio, periodo_fim, status, created_at")
            .eq("horizonte", horizonte)
            .gte("periodo_inicio", str(dt_ini))
            .lt("periodo_inicio", str(dt_fim))
            .order("periodo_inicio", desc=False)
            .order("id_prioridade", desc=False)
            .execute()
        )

        data = resp.data or []
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["periodo_inicio"] = pd.to_datetime(df["periodo_inicio"], errors="coerce").dt.date
        df["periodo_fim"] = pd.to_datetime(df["periodo_fim"], errors="coerce").dt.date
        return df
    except Exception as e:
        print(f"Erro carregar_prioridades: {e}")
        return pd.DataFrame()


def inserir_prioridade(titulo: str, descricao: str | None, horizonte: str, periodo_inicio: dt.date, periodo_fim: dt.date, status: str):
    if horizonte not in HORIZONTE_PRIORIDADE_OPTIONS:
        horizonte = "SEMESTRE"
    if status not in STATUS_PRIORIDADE_OPTIONS:
        status = "ATIVA"

    payload = {
        "titulo": titulo[:120],
        "descricao": descricao,
        "horizonte": horizonte,
        "periodo_inicio": str(periodo_inicio),
        "periodo_fim": str(periodo_fim),
        "status": status,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        supabase.table("prioridade").insert(payload).execute()
        return True, "Prioridade criada!"
    except Exception as e:
        return False, f"Erro ao criar prioridade: {e}"


def atualizar_prioridade(id_prioridade: int, titulo: str, descricao: str | None, horizonte: str, periodo_inicio: dt.date, periodo_fim: dt.date, status: str):
    if horizonte not in HORIZONTE_PRIORIDADE_OPTIONS:
        return False, f"Horizonte inválido: {horizonte}"
    if status not in STATUS_PRIORIDADE_OPTIONS:
        return False, f"Status inválido: {status}"

    payload = {
        "titulo": titulo[:120],
        "descricao": descricao,
        "horizonte": horizonte,
        "periodo_inicio": str(periodo_inicio),
        "periodo_fim": str(periodo_fim),
        "status": status,
    }
    try:
        supabase.table("prioridade").update(payload).eq("id_prioridade", id_prioridade).execute()
        return True, "Prioridade atualizada!"
    except Exception as e:
        return False, f"Erro ao atualizar prioridade: {e}"


def deletar_prioridade(id_prioridade: int):
    try:
        supabase.table("prioridade").delete().eq("id_prioridade", id_prioridade).execute()
        return True, "Prioridade apagada!"
    except Exception as e:
        return False, f"Erro ao apagar prioridade: {e}"

# ==========================
# CÍRCULO DA VIDA (CASAL)
# ==========================

def _primeiro_dia_mes(data: dt.date) -> dt.date:
    return dt.date(data.year, data.month, 1)


def carregar_areas_vida() -> list[dict]:
    try:
        resp = (
            supabase.table("area_vida")
            .select("id_area, nome, ativa")
            .eq("ativa", True)
            .order("id_area", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"Erro carregar_areas_vida: {e}")
        return []


def carregar_checkin_mes(mes_ref: dt.date) -> pd.DataFrame:
    """
    Retorna checkins do mês (um por área).
    """
    try:
        mes_ref = _primeiro_dia_mes(mes_ref)
        query = """
            id_checkin, mes_ref, fk_area_id, nota, comentario, created_at,
            area:fk_area_id (nome)
        """
        resp = (
            supabase.table("checkin_area_vida")
            .select(query)
            .eq("mes_ref", str(mes_ref))
            .order("fk_area_id", desc=False)
            .execute()
        )
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = []
        for r in data:
            rr = r.copy()
            area = rr.pop("area", None)
            rr["area_nome"] = area["nome"] if area else ""
            rows.append(rr)

        df = pd.DataFrame(rows)
        df["mes_ref"] = pd.to_datetime(df["mes_ref"]).dt.date
        return df
    except Exception as e:
        print(f"Erro carregar_checkin_mes: {e}")
        return pd.DataFrame()


def salvar_checkin_area(mes_ref: dt.date, fk_area_id: int, nota: int, comentario: str | None):
    """
    Upsert do check-in por (mes_ref, fk_area_id).
    Requer UNIQUE(mes_ref, fk_area_id) no banco (recomendado).
    """
    try:
        mes_ref = _primeiro_dia_mes(mes_ref)
        payload = {
            "mes_ref": str(mes_ref),
            "fk_area_id": int(fk_area_id),
            "nota": int(nota),
            "comentario": comentario if comentario else None,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        # Tenta update primeiro
        existing = (
            supabase.table("checkin_area_vida")
            .select("id_checkin")
            .eq("mes_ref", str(mes_ref))
            .eq("fk_area_id", int(fk_area_id))
            .limit(1)
            .execute()
        )
        if existing.data:
            id_checkin = existing.data[0]["id_checkin"]
            supabase.table("checkin_area_vida").update(payload).eq("id_checkin", id_checkin).execute()
            return True, "Atualizado"
        else:
            supabase.table("checkin_area_vida").insert(payload).execute()
            return True, "Criado"

    except Exception as e:
        return False, f"Erro ao salvar check-in: {e}"


def historico_checkins_ano(ano: int) -> pd.DataFrame:
    """
    Retorna histórico do ano: mes_ref x area_nome x nota
    """
    try:
        dt_ini = dt.date(ano, 1, 1)
        dt_fim = dt.date(ano + 1, 1, 1)

        query = """
            id_checkin, mes_ref, fk_area_id, nota,
            area:fk_area_id (nome)
        """
        resp = (
            supabase.table("checkin_area_vida")
            .select(query)
            .gte("mes_ref", str(dt_ini))
            .lt("mes_ref", str(dt_fim))
            .order("mes_ref", desc=False)
            .order("fk_area_id", desc=False)
            .execute()
        )
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = []
        for r in data:
            rr = r.copy()
            area = rr.pop("area", None)
            rr["area_nome"] = area["nome"] if area else ""
            rows.append(rr)

        df = pd.DataFrame(rows)
        df["mes_ref"] = pd.to_datetime(df["mes_ref"]).dt.date
        return df
    except Exception as e:
        print(f"Erro historico_checkins_ano: {e}")
        return pd.DataFrame()

# ==========================
# DESAPEGO CONSCIENTE
# ==========================

DECISAO_DESAPEGO_OPTIONS = ["MANTER", "CORTAR", "TESTAR", "RENEGOCIAR"]


def carregar_desapego() -> pd.DataFrame:
    try:
        query = """
            id_item, nome_item, fk_caixinha_id, valor_estimado, frequencia, decisao, prazo_revisao,
            observacao, ativo, created_at,
            caixinha:fk_caixinha_id (caixinha)
        """
        resp = (
            supabase.table("desapego_item")
            .select(query)
            .order("ativo", desc=True)
            .order("prazo_revisao", desc=False)
            .order("id_item", desc=False)
            .execute()
        )
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = []
        for r in data:
            rr = r.copy()
            cx = rr.pop("caixinha", None)
            rr["nome_caixinha"] = cx["caixinha"] if cx else ""
            rows.append(rr)

        df = pd.DataFrame(rows)
        if "prazo_revisao" in df.columns:
            df["prazo_revisao"] = pd.to_datetime(df["prazo_revisao"], errors="coerce").dt.date
        return df
    except Exception as e:
        print(f"Erro carregar_desapego: {e}")
        return pd.DataFrame()


def inserir_desapego_item(nome_item: str, fk_caixinha_id: int | None, valor_estimado: float | None,
                         frequencia: str, decisao: str, prazo_revisao: dt.date | None,
                         observacao: str | None, ativo: bool = True):
    if decisao not in DECISAO_DESAPEGO_OPTIONS:
        decisao = "TESTAR"
    if frequencia not in RECORRENCIA_OPTIONS:
        frequencia = "MENSAL"

    payload = {
        "nome_item": nome_item[:120],
        "fk_caixinha_id": fk_caixinha_id,
        "valor_estimado": float(valor_estimado) if valor_estimado is not None else None,
        "frequencia": frequencia,
        "decisao": decisao,
        "prazo_revisao": str(prazo_revisao) if prazo_revisao else None,
        "observacao": observacao,
        "ativo": bool(ativo),
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        supabase.table("desapego_item").insert(payload).execute()
        return True, "Item criado!"
    except Exception as e:
        return False, f"Erro ao criar item: {e}"


def atualizar_desapego_item(id_item: int, nome_item: str, fk_caixinha_id: int | None, valor_estimado: float | None,
                           frequencia: str, decisao: str, prazo_revisao: dt.date | None,
                           observacao: str | None, ativo: bool):
    if decisao not in DECISAO_DESAPEGO_OPTIONS:
        return False, f"Decisão inválida: {decisao}"
    if frequencia not in RECORRENCIA_OPTIONS:
        return False, f"Frequência inválida: {frequencia}"

    payload = {
        "nome_item": nome_item[:120],
        "fk_caixinha_id": fk_caixinha_id,
        "valor_estimado": float(valor_estimado) if valor_estimado is not None else None,
        "frequencia": frequencia,
        "decisao": decisao,
        "prazo_revisao": str(prazo_revisao) if prazo_revisao else None,
        "observacao": observacao,
        "ativo": bool(ativo),
    }
    try:
        supabase.table("desapego_item").update(payload).eq("id_item", id_item).execute()
        return True, "Item atualizado!"
    except Exception as e:
        return False, f"Erro ao atualizar item: {e}"


def deletar_desapego_item(id_item: int):
    try:
        supabase.table("desapego_item").delete().eq("id_item", id_item).execute()
        return True, "Item apagado!"
    except Exception as e:
        return False, f"Erro ao apagar item: {e}"


def criar_planejado_de_desapego(id_item: int) -> tuple[bool, str]:
    """
    Cria um planejado a partir do item do desapego:
      - pessoa: Casal
      - recorrência: item.frequencia (MENSAL/SEMANAL/UNICO)
      - dia_plan: dia do prazo_revisao se existir; senão dia de hoje
      - dt_inicio_plan: hoje
      - repeticoes_plan: -1 (sempre), exceto UNICO => 1
    """
    try:
        resp = (
            supabase.table("desapego_item")
            .select("id_item, nome_item, fk_caixinha_id, valor_estimado, frequencia, decisao, prazo_revisao, ativo")
            .eq("id_item", id_item)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return False, "Item não encontrado."

        it = resp.data[0]

        if not it.get("fk_caixinha_id"):
            return False, "O item não tem caixinha. Selecione uma caixinha antes de criar o Planejado."

        if it.get("valor_estimado") is None:
            return False, "O item não tem valor_estimado. Preencha um valor para criar o Planejado."

        id_pessoa_casal = _get_id_pessoa_casal()
        if not id_pessoa_casal:
            return False, "Não encontrei a pessoa 'Casal' na tabela pessoa."

        hoje = dt.date.today()
        prazo = it.get("prazo_revisao")
        if prazo:
            prazo = pd.to_datetime(prazo).date()
            dia = prazo.day
        else:
            dia = hoje.day

        freq = it.get("frequencia") or "MENSAL"
        repet = 1 if freq == "UNICO" else -1

        descricao = f"[Desapego] {it.get('nome_item','Item')}"
        ok, inserted = inserir_planejado(
            recorrencia=freq,
            dia=dia,
            valor=float(it["valor_estimado"]),
            descricao=descricao[:255],
            fk_caixinha_id=int(it["fk_caixinha_id"]),
            fk_pessoa_id=int(id_pessoa_casal),
            dt_inicio=hoje,
            repeticoes_plan=repet,
            ativo=True,
        )
        if not ok:
            return False, f"Falha ao criar Planejado: {inserted}"

        if isinstance(inserted, dict) and inserted.get("id_plan"):
            return True, f"Planejado #{inserted['id_plan']} criado a partir do item."
        return True, "Planejado criado a partir do item."

    except Exception as e:
        return False, f"Erro ao criar planejado: {e}"
# ==========================
# DASHBOARD (REAL x PLANEJADO)
# ==========================

def _range_mes(ano: int, mes: int):
    ini = dt.date(ano, mes, 1)
    if mes == 12:
        fim = dt.date(ano + 1, 1, 1)
    else:
        fim = dt.date(ano, mes + 1, 1)
    return ini, fim


def carregar_mov_mes_agregado(ano: int, mes: int, id_pessoa: int | None = None, somente_confirmado: bool = True) -> pd.DataFrame:
    """
    Soma movimentações no mês por (categoria, tipo_caixinha).
    """
    try:
        ini, fim = _range_mes(ano, mes)

        query = """
            id_mov, dt_mov, valor_mov, status_mov,
            fk_caixinha_id, fk_pessoa_id,
            caixinha:fk_caixinha_id (tipo_caixinha, fk_categoria_id,
                categoria:fk_categoria_id (categoria)
            )
        """

        q = (
            supabase.table("movimentacao")
            .select(query)
            .gte("dt_mov", str(ini))
            .lt("dt_mov", str(fim))
        )

        if somente_confirmado:
            q = q.in_("status_mov", ["CONFIRMADO", "CONCILIADO"])

        if id_pessoa:
            q = q.eq("fk_pessoa_id", id_pessoa)

        resp = q.execute()
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = []
        for r in data:
            cx = r.get("caixinha") or {}
            tipo = cx.get("tipo_caixinha") or ""
            cat_obj = cx.get("categoria") or {}
            categoria = cat_obj.get("categoria") or ""

            rows.append({
                "categoria": categoria,
                "tipo": tipo,
                "valor": float(r.get("valor_mov") or 0),
            })

        df = pd.DataFrame(rows)
        df = df.groupby(["categoria", "tipo"], as_index=False)["valor"].sum()
        return df

    except Exception as e:
        print(f"Erro carregar_mov_mes_agregado: {e}")
        return pd.DataFrame()


def _gera_valores_planejados_para_mes(rows_plan: list[dict], ano: int, mes: int) -> list[dict]:
    """
    Projeta valor do planejado para o mês:
      - plan_ativo = true
      - dt_inicio_plan <= fim do mês
      - repeticoes_plan:
          - -1 => sempre
          - N => conta ocorrências até atingir N (a partir de dt_inicio)
      - recorrencia_plan:
          - MENSAL => 1 ocorrência por mês
          - SEMANAL => nº de semanas no mês em que a data cai
          - UNICO => 1 se data estiver no mês
    Retorna lista [{categoria, tipo, valor}]
    """
    ini, fim = _range_mes(ano, mes)
    fim_m = fim - dt.timedelta(days=1)

    out = []

    def count_weekly_occurrences(start_date: dt.date, target_ano: int, target_mes: int, dia_plan: int) -> int:
        # conta quantas datas no mês target com dia do mês = dia_plan e que caem após start_date
        # (simples: percorre dias do mês)
        count = 0
        d = dt.date(target_ano, target_mes, 1)
        while d.month == target_mes:
            if d.day == dia_plan and d >= start_date:
                count += 1
            d += dt.timedelta(days=1)
        return count

    for p in rows_plan:
        if not p.get("plan_ativo", True):
            continue

        dt_ini = p.get("dt_inicio_plan")
        if dt_ini:
            dt_ini = pd.to_datetime(dt_ini).date()
        else:
            dt_ini = ini  # fallback

        # se começa depois do mês, ignora
        if dt_ini > fim_m:
            continue

        recorr = p.get("recorrencia_plan")
        dia = int(p.get("dia_plan") or 1)
        valor = float(p.get("valor_plan") or 0.0)
        repet = int(p.get("repeticoes_plan") if p.get("repeticoes_plan") is not None else -1)

        cx = p.get("caixinha") or {}
        tipo = cx.get("tipo_caixinha") or ""
        cat_obj = cx.get("categoria") or {}
        categoria = cat_obj.get("categoria") or ""

        # data "representativa" no mês (para UNICO e para garantir dia válido)
        last_day = (fim - dt.timedelta(days=1)).day
        dia_safe = min(max(dia, 1), last_day)
        data_no_mes = dt.date(ano, mes, dia_safe)

        # quantas ocorrências no mês?
        occ = 0
        if recorr == "MENSAL":
            occ = 1 if data_no_mes >= dt_ini else 0
        elif recorr == "UNICO":
            # ocorre só se dt_inicio estiver no mês alvo (ou o dia_plan no mês e inicio <= data)
            occ = 1 if (dt_ini.year == ano and dt_ini.month == mes) else 0
        elif recorr == "SEMANAL":
            # simplificado: conta se "dia_plan" existe no mês e é >= dt_inicio
            occ = count_weekly_occurrences(dt_ini, ano, mes, dia_safe)
        else:
            occ = 0

        # aplicar limite de repetições (N) de forma simples:
        if repet != -1:
            # se já passou do limite antes deste mês, zera
            # aproximação: para mensal, calcula meses desde dt_ini; para semanal, semanas; para unico, 1
            if recorr == "MENSAL":
                months_since = (ano - dt_ini.year) * 12 + (mes - dt_ini.month)
                occ_total_ate_mes = months_since + 1  # contando mês inicial
                if occ_total_ate_mes > repet:
                    occ = 0
            elif recorr == "UNICO":
                occ = 1 if repet >= 1 and (dt_ini.year == ano and dt_ini.month == mes) else 0
            elif recorr == "SEMANAL":
                # aproximação: se repet < ocorrências do mês, corta
                occ = min(occ, repet)

        if occ > 0 and valor:
            out.append({"categoria": categoria, "tipo": tipo, "valor": valor * occ})

    return out


def carregar_planejado_mes_agregado(ano: int, mes: int, id_pessoa: int | None = None) -> pd.DataFrame:
    """
    Projeta planejados no mês e agrega por (categoria, tipo_caixinha).
    """
    try:
        query = """
            id_plan, recorrencia_plan, dia_plan, valor_plan, dt_inicio_plan, repeticoes_plan, plan_ativo,
            fk_caixinha_id, fk_pessoa_id,
            caixinha:fk_caixinha_id (tipo_caixinha, fk_categoria_id,
                categoria:fk_categoria_id (categoria)
            )
        """
        q = supabase.table("planejado").select(query).eq("plan_ativo", True)
        if id_pessoa:
            q = q.eq("fk_pessoa_id", id_pessoa)

        resp = q.execute()
        data = resp.data or []
        if not data:
            return pd.DataFrame()

        rows = _gera_valores_planejados_para_mes(data, ano, mes)
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.groupby(["categoria", "tipo"], as_index=False)["valor"].sum()
        return df
    except Exception as e:
        print(f"Erro carregar_planejado_mes_agregado: {e}")
        return pd.DataFrame()



def _normalize_enum_case(value: str, mode: str) -> str:
    if value is None:
        return value
    return value.upper() if mode == "upper" else value.lower()

def inserir_movimentacoes_em_lote(payloads: list[dict]):
    """
    Insere várias movimentações de uma vez.
    Tenta inserir como vem; se falhar por case de enum, tenta uppercase e lowercase.
    Retorna (ok: bool, msg: str).
    """
    if not payloads:
        return False, "Nada para importar."

    # remove chaves None (pra não quebrar se coluna não existir em algum ambiente)
    cleaned = []
    for p in payloads:
        cleaned.append({k: v for k, v in p.items() if v is not None})

    # 1) tenta direto
    try:
        supabase.table("movimentacao").insert(cleaned).execute()
        return True, f"Importação concluída: {len(cleaned)} linha(s)."
    except Exception as e1:
        err1 = str(e1)

    # 2) tenta uppercase
    try:
        up = []
        for p in cleaned:
            pp = p.copy()
            if "status_mov" in pp:
                pp["status_mov"] = _normalize_enum_case(pp["status_mov"], "upper")
            if "origem_mov" in pp:
                pp["origem_mov"] = _normalize_enum_case(pp["origem_mov"], "upper")
            up.append(pp)

        supabase.table("movimentacao").insert(up).execute()
        return True, f"Importação concluída: {len(up)} linha(s). (normalizado para MAIÚSCULO)"
    except Exception as e2:
        err2 = str(e2)

    # 3) tenta lowercase
    try:
        low = []
        for p in cleaned:
            pp = p.copy()
            if "status_mov" in pp:
                pp["status_mov"] = _normalize_enum_case(pp["status_mov"], "lower")
            if "origem_mov" in pp:
                pp["origem_mov"] = _normalize_enum_case(pp["origem_mov"], "lower")
            low.append(pp)

        supabase.table("movimentacao").insert(low).execute()
        return True, f"Importação concluída: {len(low)} linha(s). (normalizado para minúsculo)"
    except Exception as e3:
        err3 = str(e3)

    return False, f"Falhou ao importar.\n1) {err1}\n2) {err2}\n3) {err3}"
