# Dados — Caso 2: Copiloto de FP&A

Dados **sintéticos e fictícios** para o workshop Databricks (Free Edition). Simulam o
**planejamento financeiro & análise (FP&A)** de uma empresa de mineração fictícia:
centros de custo, plano de contas, **orçamento** (orçado) e **lançamentos** (realizado),
mês a mês. Servem para construir o pipeline Bronze → Silver → Gold, a Metric View,
a projeção (`ai_forecast`), o AI/BI Dashboard, o Genie Space e o App do caso.

> ⚠️ Empresas, nomes, centros, valores e contas são **gerados aleatoriamente** — não representam dados reais.

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `centros_custo.csv` | 10 | Centros de custo por área (Operações, Logística, Comercial, TI, RH, Corporativo). |
| `contas_contabeis.csv` | 22 | Plano de contas (Receita / Despesa / CAPEX) com grupo gerencial. |
| `orcamento.csv` | 4.212 | Orçado por conta × centro × mês (36 meses: 2023-12 a 2026-11). |
| `lancamentos.csv` | 3.510 | Realizado por conta × centro × mês (30 meses fechados: 2023-12 a 2026-05). |

Definição completa de colunas e tipos em **[`DICIONARIO.md`](./DICIONARIO.md)**.

### Sinais de negócio embutidos nos dados
- **Empresa lucrativa:** receita realizada (~R$ 3,6 bi no histórico) bem acima da despesa (~R$ 1,7 bi).
- **Estouro de orçamento em despesa:** ~+3% no agregado, concentrado em alguns pares conta × centro
  **crônicos** (ex.: *Energia elétrica* e *Combustíveis* na **Mina Norte**, *Fretes* no **Terminal
  Portuário**, *Serviços de terceiros* na **Logística e Ferrovia**) — viram os "maiores estouros".
- **Receita perto do plano** (leve alta), com **sazonalidade** anual (preço de commodity) e **tendência**
  de crescimento ao longo dos meses.
- **CAPEX** tende a **subexecutar** (projetos atrasam) — variância negativa.
- **6 meses orçados sem realizado** (2026-06 a 2026-11): é o intervalo que a **projeção** preenche.
- Integridade referencial total: todo orçamento/lançamento aponta para um centro e uma conta válidos,
  e **todo realizado tem um orçado correspondente** (mesma chave centro × conta × mês).

## Como subir para um UC Volume

Volume do caso: `/Volumes/treinamento_databricks/financas/raw`

**Recomendado — automático via Genie Code (Git folder no workspace):** como o repositório fica
clonado como Git folder no workspace, peça ao Genie Code para copiar os CSVs da pasta
`casos/02-fpa-copiloto/data` deste repositório para o volume `raw`. Ele resolve a cópia em uma
célula (os Volumes são montados via FUSE). O prompt pronto está na Fase 0 do runbook (`../README.md`).

> ℹ️ O Bronze lê com `read_files`, que acessa **Volumes / object storage** (não caminhos
> `/Workspace/...`). Por isso copiamos os arquivos do Git folder para o Volume antes de ingerir.

**Alternativas:**
- **UI do Catalog:** Catalog → `treinamento_databricks` → `financas` → `raw` →
  **Upload to this volume** → selecione os 4 CSVs.
- **Gerar no workspace:** peça ao Genie Code para rodar `gen_fpa_data.py` em um notebook e
  gravar os dados direto no Volume.

Depois, leia no Bronze com `read_files` (csv, `header=true`). Ver o runbook do caso em `../README.md`.

## Como regenerar (em um notebook do workspace)

Determinístico (seed=42) e re-executável — sobrescreve os 4 CSVs:

```python
%pip install --quiet pandas faker
%run ./gen_fpa_data.py
```

Ao final, o script imprime contagens, checagem de integridade (órfãos e chaves duplicadas),
os sinais de negócio (resultado, variância de despesa, top estouros), a prontidão da série
mensal para o `ai_forecast` e amostras de cada arquivo.
