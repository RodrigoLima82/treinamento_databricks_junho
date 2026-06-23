---
name: manutencao-preditiva
description: >-
  Especificação do Caso 3 do workshop — "Manutenção Preditiva de Ativos".
  Define os dados de entrada (telemetria de sensores + falhas + ordens), as tabelas
  bronze/silver/gold com ingestão tipo streaming, o modelo de ML (MLflow), o
  Model Serving (opcional), os KPIs, o dashboard, o Genie Space e o app. Use junto
  com dbx-genie-code-playbook, dbx-foundation, dbx-app e dbx-brand para o Genie Code
  construir o caso 0→100.
---

# manutencao-preditiva — Caso 3 (Manutenção Preditiva)

**Objetivo:** monitorar ativos industriais (bombas, motores, britadores, moinhos…) de uma
mineradora fictícia para **antecipar falhas**: ingerir telemetria de sensores de forma incremental
(tipo streaming), calcular saúde/risco por ativo, MTBF e custo de manutenção, e **treinar um modelo
de ML** que prevê o risco de falha a partir dos sensores. Público: Operações, Manutenção,
Confiabilidade (Reliability) e Performance.

- **Catálogo/schema:** `treinamento_databricks.manutencao`
- **Volume cru:** `/Volumes/treinamento_databricks/manutencao/raw`
- **Prefixo de objetos (views/UC Functions):** `mnt_`
- **Skills de apoio:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-app`, `dbx-brand`
- **Destaques de plataforma:** Structured Streaming (simulado) · Lakeflow SDP · **MLflow** ·
  **Model Serving (opcional)** · AI/BI Dashboard · Genie · App

## 1. Dados de entrada (em `casos/03-manutencao-preditiva/data/`)
Ver `data/DICIONARIO.md`. Arquivos: `ativos.csv`, `falhas.csv`, `ordens_manutencao.csv` e a
telemetria em **3 lotes** `leituras_sensores_lote01/02/03.csv` (28.800 leituras no total).
Chaves: `id_ativo`, `id_falha`, `id_ordem`, `id_leitura`. A telemetria é dividida em lotes para
**simular ingestão incremental** (Auto Loader). Sites fictícios (Mina Norte/Sul/Central/Leste/Oeste,
Terminal Portuário). Sinal embutido: vibração/temperatura **sobem antes da falha**; 4 ativos em
degradação atual ainda sem falha (alvos da predição).

## 2. Bronze (`bronze_*`)
Uma streaming table por fonte, sem regra de negócio (lê do volume com `read_files`/Auto Loader):
`bronze_ativos`, `bronze_falhas`, `bronze_ordens_manutencao`, `bronze_leituras_sensores`.
A de telemetria casa **todos os lotes** (`pathGlobFilter => 'leituras_sensores_lote*.csv'`) e
ingere de forma **incremental** — é o componente "tipo streaming" do caso.

## 3. Silver (`silver_*`)
- `silver_ativos` — cadastro tipado (data de instalação, potência).
- `silver_leituras` — telemetria tipada (timestamp, doubles) + dimensão do ativo (`tag`, `tipo`,
  `site`, `criticidade`) via join estático (stream-static).
- `silver_falhas` — falhas tipadas (data, causa, componente, severidade).
- `silver_ordens` — ordens tipadas (`tipo_ordem`, custo em BRL, downtime em horas).

## 4. Gold (`gold_*`) — uma tabela por pergunta de negócio
- `gold_telemetria_resumo` — agregados de sensor por **ativo × dia** (média/máx/desvio). Também é a
  **fonte de features** do modelo de ML.
- `gold_saude_ativo` — **score de risco (0–100)** e `categoria_risco` (Saudável/Atenção/Crítico) por
  ativo: compara a janela recente (7 dias) com a média histórica do próprio ativo (heurístico).
- `gold_mtbf` — **MTBF** por ativo/tipo (tempo médio entre falhas; nulo se < 2 falhas).
- `gold_custo_manutencao` — custo e downtime por **ativo × tipo de ordem** (corretiva/preventiva).
- `gold_ativos_risco` — **ranking de risco** combinando saúde + nº de falhas + MTBF + custo acumulado.

## 5. Modelo de ML (MLflow) — Fase 2 (notebook, não é parte do SDP)
- **Features:** a partir de `gold_telemetria_resumo` (médias/máximos/desvios diários por ativo) +
  janelas móveis sobre `silver_leituras` (ex.: média de vibração/temperatura dos últimos 7 dias).
- **Rótulo:** `falha_proxima` = houve falha (`silver_falhas`) nos **próximos N dias** após a janela
  da feature (ex.: N=7). Grão recomendado: **ativo × dia**.
- **Treino:** classificador simples (ex.: `GradientBoostingClassifier`/`RandomForest` do scikit-learn),
  com **`mlflow.autolog()`**; logar métrica (ex.: AUC/F1) e o modelo.
- **Registro:** registrar no **Unity Catalog** como `treinamento_databricks.manutencao.modelo_risco_falha`.
- Tudo **serverless** (sem GPU). Dataset pequeno e determinístico — treino em segundos.

## 6. Model Serving (opcional) — Fase 3
- **Opção A (UI):** servir o modelo registrado via **Serving → Create endpoint** (CPU pequeno,
  scale-to-zero). Pode exigir permissão/cota — por isso é **opcional**.
- **Opção B (sempre funciona):** **batch scoring** no notebook — carregar o modelo com
  `mlflow.pyfunc`/`spark_udf`, pontuar `gold_telemetria_resumo` e gravar `gold_predicoes_risco`
  (probabilidade de falha por ativo). Não exige endpoint nem cota de serving.

## 7. AI/BI Dashboard (Lakeview) — "Saúde de Ativos & Manutenção Preditiva"
Widgets (teste cada query antes):
- Cartões: nº de ativos Crítico/Atenção, MTBF médio, custo total de manutenção, downtime total.
- Donut: ativos por `categoria_risco`.
- Barras: custo de manutenção por tipo de ativo / por site (corretiva vs. preventiva).
- Linha: tendência de **vibração média diária** dos ativos em risco (de `gold_telemetria_resumo`).
- Tabela "atenção": `gold_ativos_risco` (top por score) com nº de falhas, MTBF e custo.

## 8. Genie Space — "Manutenção"
- Fontes: tabelas `gold_*` (e `silver_falhas`/`silver_ordens` se útil).
- Instruções: responder em PT-BR; valores em BRL; datas AAAA-MM; nunca inventar números;
  "risco/criticidade" vêm de `gold_saude_ativo`/`gold_ativos_risco`.
- Perguntas de exemplo:
  - "Quais ativos estão com categoria de risco Crítico agora?"
  - "Qual o MTBF dos britadores?"
  - "Quanto gastamos com manutenção corretiva por site?"
  - "Quais ativos tiveram vibração média subindo nos últimos dias?"

## 9. App (Databricks App) — "Manutenção Preditiva · Databricks Workshop"
Stack Streamlit (skill `dbx-app`; visual `dbx-brand`, logo Databricks). Telas:
- **Home/Saúde:** cartões (ativos críticos, MTBF médio, custo de manutenção, downtime) + donut de
  risco + tabela "ativos em risco" (de `gold_ativos_risco`).
- **Ativo:** série temporal de sensores de um ativo (de `gold_telemetria_resumo`) + risco previsto
  (de `gold_predicoes_risco`, se a Fase 3 gerou).
- **Chat:** chat embarcado no **Genie Space "Manutenção"**.
Backend lê via `databricks-sdk`/`databricks-sql-connector` do warehouse; sem PAT no App (OAuth).

## 10. Definição de pronto
- [ ] 4 tabelas bronze; `bronze_leituras_sensores` com 28.800 linhas (após os 3 lotes)
- [ ] silver/gold sem nulos em chaves; telemetria enriquecida com a dimensão do ativo
- [ ] ingestão incremental demonstrada (linhas crescem ao subir um lote novo)
- [ ] modelo treinado e **registrado no Unity Catalog** (MLflow), com métrica logada
- [ ] (opcional) endpoint de serving OU `gold_predicoes_risco` gerada por batch scoring
- [ ] dashboard renderiza todos os widgets
- [ ] Genie responde as 4 perguntas com números batendo com o gold
- [ ] app sobe, mostra a saúde dos ativos e o chat do Genie funciona, com logo Databricks
