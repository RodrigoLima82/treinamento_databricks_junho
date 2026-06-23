-- =====================================================================
-- Caso 2 — Copiloto de FP&A (Finanças)
-- Lakeflow Spark Declarative Pipeline (SDP) — medalhão completo bronze -> silver -> gold
--
-- Fonte de verdade do medalhão. No treino, o participante cria UMA pipeline
-- serverless apontando para este arquivo (Git folder no workspace).
--
-- Configuração da pipeline (definir na criação, NÃO no SQL):
--   catálogo  = treinamento_databricks
--   schema    = financas
--   modo      = serverless
-- Por isso as tabelas abaixo são referenciadas SEM qualificação de catálogo/schema.
--
-- Pré-requisito (rodar uma vez fora da pipeline — ver dbx-foundation):
--   CREATE CATALOG IF NOT EXISTS treinamento_databricks;
--   CREATE SCHEMA  IF NOT EXISTS treinamento_databricks.financas;
--   CREATE VOLUME  IF NOT EXISTS treinamento_databricks.financas.raw;
--   + 4 CSVs carregados em /Volumes/treinamento_databricks/financas/raw/
--
-- Convenções (Free Edition):
--   - Streaming tables para bronze/silver; materialized views para o gold.
--   - read_files (Auto Loader) SEM schema fixo: ele adiciona a coluna técnica
--     _rescued_data; um schema fixo gera _SCHEMA_NOT_COMPATIBLE. Cada read_files
--     aponta para UM arquivo específico (os 4 CSVs dividem a pasta raw/).
--   - Serverless. Se for clusterizar, usar CLUSTER BY (nunca PARTITION BY/ZORDER).
--   - Ao alterar este arquivo, recriar com "Full refresh all" (streaming = stateful).
--
-- Regra de negócio central (FP&A):
--   variancia      = realizado - orcado     (Despesa > 0 = estouro; Receita > 0 = acima do plano)
--   variancia_pct  = 100 * variancia / orcado
--   Os 6 meses futuros (2026-06..2026-11) têm orçado mas ainda NÃO têm realizado:
--   o realizado fica NULO nesses meses — é o intervalo que o ai_forecast (Fase 2) projeta.
-- =====================================================================


-- =====================================================================
-- BRONZE — uma streaming table por CSV, dados crus, sem regra de negócio.
-- SELECT * preserva todas as colunas + _rescued_data; _ingested_at = data da carga.
-- =====================================================================

CREATE OR REFRESH STREAMING TABLE bronze_centros_custo
COMMENT 'Cru: dimensão de centros de custo.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/financas/raw/', format => 'csv', header => true, pathGlobFilter => 'centros_custo.csv');

CREATE OR REFRESH STREAMING TABLE bronze_contas_contabeis
COMMENT 'Cru: plano de contas (Receita/Despesa/CAPEX).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/financas/raw/', format => 'csv', header => true, pathGlobFilter => 'contas_contabeis.csv');

CREATE OR REFRESH STREAMING TABLE bronze_orcamento
COMMENT 'Cru: orçamento (orçado) por conta x centro x mês.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/financas/raw/', format => 'csv', header => true, pathGlobFilter => 'orcamento.csv');

CREATE OR REFRESH STREAMING TABLE bronze_lancamentos
COMMENT 'Cru: lançamentos (realizado) por conta x centro x mês.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/financas/raw/', format => 'csv', header => true, pathGlobFilter => 'lancamentos.csv');


-- =====================================================================
-- SILVER — limpo, tipado e enriquecido. Dimensões como streaming tables
-- (lidas como snapshot estático nos joins); fatos via STREAM() + join
-- stream-static com as dimensões. CASTs explícitos (bronze chega como string).
-- =====================================================================

-- Dimensão de centros de custo (limpa).
CREATE OR REFRESH STREAMING TABLE silver_centros
COMMENT 'Centros de custo: nome, área, responsável e região.'
AS SELECT
  trim(id_centro)            AS id_centro,
  trim(nome)                 AS centro_nome,
  trim(area)                 AS area,
  trim(responsavel)          AS responsavel,
  trim(regiao)               AS regiao
FROM STREAM(bronze_centros_custo);

-- Dimensão do plano de contas (limpa).
CREATE OR REFRESH STREAMING TABLE silver_contas
COMMENT 'Plano de contas: tipo (Receita/Despesa/CAPEX) e grupo gerencial.'
AS SELECT
  trim(id_conta)             AS id_conta,
  trim(nome)                 AS conta_nome,
  trim(tipo)                 AS tipo,
  trim(grupo)                AS grupo
FROM STREAM(bronze_contas_contabeis);

-- Fato orçamento + dimensões (centro/conta).
CREATE OR REFRESH STREAMING TABLE silver_orcamento
COMMENT 'Orçamento enriquecido com centro (área/região) e conta (tipo/grupo).'
AS SELECT
  o.id_orcamento,
  o.id_centro,
  o.id_conta,
  CAST(o.mes AS DATE)                       AS mes,
  CAST(o.valor_orcado AS DECIMAL(18,2))     AS valor_orcado,
  c.centro_nome,
  c.area,
  c.regiao,
  ct.conta_nome,
  ct.tipo,
  ct.grupo
FROM STREAM(bronze_orcamento) o
LEFT JOIN silver_centros c  ON o.id_centro = c.id_centro
LEFT JOIN silver_contas  ct ON o.id_conta  = ct.id_conta;

-- Fato realizado + dimensões (centro/conta).
CREATE OR REFRESH STREAMING TABLE silver_realizado
COMMENT 'Realizado (lançamentos) enriquecido com centro e conta.'
AS SELECT
  l.id_lancamento,
  l.id_centro,
  l.id_conta,
  CAST(l.mes AS DATE)                        AS mes,
  CAST(l.valor_realizado AS DECIMAL(18,2))   AS valor_realizado,
  c.centro_nome,
  c.area,
  c.regiao,
  ct.conta_nome,
  ct.tipo,
  ct.grupo
FROM STREAM(bronze_lancamentos) l
LEFT JOIN silver_centros c  ON l.id_centro = c.id_centro
LEFT JOIN silver_contas  ct ON l.id_conta  = ct.id_conta;


-- =====================================================================
-- GOLD — materialized views, uma por pergunta de negócio.
-- Percentuais expressos em 0-100 (arredondados). Meses futuros (sem realizado)
-- ficam com realizado/variância NULOS — esperado e usado pela projeção.
-- =====================================================================

-- [Base atômica] Orçado vs. realizado por conta x centro x mês — fonte da Metric View.
-- LEFT JOIN a partir do orçamento (mestre, 36 meses): o realizado fica NULO nos
-- 6 meses futuros. Como todo realizado tem orçado, nenhum dado se perde.
CREATE OR REFRESH MATERIALIZED VIEW gold_orcado_vs_realizado
COMMENT 'Orçado vs. realizado por conta, centro e mês (variância e %). Fonte da Metric View fin_orcamento.'
AS SELECT
  o.mes,
  o.id_centro,
  o.centro_nome,
  o.area,
  o.regiao,
  o.id_conta,
  o.conta_nome,
  o.tipo,
  o.grupo,
  o.valor_orcado,
  r.valor_realizado,
  CAST(r.valor_realizado - o.valor_orcado AS DECIMAL(18,2))                       AS variancia,
  round(100 * (r.valor_realizado - o.valor_orcado) / nullif(o.valor_orcado, 0), 1) AS variancia_pct
FROM silver_orcamento o
LEFT JOIN silver_realizado r
  ON  o.id_centro = r.id_centro
  AND o.id_conta  = r.id_conta
  AND o.mes       = r.mes;

-- Variância de orçamento por conta x centro (acumulada nos meses fechados).
-- "Onde estamos fora do orçamento?" — base para drill-down e Genie.
CREATE OR REFRESH MATERIALIZED VIEW gold_variacao_budget
COMMENT 'Variância (orçado vs. realizado) acumulada por conta e centro, meses fechados.'
AS SELECT
  id_conta,
  conta_nome,
  tipo,
  grupo,
  id_centro,
  centro_nome,
  area,
  CAST(sum(valor_orcado)    AS DECIMAL(18,2))                                  AS orcado_total,
  CAST(sum(valor_realizado) AS DECIMAL(18,2))                                  AS realizado_total,
  CAST(sum(valor_realizado - valor_orcado) AS DECIMAL(18,2))                   AS variancia,
  round(100 * sum(valor_realizado - valor_orcado) / nullif(sum(valor_orcado), 0), 1) AS variancia_pct,
  count(*)                                                                     AS meses
FROM gold_orcado_vs_realizado
WHERE valor_realizado IS NOT NULL
GROUP BY id_conta, conta_nome, tipo, grupo, id_centro, centro_nome, area;

-- Despesa por categoria (grupo) e mês: orçado vs. realizado.
CREATE OR REFRESH MATERIALIZED VIEW gold_despesa_categoria
COMMENT 'Despesa por grupo gerencial e mês: orçado, realizado e variância %.'
AS SELECT
  grupo,
  mes,
  CAST(sum(valor_orcado)    AS DECIMAL(18,2))                                  AS orcado,
  CAST(sum(valor_realizado) AS DECIMAL(18,2))                                  AS realizado,
  round(100 * sum(valor_realizado - valor_orcado) / nullif(sum(valor_orcado), 0), 1) AS variancia_pct
FROM gold_orcado_vs_realizado
WHERE tipo = 'Despesa'
GROUP BY grupo, mes;

-- Receita mensal (tendência): orçado vs. realizado — série base da projeção (ai_forecast).
CREATE OR REFRESH MATERIALIZED VIEW gold_receita_mensal
COMMENT 'Receita por mês: orçada, realizada e variância %. Série de tendência p/ ai_forecast.'
AS SELECT
  mes,
  CAST(sum(valor_orcado)    AS DECIMAL(18,2))                                  AS receita_orcada,
  CAST(sum(valor_realizado) AS DECIMAL(18,2))                                  AS receita_realizada,
  round(100 * sum(valor_realizado - valor_orcado) / nullif(sum(valor_orcado), 0), 1) AS variancia_pct
FROM gold_orcado_vs_realizado
WHERE tipo = 'Receita'
GROUP BY mes;

-- Maiores estouros de orçamento (Despesa): conta x centro com realizado acima do orçado.
-- estouro_total = soma(realizado - orçado) nos meses fechados; posicao = ranking desc.
CREATE OR REFRESH MATERIALIZED VIEW gold_topo_estouros
COMMENT 'Maiores estouros de orçamento (Despesa) por conta e centro, com ranking.'
AS WITH base AS (
  SELECT
    id_conta,
    conta_nome,
    grupo,
    id_centro,
    centro_nome,
    area,
    CAST(sum(valor_orcado)    AS DECIMAL(18,2))                AS orcado_total,
    CAST(sum(valor_realizado) AS DECIMAL(18,2))                AS realizado_total,
    CAST(sum(valor_realizado - valor_orcado) AS DECIMAL(18,2)) AS estouro_total
  FROM gold_orcado_vs_realizado
  WHERE tipo = 'Despesa' AND valor_realizado IS NOT NULL
  GROUP BY id_conta, conta_nome, grupo, id_centro, centro_nome, area
)
SELECT
  base.*,
  round(100 * estouro_total / nullif(orcado_total, 0), 1)      AS variancia_pct,
  rank() OVER (ORDER BY estouro_total DESC)                    AS posicao
FROM base
WHERE estouro_total > 0;
