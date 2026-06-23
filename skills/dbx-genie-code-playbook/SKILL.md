---
name: dbx-genie-code-playbook
description: >-
  Playbook de como conduzir um caso de uso do workshop de 0 a 100 no Databricks
  Genie Code, no Free Edition. Define a sequência de fases
  (fundação → bronze → silver → gold → IA → dashboard → Genie → app → validação),
  como validar cada passo e como estruturar os prompts. Use como guia mestre de
  qualquer um dos casos.
---

# dbx-genie-code-playbook — Construir um caso 0→100 no Genie Code

Guia mestre para o Genie Code construir cada caso de uso de forma incremental e
**validável a cada fase**. Sempre combine com `dbx-foundation` (convenções/limites)
e `dbx-brand` (visual do app) e `dbx-dashboard-design` (visual dos dashboards), mais a skill específica do caso.

## Princípios
- **Incremental e idempotente:** uma fase por vez; tudo pode rodar 2x sem quebrar.
- **Valide antes de avançar:** ao fim de cada fase, rode uma query/healthcheck e confirme.
- **Free Edition primeiro:** respeite os guardrails de `dbx-foundation` (1 warehouse, ≤3 apps, VS 1 unit delta-sync, sem KA, dados pequenos).
- **Pequeno e realista:** dados sintéticos enxutos e contexto de negócio plausível.

## Estrutura do README de cada caso
Abra o README de cada caso **contextualizando o negócio antes das fases**, em três blocos curtos:
- **O que é** — o que o caso entrega, em uma ou duas frases.
- **A dor** — o problema de negócio (dados espalhados, falta de visibilidade, decisão lenta), em bullets.
- **Como o Databricks resolve** — como cada camada/recurso (Lakehouse medalhão, AI Functions, AI/BI
  Dashboard, Genie Space, App, Unity Catalog) ataca a dor.

Depois venha o **"Como construir (Genie Code)"** com as fases 0→8.

## Fases padrão (aplicáveis a todos os casos)
1. **Fundação** — criar catálogo `treinamento_databricks`, schema do domínio e Volume `raw`
   (idempotente). Carregar os dados no Volume: como o repositório fica clonado como Git folder no
   workspace, peça ao Genie Code para **copiar os CSVs de `data/` do repositório para o Volume**
   (origem em `/Workspace/...`; os Volumes são FUSE, então o Bronze lê do Volume com `read_files`,
   que não acessa caminhos `/Workspace/...`). Alternativas: upload pela UI ou rodar o `gen_*.py`.
   Para conferir a criação, oriente o Genie a usar `SHOW SCHEMAS`/`SHOW VOLUMES` e `LIST` no Volume
   — **evite o `information_schema`** (as colunas de volume são `volume_catalog`/`volume_schema`/
   `volume_name`, não `catalog_name`, o que costuma gerar `UNRESOLVED_COLUMN`).
2. **Bronze** — ingerir os arquivos crus do Volume em tabelas `bronze_*`
   (via `read_files`/Auto Loader). **Não fixe um schema** nas tabelas bronze: deixe o Auto Loader
   inferir as colunas e use `SELECT *` + uma coluna de data de ingestão (o `read_files` adiciona
   automaticamente a coluna técnica `_rescued_data`, e um schema fixo conflita com ela). Sem regra
   de negócio ainda.
3. **Silver** — limpar, tipar, deduplicar e conformar; aplicar joins de enriquecimento
   → tabelas `silver_*`.
4. **Gold** — marts prontos para consumo (`gold_*`): uma tabela por pergunta de negócio.
5. **IA em SQL (AI Functions)** — onde fizer sentido: `ai_query`/`ai_classify`/`ai_extract`/
   `ai_summarize`/`ai_forecast` sobre silver/gold. Mantenha leve (cuidado com cota).
   Ofereça uma **variante No-Code opcional**: criar a mesma view (ou uma nova) montando a
   transformação visualmente no **Lakeflow Designer** (visual data prep, disponível no Free Edition)
   — arrastando fonte (tabela gold) → transformação (filtro/agregação) → saída como nova view no
   schema do caso. No README do caso, divida esta fase em **Fase 2(a) — IA em SQL** e
   **Fase 2(b) — No-Code (Lakeflow Designer)**, ambas opcionais, para mostrar o mesmo resultado por
   dois caminhos.
6. **AI/BI Dashboard (Lakeview)** — widgets sobre as `gold_*`. **Teste cada query no SQL
   antes** de colocar no dashboard. Para o visual, siga a skill `dbx-dashboard-design`
   (layout por audiência, regra 60-30-10, paletas acessíveis, workspace themes).
7. **Genie Space** — sobre as `gold_*` (+ Metric Views, se houver). Inclua instruções e
   perguntas de exemplo. **No Free Edition, crie o Space pela UI** (Genie → New): a criação por
   API/SDK falha por permissão, então peça ao Genie Code para *preparar* a configuração (tabelas,
   instruções, perguntas) e crie nos cliques finais. (Casos com agente: criar UC Functions/Vector
   Search/MAS aqui.) Para boas práticas de **configuração e uso** do Space (instruções, perguntas,
   Metric Views, conectar via Conversation API), siga a skill oficial `databricks-genie` do ai-dev-kit:
   https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/databricks-genie
8. **App (Databricks App)** — FastAPI + Next.js (skill `dbx-brand`): KPIs + visualizações
   + chat (Genie/agente). Lembre do limite de **3 apps**.
9. **Validação final** — checklist do caso: pipeline verde, dashboard renderiza, Genie
   responde, (modelo serve), app sobe.

## Como falar com o Genie Code (tom dos prompts)
Converse de forma **natural e profissional**, em português claro — como você explicaria a tarefa
a um colega. **Sem gírias**, e sem pseudo-SQL ou listas rígidas de comandos.
- Fale em **primeira pessoa** e de forma direta ("vamos criar...", "me mostre...", "associe X a Y").
- Deixe claro o **objetivo de negócio** e **o que conferir** no fim; deixe o "como" técnico a cargo do Genie.
- Cite só o essencial (nomes de catálogo/schema/tabela quando importarem) e referencie as skills
  com naturalidade ("siga as convenções da skill `dbx-foundation`").
- Peça sempre para **executar e mostrar o resultado** (contagem, amostra); se houver erro, cole-o e peça a correção.
- **Uma fase por vez** — não despeje tudo num único prompt.

## Validações rápidas (exemplos)
- Bronze: `SELECT count(*) FROM treinamento_databricks.<dom>.bronze_<t>;` para cada tabela.
- Silver/Gold: checar nulos em chaves e contagens vs. bronze.
- Dashboard: cada dataset roda isolado no editor SQL sem erro.
- Genie: faça 3 perguntas de exemplo e confira se os números batem com o gold.
- App: `/healthz` responde e a home carrega o logo `/databricks_logo.png`.

## Erros comuns (troubleshooting)
- **Schema incompatível no bronze (`_rescued_data`)** — o `read_files`/Auto Loader adiciona a coluna
  técnica `_rescued_data`; um schema fixo na streaming table conflita com a inferência. Solução: não
  declarar schema (usar `SELECT *` + data de ingestão) ou incluir `_rescued_data string` no schema.
  Como a streaming table é stateful, recrie com **Full refresh** (não apenas "Refresh").
- **Streaming table não atualiza após corrigir o código** — use **Full refresh all** na pipeline (a
  seta ao lado de **Start**); um "Refresh" simples mantém o estado antigo.
- **`UNRESOLVED_COLUMN` ao verificar objetos no `information_schema`** — as views de volumes/tabelas
  não usam `catalog_name`: em `information_schema.volumes` a coluna é `volume_catalog` (e
  `volume_schema`/`volume_name`); em `information_schema.tables`, `table_catalog`/`table_schema`. O
  erro é só da consulta de conferência — os objetos foram criados. Prefira confirmar com
  `SHOW SCHEMAS`/`SHOW VOLUMES`/`SHOW TABLES` e `LIST '/Volumes/...'`, que não dependem desses nomes.
- **Falha ao criar Genie Space por código (permissão / `ImportError` no módulo `genie`)** — no Free
  Edition o token do Genie Code não cria Genie Space via API/SDK (a API de conversa do Genie opera
  sobre spaces existentes, não cria spaces). Não insista por código (`api_client.do()`, `createAsset`): peça ao
  Genie Code para *preparar* a config (tabelas gold, instruções, perguntas) e crie o Space pela
  **UI** (Genie → New).

## Ordem recomendada dos casos no workshop
1) Suprimentos (núcleo Lakehouse — hands-on) → 2) FP&A → 3) Manutenção (ML) → 4) GRC (RAG/agente).
