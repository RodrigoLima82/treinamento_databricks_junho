# Dicionário de Dados — Caso 2: Copiloto de FP&A

Dados **sintéticos/fictícios** (seed=42). Moeda: BRL. Mês no formato `AAAA-MM-01`
(primeiro dia do mês). Empresa fictícia de mineração; centros de custo, áreas e
responsáveis são gerados aleatoriamente.

Janela temporal:
- **Orçamento:** 36 meses — `2023-12` a `2026-11`.
- **Realizado:** 30 meses fechados — `2023-12` a `2026-05`.
- Os 6 meses de orçamento **sem realizado** (`2026-06` … `2026-11`) são o intervalo que
  a **projeção (`ai_forecast`)** preenche na Fase 2.

## `centros_custo.csv` (10 linhas)
Dimensão de centros de custo.
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_centro` | string | Chave do centro de custo (`CC01`…`CC10`). |
| `nome` | string | Nome do centro (ex.: Operações Mina Norte, Diretoria Comercial). |
| `area` | string | Área de negócio: `Operações` / `Logística` / `Comercial` / `TI` / `RH` / `Corporativo`. |
| `responsavel` | string | Gestor responsável (fictício). |
| `regiao` | string | Unidade federativa (UF) do centro. |

## `contas_contabeis.csv` (22 linhas)
Plano de contas.
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_conta` | string | Chave da conta contábil (ex.: `310001`, `410001`, `510001`). |
| `nome` | string | Nome da conta (ex.: Receita de venda de minério, Energia elétrica). |
| `tipo` | string | `Receita` / `Despesa` / `CAPEX`. |
| `grupo` | string | Agrupamento gerencial (ex.: Pessoal, Utilidades, Serviços, Manutenção, Logística, Administrativas, Não-caixa, Receita operacional, Investimentos). |

## `orcamento.csv` (4.212 linhas)
Fato: valor **orçado** por conta × centro × mês (36 meses).
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_orcamento` | string | Chave da linha de orçamento (`ORC000001`…). |
| `id_centro` | string | FK → `centros_custo`. |
| `id_conta` | string | FK → `contas_contabeis`. |
| `mes` | date | Mês de competência (`AAAA-MM-01`). |
| `valor_orcado` | float | Valor orçado no mês (BRL, arredondado à centena). |

## `lancamentos.csv` (3.510 linhas)
Fato: valor **realizado** (agregado mensal) por conta × centro × mês (30 meses fechados).
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_lancamento` | string | Chave do lançamento (`LAN000001`…). |
| `id_centro` | string | FK → `centros_custo`. |
| `id_conta` | string | FK → `contas_contabeis`. |
| `mes` | date | Mês de competência (`AAAA-MM-01`). |
| `valor_realizado` | float | Valor realizado no mês (BRL, em centavos). |

> Chave natural dos fatos: **`id_centro` + `id_conta` + `mes`** (única em cada arquivo).
> Todo lançamento tem uma linha de orçamento correspondente (mesma chave) — sem realizado órfão.

## Métricas derivadas (calculadas no Silver/Gold e na Metric View)
- `variancia = valor_realizado - valor_orcado` (positiva em Despesa = **estouro**; positiva em Receita = acima do plano).
- `variancia_pct = 100 * (valor_realizado - valor_orcado) / valor_orcado`.
- `estouro` (Despesa) = `variancia` quando `valor_realizado > valor_orcado`.
- `resultado = soma(Receita) - soma(Despesa)` por mês/centro.
- Série mensal de Receita/Despesa (soma por `mes`) — base do `ai_forecast`.
