---
name: auditoria-compliance
description: >-
  Especificação do Caso 4 do workshop — "Auditoria Contínua & Compliance" (GRC).
  Define os dados estruturados (transações, regras, achados) e os documentos
  (políticas/normas), as tabelas bronze/silver/gold, os KPIs, o dashboard, o
  pipeline de RAG (ai_parse_document → chunking → Vector Search → agente custom),
  o Genie Space, o Multi-Agent Supervisor e o app. Use junto com
  dbx-genie-code-playbook, dbx-foundation, dbx-app e dbx-brand para o Genie Code
  construir o caso 0→100.
---

# auditoria-compliance — Caso 4 (Auditoria & Compliance / GRC)

**Objetivo:** uma solução de **auditoria contínua e compliance** para a empresa fictícia
*Companhia Andes* — testar automaticamente cada transação contra um catálogo de regras
(alçada, contrato, segregação de funções, cadastro, pagamentos, conduta), medir conformidade
e **explicar a política** por trás de cada achado consultando os documentos internos via RAG.
Público: Auditoria Interna, Compliance, Controladoria, Riscos (GRC).

É o caso que mostra a stack de **GenAI sobre dados não estruturados**: `ai_parse_document`,
**Vector Search** (índice Delta-Sync com embeddings gerenciados), **RAG** com agente custom,
**Genie** sobre os dados estruturados e um **Multi-Agent Supervisor** roteando os dois.

- **Catálogo/schema:** `treinamento_databricks.auditoria`
- **Volume cru:** `/Volumes/treinamento_databricks/auditoria/raw` (CSVs em `raw/`; documentos em `raw/documentos/`)
- **Prefixo de objetos** (views/funcs/índices): `aud_`
- **Skills de apoio:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-app`, `dbx-brand`,
  `dbx-dashboard-design`; e as skills oficiais do ai-dev-kit `databricks-vector-search` e
  `databricks-genie` onde fizer sentido.

> ⚠️ **Free Edition:** Vector Search **1 endpoint / 1 unit**, só **Delta-Sync + embeddings
> gerenciados** (sem Direct Access). **Knowledge Assistant NÃO existe** → o RAG é um **agente
> custom**. **Genie e Multi-Agent Supervisor** são criados na **UI**. Ver `dbx-foundation`.

## 1. Dados de entrada (em `casos/04-auditoria-compliance/data/`)
Ver `data/DICIONARIO.md`.

**Estruturado (5 CSVs):** `fornecedores.csv`, `aprovadores.csv`, `regras_compliance.csv`,
`transacoes.csv`, `achados_auditoria.csv`. Chaves: `id_fornecedor`, `id_aprovador`,
`id_regra`, `id_transacao`, `id_achado`. `id_solicitante` também referencia `aprovadores`
(é o que torna detectável a quebra de segregação de funções).

**Não estruturado (12 `.md` em `data/documentos/`):** políticas, normas, cláusulas contratuais,
manual de compliance e código de conduta da Companhia Andes. Cada regra aponta para um documento
(`politica_referencia`). Insumo do RAG.

## 2. Bronze (`bronze_*`)
Uma streaming table por CSV, tipos preservados, sem regra de negócio:
`bronze_fornecedores`, `bronze_aprovadores`, `bronze_regras_compliance`,
`bronze_transacoes`, `bronze_achados_auditoria`.

## 3. Silver (`silver_*`)
- `silver_transacoes` — transações + fornecedor (razão social, contrato, situação, parte
  relacionada) + aprovador (nome, cargo, `alcada_limite`) + as **regras recalculadas como flags**:
  `acima_alcada`, `sem_contrato_relevante`, `sod_violado`, `fornecedor_irregular`,
  `parte_relacionada`, `dia_nao_util`, `sem_categoria`. (Coração da auditoria contínua: a não
  conformidade é re-derivada dos dados.)
- `silver_achados` — achados + regra (nome, severidade, categoria, política de referência) +
  contexto da transação (área, fornecedor, valor).

## 4. Gold (`gold_*`) — uma tabela por pergunta de negócio
- `gold_achados` — achados por regra/severidade: total, em aberto, resolvidos, **valor em risco**.
- `gold_violacoes_alcada` — watchlist de pagamentos **acima da alçada** (com o valor excedente).
- `gold_gasto_sem_contrato` — gasto com **fornecedores sem contrato**, por área e fornecedor.
- `gold_resumo_compliance` — por **área × mês**: transações, valor, achados, valor em risco e
  **% de conformidade** (transações sem nenhum achado).

> O medalhão estruturado vive em `pipeline/auditoria_pipeline.sql` (uma pipeline SDP). Os
> documentos seguem em fluxo separado (Fases 2–4), porque o índice Delta-Sync precisa de uma
> tabela Delta de *chunks* própria.

## 5. RAG sobre os documentos (componentes de GenAI não estruturada)
1. **`ai_parse_document`** — parsear os documentos do Volume. Os documentos do workshop são `.md`
   (texto), então o caminho que **funciona direto** é `read_files(..., format => 'text')`; o runbook
   também mostra o `ai_parse_document` (binaryFile) como o caminho canônico para **PDF/DOCX** (o caso
   real). Saída: um texto por documento.
2. **Chunking** — quebrar o texto em pedaços (por seção/parágrafo, ~500–1000 tokens) →
   tabela Delta `silver_documento_chunks` (`chunk_id` PK, `doc_nome`, `secao_idx`, `texto`),
   com **Change Data Feed habilitado** (pré-requisito do índice Delta-Sync).
3. **Vector Search** — **1 endpoint** + **1 índice Delta-Sync (managed)** sobre
   `silver_documento_chunks`, embeddings `databricks-gte-large-en`, `pipeline_type = TRIGGERED`.
   Índice: `aud_politicas_idx`.
4. **Agente RAG custom** (`aud_rag_politicas`) — recupera os chunks relevantes do índice e responde
   citando a política/seção, usando um LLM `databricks-*`. Sem Knowledge Assistant (não há no Free
   Edition). Pode ser exposto via Model Serving (para o MAS) e/ou chamado direto pelo app.

## 6. AI/BI Dashboard (Lakeview) — "Auditoria Contínua & Compliance"
Widgets (teste cada query antes):
- Cartões: total de achados, achados de severidade **Alta** em aberto, **valor em risco**, **% de
  conformidade** (mês mais recente).
- Barras: achados por regra; achados por severidade; gasto sem contrato por área.
- Linha: evolução mensal de achados / % de conformidade por mês.
- Tabela "watchlist": pagamentos acima da alçada (`gold_violacoes_alcada`).
- Tabela: top fornecedores sem contrato por valor (`gold_gasto_sem_contrato`).

## 7. Genie Space — "Auditoria & Compliance"
- Fontes: tabelas `gold_*` (e `silver_*` se útil).
- Instruções: responder em PT-BR; valores em BRL; mês no formato AAAA-MM; severidades
  `Alta/Média/Baixa`; **nunca inventar números** nem regras (usar só o que está nas tabelas).
- Perguntas de exemplo:
  - "Quantos achados de severidade alta estão em aberto?"
  - "Qual o valor em risco por regra?"
  - "Quais pagamentos foram aprovados acima da alçada no último trimestre?"
  - "Qual a % de conformidade por área no mês mais recente?"

## 8. Multi-Agent Supervisor (Agent Bricks) — "Auditoria"
Roteia, a cada pergunta, entre:
- **Agente RAG de políticas** (`aud_rag_politicas`) — perguntas sobre **regras/políticas**
  ("qual o limite de alçada de um gerente?", "o que diz a política sobre fornecedor sem contrato?").
- **Genie Space Auditoria** — perguntas **analíticas** sobre os dados ("quantos achados de alçada
  no último mês?", "valor em risco por área").
- (Opcional) uma **UC Function** `aud_achados_fornecedor(razao_social)` como ferramenta pontual.
Criado na **UI** (no Free Edition a criação por código falha por permissão).

## 9. App (Databricks App) — "Auditoria Contínua & Compliance · Databricks Workshop"
Stack Streamlit (skill `dbx-app`; visual `dbx-brand`, logo Databricks). Telas:
- **Home/Dashboard:** cartões de KPI (achados em aberto, % conformidade, valor em risco) +
  gráfico de achados por severidade/regra + tabela "watchlist" (acima da alçada / sem contrato).
- **Chat:** chat conectado ao **Multi-Agent Supervisor** (ou, em fallback, ao **Genie Space**) —
  pergunta tanto sobre dados quanto sobre políticas.
Backend lê o gold via `databricks-sdk` (`statement_execution`) do warehouse; sem PAT no App (OAuth).

## 10. Definição de pronto
- [ ] 5 tabelas bronze com contagem = linhas dos CSVs
- [ ] silver/gold sem nulos em chaves; flags de compliance e `pct_conformidade` calculados
- [ ] documentos parseados e `silver_documento_chunks` populado (com CDF)
- [ ] Vector Search: 1 endpoint + índice `aud_politicas_idx` sincronizado e respondendo a consultas
- [ ] agente RAG responde citando a política correta para uma pergunta de regra
- [ ] dashboard renderiza todos os widgets
- [ ] Genie responde as 4 perguntas com números batendo com o gold
- [ ] Multi-Agent Supervisor roteia política→RAG e dado→Genie
- [ ] app sobe, mostra KPIs e o chat responde, com logo Databricks
