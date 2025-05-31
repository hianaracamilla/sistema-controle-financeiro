# 💰 Modelo Conceitual - Sistema de Acompanhamento Financeiro Familiar

Este repositório contém a **primeira versão** do modelo conceitual de um sistema financeiro doméstico, desenvolvido com o objetivo de **organizar, planejar e acompanhar** receitas, despesas, dívidas, investimentos e projeções de saldo familiar.

## 🧭 Objetivo do Projeto

Desenvolver um banco de dados que permita:

- Consolidar contas e movimentações em diferentes moedas (BRL, USD, ARS, etc.)
- Planejar movimentações recorrentes
- Acompanhar saldos por conta e por moeda
- Controlar dívidas e parcelas
- Gerenciar aportes e rendimentos de investimentos
- Realizar projeções financeiras futuras

## 🗂️ Versão Atual (BR Modelo)

Esta é a **versão inicial** do modelo, focada em mapear as entidades principais envolvidas no gerenciamento financeiro da casa. A modelagem está organizada no formato Entidade/Atributos.

### Entidades e Atributos

- **Pessoa**: identifica indivíduos e empresas (físicas ou jurídicas)
- **Conta**: representa contas bancárias vinculadas a uma pessoa
- **Saldo**: registra o saldo da conta em determinada data
- **Moeda**: define as moedas utilizadas no sistema
- **Movimentações Planejadas**: despesas e receitas recorrentes ou futuras
- **Movimentações Pendentes**: lançamentos aguardando confirmação
- **Histórico de Movimentações**: movimentações já realizadas
- **Histórico de Câmbio**: operações de conversão entre moedas
- **Investimentos**: aportes realizados em contas específicas
- **Dívidas**: valores parcelados a serem pagos

## 🧩 Observações

- Esta versão é conceitual e serve como base para discussões e evolução do modelo.

## 📌 Estrutura

O modelo está organizado em um único arquivo `.brmodelo`, que pode ser visualizado com a ferramenta [BR Modelo](https://github.com/brassoft/brModelo).

---

## 🚧 Em desenvolvimento

Este projeto está em evolução. Contribuições, ideias e sugestões são bem-vindas!
