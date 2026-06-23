# Dados — Caso 4: Auditoria Contínua & Compliance

Dados **sintéticos e fictícios** para o workshop Databricks (Free Edition). Simulam a área de
**Auditoria Interna / Compliance (GRC)** de uma empresa fictícia (**Companhia Andes**): fornecedores,
colaboradores com alçada, transações financeiras, um catálogo de regras de compliance e os
**achados** gerados pela auditoria contínua — além de um conjunto de **documentos** (políticas,
normas, cláusulas e código de conduta) para o componente de **RAG**.

> ⚠️ Empresas, CNPJs, nomes, valores e documentos são **gerados/curados para fins didáticos** —
> não representam dados, políticas ou pessoas reais.

## Arquivos estruturados (CSV)

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `fornecedores.csv` | 40 | Cadastro de fornecedores (contrato, situação cadastral, parte relacionada). |
| `aprovadores.csv` | 25 | Colaboradores com alçada (cargo, área, limite) — também solicitam. |
| `regras_compliance.csv` | 10 | Catálogo de regras auditadas (id, descrição, severidade, política). |
| `transacoes.csv` | 606 | Pagamentos/lançamentos (valor, fornecedor, solicitante, aprovador, data). |
| `achados_auditoria.csv` | 484 | Findings: transação × regra violada (derivado das 10 regras). |

## Documentos não estruturados (Markdown)

`documentos/` contém **12 arquivos `.md`** (políticas, normas, cláusulas contratuais, manual de
compliance e código de conduta). São o insumo do **`ai_parse_document` + Vector Search + RAG**.
Cada regra de compliance referencia um destes documentos — o que permite o agente RAG **explicar a
política** por trás de cada achado. Lista completa em **[`DICIONARIO.md`](./DICIONARIO.md)**.

Definição completa de colunas e tipos também em **[`DICIONARIO.md`](./DICIONARIO.md)**.

### Sinais de negócio embutidos nos dados
- ~12% das transações **acima da alçada** do aprovador (R001).
- ~25% das transações com **fornecedor sem contrato** (parcela relevante vira achado R002).
- ~7% com **quebra de segregação de funções** (solicitante = aprovador, R003).
- ~12% liquidadas em **dia não útil** (R004); ~5% **sem categoria** (R008).
- Fornecedores **irregulares** (R005) e **parte relacionada** (R010); clusters plantados de
  **fracionamento** (R006) e **duplicidade** (R007).
- Integridade referencial total entre `transacoes`, `fornecedores`, `aprovadores`, `regras` e `achados`.
- ~53% das transações têm ao menos um achado; o restante é conforme (base para `pct_conformidade`).

## Como subir para um UC Volume

Volume do caso: `/Volumes/treinamento_databricks/auditoria/raw`

**Recomendado — automático via Genie Code (Git folder no workspace):** como o repositório fica
clonado como Git folder no workspace, peça ao Genie Code para copiar os **5 CSVs** da pasta
`casos/04-auditoria-compliance/data` deste repositório para o volume `raw`, e os **documentos `.md`**
de `data/documentos` para uma subpasta `documentos/` do volume. Os prompts prontos estão na Fase 0
do runbook (`../README.md`).

> ℹ️ O Bronze lê com `read_files`, que acessa **Volumes / object storage** (não caminhos
> `/Workspace/...`). Por isso copiamos os arquivos do Git folder para o Volume antes de ingerir.
> Os documentos vão para `raw/documentos/` para serem parseados na Fase 2 (`ai_parse_document`).

**Alternativas:**
- **UI do Catalog:** Catalog → `treinamento_databricks` → `auditoria` → `raw` →
  **Upload to this volume** → selecione os 5 CSVs (e a pasta `documentos/` com os `.md`).
- **Gerar no workspace:** peça ao Genie Code para rodar `gen_auditoria_data.py` em um notebook e
  gravar os dados direto no Volume.

Depois, leia no Bronze com `read_files` (csv, `header=true`). Ver o runbook do caso em `../README.md`.

## Como regenerar (em um notebook do workspace ou localmente)

Determinístico (seed=42) e re-executável — sobrescreve os 5 CSVs e os 12 documentos `.md`:

```python
%pip install --quiet pandas faker
%run ./gen_auditoria_data.py
```

```bash
# local
pip install --quiet pandas faker
python3 gen_auditoria_data.py
```

Ao final, o script imprime contagens, checagem de integridade (órfãos), os sinais de negócio,
a distribuição de achados por regra/severidade e amostras de cada arquivo.
