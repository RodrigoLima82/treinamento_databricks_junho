---
name: fpa-copiloto
description: >-
  Especificação do Caso 2 do workshop — "Copiloto de FP&A".
  Define os dados de entrada, as tabelas bronze/silver/gold, a Metric View,
  os componentes de IA (ai_forecast, ai_query), os KPIs, o dashboard, o Genie
  Space e o app. Use junto com dbx-genie-code-playbook, dbx-foundation,
  dbx-app e dbx-brand para o Genie Code construir o caso 0→100.
---

# fpa-copiloto — Caso 2 (FP&A / Finanças)

**Objetivo:** copiloto de planejamento financeiro & análise (FP&A) de uma empresa de mineração
(fictícia) — visibilidade de **orçado vs. realizado** por centro de custo, conta e mês, **variância
de orçamento** (estouros), **despesa por categoria**, **tendência de receita** e **projeção** dos
próximos meses. Público: Controladoria, FP&A, Diretoria Financeira e gestores de centro de custo.

- **Catálogo/schema:** `treinamento_databricks.financas`
- **Volume cru:** `/Volumes/treinamento_databricks/financas/raw`
- **Skills de apoio:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-app`, `dbx-brand`
  (e `databricks-metric-views` para a Metric View; `databricks-ai-functions` para `ai_forecast`/`ai_query`).

## 1. Dados de entrada (em `casos/02-fpa-copiloto/data/`)
Ver `data/DICIONARIO.md`. Arquivos: `centros_custo.csv`, `contas_contabeis.csv`,
`orcamento.csv`, `lancamentos.csv`.
Chaves: `id_centro`, `id_conta`; chave natural dos fatos = `id_centro` + `id_conta` + `mes`.
- **Orçamento:** 36 meses (`2023-12` … `2026-11`). **Realizado:** 30 meses fechados (`2023-12` … `2026-05`).
- Os 6 meses orçados **sem realizado** são o intervalo da **projeção** (`ai_forecast`).
- Empresa fictícia; centros (Mina Norte/Sul/Central, Logística, Terminal, Comercial, TI, RH, Financeira).

## 2. Bronze (`bronze_*`)
Uma tabela por CSV, dados crus, sem regra de negócio:
`bronze_centros_custo`, `bronze_contas_contabeis`, `bronze_orcamento`, `bronze_lancamentos`.

## 3. Silver (`silver_*`)
- `silver_centros` — dimensão de centros (nome, área, responsável, região).
- `silver_contas` — plano de contas (tipo Receita/Despesa/CAPEX, grupo).
- `silver_orcamento` — orçamento + dimensões (mês→DATE, valor→DECIMAL, área, tipo, grupo).
- `silver_realizado` — realizado + dimensões (mesmos enriquecimentos).

## 4. Gold (`gold_*`) — uma tabela por pergunta de negócio
- `gold_orcado_vs_realizado` — **base atômica** (conta × centro × mês): orçado, realizado,
  `variancia`, `variancia_pct`. Realizado nulo nos meses futuros. **Fonte da Metric View.**
- `gold_variacao_budget` — variância acumulada por conta × centro (meses fechados).
- `gold_despesa_categoria` — despesa por grupo gerencial × mês (orçado vs. realizado).
- `gold_receita_mensal` — receita por mês (orçada/realizada) — **série base do `ai_forecast`**.
- `gold_topo_estouros` — maiores estouros de despesa por conta × centro, com `posicao` (ranking).

## 5. Componentes de IA
- **Metric View `fin_orcamento`** (sobre `gold_orcado_vs_realizado`): dimensões mês, tipo, grupo,
  área, centro, conta; medidas **Orçado**, **Realizado**, **Variância**, **Variância %** — definição
  única reutilizada por dashboard, Genie e SQL. Consulta via `MEASURE()` (sem `SELECT *`).
- **`ai_forecast`** → tabela `gold_receita_projecao`: projeta a receita (e, opcionalmente, a despesa)
  dos ~6 meses futuros a partir da série mensal realizada (`time_col=mes`, `value_col=receita_realizada`,
  `horizon='2026-11-30'`). Requer warehouse serverless (OK no Free Edition).
- **`ai_query`** → view `gold_resumo_executivo_mes`: parágrafo de resumo executivo do **mês fechado
  mais recente** (`MAX(mes)`), citando só números reais (BRL). 1 chamada por mês para poupar cota.

## 6. AI/BI Dashboard (Lakeview) — "Copiloto de FP&A"
Widgets (teste cada query antes):
- Cartões: Receita realizada, Despesa realizada, Resultado (receita − despesa), Variância de despesa %.
- Barras: orçado vs. realizado por mês; despesa por categoria (grupo).
- Linha: receita mensal (histórico + projeção do `ai_forecast`).
- Tabela: ranking de contas/centros com maiores estouros (`gold_topo_estouros`).
- Tabela: variância por centro de custo (`gold_variacao_budget`).

## 7. Genie Space — "FP&A"
- Fontes: tabelas `gold_*` + Metric View `fin_orcamento`.
- Instruções: responder em PT-BR; valores em BRL; mês no formato AAAA-MM; variância positiva em
  despesa = **estouro**; nunca inventar números.
- Perguntas de exemplo:
  - "Qual conta mais estourou o orçamento na Mina Norte?"
  - "Qual a variância de despesa por centro de custo neste ano?"
  - "Como está a receita realizada vs. orçada por mês?"
  - "Qual o resultado (receita − despesa) do último mês fechado?"

## 8. Multi-Agent Supervisor (opcional) — Agent Bricks
- **UC Function `fin_variancia_conta(nome_conta)`** — retorna orçado, realizado, variância e
  variância % de uma conta (a partir de `gold_variacao_budget`).
- **Supervisor** roteia entre o **Genie Space FP&A** (análise ampla) e a função (variância pontual).
- Criado na **UI** (no Free Edition não dá por código). Knowledge Assistant NÃO disponível.

## 9. App (Databricks App) — "Copiloto de FP&A · Databricks Workshop"
Stack Streamlit (skill `dbx-app`; visual `dbx-brand`, logo Databricks). Telas:
- **Home/Dashboard:** cartões de KPI (receita, despesa, resultado, variância de despesa %) +
  gráfico de orçado vs. realizado por mês (com projeção) + tabela de "maiores estouros".
- **Chat:** chat embarcado no **Genie Space FP&A** (perguntas em linguagem natural).
Backend lê via `databricks-sdk` (`statement_execution`) do warehouse; sem PAT no App (OAuth).

## 10. Definição de pronto
- [ ] 4 tabelas bronze com contagem = linhas dos CSVs
- [ ] silver/gold sem nulos em chaves; variância/estouros calculados; meses futuros com realizado nulo
- [ ] Metric View `fin_orcamento` consultável via `MEASURE()`
- [ ] `ai_forecast` gera `gold_receita_projecao` (~6 meses) e `ai_query` gera o resumo do mês
- [ ] dashboard renderiza todos os widgets (incl. histórico + projeção)
- [ ] Genie responde as 4 perguntas com números batendo com o gold
- [ ] app sobe, mostra KPIs e o chat do Genie funciona, com logo Databricks
