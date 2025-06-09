# 💰 Sistema de Acompanhamento Financeiro Familiar

Este é um projeto desenvolvido por **Hianara Camilla**, distribuído sob a licença **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

Este repositório contém o projeto de um sistema de controle financeiro familiar. O objetivo é oferecer uma solução personalizada para organizar, planejar e acompanhar receitas, despesas, saldos, planejamentos e operações de câmbio — tudo de forma integrada, com suporte a múltiplas moedas.

## 🧭 Objetivo do Projeto

Desenvolver um sistema completo que permita:

- Consolidar contas e movimentações em diferentes moedas (BRL, USD, ARS)
- Planejar movimentações recorrentes (mensais, semanais e anuais)
- Acompanhar saldos por conta após cada movimentação
- Registrar e visualizar operações de câmbio (com taxa e dupla movimentação automática)
- Projetar movimentações futuras com base em planejamentos
- Visualizar e editar movimentações com status, saldo e valor convertido
- Automatizar rotinas financeiras familiares com transparência


## ✅ Etapas Concluídas

- [x] **Modelagem conceitual, lógica e física do banco de dados**
- [x] Criação do banco de dados em PostgreSQL
- [x] Criação das tabelas: `pessoa`,`moeda`, `conta`, `categoria`, `tipo_movimentacao`, `movimentacao`, `planejado`, `cambio`, `saldo`
- [x] Lógica de cálculo de valor convertido com base na moeda da conta
- [x] Registro de movimentações a partir de planejamentos
- [x] Inserção de câmbio com geração automática de movimentações de entrada e saída
- [x] Interface inicial em Streamlit com abas: Movimentações, Planejamentos e Câmbio
- [x] Visualização e edição de movimentações com saldo e conversão
- [x] Registro de planejamentos com recorrência e geração futura
- [x] Commit organizado com separação de arquivos e pasta de documentação
- [x] Registro automático de saldo no db pós-movimentação


## 🗃️ Entidades e Funcionalidades

### 💵 Moeda
- BRL, USD, ARS, BTC — usadas para conversão de valores e definição de contas

### 🏦 Conta
- Associada a uma pessoa
- Vinculada a uma moeda
- Usada para registrar movimentações e câmbios

### 📊 Movimentações
- Inserção manual ou gerada automaticamente (câmbio ou planejamento)
- Conversão automática de valor para BRL
- Atualização automática do saldo

### 🧾 Planejamentos
- Recorrência mensal, semanal ou anual
- Conversão em movimentações pendentes dentro de um intervalo de tempo
- Visualização estruturada com tipo, moeda e categoria estratégica

### 💱 Câmbio
- Registra troca entre contas e moedas
- Calcula e exibe a taxa efetiva
- Gera automaticamente duas movimentações com tipo e categoria específicos

---

## 🚧 Em Desenvolvimento

Próximas etapas planejadas:
- [ ] Tela de controle de saldos por conta e moeda, visualizações futuras
- [ ] Geração de relatórios financeiros e gráficos
- [ ] Inserção e acompanhamento de metas financeiras
- [ ] Criação de dashboard por período

---

## 📝 Licença

Este projeto está licenciado sob os termos da [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

Você pode:

✅ Usar, copiar, modificar e distribuir este projeto, **desde que dê o devido crédito**.

❌ **Não pode utilizar para fins comerciais** sem autorização prévia.

Copyright (c) 2025 Hianara Camilla

Feito com ❤️ e muitos commits por [Hianara Camilla](https://github.com/hianaracamilla)
