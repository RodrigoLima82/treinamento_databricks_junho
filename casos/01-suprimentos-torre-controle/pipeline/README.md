# Pipeline SDP — Caso 1: Torre de Controle de Suprimentos

`suprimentos_pipeline.sql` é a **fonte de verdade** do medalhão deste caso: define as camadas
**bronze → silver → gold** como uma **Lakeflow Spark Declarative Pipeline (SDP)** serverless.
No treino, o participante cria **uma** pipeline apontando para este arquivo (já versionado no
Git folder do workspace) — sem montar tabela por tabela na mão.

## Como criar a pipeline

**Pela conversa (Genie Code):** use o prompt da *Fase 1 — Pipeline* do runbook (`../README.md`),
que pede para criar a pipeline serverless apontando para este `.sql`.

**Pela UI (alternativa):** Workflows → Pipelines → *Create pipeline* → serverless → em
*Source code* selecione `casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql`
→ destino: catálogo `treinamento_databricks`, schema `suprimentos` → **Full refresh all**.

## Pré-requisitos
1. Catálogo `treinamento_databricks`, schema `suprimentos` e volume `raw` criados (Fase 0).
2. Os 6 CSVs carregados em `/Volumes/treinamento_databricks/suprimentos/raw/`.

## Como funciona
- **Bronze** (6 streaming tables): lê cada CSV com `read_files` **sem schema fixo** (`SELECT *`
  + `_ingested_at`). Sem schema fixo porque o Auto Loader adiciona a coluna técnica `_rescued_data`
  — fixar o schema gera o erro `_SCHEMA_NOT_COMPATIBLE`.
- **Silver** (3 streaming tables): casts, joins stream-static (fato via `STREAM()`, dimensões
  estáticas) e as regras de negócio (`tem_contrato`, `dias_atraso`, `no_prazo`, `otif`).
- **Gold** (5 materialized views): gasto por categoria, lead time/OTIF por fornecedor, saving,
  aderência a contrato e fornecedor único.

## Observações
- **Catálogo/schema/serverless** se definem na **criação da pipeline**, não no `.sql` — por isso as
  tabelas são referenciadas sem qualificação de catálogo/schema.
- Streaming tables guardam estado: ao **alterar** este arquivo, recrie com **Full refresh all**
  (a seta ao lado de *Start*), não apenas *Refresh*.
- Se uma tentativa anterior criou `bronze_*` / `silver_*` / `gold_*` como tabelas avulsas no mesmo
  schema, **apague-as antes** — a pipeline não adota tabelas que já existem fora dela.
