---
name: suprimentos-torre-controle
description: >-
  Especificação do Caso 1 do workshop — "Torre de Controle de Suprimentos".
  Define os dados de entrada, as tabelas bronze/silver/gold, os KPIs, o dashboard,
  o Genie Space e o app. Use junto com dbx-genie-code-playbook, dbx-foundation,
  dbx-app e dbx-brand para o Genie Code construir o caso 0→100.
---

# suprimentos-torre-controle — Caso 1 (Suprimentos)

**Objetivo:** torre de controle de compras MRO de uma mineradora (fictícia) — visibilidade
de gasto, lead time/OTIF de fornecedores, saving vs. baseline, aderência a contrato e risco
de fornecedor único. Público: áreas de Suprimentos, COE, Performance e Digital.

- **Catálogo/schema:** `treinamento_databricks.suprimentos`
- **Volume cru:** `/Volumes/treinamento_databricks/suprimentos/raw`
- **Skills de apoio:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-app`, `dbx-brand`

## 1. Dados de entrada (em `casos/01-suprimentos-torre-controle/data/`)
Ver `data/DICIONARIO.md`. Arquivos: `fornecedores.csv`, `categorias_compra.csv`,
`contratos.csv`, `pedidos_compra.csv`, `itens_pedido.csv`, `recebimentos.csv`.
Chaves: `id_fornecedor`, `id_categoria`, `contrato_id`, `id_pedido`.
Sites/centros são fictícios (Mina Norte/Sul/Central/Leste/Oeste, Terminal Portuário).

## 2. Bronze (`bronze_*`)
Uma tabela por CSV, tipos preservados, sem regra de negócio:
`bronze_fornecedores`, `bronze_categorias_compra`, `bronze_contratos`,
`bronze_pedidos_compra`, `bronze_itens_pedido`, `bronze_recebimentos`.

## 3. Silver (`silver_*`)
- `silver_pedidos` — pedidos + fornecedor (razão social, criticidade, fornecedor_unico, uf)
  + categoria (nome, tipo) + flag `tem_contrato` (contrato_id não nulo).
- `silver_itens` — itens + `valor_item = preco_unitario*qtd` e
  `saving_item = (preco_baseline - preco_unitario)*qtd`.
- `silver_recebimentos` — + `dias_atraso = datediff(data_recebida, data_prometida)`,
  flags `no_prazo` (dias_atraso <= 0) e `otif` (no_prazo AND ok_qualidade).

## 4. Gold (`gold_*`) — uma tabela por pergunta de negócio
- `gold_gasto_categoria` — gasto por categoria × centro × mês.
- `gold_lead_time_fornecedor` — por fornecedor: lead time médio, % no prazo, **OTIF %**, nº pedidos.
- `gold_saving` — saving total e % vs. baseline por categoria e por mês.
- `gold_aderencia_contrato` — % de gasto **dentro vs. fora de contrato** por centro.
- `gold_fornecedor_unico` — fornecedores `fornecedor_unico=true` e o gasto concentrado neles (risco).

## 5. IA em SQL (opcional, leve)
- `ai_query` → uma view `gold_resumo_executivo_mes` com um parágrafo de destaques do mês
  (gasto, savings, principais atrasos). 1 chamada por mês para poupar cota.

## 6. AI/BI Dashboard (Lakeview) — "Torre de Controle de Suprimentos"
Widgets (teste cada query antes):
- Cartões: Gasto total, Saving %, OTIF %, % gasto fora de contrato.
- Barras: gasto por categoria; gasto por centro.
- Linha: gasto mensal (tendência).
- Tabela: top 10 fornecedores por gasto com OTIF e lead time.
- Tabela "atenção": fornecedores únicos + pedidos atrasados em aberto.

## 7. Genie Space — "Suprimentos"
- Fontes: tabelas `gold_*` (e `silver_*` se útil).
- Instruções: responder em PT-BR; valores em BRL; mês no formato AAAA-MM; nunca inventar números.
- Perguntas de exemplo:
  - "Qual o gasto total com Peças de britador na Mina Norte nos últimos 6 meses?"
  - "Quais fornecedores têm OTIF abaixo de 80%?"
  - "Qual o saving acumulado por categoria?"
  - "Quanto gastamos fora de contrato por centro?"

## 8. App (Databricks App) — "Torre de Controle de Suprimentos · Databricks Workshop"
Stack Streamlit (skill `dbx-app`; visual `dbx-brand`, logo Databricks). Telas:
- **Home/Dashboard:** cartões de KPI (gasto, saving %, OTIF %, fora de contrato %) +
  gráfico de gasto por categoria + tabela "pedidos em risco" (atrasados/abertos).
- **Chat:** chat embarcado no **Genie Space** (perguntas em linguagem natural).
Backend lê via `databricks-sdk` (`statement_execution`) do warehouse; sem PAT no App (OAuth).

## 9. Definição de pronto
- [ ] 6 tabelas bronze com contagem = linhas dos CSVs
- [ ] silver/gold sem nulos em chaves; OTIF/saving/aderência calculados
- [ ] dashboard renderiza todos os widgets
- [ ] Genie responde as 4 perguntas com números batendo com o gold
- [ ] app sobe, mostra KPIs e o chat do Genie funciona, com logo Databricks
