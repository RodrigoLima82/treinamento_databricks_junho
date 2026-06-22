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
e `dbx-brand` (visual do app), mais a skill específica do caso.

## Princípios
- **Incremental e idempotente:** uma fase por vez; tudo pode rodar 2x sem quebrar.
- **Valide antes de avançar:** ao fim de cada fase, rode uma query/healthcheck e confirme.
- **Free Edition primeiro:** respeite os guardrails de `dbx-foundation` (1 warehouse, ≤3 apps, VS 1 unit delta-sync, sem KA, dados pequenos).
- **Pequeno e realista:** dados sintéticos enxutos e contexto de negócio plausível.

## Fases padrão (aplicáveis a todos os casos)
1. **Fundação** — criar catálogo `treinamento_databricks`, schema do domínio e Volume `raw`
   (idempotente). Subir os arquivos de `data/` para o Volume.
2. **Bronze** — ingerir os arquivos crus do Volume em tabelas `bronze_*`
   (via `read_files`/Auto Loader), preservando tipos. Sem regra de negócio ainda.
3. **Silver** — limpar, tipar, deduplicar e conformar; aplicar joins de enriquecimento
   → tabelas `silver_*`.
4. **Gold** — marts prontos para consumo (`gold_*`): uma tabela por pergunta de negócio.
5. **IA em SQL (AI Functions)** — onde fizer sentido: `ai_query`/`ai_classify`/`ai_extract`/
   `ai_summarize`/`ai_forecast` sobre silver/gold. Mantenha leve (cuidado com cota).
6. **AI/BI Dashboard (Lakeview)** — widgets sobre as `gold_*`. **Teste cada query no SQL
   antes** de colocar no dashboard.
7. **Genie Space** — sobre as `gold_*` (+ Metric Views, se houver). Inclua instruções e
   perguntas de exemplo. (Casos com agente: criar UC Functions/Vector Search/MAS aqui.)
8. **App (Databricks App)** — FastAPI + Next.js (skill `dbx-brand`): KPIs + visualizações
   + chat (Genie/agente). Lembre do limite de **3 apps**.
9. **Validação final** — checklist do caso: pipeline verde, dashboard renderiza, Genie
   responde, (modelo serve), app sobe.

## Como falar com o Genie Code (tom dos prompts)
Converse de forma **natural, como uma pessoa pediria a um colega** — nada de pseudo-SQL ou
listas rígidas de comandos.
- Fale em **primeira pessoa** e no dia a dia ("agora vamos criar...", "me mostra...", "junta isso com aquilo").
- Deixe claro o **objetivo de negócio** e **o que conferir** no fim; deixe o "como" técnico a cargo do Genie.
- Cite só o essencial (nomes de catálogo/schema/tabela quando importarem) e referencie as skills
  com naturalidade ("segue as convenções que deixei na skill `dbx-foundation`").
- Peça sempre para **rodar e te mostrar o resultado** (contagem, amostra); se der erro, cole o erro e peça a correção.
- **Uma fase por vez** — não despeje tudo num único prompt.

## Validações rápidas (exemplos)
- Bronze: `SELECT count(*) FROM treinamento_databricks.<dom>.bronze_<t>;` para cada tabela.
- Silver/Gold: checar nulos em chaves e contagens vs. bronze.
- Dashboard: cada dataset roda isolado no editor SQL sem erro.
- Genie: faça 3 perguntas de exemplo e confira se os números batem com o gold.
- App: `/healthz` responde e a home carrega o logo `/databricks_logo.svg`.

## Ordem recomendada dos casos no workshop
1) Suprimentos (núcleo Lakehouse — hands-on) → 2) FP&A → 3) Manutenção (ML) → 4) GRC (RAG/agente).
