# Pipeline SDP — Caso 3: Manutenção Preditiva de Ativos

`manutencao_pipeline.sql` é a **fonte de verdade** do medalhão deste caso: define as camadas
**bronze → silver → gold** como uma **Lakeflow Spark Declarative Pipeline (SDP)** serverless.
No treino, o participante cria **uma** pipeline apontando para este arquivo (já versionado no
Git folder do workspace) — sem montar tabela por tabela na mão.

## Como criar a pipeline

**Pela conversa (Genie Code):** use o prompt da *Fase 1 — Pipeline* do runbook (`../README.md`),
que pede para criar a pipeline serverless apontando para este `.sql`.

**Pela UI (alternativa):** Jobs & Pipelines → *Create* → **ETL pipeline** → serverless → em
*Source code* selecione `casos/03-manutencao-preditiva/pipeline/manutencao_pipeline.sql`
→ destino: catálogo `treinamento_databricks`, schema `manutencao` → **Full refresh all**.

## Pré-requisitos
1. Catálogo `treinamento_databricks`, schema `manutencao` e volume `raw` criados (Fase 0).
2. CSVs carregados em `/Volumes/treinamento_databricks/manutencao/raw/`:
   `ativos.csv`, `falhas.csv`, `ordens_manutencao.csv` e os `leituras_sensores_lote*.csv`.

## Ingestão tipo streaming (telemetria)
A telemetria vem **em vários arquivos** `leituras_sensores_lote*.csv`. A bronze
`bronze_leituras_sensores` usa `read_files` (Auto Loader) com `STREAM` e
`pathGlobFilter => 'leituras_sensores_lote*.csv'`. Como streaming table, ela ingere de forma
**incremental**: cada arquivo NOVO que cai no volume entra sem reprocessar os já lidos. É assim que
simulamos *Structured Streaming* no Free Edition — sobe-se **um lote por vez** e roda a pipeline para
ver o número de linhas crescer (ver Fase 1 do runbook).

## Como funciona
- **Bronze** (4 streaming tables): lê cada fonte com `read_files` **sem schema fixo** (`SELECT *`
  + `_ingested_at`). Sem schema fixo porque o Auto Loader adiciona a coluna técnica `_rescued_data`
  — fixar o schema gera o erro `_SCHEMA_NOT_COMPATIBLE`. A de telemetria casa **todos os lotes**.
- **Silver** (4 streaming tables): casts, e a telemetria/eventos via `STREAM()` com a dimensão de
  ativo em join estático (stream-static). `silver_leituras` carrega `tipo`/`site`/`criticidade`.
- **Gold** (5 materialized views), uma por pergunta de negócio:
  - `gold_telemetria_resumo` — agregados diários de sensor por ativo (também base de features de ML).
  - `gold_saude_ativo` — score de risco (0-100) e categoria por ativo (recente vs. histórico).
  - `gold_mtbf` — tempo médio entre falhas por ativo/tipo.
  - `gold_custo_manutencao` — custo e downtime por ativo × tipo de ordem (corretiva/preventiva).
  - `gold_ativos_risco` — ranking de risco combinando saúde + falhas + custo.

## Observações
- **Catálogo/schema/serverless** se definem na **criação da pipeline**, não no `.sql` — por isso as
  tabelas são referenciadas sem qualificação de catálogo/schema.
- Streaming tables guardam estado: ao **alterar** este arquivo, recrie com **Full refresh all**
  (a seta ao lado de *Start*), não apenas *Refresh*.
- Se uma tentativa anterior criou `bronze_*` / `silver_*` / `gold_*` como tabelas avulsas no mesmo
  schema, **apague-as antes** — a pipeline não adota tabelas que já existem fora dela.
- O `gold_saude_ativo` é um score **heurístico** (regra de negócio). O modelo de risco "de verdade"
  é treinado na **Fase 2 (MLflow)**, a partir das features de `gold_telemetria_resumo`.
