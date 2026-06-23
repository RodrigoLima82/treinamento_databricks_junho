# Pipeline SDP — Caso 2: Copiloto de FP&A

`fpa_pipeline.sql` é a **fonte de verdade** do medalhão deste caso: define as camadas
**bronze → silver → gold** como uma **Lakeflow Spark Declarative Pipeline (SDP)** serverless.
No treino, o participante cria **uma** pipeline apontando para este arquivo (já versionado no
Git folder do workspace) — sem montar tabela por tabela na mão.

## Como criar a pipeline

**Pela conversa (Genie Code):** use o prompt da *Fase 1 — Pipeline* do runbook (`../README.md`),
que pede para criar a pipeline serverless apontando para este `.sql`.

**Pela UI (alternativa):** Jobs & Pipelines → *Create pipeline* → serverless → em
*Source code* selecione `casos/02-fpa-copiloto/pipeline/fpa_pipeline.sql`
→ destino: catálogo `treinamento_databricks`, schema `financas` → **Full refresh all**.

## Pré-requisitos
1. Catálogo `treinamento_databricks`, schema `financas` e volume `raw` criados (Fase 0).
2. Os 4 CSVs carregados em `/Volumes/treinamento_databricks/financas/raw/`.

## Como funciona
- **Bronze** (4 streaming tables): lê cada CSV com `read_files` **sem schema fixo** (`SELECT *`
  + `_ingested_at`). Sem schema fixo porque o Auto Loader adiciona a coluna técnica `_rescued_data`
  — fixar o schema gera o erro `_SCHEMA_NOT_COMPATIBLE`.
- **Silver** (4 streaming tables): `silver_centros` e `silver_contas` (dimensões limpas) +
  `silver_orcamento` e `silver_realizado` (fatos via `STREAM()`, com join stream-static às
  dimensões e os CASTs de `mes`→DATE e valores→DECIMAL).
- **Gold** (5 materialized views), uma por pergunta de negócio:
  - `gold_orcado_vs_realizado` — **base atômica** (conta × centro × mês) com orçado, realizado,
    variância e variância %. É a **fonte da Metric View `fin_orcamento`** (Fase 2). Os 6 meses
    futuros têm realizado **nulo** (intervalo da projeção).
  - `gold_variacao_budget` — variância acumulada por conta × centro (meses fechados).
  - `gold_despesa_categoria` — despesa por grupo gerencial × mês (orçado vs. realizado).
  - `gold_receita_mensal` — receita por mês (orçada/realizada) — **série base do `ai_forecast`**.
  - `gold_topo_estouros` — maiores estouros de despesa por conta × centro, com `posicao` (ranking).

## Regra de negócio (FP&A)
- `variancia = realizado - orcado`; `variancia_pct = 100 * variancia / orcado`.
- Em **Despesa**, variância positiva = **estouro**; em **Receita**, positiva = acima do plano.
- Meses futuros (2026-06 … 2026-11): há **orçado**, mas o **realizado é nulo** — é exatamente o
  intervalo que a **projeção (`ai_forecast`)** preenche na Fase 2. Por isso o `gold_*` agregado
  ignora nulos (médias/variâncias só nos meses fechados).

## Observações
- **Catálogo/schema/serverless** se definem na **criação da pipeline**, não no `.sql` — por isso as
  tabelas são referenciadas sem qualificação de catálogo/schema.
- Streaming tables guardam estado: ao **alterar** este arquivo, recrie com **Full refresh all**
  (a seta ao lado de *Start*), não apenas *Refresh*.
- Se uma tentativa anterior criou `bronze_*` / `silver_*` / `gold_*` como tabelas avulsas no mesmo
  schema, **apague-as antes** — a pipeline não adota tabelas que já existem fora dela.
- A **Metric View** (`fin_orcamento`), o **`ai_forecast`** e o **`ai_query`** ficam **fora** desta
  pipeline (são da Fase 2 do runbook), para manter o medalhão enxuto e poupar cota.
