import datetime
import pandas as pd
import streamlit as st

from db import get_connection, inserir_movimentacao, buscar_opcoes_moeda, buscar_opcoes_conta, buscar_opcoes_tipo, buscar_opcoes_categoria, buscar_planejados_periodo, carregar_cambios, inserir_cambio

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
moedas = buscar_opcoes_moeda()         # permanece igual: { 'BRL': 1, 'USD': 2, ... }
contas_info = buscar_opcoes_conta()     # agora retorna: { 'Nubank': (1, 'BRL'), 'Bradesco': (2, 'USD'), ... }
tipos = buscar_opcoes_tipo()           # { 'Despesa': 1, 'Receita': 2, ... }
categorias = buscar_opcoes_categoria()  # { 'Aluguel': 1, 'Mercado': 2, ... }



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

    # --- BOTÕES SUPERIORES ---
    st.header("Importação e Filtros")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.button("📥 Importar CSV")
    with col2:
        st.button("📅 Pendentes até ontem")
    with col3:
        st.button("📆 Próximos 7 dias")
    with col4:
        st.button("📆 Próximos 30 dias")

    # --- FORMULÁRIO DE NOVA MOVIMENTAÇÃO ---
    if st.button("➕ Inserir nova movimentação"):
        st.session_state.mostrar_formulario = not st.session_state.mostrar_formulario

    if st.session_state.mostrar_formulario:
        st.subheader("Inserir nova movimentação")
        with st.form("nova_movimentacao"):
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

           # Dentro do seu if submitted: (formulário de nova movimentação)
            if submitted:
                # Calcular o valor convertido EM MEMÓRIA (para usar na tela, mas NÃO armazenar na tabela)
                valor_convertido = valor
                # Extraímos a tupla (id_conta, sigla_moeda) usando o nome da conta selecionada
                id_conta, sigla_moeda = contas_info[conta]

                # Calculamos valor_convertido segundo a sigla da moeda da conta
                if sigla_moeda == "ARS":
                    valor_convertido = valor / 180
                elif sigla_moeda == "USD":
                    valor_convertido = valor * 5
                else:  # BRL ou outra
                    valor_convertido = valor


                # Agora chamamos inserir_movimentacao com os 7 parâmetros EXATOS
                inserir_movimentacao(
                    data,                            # DATE
                    descricao,                       # TEXT
                    valor,                           # NUMERIC
                    id_conta,                   # ID da conta (FK)
                    tipos[tipo],                     # ID do tipo_movimentacao (FK)
                    categorias[categoria],           # ID da categoria (FK)
                    status                           # 'pendente' / 'confirmado' / 'cancelado'
                )
                st.success("✅ Movimentação registrada com sucesso!")



    # --- TABELA EXEMPLO DE MOVIMENTAÇÕES ---
    st.subheader("📋 Movimentações")

    def carregar_movimentacoes():
        conn = get_connection()
        query = """
            SELECT 
                m.id_mov,
                m.data,
                m.descricao,
                m.valor,
                mo.moeda AS moeda,
                c.nome_conta AS conta,
                tm.nome AS tipo,
                tm.natureza,
                cat.nome AS categoria,
                m.status
            FROM movimentacao m
            JOIN conta c ON c.id_conta = m.id_conta
            JOIN moeda mo ON mo.id_moeda = c.id_moeda
            JOIN tipo_movimentacao tm ON tm.id_tipo = m.id_tipo
            JOIN categoria cat ON cat.id_categoria = m.id_categoria
            ORDER BY m.data, m.id_mov
        """
        df = pd.read_sql(query, conn)

        # Conversão de moeda para reais
        def converter_valor(row):
            if row['moeda'] == 'ARS':
                return row['valor'] / 180
            elif row['moeda'] == 'USD':
                return row['valor'] * 5
            else:
                return row['valor']

        df['valor_convertido'] = df.apply(converter_valor, axis=1)

        # Ajuste de sinal com base na natureza (entrada ou saída)
        df['valor_ajustado'] = df.apply(
            lambda row: row['valor_convertido'] if row['natureza'] == 'entrada' else -row['valor_convertido'],
            axis=1
        )

        # Cálculo do saldo após movimentação por conta
        df['saldo_pos_movimentacao'] = 0.0
        contas = df['conta'].unique()
        for conta in contas:
            filtro = df['conta'] == conta
            df.loc[filtro, 'saldo_pos_movimentacao'] = df.loc[filtro, 'valor_ajustado'].cumsum()

        # Ajusta formato final do DataFrame para exibição
        df = df[[
            'id_mov', 'data', 'descricao', 'valor', 'moeda', 'conta',
            'valor_convertido', 'tipo', 'categoria', 'saldo_pos_movimentacao', 'status'
        ]]
        return df

    df = carregar_movimentacoes()
    status_options = ["pendente", "confirmado", "cancelado"]

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        column_config={
            # id_mov é a PK e ficará oculta (readonly):
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
            "saldo_pos_movimentacao": st.column_config.NumberColumn("Saldo após transação", format="%.2f"),
            "status": st.column_config.SelectboxColumn("Status", options=status_options),
        },
        num_rows="dynamic"
    )

    # Botão para gravar alterações no banco (você implementa o UPDATE conforme precisar)
    if st.button("💾 Salvar alterações"):
        conn = get_connection()
        cur = conn.cursor()
        # Para cada linha do edited_df, faremos UPDATE:
        for row in edited_df.itertuples():
            # row.id_mov, row.data, row.descricao, row.valor, row.conta, row.status
            id_mov_atual = row.id_mov

            nova_data      = row.data
            nova_desc      = row.descricao
            novo_valor     = row.valor
            novo_status    = row.status
            # Para atualizar id_conta, extraímos o ID a partir do nome da conta:
            id_conta_novo  = contas_info[row.conta][0]

            # Montar e executar o UPDATE:
            cur.execute(
                """
                UPDATE movimentacao
                SET data = %s,
                    descricao = %s,
                    valor = %s,
                    id_conta = %s,
                    status = %s
                WHERE id_mov = %s
                """,
                (nova_data, nova_desc, novo_valor, id_conta_novo, novo_status, id_mov_atual)
            )
        conn.commit()
        cur.close()
        conn.close()
        st.success("✅ Movimentações atualizadas no banco.")


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

                inserir_cambio(
                    data_cambio,
                    id_conta_origem,
                    id_conta_destino,
                    valor_vendido,
                    valor_comprado
                )

                st.success("✅ Câmbio registrado com sucesso.")



    # Tabela de câmbios (dados simulados)
    df_cambio = carregar_cambios()
    st.dataframe(df_cambio, use_container_width=True)


elif opcao == "🗓️ Planejamentos":
    if "mostrar_planejado" not in st.session_state:
        st.session_state.mostrar_planejado = False

    st.header("🗓️ Movimentações Planejadas")

    # 1) Formulário de cadastro de novo planejado
    if st.button("➕ Inserir movimentação planejada"):
        st.session_state.mostrar_planejado = not st.session_state.mostrar_planejado

    if st.session_state.mostrar_planejado:
        st.subheader("Nova movimentação planejada")
        with st.form("nova_planejada"):
            col1, col2, col3 = st.columns(3)
            recorrencia = col1.selectbox("Recorrência", ["Mensal", "Semanal", "Anual"])
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
            data_inicial = st.date_input("Data inicial (opcional)", value=datetime.date.today())

            data_final = st.date_input("Data final da recorrência (opcional)", value=None)

            submitted_plan = st.form_submit_button("Salvar planejada")
            if submitted_plan:
                conn = get_connection()
                cur = conn.cursor()
                sql_insere_planejado = """
                    INSERT INTO planejado (
                        recorrencia,
                        dia,
                        valor,
                        id_moeda,
                        descricao,
                        id_categoria,
                        dt_inicial,
                        dt_final,
                        id_tipo
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                # Extrair id_moeda da seleção
                id_moeda = moedas[moeda]
                tipos = buscar_opcoes_tipo()
                id_tipo = tipos[tipo_mov]

                cur.execute(sql_insere_planejado, (
                    recorrencia,
                    dia,
                    valor,
                    id_moeda,
                    descricao,
                    categorias[categoria],
                    data_inicial,
                    data_final if data_final else None,
                    id_tipo
                ))
                conn.commit()
                cur.close()
                conn.close()

                st.success("📅 Planejamento salvo com sucesso!")

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

                        inserir_movimentacao(
                            data_mov,
                            descricao,
                            valor,
                            id_conta_para_inserir,
                            id_tipo,
                            id_categoria,
                            "pendente"
                        )
                        total_inseridas += 1
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

                        inserir_movimentacao(
                            dia_corrente,
                            descricao,
                            valor,
                            id_conta_para_inserir,
                            id_tipo,
                            id_categoria,
                            "pendente"
                        )
                        total_inseridas += 1

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

                        inserir_movimentacao(
                            data_mov,
                            descricao,
                            valor,
                            id_conta_para_inserir,
                            id_tipo,
                            id_categoria,
                            "pendente"
                        )
                        total_inseridas += 1
                    ano += 1

        st.success(f"✅ Foram inseridas {total_inseridas} movimentações pendentes.")

    st.subheader("📋 Planejamentos Cadastrados")
    lista_planejados = buscar_planejados_periodo()
    if lista_planejados:
        df_planejados = pd.DataFrame(lista_planejados)
        st.dataframe(df_planejados, use_container_width=True)
    else:
        st.write("Nenhum planejamento cadastrado no momento.")
