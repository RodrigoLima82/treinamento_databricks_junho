-- =====================================================================
-- Caso 4 — Auditoria Contínua & Compliance (Companhia Andes)
-- Lakeflow Spark Declarative Pipeline (SDP) — medalhão dos DADOS ESTRUTURADOS
-- bronze -> silver -> gold (transações × regras × achados).
--
-- Fonte de verdade do medalhão estruturado. No treino, o participante cria UMA
-- pipeline serverless apontando para este arquivo (Git folder no workspace).
--
-- ⚠️ Os DOCUMENTOS (políticas/normas .md) NÃO entram nesta pipeline: eles seguem
--    o fluxo de ai_parse_document -> chunking -> Vector Search (Fases 2-4 do runbook),
--    porque o índice Delta-Sync precisa de uma tabela Delta própria (com CDF).
--
-- Configuração da pipeline (definir na criação, NÃO no SQL):
--   catálogo  = treinamento_databricks
--   schema    = auditoria
--   modo      = serverless
-- Por isso as tabelas abaixo são referenciadas SEM qualificação de catálogo/schema.
--
-- Pré-requisito (rodar uma vez fora da pipeline — ver dbx-foundation):
--   CREATE CATALOG IF NOT EXISTS treinamento_databricks;
--   CREATE SCHEMA  IF NOT EXISTS treinamento_databricks.auditoria;
--   CREATE VOLUME  IF NOT EXISTS treinamento_databricks.auditoria.raw;
--   + 5 CSVs carregados em /Volumes/treinamento_databricks/auditoria/raw/
--
-- Convenções (Free Edition):
--   - Streaming tables para bronze/silver; materialized views para o gold.
--   - read_files (Auto Loader) SEM schema fixo: ele adiciona a coluna técnica
--     _rescued_data; um schema fixo gera _SCHEMA_NOT_COMPATIBLE. Cada read_files
--     aponta para UM CSV específico (os 5 CSVs dividem a pasta raw/).
--   - Serverless. Ao alterar este arquivo, recriar com "Full refresh all"
--     (streaming = stateful).
-- =====================================================================


-- =====================================================================
-- BRONZE — uma streaming table por CSV, dados crus, sem regra de negócio.
-- SELECT * preserva todas as colunas + _rescued_data; _ingested_at = data da carga.
-- =====================================================================

CREATE OR REFRESH STREAMING TABLE bronze_fornecedores
COMMENT 'Cru: cadastro de fornecedores (contrato, situação cadastral, parte relacionada).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/auditoria/raw/', format => 'csv', header => true, pathGlobFilter => 'fornecedores.csv');

CREATE OR REFRESH STREAMING TABLE bronze_aprovadores
COMMENT 'Cru: colaboradores com alçada de aprovação (cargo, área, limite).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/auditoria/raw/', format => 'csv', header => true, pathGlobFilter => 'aprovadores.csv');

CREATE OR REFRESH STREAMING TABLE bronze_regras_compliance
COMMENT 'Cru: catálogo de regras de compliance (id, descrição, severidade).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/auditoria/raw/', format => 'csv', header => true, pathGlobFilter => 'regras_compliance.csv');

CREATE OR REFRESH STREAMING TABLE bronze_transacoes
COMMENT 'Cru: pagamentos/lançamentos (fato).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/auditoria/raw/', format => 'csv', header => true, pathGlobFilter => 'transacoes.csv');

CREATE OR REFRESH STREAMING TABLE bronze_achados_auditoria
COMMENT 'Cru: achados de auditoria (transação × regra violada).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/auditoria/raw/', format => 'csv', header => true, pathGlobFilter => 'achados_auditoria.csv');


-- =====================================================================
-- SILVER — limpo, tipado e enriquecido. Fato via STREAM(); dimensões via
-- join estático (stream-static). CASTs explícitos (bronze chega como string).
-- As REGRAS DE COMPLIANCE são recalculadas aqui em colunas-flag (auditoria
-- contínua): mesmo que o achado já exista, o silver re-deriva a não conformidade.
-- =====================================================================

-- Transações enriquecidas (fornecedor + aprovador) + flags de não conformidade.
CREATE OR REFRESH STREAMING TABLE silver_transacoes
COMMENT 'Transações enriquecidas com fornecedor, aprovador e flags de compliance (alçada, contrato, SoD, cadastro, dia útil, categoria).'
AS SELECT
  t.id_transacao,
  CAST(t.data_transacao AS DATE)                       AS data_transacao,
  date_trunc('month', CAST(t.data_transacao AS DATE))  AS mes,
  t.id_fornecedor,
  t.id_solicitante,
  t.id_aprovador,
  t.area,
  NULLIF(trim(t.categoria_despesa), '')                AS categoria_despesa,
  CAST(t.valor AS DECIMAL(18,2))                        AS valor,
  t.metodo_pagamento,
  NULLIF(trim(t.contrato_id), '')                      AS contrato_id,
  t.status,
  -- dimensão fornecedor
  f.razao_social,
  f.uf,
  CAST(f.possui_contrato AS BOOLEAN)                    AS fornecedor_possui_contrato,
  f.situacao_cadastral,
  CAST(f.parte_relacionada AS BOOLEAN)                  AS fornecedor_parte_relacionada,
  -- dimensão aprovador
  a.nome                                                AS aprovador_nome,
  a.cargo                                               AS aprovador_cargo,
  CAST(a.alcada_limite AS DECIMAL(18,2))                AS alcada_limite,
  -- regras de compliance recalculadas (flags)
  (CAST(t.valor AS DECIMAL(18,2)) > CAST(a.alcada_limite AS DECIMAL(18,2)))      AS acima_alcada,
  (NOT CAST(f.possui_contrato AS BOOLEAN)
       AND CAST(t.valor AS DECIMAL(18,2)) >= 50000)                              AS sem_contrato_relevante,
  (t.id_solicitante = t.id_aprovador)                                            AS sod_violado,
  (f.situacao_cadastral = 'Irregular')                                           AS fornecedor_irregular,
  CAST(f.parte_relacionada AS BOOLEAN)                                           AS parte_relacionada,
  (dayofweek(CAST(t.data_transacao AS DATE)) IN (1, 7))                          AS dia_nao_util,
  (NULLIF(trim(t.categoria_despesa), '') IS NULL)                                AS sem_categoria
FROM STREAM(bronze_transacoes) t
LEFT JOIN bronze_fornecedores f ON t.id_fornecedor = f.id_fornecedor
LEFT JOIN bronze_aprovadores  a ON t.id_aprovador  = a.id_aprovador;

-- Achados enriquecidos com a regra (nome, severidade, categoria, política) e a transação.
CREATE OR REFRESH STREAMING TABLE silver_achados
COMMENT 'Achados enriquecidos com a regra violada (nome, severidade, categoria, política) e dados da transação.'
AS SELECT
  ac.id_achado,
  ac.id_transacao,
  ac.id_regra,
  r.nome                                       AS regra_nome,
  r.severidade,
  r.categoria                                  AS regra_categoria,
  r.politica_referencia,
  CAST(ac.data_deteccao AS DATE)               AS data_deteccao,
  date_trunc('month', CAST(ac.data_deteccao AS DATE)) AS mes,
  ac.status_achado,
  CAST(ac.valor_em_risco AS DECIMAL(18,2))     AS valor_em_risco,
  ac.descricao,
  -- contexto da transação
  t.area,
  t.id_fornecedor,
  t.razao_social,
  t.valor                                      AS valor_transacao
FROM STREAM(bronze_achados_auditoria) ac
LEFT JOIN bronze_regras_compliance r ON ac.id_regra = r.id_regra
LEFT JOIN silver_transacoes        t ON ac.id_transacao = t.id_transacao;


-- =====================================================================
-- GOLD — materialized views, uma por pergunta de negócio.
-- Percentuais expressos em 0–100 (arredondados).
-- =====================================================================

-- 1) Achados por regra e severidade (catálogo de não conformidades).
--    Pergunta: "quantos achados temos por regra/severidade e quanto está em risco?"
CREATE OR REFRESH MATERIALIZED VIEW gold_achados
COMMENT 'Achados consolidados por regra e severidade: total, abertos e valor em risco.'
AS SELECT
  id_regra,
  regra_nome,
  severidade,
  regra_categoria,
  politica_referencia,
  count(*)                                                          AS qtd_achados,
  sum(CASE WHEN status_achado IN ('Aberto', 'Em análise') THEN 1 ELSE 0 END) AS qtd_em_aberto,
  sum(CASE WHEN status_achado = 'Resolvido' THEN 1 ELSE 0 END)      AS qtd_resolvidos,
  CAST(sum(valor_em_risco) AS DECIMAL(18,2))                        AS valor_em_risco
FROM silver_achados
GROUP BY id_regra, regra_nome, severidade, regra_categoria, politica_referencia;

-- 2) Violações de alçada (watchlist detalhada).
--    Pergunta: "quais pagamentos foram aprovados acima da alçada e por quem?"
CREATE OR REFRESH MATERIALIZED VIEW gold_violacoes_alcada
COMMENT 'Pagamentos acima da alçada do aprovador, com o valor excedente (watchlist).'
AS SELECT
  id_transacao,
  data_transacao,
  area,
  aprovador_nome,
  aprovador_cargo,
  alcada_limite,
  valor,
  CAST(valor - alcada_limite AS DECIMAL(18,2))  AS valor_excedente,
  razao_social                                  AS fornecedor,
  status
FROM silver_transacoes
WHERE acima_alcada = true;

-- 3) Gasto com fornecedores sem contrato, por área e fornecedor.
--    Pergunta: "quanto gastamos com fornecedores sem contrato e com quem?"
CREATE OR REFRESH MATERIALIZED VIEW gold_gasto_sem_contrato
COMMENT 'Gasto com fornecedores sem contrato vigente, por área e fornecedor (e o quanto excede o limite).'
AS SELECT
  area,
  id_fornecedor,
  razao_social,
  situacao_cadastral,
  count(*)                                                          AS qtd_transacoes,
  CAST(sum(valor) AS DECIMAL(18,2))                                 AS valor_total,
  CAST(sum(CASE WHEN sem_contrato_relevante THEN valor ELSE 0 END) AS DECIMAL(18,2)) AS valor_acima_limite
FROM silver_transacoes
WHERE fornecedor_possui_contrato = false
GROUP BY area, id_fornecedor, razao_social, situacao_cadastral;

-- 4) Resumo de compliance por área e mês (visão executiva).
--    Pergunta: "como está a conformidade por área ao longo do tempo?"
--    pct_conformidade = % de transações da área/mês SEM nenhum achado.
CREATE OR REFRESH MATERIALIZED VIEW gold_resumo_compliance
COMMENT 'Por área e mês: transações, valor, achados, valor em risco e % de conformidade.'
AS WITH ach_por_tx AS (
  SELECT id_transacao, count(*) AS n_achados, sum(valor_em_risco) AS risco
  FROM silver_achados
  GROUP BY id_transacao
)
SELECT
  t.area,
  t.mes,
  count(*)                                                          AS qtd_transacoes,
  CAST(sum(t.valor) AS DECIMAL(18,2))                               AS valor_transacionado,
  sum(CASE WHEN a.n_achados IS NOT NULL THEN 1 ELSE 0 END)          AS qtd_transacoes_com_achado,
  CAST(coalesce(sum(a.n_achados), 0) AS BIGINT)                     AS qtd_achados,
  CAST(coalesce(sum(a.risco), 0) AS DECIMAL(18,2))                  AS valor_em_risco,
  round(100 * avg(CASE WHEN a.n_achados IS NULL THEN 1.0 ELSE 0.0 END), 1) AS pct_conformidade
FROM silver_transacoes t
LEFT JOIN ach_por_tx a ON t.id_transacao = a.id_transacao
GROUP BY t.area, t.mes;
