# app_crud.py - Interface adaptada para schema de Caixinhas

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
    buscar_caixinhas
)

st.set_page_config(layout="wide", page_title="Finanças - Caixinhas")

# --- CONEXÃO E CARGA INICIAL ---
try:
    client = get_supabase_client()
    caixinhas_map = buscar_caixinhas() # {'Nome': ID}
    
    if not caixinhas_map:
        st.sidebar.warning("⚠️ Nenhuma caixinha encontrada. Cadastre caixinhas no banco primeiro.")
        
    st.sidebar.success("✅ Conectado ao Supabase")
    
except Exception as e:
    st.sidebar.error(f"❌ Erro de conexão: {e}")
    st.stop()


# --- SIDEBAR ---
st.sidebar.title("💰 Gestão Financeira")
opcao = st.sidebar.radio("Navegar:", ["📥 Movimentações", "🗓️ Planejamentos"])


# --- TELA: MOVIMENTAÇÕES ---
if opcao == "📥 Movimentações":
    st.title("📥 Movimentações (Por Caixinha)")

    # 1. CREATE
    with st.expander("➕ Nova Movimentação", expanded=False):
        with st.form("form_mov"):
            col1, col2 = st.columns(2)
            dt_mov = col1.date_input("Data", value=datetime.date.today())
            valor_mov = col2.number_input("Valor", step=0.01, format="%.2f")
            
            descricao_mov = st.text_input("Descrição")
            
            col3, col4 = st.columns(2)
            # Seleção de Caixinha é o ponto central agora
            nome_caixinha = col3.selectbox("Caixinha", list(caixinhas_map.keys()) if caixinhas_map else [])
            status_mov = col4.selectbox("Status", ["pendente", "consolidado", "cancelado"])
            
            # Nota: 'origem_mov' vai automático como 'manual' no db_crud

            submitted = st.form_submit_button("Salvar")
            if submitted and caixinhas_map:
                id_cx = caixinhas_map[nome_caixinha]
                sucesso, msg = inserir_movimentacao(dt_mov, descricao_mov, valor_mov, id_cx, status_mov)
                
                if sucesso:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            elif submitted and not caixinhas_map:
                st.error("Você precisa ter Caixinhas cadastradas no banco.")

    # 2. READ / UPDATE / DELETE
    st.divider()
    st.subheader("Extrato")
    
    df = carregar_movimentacoes()
    
    if not df.empty:
        df["selecionar"] = False
        # Converte a coluna de string para objeto de data
        df["dt_mov"] = pd.to_datetime(df["dt_mov"]).dt.date 
        # --------------------------------
        
        df["selecionar"] = False
        
        # Ordenação e seleção de colunas para exibição
        # Colunas do DF vindo do Supabase: id_mov, dt_mov, descricao_mov, valor_mov, status_mov, nome_caixinha...
        colunas_grid = [
            "selecionar", "id_mov", "dt_mov", "descricao_mov", 
            "valor_mov", "nome_caixinha", "status_mov"
        ]
        
        # Caso alguma coluna não exista (banco vazio), filtramos
        colunas_validas = [c for c in colunas_grid if c in df.columns]
        df = df[colunas_validas].sort_values(by="dt_mov", ascending=False)

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            column_config={
                "selecionar": st.column_config.CheckboxColumn("Apagar?"),
                "id_mov": st.column_config.NumberColumn("ID", disabled=True),
                "dt_mov": st.column_config.DateColumn("Data"),
                "descricao_mov": st.column_config.TextColumn("Descrição"),
                "valor_mov": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "nome_caixinha": st.column_config.SelectboxColumn("Caixinha", options=list(caixinhas_map.keys()), required=True),
                "status_mov": st.column_config.SelectboxColumn("Status", options=["pendente", "consolidado", "cancelado"]),
            },
            num_rows="fixed"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        # Botão SALVAR EDIÇÕES
        if col_btn2.button("💾 Salvar Alterações"):
            # Comparar original vs editado
            orig_records = df.to_dict("records")
            new_records = edited_df.to_dict("records")
            atualizados = 0
            
            for old, new in zip(orig_records, new_records):
                # Verifica mudança em campos editáveis
                changes = False
                if str(old["dt_mov"]) != str(new["dt_mov"]): changes = True
                if old["descricao_mov"] != new["descricao_mov"]: changes = True
                if float(old["valor_mov"]) != float(new["valor_mov"]): changes = True
                if old["status_mov"] != new["status_mov"]: changes = True
                if old["nome_caixinha"] != new["nome_caixinha"]: changes = True
                
                if changes:
                    # Converte nome da caixinha de volta para ID
                    id_cx_novo = caixinhas_map.get(new["nome_caixinha"])
                    if id_cx_novo:
                        inserir_movimentacao # ops, atualizar
                        ok, m = atualizar_movimentacao(
                            new["id_mov"], new["dt_mov"], new["descricao_mov"], 
                            new["valor_mov"], id_cx_novo, new["status_mov"]
                        )
                        if ok: atualizados += 1
            
            if atualizados > 0:
                st.success(f"{atualizados} registros atualizados!")
                st.rerun()
        
        # Botão DELETAR
        if col_btn1.button("🗑️ Deletar Selecionados"):
            deletados = 0
            for row in edited_df.to_dict("records"):
                if row["selecionar"]:
                    ok, m = deletar_movimentacao(row["id_mov"])
                    if ok: deletados += 1
            
            if deletados > 0:
                st.success(f"{deletados} registros apagados.")
                st.rerun()

    else:
        st.info("Nenhuma movimentação encontrada.")


# --- TELA: PLANEJAMENTOS ---
elif opcao == "🗓️ Planejamentos":
    st.title("🗓️ Planejamentos Futuros")
    
    # 1. CREATE
    with st.expander("➕ Novo Planejamento", expanded=False):
        with st.form("form_plan"):
            c1, c2, c3 = st.columns(3)
            desc_plan = c1.text_input("Descrição")
            val_plan = c2.number_input("Valor Previsto", min_value=0.01)
            cx_plan = c3.selectbox("Caixinha Destino", list(caixinhas_map.keys()) if caixinhas_map else [])
            
            c4, c5, c6 = st.columns(3)
            recorrencia = c4.selectbox("Recorrência", ["MENSAL", "SEMANAL", "ANUAL", "UNICO"])
            dia_plan = c5.number_input("Dia de Vencimento", min_value=1, max_value=31)
            ativo = c6.checkbox("Ativo?", value=True)
            
            c7, c8 = st.columns(2)
            dt_ini = c7.date_input("Início", value=datetime.date.today())
            dt_fim = c8.date_input("Fim (Opcional)", value=None)
            
            sub_plan = st.form_submit_button("Criar Planejamento")
            
            if sub_plan and caixinhas_map:
                id_cx = caixinhas_map[cx_plan]
                ok, msg = inserir_planejado(recorrencia, dia_plan, val_plan, desc_plan, id_cx, dt_ini, dt_fim, ativo)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # 2. READ / UPDATE
    st.divider()
    plans = buscar_planejados() # Lista de dicts
    
    if plans:
        df_plans = pd.DataFrame(plans)

        # Converte as colunas de data se elas existirem no DataFrame
        if "dt_inicio_plan" in df_plans.columns:
             df_plans["dt_inicio_plan"] = pd.to_datetime(df_plans["dt_inicio_plan"]).dt.date
        
        if "dt_final_plan" in df_plans.columns:
             df_plans["dt_final_plan"] = pd.to_datetime(df_plans["dt_final_plan"]).dt.date

        # Colunas: id_plan, recorrencia_plan, dia_plan, valor_plan, descricao_plan, nome_caixinha...
        col_cfg = {
            "id_plan": st.column_config.NumberColumn("ID", disabled=True),
            "recorrencia_plan": st.column_config.SelectboxColumn("Recorrência", options=["MENSAL", "SEMANAL", "ANUAL", "UNICO"]     ),
            "dia_plan": st.column_config.NumberColumn("Dia"),
            "valor_plan": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "descricao_plan": st.column_config.TextColumn("Descrição"),
            "nome_caixinha": st.column_config.SelectboxColumn("Caixinha", options=list(caixinhas_map.keys())),
            "plan_ativo": st.column_config.CheckboxColumn("Ativo"),
            "dt_inicio_plan": st.column_config.DateColumn("Início"),
            "dt_final_plan": st.column_config.DateColumn("Fim"),
            "fk_caixinha_id": None
        }
        
        # Filtra colunas que existem no df
        cols_show = [k for k in col_cfg.keys() if k in df_plans.columns]
        
        edited_plans = st.data_editor(
            df_plans[cols_show],
            column_config=col_cfg,
            use_container_width=True,
            num_rows="fixed"
        )
        
        if st.button("💾 Atualizar Planejamentos"):
            # Lógica de update similar
            count = 0
            original = df_plans.to_dict("records")
            modified = edited_plans.to_dict("records")
            
            for old, new in zip(original, modified):
                # Detecção simples de mudança
                changed = False
                if old["valor_plan"] != new["valor_plan"]: changed = True
                if old["descricao_plan"] != new["descricao_plan"]: changed = True
                if old["dia_plan"] != new["dia_plan"]: changed = True
                if old["nome_caixinha"] != new["nome_caixinha"]: changed = True
                if old["plan_ativo"] != new["plan_ativo"]: changed = True
                
                if changed:
                    id_cx = caixinhas_map.get(new["nome_caixinha"])
                    if id_cx:
                        atualizar_planejado(
                            new["id_plan"], new["recorrencia_plan"], new["dia_plan"],
                            new["valor_plan"], new["descricao_plan"], id_cx,
                            new["dt_inicio_plan"], new["dt_final_plan"], new["plan_ativo"]
                        )
                        count += 1
            if count > 0:
                st.success(f"{count} planejamentos salvos!")
                st.rerun()

    else:
        st.info("Nenhum planejamento cadastrado.")