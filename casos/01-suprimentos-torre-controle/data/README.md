# Dados — Caso 1: Torre de Controle de Suprimentos

Dados **sintéticos e fictícios** para o workshop Databricks (Free Edition). Simulam a área de
**Suprimentos** de uma mineradora fictícia: fornecedores, categorias, contratos, pedidos de
compra, itens e recebimentos. Servem para construir o pipeline Bronze → Silver → Gold, o
AI/BI Dashboard, o Genie Space e o App do caso.

> ⚠️ Empresas, CNPJs, sites e valores são **gerados aleatoriamente** — não representam dados reais.

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `fornecedores.csv` | 60 | Cadastro de fornecedores (criticidade, rating, fornecedor único). |
| `categorias_compra.csv` | 12 | Categorias de compra (MRO / CAPEX / Serviço). |
| `contratos.csv` | 30 | Contratos de fornecimento (valor, vigência, saldo). |
| `pedidos_compra.csv` | 800 | Cabeçalho dos pedidos (fornecedor, categoria, centro, valor, status). |
| `itens_pedido.csv` | ~2.428 | Itens dos pedidos (qtd, preço unitário, baseline). |
| `recebimentos.csv` | ~716 | Recebimento físico (datas prometida/recebida, qualidade). |

Centros/sites são fictícios: Mina Norte, Mina Sul, Mina Central, Mina Leste, Mina Oeste, Terminal Portuário.
Definição completa de colunas e tipos em **[`DICIONARIO.md`](./DICIONARIO.md)**.

### Sinais de negócio embutidos nos dados
- ~20–25% das entregas **atrasadas** (base para lead time / OTIF).
- ~40% dos itens com **saving** (`preco_unitario` < `preco_baseline`).
- ~30% do gasto **fora de contrato** (`contrato_id` vazio).
- 4 fornecedores `fornecedor_unico = true` **concentram gasto alto** em "Peças de britador".
- Integridade referencial total e `valor_total` do pedido = soma dos itens.

## Como subir para um UC Volume

Volume do caso: `/Volumes/treinamento_databricks/suprimentos/raw`

**Pela UI do Catalog:** Catalog → `treinamento_databricks` → `suprimentos` → `raw` →
**Upload to this volume** → selecione os 6 CSVs.

> Alternativa (sem upload manual): peça ao Genie Code para rodar `gen_suprimentos_data.py`
> em um notebook do workspace e gravar os dados direto no Volume.

Depois, leia no Bronze com `read_files` (csv, `header=true`). Ver o runbook do caso em `../README.md`.

## Como regenerar (em um notebook do workspace)

Determinístico (seed=42) e re-executável — sobrescreve os 6 CSVs:

```python
%pip install --quiet pandas faker
%run ./gen_suprimentos_data.py
```

Ao final, o script imprime contagens, checagem de integridade (órfãos), os sinais de negócio
e amostras de cada arquivo.
