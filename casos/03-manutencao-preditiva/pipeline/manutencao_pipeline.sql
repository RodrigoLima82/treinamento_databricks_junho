-- =====================================================================
-- Caso 3 — Manutenção Preditiva de Ativos
-- Lakeflow Spark Declarative Pipeline (SDP) — medalhão bronze -> silver -> gold
--
-- Fonte de verdade do medalhão. No treino, o participante cria UMA pipeline
-- serverless apontando para este arquivo (Git folder no workspace).
--
-- Configuração da pipeline (definir na criação, NÃO no SQL):
--   catálogo  = treinamento_databricks
--   schema    = manutencao
--   modo      = serverless
-- Por isso as tabelas abaixo são referenciadas SEM qualificação de catálogo/schema.
--
-- Pré-requisito (rodar uma vez fora da pipeline — ver dbx-foundation):
--   CREATE CATALOG IF NOT EXISTS treinamento_databricks;
--   CREATE SCHEMA  IF NOT EXISTS treinamento_databricks.manutencao;
--   CREATE VOLUME  IF NOT EXISTS treinamento_databricks.manutencao.raw;
--   + CSVs carregados em /Volumes/treinamento_databricks/manutencao/raw/
--     (ativos.csv, falhas.csv, ordens_manutencao.csv e os leituras_sensores_lote*.csv)
--
-- INGESTÃO TIPO STREAMING (telemetria):
--   A telemetria vem em vários arquivos `leituras_sensores_lote*.csv`. A bronze
--   `bronze_leituras_sensores` usa `read_files` (Auto Loader) com STREAM e
--   pathGlobFilter 'leituras_sensores_lote*.csv'. Cada NOVO arquivo que cai no
--   volume é ingerido incrementalmente — sobe-se um lote por vez para ver o
--   comportamento de streaming (ver runbook do caso, Fase 1).
--
-- Convenções (Free Edition):
--   - Streaming tables para bronze/silver; materialized views para o gold.
--   - read_files (Auto Loader) SEM schema fixo: ele adiciona a coluna técnica
--     _rescued_data; um schema fixo gera _SCHEMA_NOT_COMPATIBLE.
--   - Serverless. Se for clusterizar, usar CLUSTER BY (nunca PARTITION BY/ZORDER).
--   - Ao alterar este arquivo, recriar com "Full refresh all" (streaming = stateful).
-- =====================================================================


-- =====================================================================
-- BRONZE — uma streaming table por fonte, dados crus, sem regra de negócio.
-- SELECT * preserva todas as colunas + _rescued_data; _ingested_at = data da carga.
-- =====================================================================

CREATE OR REFRESH STREAMING TABLE bronze_ativos
COMMENT 'Cru: cadastro dos ativos monitorados.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/manutencao/raw/', format => 'csv', header => true, pathGlobFilter => 'ativos.csv');

CREATE OR REFRESH STREAMING TABLE bronze_falhas
COMMENT 'Cru: eventos de falha dos ativos.'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/manutencao/raw/', format => 'csv', header => true, pathGlobFilter => 'falhas.csv');

CREATE OR REFRESH STREAMING TABLE bronze_ordens_manutencao
COMMENT 'Cru: ordens de manutenção (corretivas e preventivas).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/manutencao/raw/', format => 'csv', header => true, pathGlobFilter => 'ordens_manutencao.csv');

-- Telemetria — ingestão INCREMENTAL: o glob casa todos os lotes; cada arquivo
-- novo (lote02, lote03, ...) é ingerido sem reprocessar os anteriores.
CREATE OR REFRESH STREAMING TABLE bronze_leituras_sensores
COMMENT 'Cru: telemetria de sensores (vários lotes; ingestão incremental tipo streaming).'
AS SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/treinamento_databricks/manutencao/raw/', format => 'csv', header => true, pathGlobFilter => 'leituras_sensores_lote*.csv');


-- =====================================================================
-- SILVER — limpo, tipado e enriquecido. Telemetria/eventos via STREAM();
-- dimensão de ativo via join estático (stream-static). CASTs explícitos
-- (bronze chega como string).
-- =====================================================================

-- Dimensão de ativos, tipada.
CREATE OR REFRESH STREAMING TABLE silver_ativos
COMMENT 'Cadastro de ativos tipado (data de instalação, potência).'
AS SELECT
  id_ativo,
  tag,
  tipo,
  fabricante,
  modelo,
  site,
  criticidade,
  CAST(data_instalacao AS DATE)        AS data_instalacao,
  CAST(potencia_kw AS INT)             AS potencia_kw
FROM STREAM(bronze_ativos);

-- Telemetria tipada + enriquecida com a dimensão do ativo (tipo, site, criticidade).
CREATE OR REFRESH STREAMING TABLE silver_leituras
COMMENT 'Leituras de sensores tipadas e enriquecidas com tag/tipo/site/criticidade do ativo.'
AS SELECT
  l.id_leitura,
  l.id_ativo,
  CAST(l.data_hora AS TIMESTAMP)       AS data_hora,
  CAST(l.temperatura AS DOUBLE)        AS temperatura,
  CAST(l.vibracao AS DOUBLE)           AS vibracao,
  CAST(l.pressao AS DOUBLE)            AS pressao,
  CAST(l.rpm AS INT)                   AS rpm,
  -- dimensão ativo (stream-static)
  a.tag,
  a.tipo,
  a.site,
  a.criticidade
FROM STREAM(bronze_leituras_sensores) l
LEFT JOIN bronze_ativos a ON l.id_ativo = a.id_ativo;

-- Falhas tipadas.
CREATE OR REFRESH STREAMING TABLE silver_falhas
COMMENT 'Eventos de falha tipados (data, causa, componente, severidade).'
AS SELECT
  id_falha,
  id_ativo,
  CAST(data_falha AS DATE)             AS data_falha,
  causa,
  componente,
  severidade
FROM STREAM(bronze_falhas);

-- Ordens de manutenção tipadas (custo em BRL, downtime em horas).
CREATE OR REFRESH STREAMING TABLE silver_ordens
COMMENT 'Ordens de manutenção tipadas (corretiva/preventiva, custo, downtime).'
AS SELECT
  id_ordem,
  id_ativo,
  tipo                                 AS tipo_ordem,
  CAST(data_abertura AS DATE)          AS data_abertura,
  CAST(data_fechamento AS DATE)        AS data_fechamento,
  CAST(custo AS DECIMAL(18,2))         AS custo,
  CAST(downtime_horas AS DOUBLE)       AS downtime_horas,
  descricao
FROM STREAM(bronze_ordens_manutencao);


-- =====================================================================
-- GOLD — materialized views, uma por pergunta de negócio.
-- =====================================================================

-- (1) Telemetria resumida por ativo × dia (agregados de janela).
-- Também serve de FONTE DE FEATURES para o modelo de ML (Fase 2).
CREATE OR REFRESH MATERIALIZED VIEW gold_telemetria_resumo
COMMENT 'Agregados diários de sensores por ativo (média/máx/desvio) — base para tendência e features de ML.'
AS SELECT
  id_ativo,
  tag,
  tipo,
  site,
  criticidade,
  CAST(data_hora AS DATE)                      AS dia,
  count(*)                                     AS n_leituras,
  round(avg(temperatura), 1)                   AS temp_media,
  round(max(temperatura), 1)                   AS temp_max,
  round(avg(vibracao), 2)                      AS vib_media,
  round(max(vibracao), 2)                      AS vib_max,
  round(stddev(vibracao), 2)                   AS vib_dp,
  round(avg(pressao), 2)                       AS pres_media,
  round(avg(rpm), 0)                           AS rpm_media
FROM silver_leituras
GROUP BY id_ativo, tag, tipo, site, criticidade, CAST(data_hora AS DATE);

-- (2) Saúde / risco por ativo — score heurístico comparando a janela recente
-- (últimos 7 dias) contra o comportamento histórico do próprio ativo (z-score
-- de vibração e temperatura). Ativos em degradação sobem o score.
CREATE OR REFRESH MATERIALIZED VIEW gold_saude_ativo
COMMENT 'Score de risco (0-100) e categoria por ativo: vibração/temperatura recentes vs. histórico do ativo.'
-- Lógica: compara a média recente (últimos 7 dias) com a média HISTÓRICA do
-- próprio ativo (razão recente/histórico). Vibração pesa mais que temperatura;
-- a criticidade adiciona um pequeno ajuste. Score 0-100 (heurístico).
AS
WITH base AS (
  SELECT
    id_ativo,
    avg(vibracao)    AS vib_media_hist,
    avg(temperatura) AS temp_media_hist
  FROM silver_leituras
  GROUP BY id_ativo
),
ref AS (
  SELECT max(data_hora) AS agora FROM silver_leituras
),
recente AS (
  SELECT
    l.id_ativo,
    avg(l.vibracao)    AS vib_recente,
    max(l.vibracao)    AS vib_recente_max,
    avg(l.temperatura) AS temp_recente
  FROM silver_leituras l, ref
  WHERE l.data_hora >= ref.agora - INTERVAL 7 DAYS
  GROUP BY l.id_ativo
),
scored AS (
  SELECT
    a.id_ativo,
    a.tag,
    a.tipo,
    a.site,
    a.criticidade,
    round(r.vib_recente, 2)                                            AS vibracao_recente,
    round(b.vib_media_hist, 2)                                         AS vibracao_media_hist,
    round(r.temp_recente, 1)                                           AS temperatura_recente,
    round(b.temp_media_hist, 1)                                        AS temperatura_media_hist,
    round(100 * (r.vib_recente / nullif(b.vib_media_hist, 0) - 1), 0)  AS pct_acima_vibracao,
    CAST(round(least(100, greatest(0,
        70 * (r.vib_recente  / nullif(b.vib_media_hist, 0)  - 1)
      + 30 * (r.temp_recente / nullif(b.temp_media_hist, 0) - 1)
      + CASE a.criticidade WHEN 'Alta' THEN 8 WHEN 'Média' THEN 4 ELSE 0 END
    )), 0) AS INT)                                                     AS score_risco
  FROM silver_ativos a
  JOIN base    b ON a.id_ativo = b.id_ativo
  JOIN recente r ON a.id_ativo = r.id_ativo
)
SELECT
  *,
  CASE
    WHEN score_risco >= 66 THEN 'Crítico'
    WHEN score_risco >= 40 THEN 'Atenção'
    ELSE 'Saudável'
  END AS categoria_risco
FROM scored;

-- (3) MTBF — tempo médio entre falhas por ativo (e tipo de ativo).
-- mtbf_dias = média dos intervalos entre falhas consecutivas (nulo se só 1 falha).
CREATE OR REFRESH MATERIALIZED VIEW gold_mtbf
COMMENT 'MTBF por ativo: nº de falhas, primeira/última falha e tempo médio entre falhas (dias).'
AS
WITH falhas_ord AS (
  SELECT
    id_ativo,
    data_falha,
    lag(data_falha) OVER (PARTITION BY id_ativo ORDER BY data_falha) AS falha_anterior
  FROM silver_falhas
),
gaps AS (
  SELECT id_ativo, avg(datediff(data_falha, falha_anterior)) AS mtbf_dias
  FROM falhas_ord
  WHERE falha_anterior IS NOT NULL
  GROUP BY id_ativo
),
agg AS (
  SELECT
    id_ativo,
    count(*)         AS n_falhas,
    min(data_falha)  AS primeira_falha,
    max(data_falha)  AS ultima_falha
  FROM silver_falhas
  GROUP BY id_ativo
)
SELECT
  a.id_ativo,
  a.tag,
  a.tipo            AS tipo_ativo,
  a.site,
  a.criticidade,
  agg.n_falhas,
  agg.primeira_falha,
  agg.ultima_falha,
  round(g.mtbf_dias, 1) AS mtbf_dias
FROM agg
JOIN silver_ativos a ON agg.id_ativo = a.id_ativo
LEFT JOIN gaps     g ON agg.id_ativo = g.id_ativo;

-- (4) Custo de manutenção por ativo × tipo de ordem (corretiva/preventiva).
CREATE OR REFRESH MATERIALIZED VIEW gold_custo_manutencao
COMMENT 'Custo e downtime de manutenção por ativo e por tipo de ordem (corretiva/preventiva).'
AS SELECT
  a.id_ativo,
  a.tag,
  a.tipo                                        AS tipo_ativo,
  a.site,
  a.criticidade,
  o.tipo_ordem,
  count(*)                                      AS n_ordens,
  CAST(sum(o.custo) AS DECIMAL(18,2))           AS custo_total,
  round(sum(o.downtime_horas), 1)               AS downtime_total_horas
FROM silver_ordens o
JOIN silver_ativos a ON o.id_ativo = a.id_ativo
GROUP BY a.id_ativo, a.tag, a.tipo, a.site, a.criticidade, o.tipo_ordem;

-- (5) Ranking de risco — combina saúde (telemetria recente), histórico de falhas
-- e custo acumulado de manutenção. Uma linha por ativo, ordenada por risco.
CREATE OR REFRESH MATERIALIZED VIEW gold_ativos_risco
COMMENT 'Ranking de risco por ativo: score de saúde + nº de falhas + MTBF + custo/downtime acumulados.'
AS SELECT
  s.id_ativo,
  s.tag,
  s.tipo,
  s.site,
  s.criticidade,
  s.score_risco,
  s.categoria_risco,
  s.vibracao_recente,
  s.temperatura_recente,
  coalesce(m.n_falhas, 0)                       AS n_falhas,
  m.mtbf_dias,
  CAST(coalesce(c.custo_total, 0) AS DECIMAL(18,2)) AS custo_manutencao_total,
  round(coalesce(c.downtime_total_horas, 0), 1) AS downtime_total_horas
FROM gold_saude_ativo s
LEFT JOIN gold_mtbf m ON s.id_ativo = m.id_ativo
LEFT JOIN (
  SELECT id_ativo,
         sum(custo)          AS custo_total,
         sum(downtime_horas) AS downtime_total_horas
  FROM silver_ordens
  GROUP BY id_ativo
) c ON s.id_ativo = c.id_ativo
ORDER BY s.score_risco DESC, custo_manutencao_total DESC;
