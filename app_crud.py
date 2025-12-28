# app_crud.py - Interface Streamlit adaptada para o schema (Caixinhas + Pessoa + Repetições)

import datetime
import pandas as pd
import streamlit as st

from db_crud import (
    get_supabase_client,
    inserir_movimentacao,
    atualizar_movimentacao,
    carregar_movimentacoes,
    deletar_movimentacao,
    inserir_planejado,
    atualizar_planejado,
    buscar_planejados,
    buscar_caixinhas,
    buscar_pessoas,
)

# --- ENUMS (valores exatos do seu banco) ---
STATUS_MOV_OPTIONS = ["PENDENTE", "CONFIRMADO", "CONCILIADO"]
RECORRENCIA_OPTIONS = ["MENSAL", "SEMANAL", "UNICO"]

st.set_page_config(layout="wide", page_title="Finanças - Caixinhas")

# --- CONEXÃO E CARGA INICIAL ---
try:
    _client = get_supabase_client()
    caixinhas_map = buscar_caixinhas()  # {'Nome': ID}
    pessoas_map = buscar_pessoas()      # {'Nome': ID}

    if not caixinhas_map:
        st.sidebar.warning("⚠️ Nenhuma caixinha encontrada. Cadastre caixinhas no banco primeiro.")

    if not pessoas_map:
        st.sidebar.warning("⚠️ Nenhuma pessoa encontrada. Cadastre em pessoa primeiro.")

    st.sidebar.success("✅ Conectado ao Supabase")

except Exception as e:
    st.sidebar.error(f"❌ Erro de conexão: {e}")
    st.stop()

DEFAULT_PESSOA = "Casal" if "Casal" in pessoas_map else (list(pessoas_map.keys())[0] if pessoas_map else None)
DEFAULT_PESSOA_INDEX = (list(pessoas_map.keys()).index(DEFAULT_PESSOA) if DEFAULT_PESSOA in pessoas_map else 0)

# --- SIDEBAR ---
st.sidebar.title("💰 Gestão Financeira")
opcao = st.sidebar.radio("Navegar:", ["📥 Movimentações", "🗓️ Planejamentos"])

if st.sidebar.button("🔄 Recarregar listas (Caixinhas/Pessoas)"):
    st.rerun()

# ======================================================================================
# TELA: MOVIMENTAÇÕES
# ======================================================================================
if opcao == "📥 Movimentações":
    st.title("📥 Movimentações")

    # 1) CREATE
    with st.expander("➕ Nova Movimentação", expanded=False):
        with st.form("form_mov"):
            col1, col2, col3, col4 = st.columns(4)
            dt_mov = col1.date_input("Data", value=datetime.date.today())
            valor_mov = col2.number_input("Valor", step=0.01, format="%.2f")
            nome_caixinha = col3.selectbox("Caixinha", list(caixinhas_map.keys()) if caixinhas_map else [])
            nome_pessoa = col4.selectbox(
                "Pessoa",
                list(pessoas_map.keys()) if pessoas_map else [],
                index=DEFAULT_PESSOA_INDEX if pessoas_map else 0,
            )

            descricao_mov = st.text_input("Descrição (opcional)")

            col5, col6 = st.columns(2)
            status_mov = col5.selectbox("Status", STATUS_MOV_OPTIONS, index=0)
            # origem é fixa no backend como MANUAL (ou você pode expor aqui, se quiser)

            submitted = st.form_submit_button("Salvar")

            if submitted:
                if not caixinhas_map:
                    st.error("Você precisa ter Caixinhas cadastradas no banco.")
                elif not pessoas_map:
                    st.error("Você precisa ter Pessoas cadastradas no banco.")
                else:
                    id_cx = caixinhas_map[nome_caixinha]
                    id_pes = pessoas_map[nome_pessoa]

                    sucesso, msg = inserir_movimentacao(
                        dt_mov=dt_mov,
                        descricao_mov=descricao_mov,
                        valor_mov=valor_mov,
                        fk_caixinha_id=id_cx,
                        fk_pessoa_id=id_pes,
                        status_mov=status_mov,
                        origem_mov="MANUAL",
                    )

                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # 2) READ / UPDATE / DELETE
    st.divider()
    st.subheader("Extrato")

    df = carregar_movimentacoes()

    if df is None or df.empty:
        st.info("Nenhuma movimentação encontrada.")
        st.stop()

    # Garantias de colunas esperadas
    if "dt_mov" in df.columns:
        df["dt_mov"] = pd.to_datetime(df["dt_mov"]).dt.date

    df["selecionar"] = False

    # Colunas para exibição
    colunas_grid = [
        "selecionar",
        "id_mov",
        "dt_mov",
        "descricao_mov",
        "valor_mov",
        "nome_caixinha",
        "nome_pessoa",
        "status_mov",
    ]
    colunas_validas = [c for c in colunas_grid if c in df.columns]
    df_view = df[colunas_validas].sort_values(by="dt_mov", ascending=False)

    edited_df = st.data_editor(
        df_view,
        use_container_width=True,
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Apagar?"),
            "id_mov": st.column_config.NumberColumn("ID", disabled=True),
            "dt_mov": st.column_config.DateColumn("Data"),
            "descricao_mov": st.column_config.TextColumn("Descrição"),
            "valor_mov": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "nome_caixinha": st.column_config.SelectboxColumn(
                "Caixinha", options=list(caixinhas_map.keys()), required=True
            ),
            "nome_pessoa": st.column_config.SelectboxColumn(
                "Pessoa", options=list(pessoas_map.keys()), required=True
            ),
            "status_mov": st.column_config.SelectboxColumn(
                "Status", options=STATUS_MOV_OPTIONS, required=True
            ),
        },
        num_rows="fixed",
    )

    col_btn1, col_btn2 = st.columns(2)

    # SALVAR EDIÇÕES
    if col_btn2.button("💾 Salvar Alterações"):
        orig_records = df_view.to_dict("records")
        new_records = edited_df.to_dict("records")
        atualizados = 0
        erros = 0

        for old, new in zip(orig_records, new_records):
            changes = False

            # Comparações seguras
            if str(old.get("dt_mov")) != str(new.get("dt_mov")):
                changes = True
            if (old.get("descricao_mov") or "") != (new.get("descricao_mov") or ""):
                changes = True
            try:
                if float(old.get("valor_mov", 0)) != float(new.get("valor_mov", 0)):
                    changes = True
            except Exception:
                changes = True
            if (old.get("status_mov") or "") != (new.get("status_mov") or ""):
                changes = True
            if (old.get("nome_caixinha") or "") != (new.get("nome_caixinha") or ""):
                changes = True
            if (old.get("nome_pessoa") or "") != (new.get("nome_pessoa") or ""):
                changes = True

            if changes:
                id_cx_novo = caixinhas_map.get(new["nome_caixinha"])
                id_pes_novo = pessoas_map.get(new["nome_pessoa"])

                if not id_cx_novo or not id_pes_novo:
                    erros += 1
                    continue

                ok, m = atualizar_movimentacao(
                    id_mov=new["id_mov"],
                    dt_mov=new["dt_mov"],
                    descricao_mov=new.get("descricao_mov"),
                    valor_mov=new.get("valor_mov"),
                    fk_caixinha_id=id_cx_novo,
                    fk_pessoa_id=id_pes_novo,
                    status_mov=new.get("status_mov"),
                )
                if ok:
                    atualizados += 1
                else:
                    erros += 1

        if atualizados > 0:
            st.success(f"{atualizados} registro(s) atualizado(s)!")
        if erros > 0:
            st.warning(f"{erros} registro(s) não foram atualizados (verifique dados/permissões).")

        if atualizados > 0:
            st.rerun()

    # DELETAR
    if col_btn1.button("🗑️ Deletar Selecionados"):
        deletados = 0
        erros = 0

        for row in edited_df.to_dict("records"):
            if row.get("selecionar"):
                ok, m = deletar_movimentacao(row["id_mov"])
                if ok:
                    deletados += 1
                else:
                    erros += 1

        if deletados > 0:
            st.success(f"{deletados} registro(s) apagado(s).")
            st.rerun()
        elif erros > 0:
            st.error("Não foi possível apagar os selecionados. Verifique permissões/RLS.")

# ======================================================================================
# TELA: PLANEJAMENTOS
# ======================================================================================
elif opcao == "🗓️ Planejamentos":
    st.title("🗓️ Planejamentos")

    # 1) CREATE
    with st.expander("➕ Novo Planejamento", expanded=False):
        with st.form("form_plan"):
            c1, c2, c3, c4 = st.columns(4)
            desc_plan = c1.text_input("Descrição")
            val_plan = c2.number_input("Valor Previsto", min_value=0.01)
            cx_plan = c3.selectbox("Caixinha Destino", list(caixinhas_map.keys()) if caixinhas_map else [])
            pessoa_plan = c4.selectbox(
                "Pessoa",
                list(pessoas_map.keys()) if pessoas_map else [],
                index=DEFAULT_PESSOA_INDEX if pessoas_map else 0,
            )

            c5, c6, c7, c8 = st.columns(4)
            recorrencia = c5.selectbox("Recorrência", RECORRENCIA_OPTIONS)
            dia_plan = c6.number_input("Dia de Vencimento", min_value=1, max_value=31)
            ativo = c7.checkbox("Ativo?", value=True)
            dt_ini = c8.date_input("Início", value=datetime.date.today())

            c9, c10 = st.columns(2)
            sempre = c9.checkbox("Repetir para sempre?", value=True)
            repeticoes_plan = -1 if sempre else int(c10.number_input("Qtd. repetições", min_value=1, value=12, step=1))

            sub_plan = st.form_submit_button("Criar Planejamento")

            if sub_plan:
                if not caixinhas_map:
                    st.error("Você precisa ter Caixinhas cadastradas no banco.")
                elif not pessoas_map:
                    st.error("Você precisa ter Pessoas cadastradas no banco.")
                else:
                    id_cx = caixinhas_map[cx_plan]
                    id_pes = pessoas_map[pessoa_plan]

                    ok, msg = inserir_planejado(
                        recorrencia=recorrencia,
                        dia=dia_plan,
                        valor=val_plan,
                        descricao=desc_plan,
                        fk_caixinha_id=id_cx,
                        fk_pessoa_id=id_pes,
                        dt_inicio=dt_ini,
                        repeticoes_plan=repeticoes_plan,
                        ativo=ativo,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # 2) READ / UPDATE
    st.divider()
    plans = buscar_planejados()  # Lista de dicts

    if not plans:
        st.info("Nenhum planejamento cadastrado.")
        st.stop()

    df_plans = pd.DataFrame(plans)

    # Conversão de data se existir
    if "dt_inicio_plan" in df_plans.columns:
        df_plans["dt_inicio_plan"] = pd.to_datetime(df_plans["dt_inicio_plan"]).dt.date

    # Colunas desejadas (incluindo pessoa e repeticoes)
    colunas_pref = [
        "id_plan",
        "recorrencia_plan",
        "dia_plan",
        "valor_plan",
        "descricao_plan",
        "nome_caixinha",
        "nome_pessoa",
        "repeticoes_plan",
        "plan_ativo",
        "dt_inicio_plan",
    ]
    colunas_validas = [c for c in colunas_pref if c in df_plans.columns]
    df_show = df_plans[colunas_validas].copy()

    col_cfg = {
        "id_plan": st.column_config.NumberColumn("ID", disabled=True),
        "recorrencia_plan": st.column_config.SelectboxColumn("Recorrência", options=RECORRENCIA_OPTIONS, required=True),
        "dia_plan": st.column_config.NumberColumn("Dia"),
        "valor_plan": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        "descricao_plan": st.column_config.TextColumn("Descrição"),
        "nome_caixinha": st.column_config.SelectboxColumn("Caixinha", options=list(caixinhas_map.keys()), required=True),
        "nome_pessoa": st.column_config.SelectboxColumn("Pessoa", options=list(pessoas_map.keys()), required=True),
        "repeticoes_plan": st.column_config.NumberColumn("Repetições (-1 = sempre)"),
        "plan_ativo": st.column_config.CheckboxColumn("Ativo"),
        "dt_inicio_plan": st.column_config.DateColumn("Início"),
    }

    edited_plans = st.data_editor(
        df_show,
        column_config=col_cfg,
        use_container_width=True,
        num_rows="fixed",
    )

    if st.button("💾 Atualizar Planejamentos"):
        count_ok = 0
        count_err = 0

        original = df_show.to_dict("records")
        modified = edited_plans.to_dict("records")

        for old, new in zip(original, modified):
            changed = False

            # Detecção de mudanças
            if old.get("recorrencia_plan") != new.get("recorrencia_plan"):
                changed = True
            if old.get("dia_plan") != new.get("dia_plan"):
                changed = True
            if old.get("valor_plan") != new.get("valor_plan"):
                changed = True
            if (old.get("descricao_plan") or "") != (new.get("descricao_plan") or ""):
                changed = True
            if old.get("nome_caixinha") != new.get("nome_caixinha"):
                changed = True
            if old.get("nome_pessoa") != new.get("nome_pessoa"):
                changed = True
            if int(old.get("repeticoes_plan", -1)) != int(new.get("repeticoes_plan", -1)):
                changed = True
            if bool(old.get("plan_ativo")) != bool(new.get("plan_ativo")):
                changed = True
            if str(old.get("dt_inicio_plan")) != str(new.get("dt_inicio_plan")):
                changed = True

            if changed:
                id_cx = caixinhas_map.get(new["nome_caixinha"])
                id_pes = pessoas_map.get(new["nome_pessoa"])
                if not id_cx or not id_pes:
                    count_err += 1
                    continue

                ok, msg = atualizar_planejado(
                    id_plan=new["id_plan"],
                    recorrencia=new["recorrencia_plan"],
                    dia=new["dia_plan"],
                    valor=new["valor_plan"],
                    descricao=new["descricao_plan"],
                    fk_caixinha_id=id_cx,
                    fk_pessoa_id=id_pes,
                    dt_inicio=new.get("dt_inicio_plan"),
                    repeticoes_plan=int(new.get("repeticoes_plan", -1)),
                    ativo=bool(new.get("plan_ativo", True)),
                )
                if ok:
                    count_ok += 1
                else:
                    count_err += 1

        if count_ok > 0:
            st.success(f"{count_ok} planejamento(s) salvo(s)!")
            st.rerun()
        if count_err > 0:
            st.warning(f"{count_err} planejamento(s) não foram salvos (verifique dados/permissões).")
