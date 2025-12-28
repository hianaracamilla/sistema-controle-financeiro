# app_crud.py - Streamlit (Movimentações + Planejamentos + Calendário Anual)

import datetime
import pandas as pd
import streamlit as st

from db_crud import (
    get_supabase_client,
    # mov
    inserir_movimentacao,
    atualizar_movimentacao,
    carregar_movimentacoes,
    deletar_movimentacao,
    # plan
    inserir_planejado,
    atualizar_planejado,
    buscar_planejados,
    # lookups
    buscar_caixinhas,
    buscar_pessoas,
    # calendario
    carregar_eventos_calendario,
    inserir_evento_calendario,
    atualizar_evento_calendario,
    deletar_evento_calendario,
    converter_evento_para_planejado,
    TIPO_EVENTO_CALENDARIO,
    # metas
    carregar_metas_semestre,
    inserir_meta,
    atualizar_meta,
    deletar_meta,
    STATUS_META_OPTIONS,
    HORIZONTE_OPTIONS,
    TIPO_META_OPTIONS,
    # prioridades
    carregar_prioridades,
    inserir_prioridade,
    atualizar_prioridade,
    deletar_prioridade,
    STATUS_PRIORIDADE_OPTIONS,
    HORIZONTE_PRIORIDADE_OPTIONS,
    # círculo da vida
    carregar_areas_vida,
    carregar_checkin_mes,
    salvar_checkin_area,
    historico_checkins_ano,
    # desapego
    carregar_desapego,
    inserir_desapego_item,
    atualizar_desapego_item,
    deletar_desapego_item,
    criar_planejado_de_desapego,
    DECISAO_DESAPEGO_OPTIONS,
    # dashboard
    carregar_mov_mes_agregado,
    carregar_planejado_mes_agregado,
    inserir_movimentacoes_em_lote,


)

STATUS_MOV_OPTIONS = ["PENDENTE", "CONFIRMADO", "CONCILIADO"]
RECORRENCIA_OPTIONS = ["MENSAL", "SEMANAL", "UNICO"]

st.set_page_config(layout="wide", page_title="Finanças - Casal")

# --- CONEXÃO E LISTAS ---
try:
    _client = get_supabase_client()
    caixinhas_map = buscar_caixinhas()
    pessoas_map = buscar_pessoas()

    if not caixinhas_map:
        st.sidebar.warning("⚠️ Nenhuma caixinha encontrada.")
    if not pessoas_map:
        st.sidebar.warning("⚠️ Nenhuma pessoa encontrada. Cadastre em pessoa primeiro.")

    st.sidebar.success("✅ Conectado ao Supabase")
except Exception as e:
    st.sidebar.error(f"❌ Erro de conexão: {e}")
    st.stop()

DEFAULT_PESSOA = "Casal" if "Casal" in pessoas_map else (list(pessoas_map.keys())[0] if pessoas_map else None)
DEFAULT_PESSOA_INDEX = (list(pessoas_map.keys()).index(DEFAULT_PESSOA) if DEFAULT_PESSOA in pessoas_map else 0)

# --- SIDEBAR ---
st.sidebar.title("💰 Sistema Financeiro de Casal")

MENU_ITEMS = [
    ("📊 Dashboard", "dashboard"),
    ("🧘 Círculo da Vida", "vida"),
    ("📥 Movimentações", "mov"),
    ("🗓️ Planejamentos", "plan"),
    ("🧺 Desapego consciente", "desapego"),
    ("⭐ Prioridades", "prio"),
    ("🎯 Metas & Metinhas", "metas"),   
    ("📅 Calendário Anual", "cal"),   
    
]

# ---- ler page da URL (query param) ----
def _get_query_params():
    # Compatível com versões novas e antigas do Streamlit
    if hasattr(st, "query_params"):
        return dict(st.query_params)
    return st.experimental_get_query_params()

def _set_query_params(**kwargs):
    if hasattr(st, "query_params"):
        for k in list(st.query_params.keys()):
            del st.query_params[k]
        for k, v in kwargs.items():
            st.query_params[k] = v
    else:
        st.experimental_set_query_params(**kwargs)

qp = _get_query_params()
page = qp.get("page", [None])[0] if isinstance(qp.get("page"), list) else qp.get("page")

slug_to_label = {slug: label for (label, slug) in MENU_ITEMS}
label_to_slug = {label: slug for (label, slug) in MENU_ITEMS}

# default
if "opcao_menu" not in st.session_state:
    st.session_state["opcao_menu"] = "📊 Dashboard"

# se veio page na URL e é válido, sincroniza
if page in slug_to_label:
    st.session_state["opcao_menu"] = slug_to_label[page]

active_label = st.session_state["opcao_menu"]
active_slug = label_to_slug.get(active_label, "mov")

# ---- CSS do menu (cara de app) ----
st.sidebar.markdown(
    """
    <style>
      .menu-wrap { margin-top: 0.75rem; }
      .menu-item {
        display: block;
        padding: 0.6rem 0.75rem;
        border-radius: 12px;
        text-decoration: none !important;
        border: 1px solid rgba(0,0,0,0.08);
        margin-bottom: 0.4rem;
        color: inherit;
      }
      .menu-item:hover {
        border-color: rgba(0,0,0,0.18);
        transform: translateY(-1px);
      }
      .menu-item.active {
        background: rgba(38, 71, 31, 0.8);  /* “card” do ativo */
        border-color: rgba(138, 152, 113, 0.60);
        font-weight: 700;
        color: #ffffff;
      }
      .menu-caption {
        font-size: 0.85rem;
        opacity: 0.70;
        margin: 0.75rem 0 0.35rem;
      }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown('<div class="menu-wrap">', unsafe_allow_html=True)

for label, slug in MENU_ITEMS:
    is_active = (slug == active_slug)
    cls = "menu-item active" if is_active else "menu-item"
    # link que seta a página
    st.sidebar.markdown(
        f'<a class="{cls}" href="?page={slug}">{label}</a>',
        unsafe_allow_html=True
    )

st.sidebar.markdown("</div>", unsafe_allow_html=True)

# a “opcao” que o resto do app usa:
opcao = active_label


if st.sidebar.button("🔄 Recarregar listas (Caixinhas/Pessoas)"):
    st.rerun()

# ======================================================================================
# MÓDULO: DASHBOARD
# ======================================================================================
if opcao == "📊 Dashboard":
    st.title("📊 Dashboard (Real x Planejado)")

    hoje = datetime.date.today()
    c1, c2, c3 = st.columns(3)
    ano = c1.selectbox("Ano", list(range(hoje.year - 1, hoje.year + 3)), index=1)
    mes = c2.selectbox(
        "Mês",
        list(range(1, 13)),
        index=hoje.month - 1,
        format_func=lambda m: [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ][m],
    )

    pessoa_opts = ["(Todas)"] + (list(pessoas_map.keys()) if pessoas_map else [])
    pessoa_nome = c3.selectbox("Pessoa", pessoa_opts, index=0)
    id_pessoa = None if pessoa_nome == "(Todas)" else pessoas_map.get(pessoa_nome)

    somente_confirmado = st.checkbox("Considerar apenas CONFIRMADO/CONCILIADO no Real", value=True)

    df_real = carregar_mov_mes_agregado(ano, mes, id_pessoa=id_pessoa, somente_confirmado=somente_confirmado)
    df_plan = carregar_planejado_mes_agregado(ano, mes, id_pessoa=id_pessoa)

    def norm(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["categoria", "tipo", "valor"])
        df = df.copy()
        df["categoria"] = df["categoria"].fillna("SEM CATEGORIA")
        df["tipo"] = df["tipo"].fillna("SEM TIPO")
        df["valor"] = df["valor"].fillna(0).astype(float)
        return df

    df_real = norm(df_real)
    df_plan = norm(df_plan)

    base = pd.merge(
        df_plan.rename(columns={"valor": "planejado"}),
        df_real.rename(columns={"valor": "real"}),
        on=["categoria", "tipo"],
        how="outer",
    ).fillna(0.0)

    base["gap"] = base["planejado"] - base["real"]
    base = base.sort_values(["tipo", "categoria"], ascending=[True, True]).reset_index(drop=True)

    # ==========================
    # SEPARAR RECEITAS x DESPESAS
    # ==========================
    receitas = base[base["tipo"] == "ENTRADA"].copy()
    despesas = base[base["tipo"] == "SAIDA"].copy()

    total_rec_plan = float(receitas["planejado"].sum()) if not receitas.empty else 0.0
    total_rec_real = float(receitas["real"].sum()) if not receitas.empty else 0.0
    gap_rec = total_rec_plan - total_rec_real

    total_desp_plan = float(despesas["planejado"].sum()) if not despesas.empty else 0.0
    total_desp_real = float(despesas["real"].sum()) if not despesas.empty else 0.0
    gap_desp = total_desp_plan - total_desp_real  # positivo = sobrou orçamento / negativo = estourou

    saldo_plan = total_rec_plan - total_desp_plan
    saldo_real = total_rec_real - total_desp_real

    # ==========================
    # KPIs (SEPARADOS)
    # ==========================
    st.subheader("Visão geral do mês")

    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas (Real)", f"{total_rec_real:,.2f}", delta=f"{(total_rec_real - total_rec_plan):,.2f}")
    k2.metric("Despesas (Real)", f"{total_desp_real:,.2f}", delta=f"{(total_desp_real - total_desp_plan):,.2f}")
    k3.metric("Saldo (Real)", f"{saldo_real:,.2f}", delta=f"{(saldo_real - saldo_plan):,.2f}")

    st.caption("Delta: Real - Planejado (positivo em despesas = gastou a mais; positivo em receitas = recebeu a mais).")

    # ==========================
    # TERMÔMETRO DO MÊS (DESPESAS)
    # ==========================
    st.divider()
    st.subheader("🌡️ Termômetro do mês (Despesas)")

    if total_desp_plan <= 0:
        st.info("Você não tem despesas planejadas para este mês (ou o planejado está zerado).")
    else:
        pct = total_desp_real / total_desp_plan if total_desp_plan > 0 else 0.0
        pct_clamped = min(max(pct, 0.0), 2.0)  # trava pra não estourar visualmente

        st.progress(min(pct_clamped, 1.0))
        st.write(f"Você usou **{pct*100:.1f}%** do orçamento de despesas do mês.")

        if pct <= 0.80:
            st.success("Dentro do planejado (zona verde).")
        elif pct <= 1.00:
            st.warning("Atenção: perto do limite (zona amarela).")
        else:
            st.error("Estourou o planejado de despesas (zona vermelha).")

        restante = total_desp_plan - total_desp_real
        st.write(f"Restante do orçamento de despesas: **{restante:,.2f}**")

    # Termômetro por categoria (despesas)
    if despesas.empty:
        st.info("Sem despesas para este mês/filtro.")
    else:
        st.markdown("#### Termômetro por macro-categoria (SAÍDA)")
        dcat = despesas.groupby("categoria", as_index=False)[["planejado", "real"]].sum()
        dcat["pct"] = dcat.apply(lambda r: (r["real"] / r["planejado"]) if r["planejado"] > 0 else None, axis=1)
        dcat = dcat.sort_values("real", ascending=False)

        for _, r in dcat.iterrows():
            cat = r["categoria"]
            plan = float(r["planejado"])
            real = float(r["real"])
            pctc = r["pct"]

            st.write(f"**{cat}** — Real: {real:,.2f} | Planejado: {plan:,.2f}")
            if plan > 0 and pctc is not None:
                st.progress(min(max(pctc, 0.0), 1.0))
                st.write(f"{pctc*100:.1f}% do planejado")
                if pctc > 1.0:
                    st.error("Estourou nesta categoria.")
            else:
                st.info("Sem planejado nesta categoria (não dá pra medir %).")

    # ==========================
    # TABELAS: RECEITAS / DESPESAS
    # ==========================
    st.divider()
    st.subheader("Receitas — Planejado x Real (ENTRADA)")
    if receitas.empty:
        st.info("Sem receitas neste mês/filtro.")
    else:
        rview = receitas.copy()
        rview["planejado"] = rview["planejado"].round(2)
        rview["real"] = rview["real"].round(2)
        rview["gap"] = rview["gap"].round(2)
        st.dataframe(rview[["categoria", "planejado", "real", "gap"]], use_container_width=True)

    st.divider()
    st.subheader("Despesas — Planejado x Real (SAÍDA)")
    if despesas.empty:
        st.info("Sem despesas neste mês/filtro.")
    else:
        dview = despesas.copy()
        dview["planejado"] = dview["planejado"].round(2)
        dview["real"] = dview["real"].round(2)
        dview["gap"] = dview["gap"].round(2)
        st.dataframe(dview[["categoria", "planejado", "real", "gap"]], use_container_width=True)

    st.caption("Obs: Planejado é projeção simples (MENSAL/SEMANAL/UNICO + repeticoes_plan).")


# ======================================================================================
# MÓDULO: MOVIMENTAÇÕES
# ======================================================================================
elif opcao == "📥 Movimentações":
    st.title("📥 Movimentações")

    # CREATE
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

            submitted = st.form_submit_button("Salvar")

            if submitted:
                if not caixinhas_map or not pessoas_map:
                    st.error("Cadastre caixinhas e pessoas antes de inserir movimentações.")
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

    # ==========================
    # IMPORTAR EXTRATO (CSV)
    # ==========================
    with st.expander("📤 Importar extrato (CSV)", expanded=False):
        up = st.file_uploader("Envie o CSV do extrato", type=["csv"])

        # Defaults
        pessoa_default_nome = "Casal"
        status_default = "PENDENTE"

        # Caixinhas default por tipo
        cx_default_entrada = "RECEITA"
        cx_default_saida = "PENDENTE DE CAIXINHA"

        if up is not None:
            # tentar ler com ; e depois ,
            try:
                df_raw = pd.read_csv(up, sep=";", dtype=str, encoding="utf-8")
                if df_raw.shape[1] == 1:
                    up.seek(0)
                    df_raw = pd.read_csv(up, sep=",", dtype=str, encoding="utf-8")
            except Exception:
                up.seek(0)
                df_raw = pd.read_csv(up, sep=",", dtype=str, encoding="latin-1")

            df_raw.columns = [c.strip() for c in df_raw.columns]

            # Esperado (do seu Noh): Data, Iniciador, Método, Descrição, Valor, Tipo
            expected = ["Data", "Descrição", "Valor", "Tipo"]
            for c in expected:
                if c not in df_raw.columns:
                    st.error(f"Coluna obrigatória não encontrada no CSV: {c}")
                    st.stop()

            def parse_data_br(s):
                try:
                    return pd.to_datetime(s, dayfirst=True, errors="coerce").date()
                except Exception:
                    return None

            def parse_valor_br(s):
                if s is None or (isinstance(s, float) and pd.isna(s)):
                    return None
                s = str(s).strip()

                # remove moeda e QUALQUER tipo de espaço (inclui NBSP)
                s = s.replace("R$", "")
                s = s.replace("\u00a0", "").replace("\xa0", "")  # NBSP
                s = s.replace(" ", "").strip()

                # converte 1.234,56 -> 1234.56
                s = s.replace(".", "").replace(",", ".")

                try:
                    v = float(s)
                except Exception:
                    return None

                return abs(v)


            # construir dataframe de importação
            df_imp = pd.DataFrame()
            df_imp["importar"] = True
            df_imp["dt_mov"] = df_raw["Data"].apply(parse_data_br)
            df_imp["descricao_mov"] = df_raw["Descrição"].fillna("").astype(str)
            df_imp["valor_mov"] = df_raw["Valor"].apply(parse_valor_br)
            df_imp["tipo_csv"] = df_raw["Tipo"].fillna("").astype(str)

            # defaults pessoa/status/caixinha
            pessoa_nome_list = list(pessoas_map.keys()) if pessoas_map else []
            caixinha_nome_list = list(caixinhas_map.keys()) if caixinhas_map else []

            # pessoa default
            pessoa_default_nome = pessoa_default_nome if pessoa_default_nome in pessoa_nome_list else (pessoa_nome_list[0] if pessoa_nome_list else "")

            df_imp["pessoa"] = pessoa_default_nome
            df_imp["status"] = status_default

            def default_caixinha_por_tipo(t):
                t = (t or "").strip().lower()
                if "entrada" in t:
                    return cx_default_entrada if cx_default_entrada in caixinha_nome_list else ""
                if "saída" in t or "saida" in t:
                    return cx_default_saida if cx_default_saida in caixinha_nome_list else ""
                return ""

            df_imp["caixinha"] = df_imp["tipo_csv"].apply(default_caixinha_por_tipo)

            st.caption("Defaults aplicados: Pessoa=Casal, Status=PENDENTE; Entrada→RECEITA; Saída→PENDENTE DE CAIXINHA. Ajuste linha a linha abaixo.")

            edited = st.data_editor(
                df_imp,
                use_container_width=True,
                column_config={
                    "importar": st.column_config.CheckboxColumn("Importar?"),
                    "dt_mov": st.column_config.DateColumn("Data", required=True),
                    "descricao_mov": st.column_config.TextColumn("Descrição", required=True),
                    "valor_mov": st.column_config.NumberColumn("Valor", required=True, format="%.2f"),
                    "tipo_csv": st.column_config.TextColumn("Tipo (CSV)", disabled=True),
                    "pessoa": st.column_config.SelectboxColumn("Pessoa", options=pessoa_nome_list, required=True),
                    "status": st.column_config.SelectboxColumn("Status", options=["PENDENTE", "CONFIRMADO", "CONCILIADO", "pendente", "confirmado", "conciliado"], required=True),
                    "caixinha": st.column_config.SelectboxColumn("Caixinha", options=caixinha_nome_list, required=True),
                },
                num_rows="fixed",
            )

            colA, colB = st.columns([1, 2])

            if colA.button("✅ Confirmar importação"):
                if not pessoas_map:
                    st.error("Tabela pessoa vazia. Cadastre a pessoa 'Casal' e outras antes de importar.")
                    st.stop()

                # valida e cria payload
                rows = edited.to_dict("records")
                rows = [r for r in rows if r.get("importar")]

                if not rows:
                    st.info("Nenhuma linha marcada para importar.")
                    st.stop()

                payloads = []
                erros = []

                for i, r in enumerate(rows, start=1):
                    dt_mov = r.get("dt_mov")
                    desc = (r.get("descricao_mov") or "").strip()
                    valor = r.get("valor_mov")
                    pessoa_nome = r.get("pessoa")
                    status = r.get("status")
                    cx_nome = r.get("caixinha")

                    if not dt_mov or pd.isna(dt_mov):
                        erros.append(f"Linha {i}: data inválida.")
                        continue
                    if not desc:
                        erros.append(f"Linha {i}: descrição vazia.")
                        continue
                    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
                        erros.append(f"Linha {i}: valor inválido.")
                        continue

                    fk_pessoa_id = pessoas_map.get(pessoa_nome)
                    fk_caixinha_id = caixinhas_map.get(cx_nome)

                    if not fk_pessoa_id:
                        erros.append(f"Linha {i}: pessoa inválida: {pessoa_nome}")
                        continue
                    if not fk_caixinha_id:
                        erros.append(f"Linha {i}: caixinha inválida: {cx_nome}")
                        continue

                    payloads.append({
                        "dt_mov": str(dt_mov),
                        "descricao_mov": desc,
                        "valor_mov": float(valor),
                        "origem_mov": "EXTRATO_BANCO",
                        "status_mov": status,             # vai com fallback (upper/lower) no db_crud
                        "fk_caixinha_id": fk_caixinha_id,
                        "fk_pessoa_id": fk_pessoa_id,     # se sua coluna já existe, vai gravar; se não, você me avisa e removemos
                    })

                if erros:
                    st.error("Corrija estes pontos antes de importar:")
                    for e in erros[:20]:
                        st.write("-", e)
                    st.stop()

                ok, msg = inserir_movimentacoes_em_lote(payloads)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            colB.caption("Dica: se faltar a caixinha default, crie as caixinhas 'RECEITA' e 'PENDENTE DE CAIXINHA' no banco.")


    # READ/UPDATE/DELETE
    st.divider()
    st.subheader("Extrato")
    df = carregar_movimentacoes()

    if df is None or df.empty:
        st.info("Nenhuma movimentação encontrada.")
        st.stop()

    if "dt_mov" in df.columns:
        df["dt_mov"] = pd.to_datetime(df["dt_mov"]).dt.date

    df["selecionar"] = False

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
    df_view = df[[c for c in colunas_grid if c in df.columns]].sort_values(by="dt_mov", ascending=False)

    edited_df = st.data_editor(
        df_view,
        use_container_width=True,
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Apagar?"),
            "id_mov": st.column_config.NumberColumn("ID", disabled=True),
            "dt_mov": st.column_config.DateColumn("Data"),
            "descricao_mov": st.column_config.TextColumn("Descrição"),
            "valor_mov": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "nome_caixinha": st.column_config.SelectboxColumn("Caixinha", options=list(caixinhas_map.keys()), required=True),
            "nome_pessoa": st.column_config.SelectboxColumn("Pessoa", options=list(pessoas_map.keys()), required=True),
            "status_mov": st.column_config.SelectboxColumn("Status", options=STATUS_MOV_OPTIONS, required=True),
        },
        num_rows="fixed",
    )

    col_btn1, col_btn2 = st.columns(2)

    if col_btn2.button("💾 Salvar Alterações"):
        orig_records = df_view.to_dict("records")
        new_records = edited_df.to_dict("records")
        atualizados, erros = 0, 0

        for old, new in zip(orig_records, new_records):
            changes = False
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

                ok, _ = atualizar_movimentacao(
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

        if atualizados:
            st.success(f"{atualizados} registro(s) atualizado(s)!")
            st.rerun()
        if erros:
            st.warning(f"{erros} registro(s) não foram atualizados (verifique dados/RLS).")

    if col_btn1.button("🗑️ Deletar Selecionados"):
        deletados, erros = 0, 0
        for row in edited_df.to_dict("records"):
            if row.get("selecionar"):
                ok, _ = deletar_movimentacao(row["id_mov"])
                if ok:
                    deletados += 1
                else:
                    erros += 1

        if deletados:
            st.success(f"{deletados} registro(s) apagado(s).")
            st.rerun()
        elif erros:
            st.error("Não foi possível apagar os selecionados. Verifique permissões/RLS.")

# ======================================================================================
# MÓDULO: PLANEJAMENTOS
# ======================================================================================
elif opcao == "🗓️ Planejamentos":
    st.title("🗓️ Planejamentos")

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
                if not caixinhas_map or not pessoas_map:
                    st.error("Cadastre caixinhas e pessoas antes de criar planejamentos.")
                else:
                    id_cx = caixinhas_map[cx_plan]
                    id_pes = pessoas_map[pessoa_plan]
                    ok, resp = inserir_planejado(
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
                        st.success("Planejamento inserido com sucesso!")
                        st.rerun()
                    else:
                        st.error(resp)

    st.divider()
    plans = buscar_planejados()
    if not plans:
        st.info("Nenhum planejamento cadastrado.")
        st.stop()

    df_plans = pd.DataFrame(plans)
    if "dt_inicio_plan" in df_plans.columns:
        df_plans["dt_inicio_plan"] = pd.to_datetime(df_plans["dt_inicio_plan"]).dt.date

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
    df_show = df_plans[[c for c in colunas_pref if c in df_plans.columns]].copy()

    edited_plans = st.data_editor(
        df_show,
        use_container_width=True,
        column_config={
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
        },
        num_rows="fixed",
    )

    if st.button("💾 Atualizar Planejamentos"):
        original = df_show.to_dict("records")
        modified = edited_plans.to_dict("records")
        ok_count, err_count = 0, 0

        for old, new in zip(original, modified):
            changed = (str(old) != str(new))
            if changed:
                id_cx = caixinhas_map.get(new["nome_caixinha"])
                id_pes = pessoas_map.get(new["nome_pessoa"])
                if not id_cx or not id_pes:
                    err_count += 1
                    continue

                ok, _ = atualizar_planejado(
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
                    ok_count += 1
                else:
                    err_count += 1

        if ok_count:
            st.success(f"{ok_count} planejamento(s) salvo(s)!")
            st.rerun()
        if err_count:
            st.warning(f"{err_count} planejamento(s) não foram salvos (verifique dados/RLS).")

# ======================================================================================
# MÓDULO: CALENDÁRIO ANUAL
# ======================================================================================
elif opcao == "📅 Calendário Anual":
    st.title("📅 Calendário Anual")

    ano = st.selectbox("Ano", list(range(datetime.date.today().year - 1, datetime.date.today().year + 3)),
                       index=1)

    st.caption("Dica: cadastre eventos do ano e, quando fizer sentido, clique em **Converter em Planejado**.")

    # CREATE EVENT
    with st.expander("➕ Novo Evento", expanded=False):
        with st.form("form_evento"):
            c1, c2, c3 = st.columns(3)
            data_evento = c1.date_input("Data do evento", value=datetime.date.today())
            tipo = c2.selectbox("Tipo", TIPO_EVENTO_CALENDARIO, index=0)
            valor_previsto = c3.number_input("Valor previsto (opcional)", min_value=0.0, step=0.01, format="%.2f")

            titulo = st.text_input("Título", placeholder="Ex: IPTU, Viagem, Aniversário, Presentes mães...")
            descricao = st.text_area("Descrição (opcional)", height=80)

            cx_nome = st.selectbox("Caixinha (opcional)", ["(sem caixinha)"] + list(caixinhas_map.keys()))
            fk_caixinha_id = None if cx_nome == "(sem caixinha)" else caixinhas_map.get(cx_nome)

            submitted = st.form_submit_button("Criar Evento")

            if submitted:
                if not titulo.strip():
                    st.error("Título é obrigatório.")
                else:
                    ok, msg = inserir_evento_calendario(
                        data_evento=data_evento,
                        titulo=titulo.strip(),
                        descricao=descricao.strip() if descricao else None,
                        tipo=tipo,
                        valor_previsto=valor_previsto if valor_previsto and valor_previsto > 0 else None,
                        fk_caixinha_id=fk_caixinha_id,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # LOAD EVENTS
    df_ev = carregar_eventos_calendario(ano)

    if df_ev is None or df_ev.empty:
        st.info("Nenhum evento cadastrado para este ano.")
        st.stop()

    df_ev["mes"] = pd.to_datetime(df_ev["data_evento"]).dt.month
    df_ev["selecionar"] = False
    df_ev["converter"] = False

    # Mostrar por mês
    meses = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
        (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
        (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro"),
    ]

    for m_num, m_nome in meses:
        df_mes = df_ev[df_ev["mes"] == m_num].copy()
        if df_mes.empty:
            continue

        with st.expander(f"{m_nome} ({len(df_mes)})", expanded=(m_num == datetime.date.today().month and ano == datetime.date.today().year)):
            # coluna útil
            df_mes["vinculado"] = df_mes["fk_planejado_id"].apply(lambda x: "SIM" if pd.notna(x) and str(x) != "" else "NÃO")

            cols_show = [
                "selecionar",
                "converter",
                "id_evento",
                "data_evento",
                "titulo",
                "tipo",
                "valor_previsto",
                "nome_caixinha",
                "vinculado",
                "fk_planejado_id",
                "descricao",
            ]
            df_show = df_mes[[c for c in cols_show if c in df_mes.columns]]

            edited = st.data_editor(
                df_show,
                use_container_width=True,
                column_config={
                    "selecionar": st.column_config.CheckboxColumn("Apagar?"),
                    "converter": st.column_config.CheckboxColumn("Converter?"),
                    "id_evento": st.column_config.NumberColumn("ID", disabled=True),
                    "data_evento": st.column_config.DateColumn("Data"),
                    "titulo": st.column_config.TextColumn("Título", required=True),
                    "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPO_EVENTO_CALENDARIO, required=True),
                    "valor_previsto": st.column_config.NumberColumn("Valor previsto", format="R$ %.2f"),
                    "nome_caixinha": st.column_config.SelectboxColumn(
                        "Caixinha",
                        options=[""] + list(caixinhas_map.keys()),
                        help="Deixe vazio se não quiser caixinha",
                    ),
                    "descricao": st.column_config.TextColumn("Descrição"),
                    "vinculado": st.column_config.TextColumn("Vinculado?", disabled=True),
                    "fk_planejado_id": st.column_config.NumberColumn("Planejado ID", disabled=True),
                },
                num_rows="fixed",
            )

            cbtn1, cbtn2, cbtn3 = st.columns(3)

            # SALVAR EDIÇÕES
            if cbtn2.button(f"💾 Salvar {m_nome}", key=f"save_{m_num}"):
                orig = df_show.to_dict("records")
                new = edited.to_dict("records")

                ok_count, err_count = 0, 0
                for o, n in zip(orig, new):
                    # ignora colunas de controle
                    o_cmp = {k: v for k, v in o.items() if k not in ("selecionar", "converter", "vinculado")}
                    n_cmp = {k: v for k, v in n.items() if k not in ("selecionar", "converter", "vinculado")}
                    if str(o_cmp) == str(n_cmp):
                        continue

                    id_evento = n["id_evento"]
                    fk_cx = caixinhas_map.get(n["nome_caixinha"]) if n.get("nome_caixinha") else None

                    ok, _ = atualizar_evento_calendario(
                        id_evento=id_evento,
                        data_evento=n["data_evento"],
                        titulo=(n.get("titulo") or "").strip(),
                        descricao=n.get("descricao"),
                        tipo=n.get("tipo"),
                        valor_previsto=n.get("valor_previsto"),
                        fk_caixinha_id=fk_cx,
                    )
                    if ok:
                        ok_count += 1
                    else:
                        err_count += 1

                if ok_count:
                    st.success(f"{ok_count} evento(s) atualizado(s) em {m_nome}.")
                    st.rerun()
                if err_count:
                    st.warning(f"{err_count} evento(s) não foram atualizados (verifique dados/RLS).")

            # CONVERTER SELECIONADOS
            if cbtn3.button(f"🔁 Converter para Planejado ({m_nome})", key=f"conv_{m_num}"):
                rows = edited.to_dict("records")
                conv = [r for r in rows if r.get("converter")]

                if not conv:
                    st.info("Marque a coluna 'Converter?' nos eventos que você quer converter.")
                else:
                    okc, errc = 0, 0
                    msgs = []
                    for r in conv:
                        ok, msg = converter_evento_para_planejado(int(r["id_evento"]))
                        msgs.append(msg)
                        if ok:
                            okc += 1
                        else:
                            errc += 1

                    if okc:
                        st.success(f"{okc} evento(s) convertidos em Planejado.")
                    if errc:
                        st.warning(f"{errc} evento(s) não convertidos.")
                    for m in msgs[:10]:
                        st.write("-", m)
                    st.rerun()

            # DELETAR
            if cbtn1.button(f"🗑️ Deletar ({m_nome})", key=f"del_{m_num}"):
                rows = edited.to_dict("records")
                todel = [r for r in rows if r.get("selecionar")]
                if not todel:
                    st.info("Marque a coluna 'Apagar?' para deletar.")
                else:
                    okc, errc = 0, 0
                    for r in todel:
                        ok, _ = deletar_evento_calendario(int(r["id_evento"]))
                        if ok:
                            okc += 1
                        else:
                            errc += 1
                    if okc:
                        st.success(f"{okc} evento(s) deletado(s).")
                        st.rerun()
                    if errc:
                        st.warning(f"{errc} evento(s) não foram deletados (RLS?).")


# ======================================================================================
# MÓDULO: METAS & METINHAS (SEMESTRE)
# ======================================================================================
elif opcao == "🎯 Metas & Metinhas":
    st.title("🎯 Metas & Metinhas (Semestral)")

    hoje = datetime.date.today()
    colf1, colf2 = st.columns(2)
    ano = colf1.selectbox("Ano", list(range(hoje.year - 1, hoje.year + 3)), index=1)
    semestre = colf2.selectbox("Semestre", [1, 2], index=0 if hoje.month <= 6 else 1)

    st.caption("Metas 'mãe' aparecem primeiro. Metinhas são metas com meta_pai_id preenchido.")

    df = carregar_metas_semestre(ano, semestre)

    # -------------------------
    # CRIAR META MÃE
    # -------------------------
    with st.expander("➕ Criar Meta (mãe)", expanded=False):
        with st.form("form_meta_mae"):
            c1, c2, c3, c4 = st.columns(4)

            meta_txt = c1.text_input("Meta", placeholder="Ex: Reserva de emergência 6 meses")
            tipo = c2.selectbox("Tipo", TIPO_META_OPTIONS, index=0)
            status = c3.selectbox("Status", STATUS_META_OPTIONS, index=0)
            horizonte = c4.selectbox("Horizonte", HORIZONTE_OPTIONS, index=0)

            c5, c6, c7 = st.columns(3)
            dt_ini = c5.date_input("Data início (opcional)", value=None)
            dt_fim = c6.date_input("Data fim (opcional)", value=None)
            valor_alvo = c7.number_input("Valor alvo (opcional)", min_value=0.0, step=0.01, format="%.2f")

            cx_nome = st.selectbox("Caixinha (opcional)", ["(sem caixinha)"] + list(caixinhas_map.keys()))
            fk_caixinha_id = None if cx_nome == "(sem caixinha)" else caixinhas_map.get(cx_nome)

            submit = st.form_submit_button("Criar Meta")

            if submit:
                if not meta_txt.strip():
                    st.error("A meta precisa de um texto.")
                else:
                    ok, msg = inserir_meta(
                        meta=meta_txt.strip(),
                        valor_alvo=valor_alvo if valor_alvo and valor_alvo > 0 else None,
                        status=status,
                        horizonte=horizonte,
                        dt_inicio=dt_ini if isinstance(dt_ini, datetime.date) else None,
                        dt_fim=dt_fim if isinstance(dt_fim, datetime.date) else None,
                        tipo=tipo,
                        fk_caixinha_id=fk_caixinha_id,
                        meta_pai_id=None,
                    )
                    if ok:
                        st.success("Meta criada!")
                        st.rerun()
                    else:
                        st.error(msg)

    if df is None or df.empty:
        st.info("Nenhuma meta neste semestre ainda.")
        st.stop()

    # -------------------------
    # Separar mães e filhas
    # -------------------------
    df["is_mae"] = df["meta_pai_id"].isna()
    maes = df[df["is_mae"]].copy()

    # Helper: dict de filhas por meta mãe
    filhas_map = {}
    for _, r in df[~df["is_mae"]].iterrows():
        filhas_map.setdefault(int(r["meta_pai_id"]), []).append(r.to_dict())

    # -------------------------
    # Lista de metas mães
    # -------------------------
    for _, mae in maes.iterrows():
        id_mae = int(mae["id_meta"])
        titulo = mae.get("meta", "")
        status_mae = mae.get("status", "")
        tipo_mae = mae.get("tipo", "")
        alvo = mae.get("valor_alvo", None)
        cx = mae.get("nome_caixinha", "")

        header = f"{titulo}  |  {status_mae}  |  {tipo_mae}"
        if cx:
            header += f"  |  Caixinha: {cx}"
        if alvo is not None and str(alvo) != "":
            header += f"  |  Alvo: {float(alvo):.2f}"

        with st.expander(header, expanded=False):
            # -------------------------
            # EDITAR META MÃE
            # -------------------------
            c1, c2, c3, c4 = st.columns(4)
            new_meta = c1.text_input("Meta (mãe)", value=titulo, key=f"mae_txt_{id_mae}")
            new_tipo = c2.selectbox("Tipo", TIPO_META_OPTIONS, index=TIPO_META_OPTIONS.index(tipo_mae) if tipo_mae in TIPO_META_OPTIONS else 0, key=f"mae_tipo_{id_mae}")
            new_status = c3.selectbox("Status", STATUS_META_OPTIONS, index=STATUS_META_OPTIONS.index(status_mae) if status_mae in STATUS_META_OPTIONS else 0, key=f"mae_status_{id_mae}")
            new_horiz = c4.selectbox("Horizonte", HORIZONTE_OPTIONS, index=HORIZONTE_OPTIONS.index(mae.get("horizonte")) if mae.get("horizonte") in HORIZONTE_OPTIONS else 0, key=f"mae_h_{id_mae}")

            c5, c6, c7 = st.columns(3)
            di = mae.get("dt_inicio", None)
            dfim = mae.get("dt_fim", None)
            new_di = c5.date_input("Início", value=di, key=f"mae_di_{id_mae}")
            new_df = c6.date_input("Fim", value=dfim, key=f"mae_df_{id_mae}")
            new_alvo = c7.number_input("Valor alvo", min_value=0.0, step=0.01, format="%.2f",
                                       value=float(alvo) if alvo is not None else 0.0, key=f"mae_alvo_{id_mae}")

            cx_opts = ["(sem caixinha)"] + list(caixinhas_map.keys())
            cx_current = cx if cx in caixinhas_map else "(sem caixinha)"
            new_cx_nome = st.selectbox("Caixinha", cx_opts, index=cx_opts.index(cx_current), key=f"mae_cx_{id_mae}")
            new_fk = None if new_cx_nome == "(sem caixinha)" else caixinhas_map.get(new_cx_nome)

            b1, b2, b3 = st.columns(3)
            if b2.button("💾 Salvar Meta", key=f"save_mae_{id_mae}"):
                ok, msg = atualizar_meta(
                    id_meta=id_mae,
                    meta=new_meta.strip(),
                    valor_alvo=new_alvo if new_alvo > 0 else None,
                    status=new_status,
                    horizonte=new_horiz,
                    dt_inicio=new_di,
                    dt_fim=new_df,
                    tipo=new_tipo,
                    fk_caixinha_id=new_fk,
                )
                if ok:
                    st.success("Meta salva!")
                    st.rerun()
                else:
                    st.error(msg)

            if b1.button("🗑️ Apagar Meta (e metinhas)", key=f"del_mae_{id_mae}"):
                ok, msg = deletar_meta(id_mae)
                if ok:
                    st.success("Meta apagada.")
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()

            # -------------------------
            # METINHAS
            # -------------------------
            st.subheader("Metinhas")

            filhas = filhas_map.get(id_mae, [])
            if filhas:
                df_f = pd.DataFrame(filhas)
                # normalizar
                if "dt_inicio" in df_f.columns:
                    df_f["dt_inicio"] = pd.to_datetime(df_f["dt_inicio"], errors="coerce").dt.date
                if "dt_fim" in df_f.columns:
                    df_f["dt_fim"] = pd.to_datetime(df_f["dt_fim"], errors="coerce").dt.date

                df_f["selecionar"] = False

                cols = ["selecionar", "id_meta", "meta", "status", "tipo", "valor_alvo", "dt_inicio", "dt_fim"]
                df_show = df_f[[c for c in cols if c in df_f.columns]].copy()

                edited = st.data_editor(
                    df_show,
                    use_container_width=True,
                    column_config={
                        "selecionar": st.column_config.CheckboxColumn("Apagar?"),
                        "id_meta": st.column_config.NumberColumn("ID", disabled=True),
                        "meta": st.column_config.TextColumn("Metinha", required=True),
                        "status": st.column_config.SelectboxColumn("Status", options=STATUS_META_OPTIONS, required=True),
                        "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPO_META_OPTIONS, required=True),
                        "valor_alvo": st.column_config.NumberColumn("Valor alvo", format="R$ %.2f"),
                        "dt_inicio": st.column_config.DateColumn("Início"),
                        "dt_fim": st.column_config.DateColumn("Fim"),
                    },
                    num_rows="fixed",
                )

                bb1, bb2 = st.columns(2)

                if bb2.button("💾 Salvar Metinhas", key=f"save_filhas_{id_mae}"):
                    orig = df_show.to_dict("records")
                    new = edited.to_dict("records")
                    okc, errc = 0, 0

                    for o, n in zip(orig, new):
                        # deletar marcado
                        if n.get("selecionar"):
                            ok, _ = deletar_meta(int(n["id_meta"]))
                            if ok:
                                okc += 1
                            else:
                                errc += 1
                            continue

                        # detectar mudança
                        o_cmp = {k: v for k, v in o.items() if k != "selecionar"}
                        n_cmp = {k: v for k, v in n.items() if k != "selecionar"}
                        if str(o_cmp) == str(n_cmp):
                            continue

                        ok, _ = atualizar_meta(
                            id_meta=int(n["id_meta"]),
                            meta=(n.get("meta") or "").strip(),
                            valor_alvo=float(n["valor_alvo"]) if n.get("valor_alvo") not in (None, "") else None,
                            status=n.get("status"),
                            horizonte="SEMESTRE",
                            dt_inicio=n.get("dt_inicio"),
                            dt_fim=n.get("dt_fim"),
                            tipo=n.get("tipo"),
                            fk_caixinha_id=None,
                        )
                        if ok:
                            okc += 1
                        else:
                            errc += 1

                    if okc:
                        st.success(f"{okc} alterações aplicadas.")
                        st.rerun()
                    if errc:
                        st.warning(f"{errc} alterações falharam (RLS/dados).")

                if bb1.button("🧹 Apagar marcadas", key=f"del_filhas_{id_mae}"):
                    rows = edited.to_dict("records")
                    todel = [r for r in rows if r.get("selecionar")]
                    if not todel:
                        st.info("Marque 'Apagar?' nas metinhas.")
                    else:
                        okc, errc = 0, 0
                        for r in todel:
                            ok, _ = deletar_meta(int(r["id_meta"]))
                            if ok:
                                okc += 1
                            else:
                                errc += 1
                        if okc:
                            st.success(f"{okc} metinha(s) apagada(s).")
                            st.rerun()
                        if errc:
                            st.warning(f"{errc} falharam.")

            else:
                st.info("Ainda não há metinhas para essa meta.")

            # -------------------------
            # CRIAR METINHA
            # -------------------------
            with st.form(f"form_add_filha_{id_mae}"):
                cc1, cc2, cc3 = st.columns(3)
                filha_txt = cc1.text_input("Nova metinha", key=f"filha_txt_{id_mae}")
                filha_status = cc2.selectbox("Status", STATUS_META_OPTIONS, index=0, key=f"filha_status_{id_mae}")
                filha_tipo = cc3.selectbox("Tipo", TIPO_META_OPTIONS, index=0, key=f"filha_tipo_{id_mae}")

                dd1, dd2, dd3 = st.columns(3)
                filha_di = dd1.date_input("Início (opcional)", value=None, key=f"filha_di_{id_mae}")
                filha_df = dd2.date_input("Fim (opcional)", value=None, key=f"filha_df_{id_mae}")
                filha_alvo = dd3.number_input("Valor alvo (opcional)", min_value=0.0, step=0.01, format="%.2f", key=f"filha_alvo_{id_mae}")

                add = st.form_submit_button("Adicionar metinha")
                if add:
                    if not filha_txt.strip():
                        st.error("Metinha precisa de texto.")
                    else:
                        ok, msg = inserir_meta(
                            meta=filha_txt.strip(),
                            valor_alvo=filha_alvo if filha_alvo and filha_alvo > 0 else None,
                            status=filha_status,
                            horizonte="SEMESTRE",
                            dt_inicio=filha_di if isinstance(filha_di, datetime.date) else None,
                            dt_fim=filha_df if isinstance(filha_df, datetime.date) else None,
                            tipo=filha_tipo,
                            fk_caixinha_id=None,
                            meta_pai_id=id_mae,
                        )
                        if ok:
                            st.success("Metinha criada!")
                            st.rerun()
                        else:
                            st.error(msg)
# ======================================================================================
# MÓDULO: PRIORIDADES (SEMESTRE / ANO)
# ======================================================================================
elif opcao == "⭐ Prioridades":
    st.title("⭐ Prioridades (Casal)")

    hoje = datetime.date.today()
    c1, c2 = st.columns(2)
    ano = c1.selectbox("Ano", list(range(hoje.year - 1, hoje.year + 3)), index=1)
    horizonte = c2.selectbox("Horizonte", HORIZONTE_PRIORIDADE_OPTIONS, index=0)

    # Sugestão de período padrão
    if horizonte == "SEMESTRE":
        semestre = st.selectbox("Semestre", [1, 2], index=0 if hoje.month <= 6 else 1)
        if semestre == 1:
            p_ini_default = datetime.date(ano, 1, 1)
            p_fim_default = datetime.date(ano, 6, 30)
        else:
            p_ini_default = datetime.date(ano, 7, 1)
            p_fim_default = datetime.date(ano, 12, 31)
    else:
        p_ini_default = datetime.date(ano, 1, 1)
        p_fim_default = datetime.date(ano, 12, 31)

    with st.expander("➕ Criar prioridade", expanded=False):
        with st.form("form_prioridade"):
            titulo = st.text_input("Título", placeholder="Ex: Q1 - reorganizar rotina financeira / fortalecer saúde")
            descricao = st.text_area("Descrição (opcional)", height=80)

            c3, c4, c5 = st.columns(3)
            periodo_inicio = c3.date_input("Início", value=p_ini_default)
            periodo_fim = c4.date_input("Fim", value=p_fim_default)
            status = c5.selectbox("Status", STATUS_PRIORIDADE_OPTIONS, index=0)

            sub = st.form_submit_button("Criar")
            if sub:
                if not titulo.strip():
                    st.error("Título é obrigatório.")
                elif periodo_fim < periodo_inicio:
                    st.error("Período inválido: fim < início.")
                else:
                    ok, msg = inserir_prioridade(
                        titulo=titulo.strip(),
                        descricao=descricao.strip() if descricao else None,
                        horizonte=horizonte,
                        periodo_inicio=periodo_inicio,
                        periodo_fim=periodo_fim,
                        status=status,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()
    df = carregar_prioridades(ano=ano, horizonte=horizonte)

    if df is None or df.empty:
        st.info("Nenhuma prioridade cadastrada nesse filtro.")
        st.stop()

    df = df.copy()
    df["selecionar"] = False

    cols = ["selecionar", "id_prioridade", "titulo", "status", "periodo_inicio", "periodo_fim", "descricao", "horizonte"]
    df_show = df[[c for c in cols if c in df.columns]].copy()

    edited = st.data_editor(
        df_show,
        use_container_width=True,
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Apagar?"),
            "id_prioridade": st.column_config.NumberColumn("ID", disabled=True),
            "titulo": st.column_config.TextColumn("Título", required=True),
            "status": st.column_config.SelectboxColumn("Status", options=STATUS_PRIORIDADE_OPTIONS, required=True),
            "periodo_inicio": st.column_config.DateColumn("Início", required=True),
            "periodo_fim": st.column_config.DateColumn("Fim", required=True),
            "descricao": st.column_config.TextColumn("Descrição"),
            "horizonte": st.column_config.SelectboxColumn("Horizonte", options=HORIZONTE_PRIORIDADE_OPTIONS, required=True),
        },
        num_rows="fixed",
    )

    b1, b2 = st.columns(2)

    if b2.button("💾 Salvar alterações"):
        orig = df_show.to_dict("records")
        new = edited.to_dict("records")
        okc, errc = 0, 0

        for o, n in zip(orig, new):
            # deletar marcado
            if n.get("selecionar"):
                continue

            o_cmp = {k: v for k, v in o.items() if k != "selecionar"}
            n_cmp = {k: v for k, v in n.items() if k != "selecionar"}
            if str(o_cmp) == str(n_cmp):
                continue

            ok, _ = atualizar_prioridade(
                id_prioridade=int(n["id_prioridade"]),
                titulo=(n.get("titulo") or "").strip(),
                descricao=n.get("descricao"),
                horizonte=n.get("horizonte"),
                periodo_inicio=n.get("periodo_inicio"),
                periodo_fim=n.get("periodo_fim"),
                status=n.get("status"),
            )
            if ok:
                okc += 1
            else:
                errc += 1

        if okc:
            st.success(f"{okc} prioridade(s) atualizada(s).")
            st.rerun()
        if errc:
            st.warning(f"{errc} falharam (RLS/dados).")

    if b1.button("🗑️ Deletar selecionadas"):
        rows = edited.to_dict("records")
        todel = [r for r in rows if r.get("selecionar")]
        if not todel:
            st.info("Marque 'Apagar?' para deletar.")
        else:
            okc, errc = 0, 0
            for r in todel:
                ok, _ = deletar_prioridade(int(r["id_prioridade"]))
                if ok:
                    okc += 1
                else:
                    errc += 1
            if okc:
                st.success(f"{okc} prioridade(s) deletada(s).")
                st.rerun()
            if errc:
                st.warning(f"{errc} falharam (RLS?).")

    # Pequena regra de UX (não trava, só alerta)
    st.caption("Dica Rico Zen: evite ter muitas prioridades ATIVAS no mesmo período.")
    ativas = edited[edited["status"] == "ATIVA"]
    if len(ativas) > 5:
        st.warning(f"Você tem {len(ativas)} prioridades ATIVAS nesse filtro. Talvez valha reduzir para 3–5.")

# ======================================================================================
# MÓDULO: CÍRCULO DA VIDA (CASAL)
# ======================================================================================
elif opcao == "🧘 Círculo da Vida":
    st.title("🧘 Círculo da Vida (Casal)")

    hoje = datetime.date.today()
    c1, c2 = st.columns(2)
    ano = c1.selectbox("Ano", list(range(hoje.year - 1, hoje.year + 3)), index=1)

    # Selecionar mês
    mes_num = c2.selectbox(
        "Mês",
        list(range(1, 13)),
        index=hoje.month - 1,
        format_func=lambda m: [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ][m]
    )

    mes_ref = datetime.date(ano, mes_num, 1)

    areas = carregar_areas_vida()
    if not areas:
        st.warning("Nenhuma área ativa encontrada em area_vida. Cadastre ou ative pelo banco.")
        st.stop()

    df_mes = carregar_checkin_mes(mes_ref)

    # mapa (area_nome -> dados)
    dados = {}
    if df_mes is not None and not df_mes.empty:
        for _, r in df_mes.iterrows():
            dados[r["area_nome"]] = {
                "nota": int(r.get("nota", 0)),
                "comentario": r.get("comentario") or ""
            }

    st.subheader("Check-in do mês")
    st.caption("Dica: note o mês como o primeiro dia do mês (o sistema faz isso automaticamente).")

    # Form para salvar tudo de uma vez
    with st.form("form_circulo"):
        inputs = []
        for a in areas:
            nome = a["nome"]
            default_nota = dados.get(nome, {}).get("nota", 0)
            default_com = dados.get(nome, {}).get("comentario", "")

            st.markdown(f"### {nome}")
            coln1, coln2 = st.columns([1, 2])
            nota = coln1.slider(f"Nota - {nome}", min_value=0, max_value=10, value=int(default_nota), key=f"nota_{a['id_area']}")
            comentario = coln2.text_area(f"Comentário - {nome} (opcional)", value=default_com, height=80, key=f"com_{a['id_area']}")

            inputs.append((a["id_area"], nota, comentario))

        submitted = st.form_submit_button("💾 Salvar check-in do mês")

        if submitted:
            okc, errc = 0, 0
            msgs = []
            for id_area, nota, comentario in inputs:
                ok, msg = salvar_checkin_area(mes_ref=mes_ref, fk_area_id=id_area, nota=nota, comentario=comentario)
                msgs.append((ok, msg))
                if ok:
                    okc += 1
                else:
                    errc += 1

            if okc:
                st.success(f"{okc} área(s) salvas para {mes_ref.strftime('%m/%Y')}.")
            if errc:
                st.error(f"{errc} área(s) não foram salvas. Veja detalhes abaixo:")
                for ok, msg in msgs:
                    if not ok:
                        st.write("-", msg)
            st.rerun()

    st.divider()
    st.subheader("Histórico do ano")

    df_hist = historico_checkins_ano(ano)
    if df_hist is None or df_hist.empty:
        st.info("Sem histórico para este ano ainda.")
        st.stop()

    # Pivot: linhas = mes_ref, colunas = area_nome, valores = nota
    pivot = df_hist.pivot_table(index="mes_ref", columns="area_nome", values="nota", aggfunc="max").reset_index()
    pivot = pivot.sort_values("mes_ref", ascending=True)

    st.dataframe(pivot, use_container_width=True)
# ======================================================================================
# MÓDULO: DESAPEGO CONSCIENTE
# ======================================================================================
elif opcao == "🧺 Desapego consciente":
    st.title("🧺 Desapego consciente")

    st.caption("Use para revisar gastos recorrentes e decidir: manter, cortar, testar ou renegociar. "
               "Quando fizer sentido, crie um Planejado direto daqui (pessoa = Casal).")

    # CREATE
    with st.expander("➕ Novo item", expanded=False):
        with st.form("form_desapego"):
            c1, c2, c3, c4 = st.columns(4)
            nome_item = c1.text_input("Item", placeholder="Ex: Netflix, iCloud, Academia, Plano celular...")
            decisao = c2.selectbox("Decisão", DECISAO_DESAPEGO_OPTIONS, index=2)  # TESTAR
            frequencia = c3.selectbox("Frequência", RECORRENCIA_OPTIONS, index=0)
            ativo = c4.checkbox("Ativo?", value=True)

            c5, c6, c7 = st.columns(3)
            valor_estimado = c5.number_input("Valor estimado (opcional)", min_value=0.0, step=0.01, format="%.2f")
            prazo = c6.date_input("Prazo revisão (opcional)", value=None)
            cx_nome = c7.selectbox("Caixinha (opcional)", ["(sem caixinha)"] + list(caixinhas_map.keys()))
            fk_caixinha_id = None if cx_nome == "(sem caixinha)" else caixinhas_map.get(cx_nome)

            observacao = st.text_area("Observação (opcional)", height=80)

            sub = st.form_submit_button("Criar item")

            if sub:
                if not nome_item.strip():
                    st.error("O campo Item é obrigatório.")
                else:
                    ok, msg = inserir_desapego_item(
                        nome_item=nome_item.strip(),
                        fk_caixinha_id=fk_caixinha_id,
                        valor_estimado=valor_estimado if valor_estimado and valor_estimado > 0 else None,
                        frequencia=frequencia,
                        decisao=decisao,
                        prazo_revisao=prazo if isinstance(prazo, datetime.date) else None,
                        observacao=observacao.strip() if observacao else None,
                        ativo=ativo,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()

    # READ
    df = carregar_desapego()
    if df is None or df.empty:
        st.info("Nenhum item ainda.")
        st.stop()

    df = df.copy()
    df["selecionar"] = False
    df["criar_planejado"] = False

    cols = [
        "selecionar", "criar_planejado",
        "id_item", "nome_item", "decisao", "frequencia", "valor_estimado",
        "nome_caixinha", "prazo_revisao", "ativo", "observacao"
    ]
    df_show = df[[c for c in cols if c in df.columns]].copy()

    edited = st.data_editor(
        df_show,
        use_container_width=True,
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Apagar?"),
            "criar_planejado": st.column_config.CheckboxColumn("Criar Planejado?"),
            "id_item": st.column_config.NumberColumn("ID", disabled=True),
            "nome_item": st.column_config.TextColumn("Item", required=True),
            "decisao": st.column_config.SelectboxColumn("Decisão", options=DECISAO_DESAPEGO_OPTIONS, required=True),
            "frequencia": st.column_config.SelectboxColumn("Frequência", options=RECORRENCIA_OPTIONS, required=True),
            "valor_estimado": st.column_config.NumberColumn("Valor estimado", format="R$ %.2f"),
            "nome_caixinha": st.column_config.SelectboxColumn("Caixinha", options=[""] + list(caixinhas_map.keys())),
            "prazo_revisao": st.column_config.DateColumn("Prazo revisão"),
            "ativo": st.column_config.CheckboxColumn("Ativo"),
            "observacao": st.column_config.TextColumn("Observação"),
        },
        num_rows="fixed",
    )

    b1, b2, b3 = st.columns(3)

    # SALVAR ALTERAÇÕES
    if b2.button("💾 Salvar alterações"):
        orig = df_show.to_dict("records")
        new = edited.to_dict("records")
        okc, errc = 0, 0

        for o, n in zip(orig, new):
            if n.get("selecionar"):
                continue

            o_cmp = {k: v for k, v in o.items() if k not in ("selecionar", "criar_planejado")}
            n_cmp = {k: v for k, v in n.items() if k not in ("selecionar", "criar_planejado")}
            if str(o_cmp) == str(n_cmp):
                continue

            fk = caixinhas_map.get(n["nome_caixinha"]) if n.get("nome_caixinha") else None
            ok, _ = atualizar_desapego_item(
                id_item=int(n["id_item"]),
                nome_item=(n.get("nome_item") or "").strip(),
                fk_caixinha_id=fk,
                valor_estimado=float(n["valor_estimado"]) if n.get("valor_estimado") not in (None, "") else None,
                frequencia=n.get("frequencia"),
                decisao=n.get("decisao"),
                prazo_revisao=n.get("prazo_revisao"),
                observacao=n.get("observacao"),
                ativo=bool(n.get("ativo", True)),
            )
            if ok:
                okc += 1
            else:
                errc += 1

        if okc:
            st.success(f"{okc} item(ns) atualizado(s).")
            st.rerun()
        if errc:
            st.warning(f"{errc} falharam (RLS/dados).")

    # CRIAR PLANEJADO
    if b3.button("🔁 Criar Planejado a partir dos marcados"):
        rows = edited.to_dict("records")
        marcados = [r for r in rows if r.get("criar_planejado")]

        if not marcados:
            st.info("Marque 'Criar Planejado?' nos itens desejados.")
        else:
            okc, errc = 0, 0
            msgs = []
            for r in marcados:
                ok, msg = criar_planejado_de_desapego(int(r["id_item"]))
                msgs.append(msg)
                if ok:
                    okc += 1
                else:
                    errc += 1

            if okc:
                st.success(f"{okc} planejado(s) criado(s).")
            if errc:
                st.warning(f"{errc} item(ns) não geraram planejado.")
            for m in msgs[:12]:
                st.write("-", m)
            st.rerun()

    # DELETAR
    if b1.button("🗑️ Deletar selecionados"):
        rows = edited.to_dict("records")
        todel = [r for r in rows if r.get("selecionar")]
        if not todel:
            st.info("Marque 'Apagar?' para deletar.")
        else:
            okc, errc = 0, 0
            for r in todel:
                ok, _ = deletar_desapego_item(int(r["id_item"]))
                if ok:
                    okc += 1
                else:
                    errc += 1
            if okc:
                st.success(f"{okc} item(ns) deletado(s).")
                st.rerun()
            if errc:
                st.warning(f"{errc} falharam (RLS?).")

else:
    st.info("Módulo não encontrado.")
