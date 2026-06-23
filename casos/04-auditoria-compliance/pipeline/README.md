# Pipeline SDP — Caso 4: Auditoria Contínua & Compliance

`auditoria_pipeline.sql` é a **fonte de verdade** do medalhão dos **dados estruturados** deste
caso: define as camadas **bronze → silver → gold** (transações × regras × achados) como uma
**Lakeflow Spark Declarative Pipeline (SDP)** serverless. No treino, o participante cria **uma**
pipeline apontando para este arquivo (já versionado no Git folder do workspace) — sem montar tabela
por tabela na mão.

> ℹ️ **Os documentos (políticas/normas `.md`) NÃO entram nesta pipeline.** Eles seguem o fluxo
> `ai_parse_document` → chunking → **Vector Search** (Fases 2–4 do runbook), que produz uma tabela
> Delta própria de *chunks* (com Change Data Feed) para o índice Delta-Sync. Manter os dois fluxos
> separados deixa a pipeline estruturada enxuta e o RAG independente.

## Como criar a pipeline

**Pela conversa (Genie Code):** use o prompt da *Fase 1 — Pipeline* do runbook (`../README.md`),
que pede para criar a pipeline serverless apontando para este `.sql`.

**Pela UI (alternativa):** Jobs & Pipelines → *Create* → **ETL pipeline** → serverless → em
*Source code* selecione `casos/04-auditoria-compliance/pipeline/auditoria_pipeline.sql`
→ destino: catálogo `treinamento_databricks`, schema `auditoria` → **Full refresh all**.

## Pré-requisitos
1. Catálogo `treinamento_databricks`, schema `auditoria` e volume `raw` criados (Fase 0).
2. Os 5 CSVs carregados em `/Volumes/treinamento_databricks/auditoria/raw/`.

## Como funciona
- **Bronze** (5 streaming tables): lê cada CSV com `read_files` **sem schema fixo** (`SELECT *`
  + `_ingested_at`). Sem schema fixo porque o Auto Loader adiciona a coluna técnica `_rescued_data`
  — fixar o schema gera o erro `_SCHEMA_NOT_COMPATIBLE`.
- **Silver** (2 streaming tables):
  - `silver_transacoes` — casts, join stream-static com fornecedores e aprovadores, e as **regras
    de compliance recalculadas como flags** (`acima_alcada`, `sem_contrato_relevante`, `sod_violado`,
    `fornecedor_irregular`, `parte_relacionada`, `dia_nao_util`, `sem_categoria`). É o coração da
    **auditoria contínua**: a não conformidade é re-derivada dos dados, não só lida do CSV.
  - `silver_achados` — achados + regra (nome, severidade, categoria, política) + contexto da transação.
- **Gold** (4 materialized views, uma por pergunta de negócio):
  - `gold_achados` — achados por regra/severidade (total, em aberto, valor em risco).
  - `gold_violacoes_alcada` — watchlist de pagamentos acima da alçada (com o excedente).
  - `gold_gasto_sem_contrato` — gasto com fornecedores sem contrato, por área e fornecedor.
  - `gold_resumo_compliance` — por área × mês: transações, valor, achados, valor em risco e
    **% de conformidade**.

## Observações
- **Catálogo/schema/serverless** se definem na **criação da pipeline**, não no `.sql` — por isso as
  tabelas são referenciadas sem qualificação de catálogo/schema.
- Streaming tables guardam estado: ao **alterar** este arquivo, recrie com **Full refresh all**
  (a seta ao lado de *Start*), não apenas *Refresh*.
- Se uma tentativa anterior criou `bronze_*` / `silver_*` / `gold_*` como tabelas avulsas no mesmo
  schema, **apague-as antes** — a pipeline não adota tabelas que já existem fora dela.
