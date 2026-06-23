# Dicionário de Dados — Caso 3: Manutenção Preditiva

Dados **sintéticos/fictícios** (seed=42). Moeda: BRL. Datas no formato `AAAA-MM-DD`;
`data_hora` da telemetria no formato `AAAA-MM-DD HH:MM:SS`.
Sites/centros fictícios: Mina Norte, Mina Sul, Mina Central, Mina Leste, Mina Oeste, Terminal Portuário.
Janela de telemetria: **90 dias** terminando em **2026-06-22**, 8 leituras/dia (a cada 3 h) por ativo.

## `ativos.csv` (40 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_ativo` | string | Chave do ativo (`ATV001`…). |
| `tag` | string | TAG operacional (ex.: `BP-001` bomba, `BR-002` britador). |
| `tipo` | string | Tipo do equipamento (Bomba de polpa, Motor elétrico, Britador de mandíbula, Correia transportadora, Compressor de ar, Peneira vibratória, Moinho de bolas, Ventilador industrial). |
| `fabricante` | string | Fabricante (fictício/genérico). |
| `modelo` | string | Modelo (fictício). |
| `site` | string | Site/centro (fictício). |
| `criticidade` | string | `Alta` / `Média` / `Baixa`. |
| `data_instalacao` | date | Data de instalação. |
| `potencia_kw` | int | Potência nominal (kW). |

## `falhas.csv` (14 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_falha` | string | Chave da falha (`FAL0001`…). |
| `id_ativo` | string | FK → `ativos`. |
| `data_falha` | date | Data do evento de falha. |
| `causa` | string | Causa raiz (ex.: Desgaste de rolamento, Superaquecimento, Cavitação…). |
| `componente` | string | Componente afetado (Rolamento, Mancal, Eixo, Impelidor, Bobina…). |
| `severidade` | string | `Alta` / `Média` / `Baixa`. |

## `ordens_manutencao.csv` (97 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_ordem` | string | Chave da ordem (`OM00001`…). |
| `id_ativo` | string | FK → `ativos`. |
| `tipo` | string | `Corretiva` (após falha) / `Preventiva` (programada). |
| `data_abertura` | date | Abertura da ordem. |
| `data_fechamento` | date | Encerramento da ordem. |
| `custo` | float | Custo da intervenção (BRL). |
| `downtime_horas` | float | Horas de parada do ativo. |
| `descricao` | string | Descrição livre da intervenção. |

## `leituras_sensores_lote01.csv` · `_lote02.csv` · `_lote03.csv` (9.600 linhas cada · 28.800 no total)
Telemetria dos sensores — o arquivo de **maior volume**, dividido em **3 lotes por janela de tempo**
(lote01 = dias 1–30, lote02 = 31–60, lote03 = 61–90) para **simular ingestão incremental tipo
streaming** (sobe-se um lote por vez; ver runbook do caso).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_leitura` | string | Chave da leitura (`LE0000001`…). |
| `id_ativo` | string | FK → `ativos`. |
| `data_hora` | timestamp | Instante da leitura (a cada 3 h). |
| `temperatura` | float | Temperatura (°C). |
| `vibracao` | float | Vibração (mm/s) — principal sinal de degradação. |
| `pressao` | float | Pressão (bar). |
| `rpm` | int | Rotação (rpm). |

## Métricas derivadas (calculadas no Silver/Gold)
- **Resumo de telemetria** (por ativo × dia): `temp_media`/`temp_max`, `vib_media`/`vib_max`/`vib_dp`,
  `pres_media`, `rpm_media`.
- **Saúde do ativo** (`gold_saude_ativo`): compara a média **recente** (últimos 7 dias) com a média
  **histórica** do próprio ativo → `score_risco` (0–100, heurístico) e `categoria_risco`
  (`Saudável` / `Atenção` / `Crítico`).
- **MTBF** (`gold_mtbf`): `mtbf_dias = média dos intervalos entre falhas consecutivas` (nulo se < 2 falhas).
- **Custo** (`gold_custo_manutencao`): `custo_total` e `downtime_total_horas` por ativo × tipo de ordem.
- **Risco** (`gold_ativos_risco`): ranking por `score_risco`, com nº de falhas, MTBF e custo acumulado.
