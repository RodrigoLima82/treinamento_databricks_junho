# Pipeline SDP — Torre de Controle de Suprimentos

`suprimentos_pipeline.sql` é a **fonte de verdade do medalhão** do Caso 1. Um único
arquivo SQL versionado constrói todo o fluxo **bronze → silver → gold** como uma
**Lakeflow Spark Declarative Pipeline (SDP)**.

No treino, em vez de pedir ao Genie para gerar transformações ad-hoc, o participante
**cria uma pipeline serverless apontando para este arquivo** (que já está no workspace
como Git folder).

## O que o arquivo cria

**Bronze (6 streaming tables)** — uma por CSV, dados crus (`SELECT *` + `_ingested_at`),
sem schema fixo (Auto Loader infere e adiciona `_rescued_data`):
`bronze_fornecedores`, `bronze_categorias_compra`, `bronze_contratos`,
`bronze_pedidos_compra`, `bronze_itens_pedido`, `bronze_recebimentos`.

**Silver (3 streaming tables)** — limpo, tipado e enriquecido:
- `silver_pedidos` — pedidos + fornecedor + categoria + flag `tem_contrato`.
- `silver_itens` — `valor_item` e `saving_item` (vs. baseline).
- `silver_recebimentos` — `dias_atraso`, `no_prazo`, `otif` (nulos quando não recebido).

**Gold (5 materialized views)** — uma por pergunta de negócio:
- `gold_gasto_categoria` — gasto por categoria × centro × mês.
- `gold_lead_time_fornecedor` — lead time médio, % no prazo, OTIF % e nº de pedidos por fornecedor.
- `gold_saving` — saving total e % vs. baseline por categoria e mês.
- `gold_aderencia_contrato` — % de gasto dentro vs. fora de contrato por centro.
- `gold_fornecedor_unico` — fornecedores de fonte única e o gasto concentrado neles.

> **Definição de lead time:** média de dias entre a **data do pedido** e a **data de
> recebimento** efetiva — `avg(datediff(data_recebida, data_pedido))`. Lead time, % no
> prazo e OTIF consideram apenas pedidos já recebidos (`data_recebida` não nula).

## Pré-requisitos (rodar uma vez, fora da pipeline)

A pipeline **não** cria catálogo/schema/volume nem carrega os CSVs. Faça isto antes
(SQL editor ou Genie Code — ver skill `dbx-foundation`):

```sql
CREATE CATALOG IF NOT EXISTS treinamento_databricks;
CREATE SCHEMA  IF NOT EXISTS treinamento_databricks.suprimentos;
CREATE VOLUME  IF NOT EXISTS treinamento_databricks.suprimentos.raw;
```

Depois carregue os 6 CSVs de `casos/01-suprimentos-torre-controle/data/` em
`/Volumes/treinamento_databricks/suprimentos/raw/` (cópia do Git folder via Genie Code,
ou *Upload to this volume* na UI do Catalog).

## Como criar a pipeline (serverless, apontando para este arquivo)

1. **Jobs & Pipelines → Create → ETL pipeline** (Lakeflow Declarative Pipeline).
2. **Serverless**: ligado (no Free Edition só há compute serverless).
3. **Source code**: selecione este arquivo do Git folder
   (`casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql`).
4. **Destination**: catálogo `treinamento_databricks`, schema `suprimentos`.
   > As tabelas no SQL **não têm qualificação** de catálogo/schema de propósito —
   > elas herdam o destino configurado aqui.
5. **Create** e depois **Start**.

## Notas (Free Edition)

- **1 pipeline ativa por tipo**: se já houver outra pipeline ETL rodando, pare/exclua
  antes — o Free Edition permite apenas uma.
- **Alterou o SQL?** Use **Full refresh all** (a seta ao lado de *Start*). As streaming
  tables são stateful; um *Refresh* simples mantém o estado antigo. Isso também resolve
  o erro de schema incompatível (`_SCHEMA_NOT_COMPATIBLE`) ao recriar o bronze.
- O **resumo executivo com `ai_query`** (skill do caso) **não** faz parte desta pipeline
  (depende de modelo servido + cota) — fica como fase conversacional à parte.
