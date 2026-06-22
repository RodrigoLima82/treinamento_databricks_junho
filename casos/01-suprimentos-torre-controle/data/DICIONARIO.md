# Dicionário de Dados — Caso 1: Suprimentos

Dados **sintéticos/fictícios** (seed=42). Moeda: BRL. Datas no formato `AAAA-MM-DD`.
Centros/sites fictícios: Mina Norte, Mina Sul, Mina Central, Mina Leste, Mina Oeste, Terminal Portuário.

## `fornecedores.csv` (60 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_fornecedor` | string | Chave do fornecedor (`FOR0001`…). |
| `razao_social` | string | Nome da empresa (fictício). |
| `cnpj` | string | CNPJ fictício formatado. |
| `categoria_principal` | string | Categoria de fornecimento predominante. |
| `uf` | string | Unidade federativa. |
| `criticidade` | string | `Alta` / `Média` / `Baixa`. |
| `rating` | float | Avaliação 1.0–5.0. |
| `prazo_medio_dias` | int | Prazo médio de entrega (5–60). |
| `fornecedor_unico` | bool | `true` = fonte única (risco de concentração). |

## `categorias_compra.csv` (12 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_categoria` | string | Chave da categoria (`CAT01`…). |
| `nome` | string | Nome (ex.: Peças de britador, Correias transportadoras, EPI…). |
| `tipo` | string | `MRO` / `CAPEX` / `Serviço`. |

## `contratos.csv` (30 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `contrato_id` | string | Chave do contrato (`CT001`…). |
| `id_fornecedor` | string | FK → `fornecedores`. |
| `valor_contratado` | float | Valor total contratado (BRL). |
| `vigencia_inicio` | date | Início da vigência. |
| `vigencia_fim` | date | Fim da vigência. |
| `saldo` | float | Saldo disponível (≤ `valor_contratado`). |

## `pedidos_compra.csv` (800 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_pedido` | string | Chave do pedido (`PC000001`…). |
| `id_fornecedor` | string | FK → `fornecedores`. |
| `id_categoria` | string | FK → `categorias_compra`. |
| `data_pedido` | date | Data do pedido (últimos 12 meses). |
| `centro` | string | Site/centro (fictício). |
| `valor_total` | float | Valor do pedido (BRL) = soma dos itens. |
| `status` | string | `Aberto` / `Aprovado` / `Recebido` / `Cancelado`. |
| `contrato_id` | string\|null | FK → `contratos` (vazio = compra fora de contrato). |

## `itens_pedido.csv` (~2.428 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_pedido` | string | FK → `pedidos_compra`. |
| `id_item` | int | Sequencial do item no pedido. |
| `descricao` | string | Descrição do item/serviço. |
| `qtd` | float | Quantidade. |
| `preco_unitario` | float | Preço unitário praticado (BRL). |
| `preco_baseline` | float | Preço de referência/baseline (BRL) — base do saving. |

## `recebimentos.csv` (~716 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_pedido` | string | FK → `pedidos_compra` (pedidos não cancelados). |
| `data_prometida` | date | Data prometida de entrega. |
| `data_recebida` | date\|null | Data efetiva (vazio se ainda não recebido). |
| `qtd_recebida` | float | Quantidade recebida. |
| `ok_qualidade` | bool | Aprovado na inspeção de qualidade. |

## Métricas derivadas (calculadas no Silver/Gold)
- `valor_item = preco_unitario * qtd` · `saving_item = (preco_baseline - preco_unitario) * qtd`
- `dias_atraso = datediff(data_recebida, data_prometida)` · `no_prazo = dias_atraso <= 0`
- `otif = no_prazo AND ok_qualidade` (On-Time-In-Full)
- `tem_contrato = contrato_id IS NOT NULL`
