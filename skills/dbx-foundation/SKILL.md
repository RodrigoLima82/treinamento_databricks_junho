---
name: dbx-foundation
description: >-
  Convenções de plataforma e guardrails do Databricks Free Edition para os casos
  de uso do workshop. Use SEMPRE antes de criar catálogo, schemas, volumes,
  warehouse, pipelines, Vector Search, Model Serving ou Apps. Define nomes
  padronizados, limites do Free Edition e os endpoints de modelo a usar.
---

# dbx-foundation — Fundação da plataforma (Free Edition)

Padrão único para os casos de uso do workshop. **Leia isto antes de criar
qualquer objeto no workspace.** Tudo é executado **dentro do workspace** (Genie Code,
notebooks, SQL editor) — **não há CLI local**.

## 1. Nomenclatura (Unity Catalog)
- **Catálogo único:** `treinamento_databricks`
- **Um schema por caso de uso (domínio):**
  - `suprimentos` · `financas` · `operacoes` · `grc`
- **Camadas medallion por prefixo de tabela** (dentro do schema do domínio):
  - `bronze_*` (cru) · `silver_*` (limpo/conformado) · `gold_*` (pronto p/ consumo)
  - Ex.: `treinamento_databricks.suprimentos.gold_gasto_categoria`
- **Volume para arquivos crus:** `treinamento_databricks.<dominio>.raw`
  - Ex.: `/Volumes/treinamento_databricks/suprimentos/raw`
- **Views/UC Functions/Metric Views:** prefixo do domínio (ex.: `sup_`, `fin_`, `ops_`, `grc_`).
- **Idempotência sempre:** `CREATE CATALOG/SCHEMA/VOLUME IF NOT EXISTS`; tabelas com
  `CREATE OR REPLACE` ou `.mode("overwrite")`. Tudo deve poder rodar 2x sem quebrar.

## 2. Setup mínimo (rode uma vez, no SQL editor ou via Genie Code)
```sql
CREATE CATALOG IF NOT EXISTS treinamento_databricks;
CREATE SCHEMA  IF NOT EXISTS treinamento_databricks.suprimentos;
CREATE VOLUME  IF NOT EXISTS treinamento_databricks.suprimentos.raw;
-- repita schema+volume para financas, operacoes, grc conforme o caso.
```
- **SQL Warehouse:** use o **único warehouse serverless** do workspace (tamanho 2X-Small). Não tente criar outro.
- **Upload de arquivos ao Volume:** pela **UI do Catalog** (Volume → *Upload to this volume*) ou gerando os dados em notebook no próprio workspace.

## 3. Modelos de fundação (Foundation Models)
- **Chat/LLM:** use um endpoint `databricks-*` disponível no **AI Playground** do workspace.
  Confirme a lista no Playground (ou em *Serving*) antes de cravar.
  Sugestões comuns: `databricks-claude-3-7-sonnet`, `databricks-claude-haiku`, `databricks-llama-...`.
- **Embeddings (para Vector Search com embeddings gerenciados):** `databricks-gte-large-en`
  (confirme disponibilidade). Use sempre **managed embeddings** (não self-managed).
- **AI Functions** (`ai_query`, `ai_classify`, `ai_extract`, `ai_summarize`, `ai_parse_document`,
  `ai_forecast`) funcionam direto em SQL e chamam os FMs hospedados.

## 4. Guardrails do Free Edition (NÃO violar)
| Recurso | Limite no Free Edition |
|---|---|
| Compute | **Serverless apenas** (sem cluster clássico, sem GPU, sem Scala/R) |
| SQL Warehouse | **1 só, máx 2X-Small** — compartilhado por Genie/Dashboards/SQL |
| Lakeflow Declarative Pipelines | **1 pipeline ativo por tipo** |
| Vector Search | **1 endpoint, 1 unit; só Delta-Sync + embeddings gerenciados** (sem Direct Access) |
| AgentBricks | **Genie e Multi-Agent Supervisor OK; Knowledge Assistant (KA) NÃO disponível** |
| Model Serving / FM APIs | pay-per-token OK; **sem provisioned throughput, sem GPU, sem batch** |
| Databricks Apps | **máx 3 apps**, auto-stop após 24h (reinicie antes da demo) |
| Jobs | **máx 5 tasks concorrentes** por conta |
| Cota | **Fair-usage diária** — se estourar, o compute para até o dia seguinte |

**Implicações de projeto:**
- RAG (Caso 4) = `ai_parse_document` → chunk → **Vector Search Delta-Sync (managed)** → **agente RAG custom** servido (não use KA).
- Mantenha **datasets pequenos**; pipelines enxutos; **não rode os 4 apps ao mesmo tempo** (≤3 vivos).
- **Ensaie cedo** e não queime cota antes da demo.

## 5. Execução e autenticação
- **Tudo roda dentro do workspace Free Edition (Genie Code / notebooks / SQL editor).**
  Não há CLI local — **não use** `databricks auth login`, profiles ou `databricks fs cp`.
- A autenticação é a **sessão do próprio workspace**.
- Em **Apps**, a auth é **OAuth** (a plataforma injeta as credenciais; nunca use PAT dentro do App).

## 6. Checklist antes de construir um caso
- [ ] Catálogo `treinamento_databricks` + schema do domínio + volume `raw` criados (idempotente)
- [ ] Dados crus subidos no Volume (pela UI do Catalog)
- [ ] Warehouse serverless selecionado
- [ ] Endpoints de modelo confirmados no Playground
- [ ] Nada fora dos limites do Free Edition (tabela acima)
