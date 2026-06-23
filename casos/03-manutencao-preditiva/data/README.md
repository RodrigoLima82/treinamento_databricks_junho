# Dados — Caso 3: Manutenção Preditiva de Ativos

Dados **sintéticos e fictícios** para o workshop Databricks (Free Edition). Simulam o
**monitoramento de ativos industriais** de uma mineradora fictícia: cadastro de ativos, telemetria
de sensores, ordens de manutenção e eventos de falha. Servem para construir o pipeline
Bronze → Silver → Gold (com ingestão tipo streaming), o modelo de ML, o AI/BI Dashboard, o Genie
Space e o App do caso.

> ⚠️ Ativos, fabricantes, sites e valores são **gerados aleatoriamente** — não representam dados reais.

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `ativos.csv` | 40 | Cadastro dos ativos (tipo, criticidade, site, potência). |
| `falhas.csv` | 14 | Eventos de falha (causa, componente, severidade). |
| `ordens_manutencao.csv` | 97 | Ordens corretivas e preventivas (custo, downtime). |
| `leituras_sensores_lote01.csv` | 9.600 | Telemetria — dias 1–30 (temperatura, vibração, pressão, rpm). |
| `leituras_sensores_lote02.csv` | 9.600 | Telemetria — dias 31–60. |
| `leituras_sensores_lote03.csv` | 9.600 | Telemetria — dias 61–90. |
| **(telemetria total)** | **28.800** | A telemetria é o arquivo de **maior volume**. |

Definição completa de colunas e tipos em **[`DICIONARIO.md`](./DICIONARIO.md)**.

### Sinais de negócio embutidos nos dados
- **Vibração e temperatura sobem (rampa) ANTES de uma falha** nos ativos críticos — o sinal que o
  modelo de ML aprende (vibração pré-falha tipicamente **+60% a +75%** acima da base do ativo).
- **4 ativos em degradação ATUAL** (rampa até o fim da janela, ainda **sem falha registrada**) —
  são os que o `gold_saude_ativo`/modelo devem sinalizar a tempo (2 ficam **Crítico**, 2 **Atenção**).
- **4 ativos com 2 falhas** cada (MTBF ~42–46 dias) e 6 com 1 falha — base para o MTBF.
- **Custo concentrado nas corretivas** (poucas ordens, alto custo/downtime) vs. preventivas (muitas, baratas).
- Integridade referencial total (todo `id_ativo` de leituras/falhas/ordens existe em `ativos`).

### Por que a telemetria vem em 3 lotes
Para **simular ingestão incremental tipo streaming** no Free Edition. A camada bronze usa
`read_files` (Auto Loader) sobre `leituras_sensores_lote*.csv` como **streaming table** — ela ingere
só os arquivos **novos**. Sobe-se um lote por vez para ver o número de linhas crescer sem reprocessar.

## Como subir para um UC Volume

Volume do caso: `/Volumes/treinamento_databricks/manutencao/raw`

**Recomendado — automático via Genie Code (Git folder no workspace):** como o repositório fica
clonado como Git folder no workspace, peça ao Genie Code para copiar os CSVs da pasta
`casos/03-manutencao-preditiva/data` deste repositório para o volume `raw`. O prompt pronto está na
Fase 0 do runbook (`../README.md`). Para **ver o streaming**, suba primeiro `ativos.csv`, `falhas.csv`,
`ordens_manutencao.csv` e os lotes `lote01`/`lote02`; depois suba o `lote03` (Fase 1).

> ℹ️ O Bronze lê com `read_files`, que acessa **Volumes / object storage** (não caminhos
> `/Workspace/...`). Por isso copiamos os arquivos do Git folder para o Volume antes de ingerir.

**Alternativas:**
- **UI do Catalog:** Catalog → `treinamento_databricks` → `manutencao` → `raw` →
  **Upload to this volume** → selecione os CSVs.
- **Gerar no workspace:** peça ao Genie Code para rodar `gen_manutencao_data.py` em um notebook e
  gravar os dados direto no Volume.

## Como regenerar (em um notebook do workspace ou local)

Determinístico (seed=42) e re-executável — sobrescreve os CSVs:

```python
%pip install --quiet pandas faker numpy
%run ./gen_manutencao_data.py
```

Ao final, o script imprime contagens, checagem de integridade (órfãos/duplicatas), o sinal de
degradação (vibração pré-falha vs. baseline) e amostras de cada arquivo.
