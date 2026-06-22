# Caso 1 — Torre de Controle de Suprimentos (Runbook Genie Code)

Construa este caso **0→100 no Databricks Genie Code** (Free Edition) colando os prompts
abaixo **na ordem**. Valide cada fase antes de avançar.

- **Catálogo/schema:** `treinamento_databricks.suprimentos`
- **Volume:** `/Volumes/treinamento_databricks/suprimentos/raw`
- **Skills:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-brand`, `suprimentos-torre-controle`
- **Dados:** `casos/01-suprimentos-torre-controle/data/*.csv` (ver `data/DICIONARIO.md`)

> Dica: em cada prompt, deixe o Genie Code **rodar e mostrar o resultado**. Se der erro,
> cole o **erro literal** e peça a correção antes de seguir.

---

## Pré-requisitos
1. Acesso ao workspace **Free Edition** — tudo roda **dentro do workspace**, via Genie Code (sem CLI local).
2. Este repositório aberto no workspace como **Git folder** (Repos), para o Genie Code ler skills, dados e runbooks.

---

## Fase 0 — Fundação
**Prompt (Genie Code):**
```
Vamos construir o Caso 1 "Torre de Controle de Suprimentos" seguindo
skills/dbx-foundation/SKILL.md e skills/dbx-genie-code-playbook/SKILL.md.
Fase 0 — Fundação: crie de forma idempotente (IF NOT EXISTS) o catálogo
treinamento_databricks, o schema treinamento_databricks.suprimentos e o volume
treinamento_databricks.suprimentos.raw. Ao final, liste os objetos criados.
```
**Suba os 6 CSVs ao Volume pela UI:** Catalog → `treinamento_databricks` → `suprimentos` →
volume `raw` → **Upload to this volume** → selecione os arquivos de
`casos/01-suprimentos-torre-controle/data/*.csv`.
> Alternativa: peça ao Genie Code para **gerar os dados no próprio workspace** rodando
> `data/gen_suprimentos_data.py` (em um notebook) e gravar direto no Volume.

✅ **Validar:** os 6 CSVs aparecem no Volume.

---

## Fase 1 — Bronze
**Prompt:**
```
Fase 1 — Bronze. A partir dos 6 CSVs em /Volumes/treinamento_databricks/suprimentos/raw,
crie no schema treinamento_databricks.suprimentos as tabelas bronze lendo com read_files
(csv, header=true, inferSchema), idempotente (CREATE OR REPLACE):
bronze_fornecedores, bronze_categorias_compra, bronze_contratos,
bronze_pedidos_compra, bronze_itens_pedido, bronze_recebimentos.
Ao final, mostre SELECT count(*) de cada tabela.
```
✅ **Validar:** contagens batem com as linhas dos CSVs.

---

## Fase 2 — Silver
**Prompt:**
```
Fase 2 — Silver, conforme skills/suprimentos-torre-controle/SKILL.md §3.
Crie (CREATE OR REPLACE):
- silver_pedidos: pedidos + dados do fornecedor (razao_social, criticidade,
  fornecedor_unico, uf) + categoria (nome, tipo) + flag tem_contrato (contrato_id não nulo).
- silver_itens: itens + valor_item = preco_unitario*qtd e
  saving_item = (preco_baseline - preco_unitario)*qtd.
- silver_recebimentos: + dias_atraso = datediff(data_recebida, data_prometida),
  no_prazo = (dias_atraso <= 0), otif = (no_prazo AND ok_qualidade).
Trate nulos e mostre 5 linhas de cada.
```
✅ **Validar:** sem nulos em chaves; flags coerentes.

---

## Fase 3 — Gold
**Prompt:**
```
Fase 3 — Gold, conforme §4 da skill do caso. Crie (CREATE OR REPLACE):
- gold_gasto_categoria: gasto por categoria x centro x mês (AAAA-MM).
- gold_lead_time_fornecedor: por fornecedor — lead time médio, % no prazo, OTIF %, nº pedidos.
- gold_saving: saving total e saving % vs baseline por categoria e por mês.
- gold_aderencia_contrato: % de gasto dentro vs fora de contrato por centro.
- gold_fornecedor_unico: fornecedores únicos e gasto concentrado neles.
Mostre uma amostra de cada.
```
✅ **Validar:** OTIF, saving % e % fora de contrato fazem sentido.

> **Variante showcase (opcional):** *"Empacote as transformações silver→gold como uma
> Lakeflow Declarative Pipeline (serverless)."* — respeite o limite de **1 pipeline por tipo**.

---

## Fase 4 — IA em SQL (opcional, leve)
**Prompt:**
```
Fase 4 — Crie a view gold_resumo_executivo_mes usando ai_query sobre os números do mês
mais recente (gasto total, saving %, OTIF %, principais atrasos), gerando um parágrafo
executivo em PT-BR. Use um endpoint databricks-* disponível (confirme no AI Playground).
Faça 1 chamada por mês para poupar cota.
```
✅ **Validar:** o parágrafo cita números reais do gold.

---

## Fase 5 — AI/BI Dashboard
**Prompt:**
```
Fase 5 — Crie um AI/BI Dashboard (Lakeview) "Torre de Controle de Suprimentos" com os
widgets da §6 da skill do caso: cartões (Gasto total, Saving %, OTIF %, % fora de contrato);
barras de gasto por categoria e por centro; linha de gasto mensal; tabela top 10 fornecedores
(gasto, OTIF, lead time); tabela de atenção (fornecedores únicos + pedidos atrasados em aberto).
TESTE cada query no editor SQL antes de adicionar ao dashboard.
```
✅ **Validar:** todos os widgets renderizam sem erro.

---

## Fase 6 — Genie Space
**Prompt:**
```
Fase 6 — Crie um Genie Space "Suprimentos" sobre as tabelas gold_* de
treinamento_databricks.suprimentos. Instruções: responder em PT-BR, valores em BRL, mês AAAA-MM,
nunca inventar números. Adicione as perguntas de exemplo da §7 da skill do caso e teste-as.
```
✅ **Validar:** as 4 perguntas retornam números coerentes com o gold. Anote o `GENIE_SPACE_ID`.

---

## Fase 7 — App (Databricks App)
**Prompt:**
```
Fase 7 — Crie um Databricks App "Torre de Controle de Suprimentos · Databricks Workshop"
(FastAPI BFF + Next.js, seguindo skills/dbx-brand/SKILL.md; copie assets/databricks_logo.svg
para client/public/databricks_logo.svg). Telas: (1) Home com cartões de KPI (gasto, saving %,
OTIF %, % fora de contrato), gráfico de gasto por categoria e tabela "pedidos em risco"
(atrasados/abertos), lendo do warehouse via databricks-sdk (statement_execution);
(2) Chat embarcado no Genie Space (use o GENIE_SPACE_ID da Fase 6).
Faça o deploy como Databricks App pelo próprio workspace. Respeite o limite de 3 apps no Free Edition.
```
✅ **Validar:** `/healthz` ok, home carrega com o logo, KPIs corretos, chat do Genie responde.

---

## Fase 8 — Definição de pronto & como apresentar
- [ ] Bronze (6 tabelas) · Silver · Gold criados e validados
- [ ] Dashboard renderiza · Genie responde · App no ar
- **No treino:** comece mostrando o CSV cru → vire a tabela gold → faça uma pergunta no
  Genie → abra o App. É o "0→100" do Lakehouse em poucos minutos.

> ⚠️ **Free Edition:** 1 warehouse 2X-Small, ≤3 apps (auto-stop 24h), cota diária.
> Ensaie antes e reinicie o App pouco antes da apresentação.
