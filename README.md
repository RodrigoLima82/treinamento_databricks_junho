<p align="center">
  <img src="assets/databricks_logo.png" alt="Databricks" height="72">
</p>

<h1 align="center">Workshop Databricks — Zero to Hero</h1>

<p align="center">
  <i>Aprenda a plataforma Databricks construindo 4 casos de uso de ponta a ponta —
  do dado cru ao app — usando o <b>Databricks Genie Code</b> no <b>Free Edition</b>.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Databricks-Free%20Edition-FF3621">
  <img src="https://img.shields.io/badge/Genie%20Code-assisted-1B3139">
  <img src="https://img.shields.io/badge/serverless-only-00A972">
</p>

---

## 🎯 Sobre o workshop

Um treinamento **mão na massa** que percorre a plataforma Databricks inteira. Em vez de
slides, cada participante constrói **soluções completas** (pipeline de dados, dashboards,
modelos, agentes e aplicações web) conversando com o **Genie Code** — o assistente de
desenvolvimento do Databricks. Tudo roda no **Free Edition**, serverless, dentro do workspace.

A proposta é simples: **0 → 100**. Você parte de arquivos crus e, seguindo um *runbook* de
prompts, chega a um app funcional com BI e IA generativa, entendendo cada camada da plataforma
no caminho.

## 🧩 Os 4 casos de uso

| # | Caso de uso | Domínio | Destaques da plataforma |
|---|-------------|---------|--------------------------|
| 1 | **Torre de Controle de Compras** | Supply Chain / Suprimentos | Volumes · Lakeflow (Bronze→Silver→Gold) · Unity Catalog · AI/BI Dashboard · Genie · AI Functions · App |
| 2 | **Copiloto de FP&A** | Finanças | Metric Views · AI Functions (`ai_forecast`, `ai_query`) · Genie · Multi-Agent Supervisor · App |
| 3 | **Manutenção Preditiva de Ativos** | Operações / Manutenção | Structured Streaming · Lakeflow · MLflow · Model Serving · Dashboard · Genie · App |
| 4 | **Auditoria Contínua & Compliance** | Risco / Auditoria (GRC) | `ai_parse_document` · Vector Search · RAG (agente custom) · Genie · Multi-Agent Supervisor · App |

Juntos, os 4 casos cobrem: **ingestão → Lakeflow → Unity Catalog → Metric Views → AI Functions
→ Genie → AgentBricks (Supervisor) → Vector Search/RAG → MLflow + Model Serving → Databricks Apps.**

## 🚀 O que você vai aprender
- Organizar dados em **Unity Catalog** com a arquitetura **medallion** (bronze/silver/gold).
- Construir pipelines **Lakeflow Declarative Pipelines** serverless.
- Criar **AI/BI Dashboards** e explorar dados em linguagem natural com **Genie**.
- Usar **AI Functions** (`ai_query`, `ai_forecast`, `ai_parse_document`, …) direto no SQL.
- Treinar e servir modelos com **MLflow + Model Serving**.
- Montar **RAG** com **Vector Search** e orquestrar agentes com **AgentBricks**.
- Publicar **Databricks Apps** (Streamlit) sobre tudo isso.

## 🛠️ Como o kit funciona

Este repositório é o "combustível" do workshop. Para cada caso há:
- uma **skill** (`skills/`) com as convenções e specs que o Genie Code segue;
- um **runbook** (`casos/0X-.../README.md`) com os **prompts prontos** para colar no Genie Code, fase a fase;
- **dados sintéticos** (`casos/0X-.../data/`) para subir a um Volume.

Você abre o repositório no workspace (Git folder), cola os prompts do runbook no Genie Code
**na ordem**, validando cada fase. Dados 100% **sintéticos** — gerados para fins didáticos.

## 📂 Estrutura
```
.
├─ assets/                         # identidade visual (logo)
├─ skills/                         # skills (formato ai-dev-kit / Agent Skills)
│  ├─ <foundation>/                # convenções de plataforma + limites do Free Edition
│  ├─ <brand>/                     # logo, paleta e tema dos apps
│  ├─ <dashboard-design>/          # boas práticas de design de dashboards AI/BI
│  ├─ <genie-code-playbook>/       # fluxo 0→100 reutilizável
│  └─ <caso-1>/ ...                # uma skill por caso de uso
└─ casos/
   └─ 01-.../{README.md, data/}    # runbook (prompts) + dados de simulação
```

## ▶️ Como executar
1. Acesse um workspace **Databricks Free Edition** (tudo roda **dentro do workspace**, via Genie Code — sem CLI local).
2. Abra este repositório como **Git folder** (Repos) no workspace.
3. Escolha um caso, abra `casos/0X-.../README.md` e **cole os prompts no Genie Code na ordem**.
4. Suba os dados do caso ao Volume indicado (pela UI do Catalog) e siga as fases até o app.

## ⚠️ Notas do Free Edition
Serverless apenas · 1 SQL Warehouse (2X-Small) · 1 pipeline ativo por tipo ·
Vector Search 1 endpoint/1 unit (Delta-Sync, embeddings gerenciados) ·
Model Serving pay-per-token · até **3 Databricks Apps** (auto-stop em 24h) · cota diária de uso.
Ensaie antes da demo para não esbarrar na cota.

---

<p align="center"><sub>Material educativo. Dados fictícios. Construído com Databricks Genie Code.</sub></p>
