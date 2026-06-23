-- =====================================================================
-- Caso 1 — Torre de Controle de Suprimentos
-- Lakeflow Spark Declarative Pipeline (SDP) — medalhão completo bronze -> silver -> gold
--
-- Fonte de verdade do medalhão. No treino, o participante cria UMA pipeline
-- serverless apontando para este arquivo (Git folder no workspace).
--
-- Configuração da pipeline (definir na criação, NÃO no SQL):
--   catálogo  = treinamento_databricks
--   schema    = suprimentos
--   modo      = serverless
-- Por isso as tabelas abaixo são referenciadas SEM qualificação de catálogo/schema.
--
-- Pré-requisito (rodar uma vez fora da pipeline — ver dbx-foundation):
--   CREATE CATALOG IF NOT EXISTS treinamento_databricks;
--   CREATE SCHEMA  IF NOT EXISTS treinamento_databricks.suprimentos;
--   CREATE VOLUME  IF NOT EXISTS treinamento_databricks.suprimentos.raw;
--   + 6 CSVs carregados em /Volumes/treinamento_databricks/suprimentos/raw/
--
-- Convenções (Free Edition):
--   - Streaming tables para bronze/silver; materialized views para o gold.
--   - read_files (Auto Loader) SEM schema fixo: ele adiciona a coluna técnica
--     _rescued_data; um schema fixo gera _SCHEMA_NOT_COMPATIBLE. Cada read_files
--     aponta para UM arquivo específico (os 6 CSVs dividem a pasta raw/).
--   - Serverless. Se for clusterizar, usar CLUSTER BY (nunca PARTITION BY/ZORDER).
--   - Ao alterar este arquivo, recriar com "Full refresh all" (streaming = stateful).
-- =====================================================================


-- =====================================================================
-- BRONZE — uma streaming table por CSV, dados crus, sem regra de negócio.
-- SELECT * preserva todas as colunas + _rescued_data; _ingested_at = data da carga.
-- =====================================================================

CREATE OR REFRESH STREAMING TABLE bronze_fornecedores
COMMENT 'Cru: cadastro de fornecedores.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/suprimentos/raw/', format => 'csv', header => true, pathGlobFilter => 'fornecedores.csv');

CREATE OR REFRESH STREAMING TABLE bronze_categorias_compra
COMMENT 'Cru: categorias de compra.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/suprimentos/raw/', format => 'csv', header => true, pathGlobFilter => 'categorias_compra.csv');

CREATE OR REFRESH STREAMING TABLE bronze_contratos
COMMENT 'Cru: contratos de fornecimento.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/suprimentos/raw/', format => 'csv', header => true, pathGlobFilter => 'contratos.csv');

CREATE OR REFRESH STREAMING TABLE bronze_pedidos_compra
COMMENT 'Cru: pedidos de compra (fato).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/suprimentos/raw/', format => 'csv', header => true, pathGlobFilter => 'pedidos_compra.csv');

CREATE OR REFRESH STREAMING TABLE bronze_itens_pedido
COMMENT 'Cru: itens dos pedidos de compra.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/suprimentos/raw/', format => 'csv', header => true, pathGlobFilter => 'itens_pedido.csv');

CREATE OR REFRESH STREAMING TABLE bronze_recebimentos
COMMENT 'Cru: recebimentos (entregas) dos pedidos.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/suprimentos/raw/', format => 'csv', header => true, pathGlobFilter => 'recebimentos.csv');


-- =====================================================================
-- SILVER — limpo, tipado e enriquecido. Fato via STREAM(); dimensões via
-- join estático (stream-static). CASTs explícitos (bronze chega como string).
-- =====================================================================

-- Pedidos + fornecedor + categoria + flag de contrato.
CREATE OR REFRESH STREAMING TABLE silver_pedidos
COMMENT 'Pedidos enriquecidos com fornecedor, categoria e flag tem_contrato.'
AS SELECT
  p.id_pedido,
  p.id_fornecedor,
  p.id_categoria,
  NULLIF(trim(p.contrato_id), '')               AS contrato_id,
  CAST(p.data_pedido AS DATE)                   AS data_pedido,
  p.centro,
  CAST(p.valor_total AS DECIMAL(18,2))          AS valor_total,
  p.status,
  -- dimensão fornecedor
  f.razao_social,
  f.criticidade,
  CAST(f.fornecedor_unico AS BOOLEAN)           AS fornecedor_unico,
  f.uf,
  -- dimensão categoria
  c.nome                                        AS categoria_nome,
  c.tipo                                        AS categoria_tipo,
  -- regra de negócio: pedido coberto por contrato?
  (NULLIF(trim(p.contrato_id), '') IS NOT NULL) AS tem_contrato
FROM STREAM(bronze_pedidos_compra) p
LEFT JOIN bronze_fornecedores      f ON p.id_fornecedor = f.id_fornecedor
LEFT JOIN bronze_categorias_compra c ON p.id_categoria  = c.id_categoria;

-- Itens + valor do item e saving vs. baseline.
CREATE OR REFRESH STREAMING TABLE silver_itens
COMMENT 'Itens com valor_item (preco_unitario*qtd) e saving_item vs. baseline.'
AS SELECT
  id_pedido,
  CAST(id_item AS INT)                                       AS id_item,
  descricao,
  CAST(qtd AS DECIMAL(18,2))                                 AS qtd,
  CAST(preco_unitario AS DECIMAL(18,2))                      AS preco_unitario,
  CAST(preco_baseline AS DECIMAL(18,2))                      AS preco_baseline,
  CAST(preco_unitario * qtd AS DECIMAL(18,2))               AS valor_item,
  CAST((preco_baseline - preco_unitario) * qtd AS DECIMAL(18,2)) AS saving_item
FROM STREAM(bronze_itens_pedido);

-- Recebimentos + atraso e flags de no_prazo / OTIF.
-- data_recebida NULA = pedido ainda não recebido (atraso/flags ficam nulos).
CREATE OR REFRESH STREAMING TABLE silver_recebimentos
COMMENT 'Recebimentos com dias_atraso, no_prazo e OTIF; nulos quando não recebido.'
AS SELECT
  id_pedido,
  CAST(data_prometida AS DATE)                              AS data_prometida,
  CAST(data_recebida  AS DATE)                              AS data_recebida,
  CAST(qtd_recebida AS DECIMAL(18,2))                       AS qtd_recebida,
  CAST(ok_qualidade AS BOOLEAN)                             AS ok_qualidade,
  datediff(CAST(data_recebida AS DATE), CAST(data_prometida AS DATE)) AS dias_atraso,
  (datediff(CAST(data_recebida AS DATE), CAST(data_prometida AS DATE)) <= 0) AS no_prazo,
  ((datediff(CAST(data_recebida AS DATE), CAST(data_prometida AS DATE)) <= 0)
     AND CAST(ok_qualidade AS BOOLEAN))                     AS otif
FROM STREAM(bronze_recebimentos);


-- =====================================================================
-- GOLD — materialized views, uma por pergunta de negócio.
-- Dimensões de negócio preservadas para os filtros do dashboard.
-- Percentuais expressos em 0–100 (arredondados).
-- =====================================================================

-- Gasto por categoria × centro × mês.
CREATE OR REFRESH MATERIALIZED VIEW gold_gasto_categoria
COMMENT 'Gasto (soma de valor_total) por categoria, centro e mês.'
AS SELECT
  categoria_nome,
  categoria_tipo,
  centro,
  date_trunc('month', data_pedido)             AS mes,
  CAST(sum(valor_total) AS DECIMAL(18,2))       AS gasto,
  count(*)                                      AS qtd_pedidos
FROM silver_pedidos
GROUP BY categoria_nome, categoria_tipo, centro, date_trunc('month', data_pedido);

-- Desempenho de entrega por fornecedor.
-- Lead time = média de dias entre a DATA DO PEDIDO e a DATA DE RECEBIMENTO efetiva
--   (avg(datediff(data_recebida, data_pedido))). Considera apenas pedidos já
--   recebidos (data_recebida não nula); o mesmo recorte vale para no_prazo e OTIF.
CREATE OR REFRESH MATERIALIZED VIEW gold_lead_time_fornecedor
COMMENT 'Por fornecedor: lead time médio (pedido->recebimento), % no prazo, OTIF % e nº de pedidos recebidos.'
AS SELECT
  p.id_fornecedor,
  p.razao_social,
  p.criticidade,
  count(*)                                                     AS qtd_pedidos_recebidos,
  round(avg(datediff(r.data_recebida, p.data_pedido)), 1)      AS lead_time_medio_dias,
  round(100 * avg(CASE WHEN r.no_prazo THEN 1.0 ELSE 0.0 END), 1) AS pct_no_prazo,
  round(100 * avg(CASE WHEN r.otif    THEN 1.0 ELSE 0.0 END), 1) AS otif_pct
FROM silver_recebimentos r
JOIN silver_pedidos      p ON r.id_pedido = p.id_pedido
WHERE r.data_recebida IS NOT NULL
GROUP BY p.id_fornecedor, p.razao_social, p.criticidade;

-- Saving realizado vs. baseline, por categoria e mês.
-- saving% = sum(saving_item) / sum(preco_baseline*qtd).
CREATE OR REFRESH MATERIALIZED VIEW gold_saving
COMMENT 'Saving total e % vs. baseline por categoria e mês.'
AS SELECT
  p.categoria_nome,
  p.categoria_tipo,
  date_trunc('month', p.data_pedido)                          AS mes,
  CAST(sum(i.saving_item) AS DECIMAL(18,2))                    AS saving_total,
  CAST(sum(i.preco_baseline * i.qtd) AS DECIMAL(18,2))         AS baseline_total,
  round(100 * sum(i.saving_item) / nullif(sum(i.preco_baseline * i.qtd), 0), 1) AS saving_pct
FROM silver_itens   i
JOIN silver_pedidos p ON i.id_pedido = p.id_pedido
GROUP BY p.categoria_nome, p.categoria_tipo, date_trunc('month', p.data_pedido);

-- Aderência a contrato: gasto dentro vs. fora de contrato por centro.
CREATE OR REFRESH MATERIALIZED VIEW gold_aderencia_contrato
COMMENT 'Gasto dentro vs. fora de contrato e % de aderência por centro.'
AS SELECT
  centro,
  CAST(sum(CASE WHEN tem_contrato      THEN valor_total ELSE 0 END) AS DECIMAL(18,2)) AS gasto_em_contrato,
  CAST(sum(CASE WHEN NOT tem_contrato  THEN valor_total ELSE 0 END) AS DECIMAL(18,2)) AS gasto_fora_contrato,
  CAST(sum(valor_total) AS DECIMAL(18,2))                                              AS gasto_total,
  round(100 * sum(CASE WHEN tem_contrato     THEN valor_total ELSE 0 END) / nullif(sum(valor_total), 0), 1) AS pct_em_contrato,
  round(100 * sum(CASE WHEN NOT tem_contrato THEN valor_total ELSE 0 END) / nullif(sum(valor_total), 0), 1) AS pct_fora_contrato
FROM silver_pedidos
GROUP BY centro;

-- Risco de fonte única: fornecedores fornecedor_unico=true e o gasto concentrado neles.
CREATE OR REFRESH MATERIALIZED VIEW gold_fornecedor_unico
COMMENT 'Fornecedores de fonte única e o gasto concentrado neles (risco de concentração).'
AS SELECT
  id_fornecedor,
  razao_social,
  uf,
  criticidade,
  count(*)                                      AS qtd_pedidos,
  CAST(sum(valor_total) AS DECIMAL(18,2))        AS gasto_total
FROM silver_pedidos
WHERE fornecedor_unico = true
GROUP BY id_fornecedor, razao_social, uf, criticidade;
