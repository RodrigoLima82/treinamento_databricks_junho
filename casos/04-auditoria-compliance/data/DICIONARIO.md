# Dicionário de Dados — Caso 4: Auditoria Contínua & Compliance

Dados **sintéticos/fictícios** (seed=42) da empresa fictícia **Companhia Andes**.
Moeda: BRL. Datas no formato `AAAA-MM-DD`. Janela: 2025-06-23 a 2026-06-22.

Há duas naturezas de dados:
- **Estruturado** (5 CSVs) — para o pipeline medalhão, o dashboard e o Genie.
- **Não estruturado** (12 `.md` em `documentos/`) — para `ai_parse_document` + Vector Search + RAG.

---

## `fornecedores.csv` (40 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_fornecedor` | string | Chave do fornecedor (`FOR0001`…). |
| `razao_social` | string | Nome da empresa (fictício). |
| `cnpj` | string | CNPJ fictício formatado. |
| `uf` | string | Unidade federativa. |
| `categoria_fornecimento` | string | Categoria predominante de fornecimento. |
| `possui_contrato` | bool | `true` = tem contrato vigente; `false` = sem contrato (risco). |
| `contrato_id` | string\|null | Id do contrato (`CTR0001`…); vazio se sem contrato. |
| `situacao_cadastral` | string | `Regular` / `Irregular` (due diligence). |
| `parte_relacionada` | bool | `true` = sinalizado como parte relacionada (conflito de interesse). |

## `aprovadores.csv` (25 linhas)
Colaboradores com alçada de aprovação. **Também atuam como solicitantes** (a chave
`id_solicitante` das transações referencia esta tabela) — é assim que a quebra de
segregação de funções (solicitante = aprovador) fica detectável.
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_aprovador` | string | Chave do colaborador (`APR001`…). |
| `nome` | string | Nome (fictício). |
| `cargo` | string | `Analista` / `Coordenador` / `Gerente` / `Diretor` / `Vice-Presidente`. |
| `area` | string | Área (Compras, TI, Facilities, Logística, Marketing, Jurídico, RH, Operações). |
| `alcada_limite` | float | Limite de aprovação em BRL (ver tabela de alçadas abaixo). |

## `regras_compliance.csv` (10 linhas)
Catálogo de regras auditadas. Cada regra aponta para a **política de referência** (um `.md`).
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_regra` | string | Chave da regra (`R001`…`R010`). |
| `nome` | string | Nome curto da regra. |
| `descricao` | string | O que a regra verifica. |
| `severidade` | string | `Alta` / `Média` / `Baixa`. |
| `categoria` | string | Alçada, Contrato, Segregação de funções, Cadastro, Pagamento, Fracionamento, Conduta. |
| `politica_referencia` | string | Nome do documento `.md` que fundamenta a regra. |

## `transacoes.csv` (~606 linhas)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_transacao` | string | Chave da transação (`TX000001`…). |
| `data_transacao` | date | Data do pagamento/lançamento. |
| `id_fornecedor` | string | FK → `fornecedores`. |
| `id_solicitante` | string | FK → `aprovadores` (quem solicitou). |
| `id_aprovador` | string | FK → `aprovadores` (quem aprovou). |
| `area` | string | Área da despesa (= área do aprovador). |
| `categoria_despesa` | string\|null | Categoria contábil/gerencial; vazio = lançamento sem categoria. |
| `valor` | float | Valor da transação (BRL). |
| `metodo_pagamento` | string | Transferência / Boleto / Cartão corporativo / Pix. |
| `contrato_id` | string\|null | Contrato associado (do fornecedor); vazio = sem contrato. |
| `status` | string | `Pago` / `Pendente` / `Estornado`. |

## `achados_auditoria.csv` (~480 linhas)
Findings da auditoria contínua: cada linha liga **uma transação** a **uma regra violada**
(uma transação pode ter vários achados). **Derivado** das transações pela aplicação das 10 regras.
| Coluna | Tipo | Descrição |
|---|---|---|
| `id_achado` | string | Chave do achado (`AC000001`…). |
| `id_transacao` | string | FK → `transacoes`. |
| `id_regra` | string | FK → `regras_compliance`. |
| `severidade` | string | Severidade da regra (`Alta`/`Média`/`Baixa`). |
| `data_deteccao` | date | Data de detecção (= data da transação). |
| `status_achado` | string | `Aberto` / `Em análise` / `Resolvido` / `Falso positivo`. |
| `valor_em_risco` | float | Valor exposto pela não conformidade (BRL). |
| `descricao` | string | Texto do achado (com valores em formato pt-BR). |

---

## Regras de compliance e como são detectadas
| Regra | Severidade | Detecção (sobre `transacoes`) |
|---|---|---|
| R001 Alçada excedida | Alta | `valor` > `alcada_limite` do aprovador |
| R002 Sem contrato vigente | Alta | fornecedor `possui_contrato = false` **e** `valor ≥ 50.000` |
| R003 Segregação de funções | Alta | `id_solicitante = id_aprovador` |
| R004 Pagamento em dia não útil | Baixa | `data_transacao` cai em sábado/domingo e `status = Pago` |
| R005 Fornecedor irregular | Alta | fornecedor `situacao_cadastral = Irregular` |
| R006 Fracionamento | Média | ≥3 pagamentos ao mesmo fornecedor (< 50k) em 10 dias somando ≥ 50k |
| R007 Duplicidade | Alta | mesmo fornecedor + mesmo valor + mesma semana (≥2 ocorrências) |
| R008 Sem categoria | Baixa | `categoria_despesa` vazia |
| R009 Brinde acima do limite | Média | categoria "Brindes e hospitalidade" e `valor > 1.000` |
| R010 Parte relacionada | Alta | fornecedor `parte_relacionada = true` |

## Tabela de alçadas (espelha `documentos/norma_alcadas_aprovacao.md`)
| Cargo | Limite (R$) |
|---|---|
| Analista | 10.000 |
| Coordenador | 50.000 |
| Gerente | 200.000 |
| Diretor | 1.000.000 |
| Vice-Presidente | 5.000.000 |

## Métricas derivadas (calculadas no Silver/Gold)
- Flags por transação: `acima_alcada`, `sem_contrato_relevante`, `sod_violado`,
  `fornecedor_irregular`, `parte_relacionada`, `dia_nao_util`, `sem_categoria`.
- `valor_excedente = valor - alcada_limite` (quando acima da alçada).
- `pct_conformidade = % de transações sem nenhum achado` (por área e mês).
- `valor_em_risco` consolidado por regra, por severidade e por área.

## Documentos (`documentos/*.md`, 12 arquivos)
Políticas/normas/cláusulas/código de conduta fictícios da Companhia Andes, em PT-BR — insumo do
`ai_parse_document` + Vector Search (RAG). Cada regra de compliance aponta para um destes documentos.
| Arquivo | Tema |
|---|---|
| `politica_compras.md` | Compras, contrato obrigatório (≥ R$ 50k), vedação ao fracionamento. |
| `norma_alcadas_aprovacao.md` | Tabela de alçadas por cargo. |
| `politica_segregacao_funcoes.md` | Segregação de funções (SoD). |
| `politica_pagamentos.md` | Janela de pagamentos, duplicidade. |
| `norma_due_diligence_fornecedores.md` | Situação cadastral, partes relacionadas. |
| `codigo_conduta.md` | Princípios, conflito de interesses, brindes, canal de ética. |
| `politica_conflito_interesses.md` | Partes relacionadas, declaração anual. |
| `politica_brindes_hospitalidade.md` | Teto de brindes (R$ 1.000). |
| `manual_compliance.md` | Auditoria contínua, catálogo de regras, ciclo de achados. |
| `politica_privacidade_lgpd.md` | LGPD, auditoria de acessos. |
| `clausulas_contratuais_padrao.md` | Cláusulas-padrão (anticorrupção, conflito, auditoria). |
| `politica_viagens_despesas.md` | Viagens, reembolso, categorização obrigatória. |
