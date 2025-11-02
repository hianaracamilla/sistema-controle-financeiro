# Copyright (c) 2025 Hianara Camilla
# Licensed under CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/)

import datetime
import pandas as pd
import  streamlit as st

from db import (
    get_connection,
    inserir_movimentacao,
    atualizar_movimentacao,
    carregar_movimentacoes,
    movimentacao_existe,
    inserir_planejado,
    atualizar_planejado,
    buscar_planejados_periodo,
    inserir_cambio,
    carregar_cambios,
    inserir_recebido_pj,
    buscar_opcoes_moeda,
    buscar_opcoes_conta,
    buscar_opcoes_tipo,
    buscar_opcoes_categoria,
    movimentacoes_pj_ja_existem,
    deletar_movimentacao,
    inserir_transferencia_entre_contas,
    buscar_ultima_cotacao_por_conta
)

# Conta padrão (fictícia) para gerar movimentações de planejados
DEFAULT_CONTA_POR_MOEDA = {
    1: 97,   # ARS → id_conta 97
    2: 98,   # BRL → id_conta 98
    3: 99,   # USD → id_conta 99
}


try:
    conn = get_connection()
    conn.close()   # usando somente para testar a conexão
    st.sidebar.success("✅ Conectado ao banco de dados")
except Exception as e:
    st.sidebar.error(f"❌ Erro de conexão: {e}")


# Buscar as listas reais de opções no banco
moedas = buscar_opcoes_moeda()        
contas_info = buscar_opcoes_conta()     
tipos = buscar_opcoes_tipo()         
categorias = buscar_opcoes_categoria()  



# --- Sidebar de navegação ---
st.sidebar.title("💰 Sistema Financeiro")
opcao = st.sidebar.radio(
    "Navegar para:",
    ["📥 Movimentações", "💱 Câmbio", "🗓️ Planejamentos"]
)


if opcao == "📥 Movimentações":
    # --- TELA DE MOVIMENTAÇÕES ---
    if "mostrar_formulario" not in st.session_state:
        st.session_state.mostrar_formulario = False

    # Título da página
    st.title("📊 Controle de Movimentações Financeiras")

    # Cotações padrão
    if "cotacao_ARS" not in st.session_state:
        st.session_state.cotacao_ARS = 180.0
    if "cotacao_USD" not in st.session_state:
        st.session_state.cotacao_USD = 5.0

    with st.expander("💱 Ajustar cotações padrão (para valores pendentes)", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state.cotacao_ARS = st.number_input("Cotação ARS → BRL", value=st.session_state.cotacao_ARS, min_value=0.01, step=0.1)
        with col_b:
            st.session_state.cotacao_USD = st.number_input("Cotação USD → BRL", value=st.session_state.cotacao_USD, min_value=0.01, step=0.1)


    # --- BOTÕES SUPERIORES ---
    st.header("Importação e Filtros")

    with st.expander("🔎 Filtros de busca", expanded=True):
        st.markdown("### 🎯 Filtro por período")

        col_data1, col_data2 = st.columns(2)
        with col_data1:
            data_inicio_filtro = st.date_input("Data inicial", value=None, key="data_inicio_filtro")
        with col_data2:
            data_fim_filtro = st.date_input("Data final", value=None, key="data_fim_filtro")

        st.markdown("### 🧮 Filtros adicionais")

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            conta_filtro = st.selectbox(
                "Filtrar por conta",
                options=["Todas"] + list(contas_info.keys()),
                index=0
            )

        with col_f2:
            categoria_filtro = st.selectbox(
                "Filtrar por categoria",
                options=["Todas"] + list(categorias.keys()),
                index=0
            )


        if "filtro_mov" not in st.session_state:
            st.session_state.filtro_mov = None
        filtro_personalizado = st.session_state.get("filtro_mov", None)
        
        st.markdown("### ⚡ Filtros rápidos")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("📅 Ultimos 7 dias"):
                st.session_state.filtro_mov = ("ate_ontem", datetime.date.today() - datetime.timedelta(days=7))
                st.rerun()
        with col2:
            if st.button("📆 Próximos 7 dias"):
                st.session_state.filtro_mov = ("proximos_7", datetime.date.today() + datetime.timedelta(days=7))
                st.rerun()
        with col3:
            if st.button("⏳ Todas pendentes"):
                st.session_state.filtro_mov = ("somente_pendentes", None)
                st.rerun()
        with col4:
            if st.button("❌ Limpar Filtros"):
                st.session_state.filtro_mov = None
                st.rerun()
        



    df = carregar_movimentacoes()
    df["data"] = pd.to_datetime(df["data"])

    # AQUI: adiciona a coluna com ID da conta para ser usada na função
    df["id_conta"] = df["conta"].map(lambda nome: contas_info[nome][0] if nome in contas_info else None)

    filtro_personalizado = st.session_state.get("filtro_mov", None)

    # ✅ Filtro por intervalo de datas (manual) — sempre aplicado
    if data_inicio_filtro:
        df = df[df["data"] >= pd.Timestamp(data_inicio_filtro)]
    if data_fim_filtro:
        df = df[df["data"] <= pd.Timestamp(data_fim_filtro)]


    # Filtro por conta (nome)
    if conta_filtro != "Todas":
        df = df[df["conta"] == conta_filtro]

    # Filtro por categoria (nome)
    if categoria_filtro != "Todas":
        df = df[df["categoria"] == categoria_filtro]


    # ✅ Filtros especiais baseados nos botões
    if filtro_personalizado:
        tipo_filtro, data_limite = filtro_personalizado
        hoje = datetime.date.today()
        if tipo_filtro == "ate_ontem":
            df = df[(df["data"] <= data_limite) & (df["status"] == "pendente")]
        elif tipo_filtro == "proximos_7":
            df = df[(df["data"] > hoje) & (df["data"] <= data_limite) & (df["status"] == "pendente")]
        elif tipo_filtro == "somente_pendentes":
            df = df[df["status"] == "pendente"]




    # --- FORMULÁRIO DE NOVA MOVIMENTAÇÃO ---
    with st.expander("➕ Inserir nova movimentação", expanded=st.session_state.mostrar_formulario):
        with st.form("nova_movimentacao"):
            st.markdown("Preencha os dados abaixo para adicionar uma nova movimentação:")

            col1, col2, col3 = st.columns(3)
            data = col1.date_input("Data", value=datetime.date.today())
            descricao = col2.text_input("Descrição")
            valor = col3.number_input("Valor", min_value=0.0, step=0.01)

            col4, col5 = st.columns(2)
            conta = col5.selectbox("Conta", list(contas_info.keys()))
            tipo = st.selectbox("Tipo de movimentação", list(tipos.keys()))
            categoria = st.selectbox("Categoria", list(categorias.keys()))
            status = st.selectbox("Status", ["pendente", "confirmado", "cancelado"])

            submitted = st.form_submit_button("Salvar movimentação")
            if submitted:
                valor_convertido = valor
                id_conta, sigla_moeda = contas_info[conta]

                if sigla_moeda == "ARS":
                    valor_convertido = valor / st.session_state.cotacao_ARS
                elif sigla_moeda == "USD":
                    valor_convertido = valor * st.session_state.cotacao_USD
                else:
                    valor_convertido = valor


                cat_id = categorias[categoria]
                if cat_id == 18:
                    if not movimentacoes_pj_ja_existem(data):
                        sucesso, msg = inserir_recebido_pj(
                            data, descricao, valor,
                            id_conta, tipos[tipo]
                        )
                    else:
                        sucesso, msg = False, "❗ Movimentações PJ já existentes nesta data."
                elif cat_id == 28:
                    id_moeda = [moeda_id for moeda_sigla, moeda_id in moedas.items() if moeda_sigla == sigla_moeda][0]
                    sucesso, msg = inserir_transferencia_entre_contas(
                        data, descricao, valor, id_moeda
                    )
                else:
                    sucesso, msg = inserir_movimentacao(
                        data, descricao, valor,
                        id_conta, tipos[tipo], cat_id, status
                    )

                if sucesso:
                    st.success(msg)
                else:
                    st.error(msg)



    # --- TABELA MOVIMENTAÇÕES ---
    st.subheader("📋 Visualização das movimentações")

    def converter_valor(row):
        sigla_moeda = row["moeda"]
        status = row["status"]
        valor = row["valor"]
        id_conta = row["id_conta"]

        data_mov = row["data"]
        if isinstance(data_mov, pd.Timestamp):
            data_mov = data_mov.date()

        if sigla_moeda == "BRL" or not sigla_moeda:
            return valor

        if status == "pendente":
            if sigla_moeda == "ARS":
                return valor / st.session_state.cotacao_ARS
            elif sigla_moeda == "USD":
                return valor * st.session_state.cotacao_USD
            else:
                return valor

        elif status == "confirmado":
            cotacao_real = buscar_ultima_cotacao_por_conta(id_conta, data_mov)
            if cotacao_real:
                return valor * cotacao_real  # pois é valor estrangeiro → BRL
            return valor  # fallback

        else:
            return valor



    # AQUI: aplica a função usando a coluna já criada
    df["valor_convertido"] = df.apply(converter_valor, axis=1)

    # Ajuste de sinal na moeda original
    df['valor_ajustado_moeda'] = df.apply(
        lambda row: row['valor'] if row['natureza'] == 'entrada' else -row['valor'],
        axis=1
    )

    # Cálculo do saldo após movimentação por conta, na moeda original
    df['saldo_pos_movimentacao'] = 0.0
    for conta in df['conta'].unique():
        filtro = df['conta'] == conta
        df.loc[filtro, 'saldo_pos_movimentacao'] = df.loc[filtro, 'valor_ajustado_moeda'].cumsum()

    # Exibe saldo com moeda ao lado
    df['saldo_exibido'] = df['saldo_pos_movimentacao'].round(2).astype(str) + " " + df['moeda']

    df["selecionar"] = False
    df = df[[  # reorganiza as colunas
    'selecionar', 'id_mov', 'data', 'descricao', 'valor', 'moeda', 'valor_convertido',
    'conta', 'saldo_exibido', 'status', 'tipo', 'categoria', 'id_tipo', 'natureza'
    ]]



    edited_df = st.data_editor(
        df,
        use_container_width=True,
        column_config={
            # id_mov é a PK e ficará oculta (readonly):
            "selecionar": st.column_config.CheckboxColumn("Selecionar"),
            "id_mov": st.column_config.NumberColumn(
            "ID", help="(chave primária)", disabled=True
            ),
            "data": st.column_config.DateColumn("Data"),
            "descricao": st.column_config.TextColumn("Descrição"),
            "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
            "moeda": st.column_config.TextColumn("Moeda"),
            "conta": st.column_config.SelectboxColumn("Conta", options=list(contas_info.keys())),
            "valor_convertido": st.column_config.NumberColumn("Valor em reais", format="R$ %.2f"),
            "tipo": st.column_config.TextColumn("Tipo"),
            "categoria": st.column_config.TextColumn("Categoria"),
            'id_tipo': st.column_config.NumberColumn(
                "ID Tipo", help="(chave estrangeira)", disabled=True),
            "natureza": st.column_config.TextColumn("Natureza", disabled=True),
            "saldo_exibido": st.column_config.TextColumn("Saldo após transação"),
            "status": st.column_config.SelectboxColumn("Status", options=["pendente", "confirmado", "cancelado"]),
        },
        num_rows="dynamic"
    )

    # --- TOTAIS PENDENTES POR MOEDA ---
    st.markdown("### 💰 Totais pendentes por moeda")

    # Filtra pendentes
    df_pendentes = df[df["status"] == "pendente"].copy()

    # Aplica sinal com base na natureza
    df_pendentes["valor_ajustado"] = df_pendentes.apply(
        lambda row: row["valor"] if row["natureza"] == "entrada" else -row["valor"],
        axis=1
    )

    # Agrupa e mostra
    totais_pendentes = df_pendentes.groupby("moeda")["valor_ajustado"].sum().reset_index()

    if not totais_pendentes.empty:
        for _, row in totais_pendentes.iterrows():
            st.write(f"• {row['moeda']}: {row['valor_ajustado']:,.2f}")
    else:
        st.write("Nenhuma movimentação pendente nos filtros aplicados.")




    if st.button("🗑️ Deletar movimentações selecionadas"):
        deletadas = 0
        for linha in edited_df.to_dict("records"):
            if linha["selecionar"]:
                sucesso, msg = deletar_movimentacao(linha["id_mov"])
                if sucesso:
                    deletadas += 1
                else:
                    st.error(f"Erro ao deletar #{linha['id_mov']}: {msg}")
        st.success(f"🗑️ {deletadas} movimentações deletadas com sucesso.")
        st.rerun()

    if st.button("💾 Salvar alterações"):
        # Convertemos ambos em listas de dicts, na mesma ordem de linhas
        orig_records  = df.to_dict("records")
        edited_records = edited_df.to_dict("records")

        atualizacoes = 0

        # Para cada par (original, editado)...
        for orig, new in zip(orig_records, edited_records):
            # verifica se mudou algum dos campos editáveis
            campos_editaveis = ["data", "descricao", "valor", "conta", "status"]
            if any(orig[c] != new[c] for c in campos_editaveis):
                id_mov       = orig["id_mov"]
                nova_data    = new["data"]
                nova_desc    = new["descricao"]
                novo_valor   = new["valor"]
                novo_status  = new["status"]
                id_conta_novo = contas_info[new["conta"]][0]  # traduz nome da conta para id

                # Recupera tipo e categoria do original (não foram editáveis)
                id_tipo       = orig["id_tipo"]

                # Chama a função de atualização completa
                sucesso, msg = atualizar_movimentacao(
                    id_mov,
                    nova_data,
                    nova_desc,
                    novo_valor,
                    id_conta_novo,
                    id_tipo,
                    novo_status
                )

                if sucesso:
                    atualizacoes += 1
                else:
                    st.error(f"Erro ao atualizar #{id_mov}: {msg}")

        st.success(f"✅ {atualizacoes} movimentações atualizadas com sucesso.")
        st.rerun()

        # --- SESSÃO: SALDOS AGRUPADOS ---
    st.markdown("## 📊 Saldos Agrupados")

    # Ajuste de sinal na moeda original
    df['valor_ajustado_moeda'] = df.apply(
        lambda row: row['valor'] if row['natureza'] == 'entrada' else -row['valor'],
        axis=1
    )


    # Agrupamento por Pessoa x Moeda x Tipo de Conta
    st.subheader("👥 Pessoa x Moeda x Tipo de Conta")
    saldos_pessoa = df.groupby(["conta", "moeda"], as_index=False)["valor_ajustado_moeda"].sum()
    saldos_pessoa["pessoa"] = saldos_pessoa["conta"].apply(lambda x: x.split()[0])
    saldos_pessoa["tipo_conta"] = saldos_pessoa["conta"].apply(lambda x: x.split()[-1])
    saldos_pessoa = saldos_pessoa.groupby(["pessoa", "moeda", "tipo_conta"], as_index=False)["valor_ajustado_moeda"].sum()
    st.dataframe(saldos_pessoa, use_container_width=True)

    # Agrupamento por Moeda x Tipo de Conta
    st.subheader("💱 Moeda x Tipo de Conta")
    saldos_moeda_tipo = saldos_pessoa.groupby(["moeda", "tipo_conta"], as_index=False)["valor_ajustado_moeda"].sum()
    st.dataframe(saldos_moeda_tipo, use_container_width=True)

    # Gastos por Categoria Estratégica (exceto categoria 18: Recebido PJ)
    st.subheader("🧾 Gastos por Categoria Estratégica")
    gastos_categoria = df[df["id_tipo"] != 18].groupby("categoria", as_index=False)["valor_ajustado_moeda"].sum()
    gastos_categoria = gastos_categoria[gastos_categoria["valor_ajustado_moeda"] < 0]  # apenas gastos (valores negativos)
    gastos_categoria["valor_ajustado_moeda"] = gastos_categoria["valor_ajustado_moeda"].abs()  # mostra em positivo
    st.dataframe(gastos_categoria, use_container_width=True)



elif opcao == "💱 Câmbio":
    if "mostrar_cambio" not in st.session_state:
        st.session_state.mostrar_cambio = False

    # --- TELA DE CÂMBIO ---
    st.header("💱 Câmbio")

    # Formulário para novo câmbio
    if st.button("➕ Registrar novo câmbio"):
        st.session_state.mostrar_cambio = not st.session_state.mostrar_cambio

    if st.session_state.mostrar_cambio:
        st.subheader("Registrar novo câmbio")

        with st.form("novo_cambio"):
            col1, col2 = st.columns(2)

            data_cambio = col1.date_input("Data", value=datetime.date.today())
            conta_venda = col1.selectbox("Conta de origem", list(contas_info.keys()))
            valor_vendido = col1.number_input("Valor vendido", min_value=0.01)

            conta_compra = col2.selectbox("Conta de destino", list(contas_info.keys()))
            valor_comprado = col2.number_input("Valor comprado", min_value=0.01)

            submitted_cambio = st.form_submit_button("Registrar câmbio")
            if submitted_cambio:
                id_conta_origem = contas_info[conta_venda][0]
                id_conta_destino = contas_info[conta_compra][0]

                sucesso, msg = inserir_cambio(
                    data_cambio, id_conta_origem, id_conta_destino,
                    valor_vendido, valor_comprado
                )
                if sucesso: st.success(msg)
                else:        st.error(msg)



    # Tabela de câmbios (dados simulados)
    df_cambio = carregar_cambios()
    st.subheader("📋 Histórico de Câmbios")
    st.dataframe(df_cambio, use_container_width=True)


elif opcao == "🗓️ Planejamentos":
    if "mostrar_planejado" not in st.session_state:
        st.session_state.mostrar_planejado = False

    # --- TELA DE PLANEJAMENTOS ---
    st.title("🗓️ Planejamentos Financeiros")
        # Cotações padrão
    if "cotacao_ARS" not in st.session_state:
        st.session_state.cotacao_ARS = 180.0
    if "cotacao_USD" not in st.session_state:
        st.session_state.cotacao_USD = 5.0

    with st.expander("💱 Ajustar cotações padrão (para valores pendentes)", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state.cotacao_ARS = st.number_input("Cotação ARS → BRL", value=st.session_state.cotacao_ARS, min_value=0.01, step=0.1)
        with col_b:
            st.session_state.cotacao_USD = st.number_input("Cotação USD → BRL", value=st.session_state.cotacao_USD, min_value=0.01, step=0.1)


    st.header("🗓️ Movimentações Planejadas")

    # 1) Formulário de cadastro de novo planejado
    if st.button("➕ Inserir movimentação planejada"):
        st.session_state.mostrar_planejado = not st.session_state.mostrar_planejado

    if st.session_state.mostrar_planejado:
        st.subheader("Nova movimentação planejada")
        with st.form("nova_planejada"):
            col1, col2, col3 = st.columns(3)
            recorrencia = col1.selectbox("Recorrência", ["Mensal", "Semanal", "Semestral","Anual"])
            tipo_mov = col2.selectbox("Tipo", list(buscar_opcoes_tipo().keys()))
            dia = col3.number_input("Dia (para recorrência)", min_value=1, max_value=31)

            valor = st.number_input("Valor planejado", min_value=0.01)

            # Removemos o selectbox de Conta; incluímos Moeda
            moedas = buscar_opcoes_moeda()   # ex: { "BRL":1, "USD":2, "ARS":3 }
            moeda = st.selectbox("Moeda", list(moedas.keys()))

            descricao = st.text_input("Descrição")

            categorias = buscar_opcoes_categoria()
            categoria = st.selectbox("Categoria", list(categorias.keys()))

            # Data inicial (opcional)
            data_inicial = st.date_input("Data inicial (opcional)", value=None)

            data_final = st.date_input("Data final da recorrência (opcional)", value=None)

            submitted_plan = st.form_submit_button("Salvar planejada")
            if submitted_plan:
                sucesso, msg = inserir_planejado(
                    recorrencia,
                    dia,
                    valor,
                    moedas[moeda],
                    descricao,
                    categorias[categoria],
                    data_inicial,
                    data_final,
                    tipos[tipo_mov]
                )
                if sucesso: st.success(msg)
                else:       st.error(msg)

    st.markdown("---")
    st.subheader("📌 Gerar Movimentações a partir de Planejamentos")

    col_a, col_b = st.columns(2)
    with col_a:
        data_inicio = st.date_input("Data Início", value=datetime.date.today())
    with col_b:
        data_fim = st.date_input("Data Fim", value=(datetime.date.today() + datetime.timedelta(days=30)))

    if st.button("▶️ Gerar Movimentações Planejadas"):
        lista_planejados = buscar_planejados_periodo()
        total_inseridas = 0

        for p in lista_planejados:
            rec = p["recorrencia"]
            dia = p["dia"]
            valor = p["valor"]
            id_moeda = p["id_moeda"]
            descricao = p["descricao"]
            id_categoria = p["id_categoria"]
            dt_inicial = p["dt_inicial"]
            dt_final = p["dt_final"]
            id_tipo = p["id_tipo"]

            datas = []
            if rec == "mensal":
                d = data_inicio.replace(day=1)
                while d <= data_fim:
                    try:
                        data_mov = d.replace(day=dia)
                    except ValueError:
                        data_mov = None
                    if data_mov and (
                        data_inicio <= data_mov <= data_fim
                        and (dt_inicial is None or data_mov >= dt_inicial)
                        and (dt_final   is None or data_mov <= dt_final)
                    ):
                        
                        id_conta_para_inserir = DEFAULT_CONTA_POR_MOEDA.get(id_moeda)
                        if id_conta_para_inserir is None:
                           id_conta_para_inserir = DEFAULT_CONTA_POR_MOEDA[2]
                        if not movimentacao_existe(data_mov, descricao, id_categoria):   
                            if id_categoria == 18:
                                if not movimentacoes_pj_ja_existem(data_mov):
                                    inserir_recebido_pj(
                                        data_mov,
                                        valor,
                                        id_conta_para_inserir,
                                        id_tipo,
                                    )
                            else:
                                inserir_movimentacao(
                                    data_mov,                            # DATE
                                    descricao,                       # TEXT
                                    valor,                           # NUMERIC
                                    id_conta_para_inserir,                   # ID da conta (FK)
                                    id_tipo,                     # ID do tipo_movimentacao (FK)
                                    id_categoria,           # ID da categoria (FK)
                                    "pendente"                           # 'pendente' / 'confirmado' / 'cancelado'
                                )
                            total_inseridas += 1
                        else:
                        # opcional: registrar log ou exibir info
                            st.info(f"Movimentação já existente em {data_mov}: «{descricao}»")

                    if d.month == 12:
                        d = d.replace(year=d.year + 1, month=1)
                    else:
                        d = d.replace(month=d.month + 1)

            elif rec == "semanal":
                for i in range((data_fim - data_inicio).days + 1):
                    dia_corrente = data_inicio + datetime.timedelta(days=i)
                    if dia_corrente.isoweekday() == dia and (
                        (dt_inicial is None or dia_corrente >= dt_inicial)
                        and (dt_final   is None or dia_corrente <= dt_final)
                    ):
                        
                        id_conta_para_inserir = DEFAULT_CONTA_POR_MOEDA.get(id_moeda)
                        if id_conta_para_inserir is None:
                           id_conta_para_inserir = DEFAULT_CONTA_POR_MOEDA[2]
                        if not movimentacao_existe(dia_corrente, descricao, id_categoria):
                            if id_categoria == 18:
                                if not movimentacoes_pj_ja_existem(data_mov):
                                    inserir_recebido_pj(
                                        dia_corrente,
                                        valor,
                                        id_conta_para_inserir,
                                        id_tipo,
                                    )
                            else:
                                inserir_movimentacao(
                                    dia_corrente,                            # DATE
                                    descricao,                       # TEXT
                                    valor,                           # NUMERIC
                                    id_conta_para_inserir,                   # ID da conta (FK)
                                    id_tipo,                     # ID do tipo_movimentacao (FK)
                                    id_categoria,           # ID da categoria (FK)
                                    "pendente"                           # 'pendente' / 'confirmado' / 'cancelado'
                                )
                            total_inseridas += 1
                        else:
                        # opcional: registrar log ou exibir info
                            st.info(f"Movimentação já existente em {data_mov}: «{descricao}»")

            elif rec == "anual":
                ano = data_inicio.year
                while datetime.date(ano, 1, 1) <= data_fim:
                    try:
                        data_mov = datetime.date(ano, data_inicio.month, data_inicio.day)
                    except ValueError:
                        data_mov = None
                    if data_mov and (
                        data_inicio <= data_mov <= data_fim
                        and (dt_inicial is None or data_mov >= dt_inicial)
                        and (dt_final   is None or data_mov <= dt_final)
                    ):
                        
                        id_conta_para_inserir = DEFAULT_CONTA_POR_MOEDA.get(id_moeda)
                        if id_conta_para_inserir is None:
                           id_conta_para_inserir = DEFAULT_CONTA_POR_MOEDA[2]
                        if not movimentacao_existe(data_mov, descricao, id_categoria):
                            if id_categoria == 18:
                                if not movimentacoes_pj_ja_existem(data_mov):
                                    inserir_recebido_pj(
                                        data_mov,
                                        valor,
                                        id_conta_para_inserir,
                                        id_tipo,
                                    )
                            else:
                                inserir_movimentacao(
                                    data_mov,                            # DATE
                                    descricao,                       # TEXT
                                    valor,                           # NUMERIC
                                    id_conta_para_inserir,                   # ID da conta (FK)
                                    id_tipo,                     # ID do tipo_movimentacao (FK)
                                    id_categoria,           # ID da categoria (FK)
                                    "pendente"                           # 'pendente' / 'confirmado' / 'cancelado'
                                )
                            total_inseridas += 1
                        else:
                        # opcional: registrar log ou exibir info
                            st.info(f"Movimentação já existente em {data_mov}: «{descricao}»")
                    ano += 1

        st.success(f"✅ Foram inseridas {total_inseridas} movimentações pendentes.")

    st.subheader("📋 Planejamentos Cadastrados")
    lista_planejados = buscar_planejados_periodo()

    if lista_planejados:
        df_plan = pd.DataFrame(lista_planejados)
        edited_plan = st.data_editor(
            df_plan,
            use_container_width=True,
            column_config={
                "id_planejado": st.column_config.NumberColumn("ID", disabled=True),
                "recorrencia":  st.column_config.SelectboxColumn("Recorrência", options=["Mensal","Semanal","Anual"]),
                "dia":          st.column_config.NumberColumn("Dia", min_value=1, max_value=31),
                "valor":        st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "moeda":        st.column_config.TextColumn("Moeda", disabled=True),
                "descricao":    st.column_config.TextColumn("Descrição"),
                "categoria":    st.column_config.TextColumn("Categoria", disabled=True),
                "categoria_estrategica": st.column_config.TextColumn("Estratégia", disabled=True),
                "tipo":         st.column_config.TextColumn("Tipo", disabled=True),
                "dt_inicial":   st.column_config.DateColumn("Início"),
                "dt_final":     st.column_config.DateColumn("Fim")
            },
            num_rows="dynamic"
        )
        if st.button("💾 Salvar alterações de planejados"):
            # compara original e editado
            df_orig = pd.DataFrame(lista_planejados)
            for orig, new in zip(df_orig.to_dict('records'), edited_plan.to_dict('records')):
                # se mudou algum campo editável
                if any(orig[k] != new[k] for k in ["recorrencia","dia","valor","dt_inicial","dt_final","descricao"]):
                    sucesso, msg = atualizar_planejado(
                        new["id_planejado"],
                        new["recorrencia"],
                        new["dia"],
                        new["valor"],
                        orig["id_moeda"],      # moeda não editável na grid
                        new["descricao"],
                        orig["id_categoria"],  # idem categoria
                        new["dt_inicial"],
                        new["dt_final"],
                        orig["id_tipo"]
                    )
                    if not sucesso:
                        st.error(msg)
            st.success("Planejados atualizados.")
    else:
        st.write("Nenhum planejamento cadastrado.")


