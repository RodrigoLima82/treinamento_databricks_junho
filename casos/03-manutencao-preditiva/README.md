# Caso 3 — Manutenção Preditiva de Ativos (Runbook Genie Code)

## O que é
Um painel de **manutenção preditiva** para uma mineradora (fictícia): a telemetria dos sensores de
bombas, motores, britadores e moinhos chega de forma contínua, vira **saúde por ativo**, MTBF e custo
de manutenção, e alimenta um **modelo de ML** que aponta *quais ativos vão falhar antes de falharem*.

## A dor
A manutenção hoje é **reativa**: o ativo quebra, a produção para e o custo da corretiva (mais o
downtime) explode. Os dados de sensor existem, mas ficam presos no histórico do supervisório, sem
ninguém cruzando com o histórico de falhas e de ordens. Falta uma visão única de **quem está
degradando agora**, quanto cada ativo custa e quando ele tende a falhar de novo.

## Como o Databricks resolve
Construímos a solução **0→100 numa única plataforma governada**, do sensor à decisão:
ingestão **tipo streaming** (Lakeflow + Auto Loader) → medalhão Bronze → Silver → Gold →
**MLflow** (treino e registro do modelo de risco) → **Model Serving** (opcional) → AI/BI Dashboard →
Genie Space → Databricks App, tudo sobre o Unity Catalog.

---

## Como construir (Genie Code)

Construa este caso **conversando com o Databricks Genie Code** (Free Edition). Vá **uma fase por
vez**: cole o texto em destaque no Genie, espere terminar e confira o resultado antes de seguir.

> 💬 Os textos são um ponto de partida — adapte com suas palavras. Se algo der errado, cole a
> mensagem de erro e peça ao Genie para corrigir antes de continuar.

---

## Fase 0 — Fundação
> "Vou montar um caso de uso de Manutenção Preditiva e gostaria que você seguisse as convenções das
> skills `dbx-foundation` e `dbx-genie-code-playbook` deste repositório. Para começar, prepare a base
> no Unity Catalog: crie um catálogo `treinamento_databricks`, um schema `manutencao` e um volume
> `raw` para eu enviar os arquivos. Faça de forma que eu possa executar novamente sem erros e, ao
> final, confirme o que foi criado usando `SHOW SCHEMAS IN treinamento_databricks` e
> `SHOW VOLUMES IN treinamento_databricks.manutencao` — não use o `information_schema` para essa
> conferência."

**Carregue os dados** (os CSVs já estão no Git folder do workshop). Para conseguirmos **ver a
ingestão incremental** na próxima fase, vamos segurar o último lote de telemetria:
> "Este repositório do workshop já está clonado como Git folder no meu workspace, e os arquivos do
> caso estão em `casos/03-manutencao-preditiva/data`. Copie para o volume `raw` de manutenção os
> arquivos `ativos.csv`, `falhas.csv`, `ordens_manutencao.csv` e os dois primeiros lotes de
> telemetria, `leituras_sensores_lote01.csv` e `leituras_sensores_lote02.csv`. **Deixe o
> `leituras_sensores_lote03.csv` de fora por enquanto** — vou usá-lo na próxima fase para ver a
> ingestão incremental. Ao terminar, liste os arquivos que ficaram no volume."

✅ **Confira:** estão no volume `raw` os 3 arquivos de cadastro/eventos + os lotes 01 e 02 (o 03 ainda não).

---

## Fase 1 — Pipeline (Bronze → Silver → Gold) com ingestão tipo streaming
Todo o medalhão já está versionado como uma **Lakeflow Declarative Pipeline (SDP)**:
`casos/03-manutencao-preditiva/pipeline/manutencao_pipeline.sql`. A camada bronze da telemetria usa
`read_files` (Auto Loader) como **streaming table** — é assim que simulamos *Structured Streaming* no
Free Edition: ela ingere os arquivos de lote de forma **incremental**.

> "Neste repositório, que já está clonado como Git folder no meu workspace, há um arquivo SQL pronto
> que define toda a transformação de Manutenção — as camadas bronze, silver e gold — em
> `casos/03-manutencao-preditiva/pipeline/manutencao_pipeline.sql`. Crie uma Lakeflow Declarative
> Pipeline serverless usando esse arquivo como código-fonte, tendo como destino o catálogo
> `treinamento_databricks` e o schema `manutencao`. Em seguida, rode a pipeline com **Full refresh**
> e, ao terminar, me mostre o diagrama (DAG) e a contagem de linhas de `bronze_leituras_sensores` e
> das tabelas gold para eu conferir."

✅ **Confira:** a pipeline cria as tabelas `bronze_*`, `silver_*` e as views `gold_*`; o DAG roda sem
erro; `bronze_leituras_sensores` tem **~19.200** linhas (só os lotes 01 e 02).

### Fase 1(b) — Veja o streaming incremental em ação
Agora chega um **lote novo** de telemetria — como chegaria em produção. A streaming table deve
ingerir **só os dados novos**, sem reprocessar o que já leu.
> "Copie agora o arquivo `casos/03-manutencao-preditiva/data/leituras_sensores_lote03.csv` para o
> volume `raw` de manutenção. Em seguida, rode a pipeline de novo (um **Refresh** normal, não full) e
> me mostre a nova contagem de `bronze_leituras_sensores`. Quero ver que ela cresceu só com as linhas
> do lote novo."

✅ **Confira:** `bronze_leituras_sensores` passa para **28.800** linhas (ingestão incremental dos
~9.600 do lote 03). As views gold (saúde, MTBF, custo, risco) se atualizam sozinhas.

> 💡 Em produção, em vez de subir arquivos à mão, novos arquivos cairiam no volume continuamente e a
> mesma streaming table os ingeriria — é o mesmo mecanismo do Auto Loader / Structured Streaming.

---

## Fase 2 — Modelo de risco de falha (MLflow)
Aqui saímos do score heurístico (`gold_saude_ativo`) e treinamos um **modelo de verdade** que aprende
o padrão de degradação dos sensores que antecede uma falha. Isso é feito em um **notebook** (não faz
parte do pipeline SQL), com **MLflow**.

> "Quero treinar um modelo simples de risco de falha com MLflow, em um notebook serverless. Use como
> base a telemetria resumida `treinamento_databricks.manutencao.gold_telemetria_resumo` (um registro
> por ativo e dia, com médias e máximos de vibração, temperatura, pressão e rpm) e o histórico de
> falhas `silver_falhas`. Monte um conjunto de treino no grão **ativo × dia**, onde o rótulo
> `falha_proxima` é 1 se aquele ativo teve uma falha **nos 7 dias seguintes** à data, e 0 caso
> contrário. Adicione as features dos sensores e a criticidade do ativo. Treine um classificador
> simples do scikit-learn (por exemplo, gradient boosting). Como a falha é rara (~3% dos dias),
> **balanceie as classes por padrão** (ex.: `class_weight='balanced'` em RandomForest/LogisticRegression,
> ou `sample_weight` no gradient boosting). Ative o `mlflow.autolog()`, registre a
> métrica de qualidade (AUC e F1) e **registre o modelo no Unity Catalog** como
> `treinamento_databricks.manutencao.modelo_risco_falha`. No fim, me mostre a métrica e a importância
> das features para eu ver que vibração e temperatura pesam mais."

✅ **Confira:** o run aparece no **MLflow** com a métrica logada; o modelo
`modelo_risco_falha` fica registrado no Unity Catalog; vibração/temperatura aparecem entre as
features mais importantes (é o sinal que embutimos nos dados).

> 💡 Dataset pequeno e determinístico (seed=42): o treino roda em segundos, sem GPU. Se a classe
> positiva ficar muito rara, peça ao Genie para balancear (ex.: `class_weight`) ou ampliar a janela do rótulo.

---

## Fase 3 — Model Serving (opcional)
> ⚠️ **Limitação do Free Edition:** Model Serving roda **pay-per-token / CPU pequeno, sem provisioned
> throughput e sem GPU**, e criar um endpoint pode esbarrar em **permissão ou cota**. Por isso esta
> fase é **opcional** — e damos um caminho alternativo (batch scoring) que **sempre funciona**.

**Opção A — Endpoint de serving (pela UI):**
1. Abra **Serving → Create serving endpoint**.
2. Escolha o modelo registrado `treinamento_databricks.manutencao.modelo_risco_falha` (versão mais recente).
3. Use o menor tamanho de CPU e **scale-to-zero**; crie e aguarde ficar *Ready*.
4. Teste com um exemplo de features e confira a probabilidade de falha retornada.

**Opção B — Batch scoring (sem endpoint, recomendado no Free Edition):**
> "Sem criar endpoint de serving, quero pontuar os ativos em lote. Em um notebook, carregue o modelo
> registrado `treinamento_databricks.manutencao.modelo_risco_falha` com o MLflow, aplique sobre as
> features mais recentes de cada ativo (a partir de `gold_telemetria_resumo`) e grave o resultado em
> uma tabela `treinamento_databricks.manutencao.gold_predicoes_risco` com o id do ativo e a
> probabilidade de falha prevista. Ao final, me mostre os 10 ativos com maior probabilidade."

✅ **Confira:** ou o endpoint responde com uma probabilidade, ou a tabela `gold_predicoes_risco`
existe e os ativos no topo coincidem com os que o `gold_saude_ativo` marcou como **Crítico/Atenção**.

---

## Fase 4 — Dashboard (AI/BI)
> "Crie um dashboard chamado **Saúde de Ativos & Manutenção Preditiva** sobre as tabelas gold. No
> topo, quero os principais indicadores: número de ativos em risco Crítico, MTBF médio, custo total
> de manutenção e horas totais de downtime. Abaixo: um donut de ativos por categoria de risco; o
> custo de manutenção por tipo de ativo separando corretiva e preventiva; a tendência de vibração
> média diária dos ativos em risco (a partir de `gold_telemetria_resumo`); e uma tabela de atenção
> com o ranking de `gold_ativos_risco` (score, nº de falhas, MTBF e custo). Antes de montar cada
> gráfico, execute a consulta no SQL para garantir que funciona."

> 💡 **Visual:** siga a skill `dbx-dashboard-design` (KPIs no topo, regra 60-30-10, paleta da marca, contraste em claro/escuro).

✅ **Confira:** todos os painéis aparecem sem erro; os ativos Crítico/Atenção batem com `gold_saude_ativo`.

---

## Fase 5(a) — Genie Space (perguntas em português)
> ⚠️ **Limitação do Free Edition:** o Genie Space **não pode ser criado por código** (API, SDK ou `createAsset`) — falha por permissão. Esta é uma etapa **manual na UI**; o Genie Code ajuda apenas preparando a configuração.

**1. Peça a configuração ao Genie Code:**
> "Quero um Genie Space chamado **Manutenção** sobre as tabelas gold, para perguntar em linguagem
> natural. Não tente criá-lo por código — em vez disso, me entregue tudo pronto para eu criar pela
> interface: a lista das tabelas gold que devo incluir, um texto de instruções em português
> (responder em reais, datas no formato ano-mês, risco e criticidade vêm de `gold_saude_ativo`/
> `gold_ativos_risco`, e nunca inventar números) e cinco perguntas de exemplo, como *'quais ativos
> estão com categoria de risco Crítico agora?'* e *'qual o MTBF dos britadores?'*."

**2. Crie o Space na UI** (passo a passo):
1. No menu lateral, abra **Genie** e clique em **New** (novo Space).
2. Em **Tables / Data**, selecione o catálogo `treinamento_databricks` → schema `manutencao` e marque as tabelas **`gold_*`**.
3. Escolha o **SQL Warehouse** (o 2X-Small do Free Edition) e dê o nome **Manutenção**.
4. Em **Instructions**, cole o texto que o Genie Code preparou (responder em português, valores em reais, nunca inventar números).
5. Em **Sample questions**, adicione as 5 perguntas sugeridas.
6. **Salve**, abra o Space e teste 2 perguntas, conferindo com o gold.

✅ **Confira:** as respostas batem com a camada gold. **Anote o ID do Space** (aparece na URL, `.../genie/rooms/<ID>`) — a Fase 6 (App) usa.

---

## Fase 5(b) — Multi-Agent Supervisor (Agent Bricks) (opcional)
Um gostinho de **orquestração de agentes**: um **Multi-Agent Supervisor** (Agent Bricks) que decide,
a cada pergunta, se chama o **Genie Space Manutenção** (perguntas analíticas sobre o gold) ou uma
**ferramenta de cálculo** específica (a saúde de um ativo pontual). Com 2 agentes/ferramentas o
supervisor tem o que rotear.

> ⚠️ **Free Edition:** o **Knowledge Assistant não existe**, mas o **Multi-Agent Supervisor está
> disponível**. Como no Genie Space, a criação é **manual na UI** (por código costuma falhar por
> permissão); o Genie Code só prepara a configuração. Depende do Genie Space da Fase 5(a).

**1. Crie uma ferramenta (UC Function) para o supervisor ter o que orquestrar:**
> "Crie uma **UC Function** em `treinamento_databricks.manutencao` chamada `mnt_saude_ativo` que
> recebe o id (ou a TAG) de um ativo e devolve o score de risco, a categoria e a vibração recente
> dele a partir de `gold_saude_ativo`. Execute com um ativo que exista nos dados e me mostre o resultado."

**2. Peça a configuração do supervisor ao Genie Code:**
> "Quero um **Multi-Agent Supervisor** de Manutenção. Não tente criá-lo por código — me entregue a
> configuração para eu montar na UI: (a) os agentes/ferramentas — o **Genie Space Manutenção** (use o
> ID que anotei) e a UC Function `mnt_saude_ativo`; (b) uma descrição de cada um (quando usar);
> (c) instruções de roteamento em português; e (d) 3 perguntas de exemplo, uma que vá para o Genie e
> outra para a função."

**3. Crie o Supervisor na UI** (passos em nível de objetivo — a UI do Agent Bricks pode variar):
1. Abra **Agents (Agent Bricks)** e crie um **Multi-Agent Supervisor**.
2. Adicione o **Genie Space Manutenção** como agente e a **UC Function** `mnt_saude_ativo` como ferramenta.
3. Cole as **descrições** e as **instruções de roteamento** que o Genie Code preparou.
4. **Salve** e abra o playground do supervisor (aguarde alguns minutos até ficar *online*).

✅ **Confira:** uma pergunta analítica (*"custo de manutenção corretiva por site"*) cai no **Genie**;
uma pergunta pontual (*"qual o risco do ativo BR-002?"*) aciona a **função** — e o supervisor combina os dois.

---

## Fase 6 — App (Databricks App)
> "Para finalizar, crie um **Databricks App em Streamlit** chamado **Manutenção Preditiva**, seguindo
> as skills `dbx-app` (build/deploy) e `dbx-brand` (logo e paleta Databricks). Quero uma tela inicial
> com os principais indicadores (ativos em risco, MTBF médio, custo de manutenção e downtime), um
> donut de risco e uma tabela de 'ativos em risco' lendo de `gold_ativos_risco`; e uma segunda tela
> que mostre, para um ativo escolhido, a série temporal de vibração e temperatura de
> `gold_telemetria_resumo` (e a probabilidade prevista de `gold_predicoes_risco`, se ela existir).
> Inclua uma aba de chat conectada ao Genie Space **Manutenção** (use o ID que anotei). Faça o app subir de primeira no Free Edition e publique."

> 🔧 A parte técnica do app — porta, autenticação, conexão ao SQL Warehouse, anexar o warehouse como *resource*, liberar acesso (GRANT) ao service principal e o troubleshooting de "Carregando…" — está toda na skill **`dbx-app`**; o Genie Code segue de lá e te pede só as confirmações de UI. (Limite Free Edition: até 3 apps, auto-stop em 24h.)

✅ **Confira:** o app abre com o logo, a saúde dos ativos correta e o chat do Genie respondendo.

---

## Fase 7 — Conclusão
- [ ] Pipeline (Bronze, Silver, Gold) criada e conferida; ingestão incremental demonstrada (lote 03)
- [ ] Modelo treinado e **registrado no Unity Catalog** (MLflow)
- [ ] (Opcional) endpoint de serving OU `gold_predicoes_risco` por batch scoring
- [ ] Dashboard funcionando · Genie respondendo · App no ar

No treino: mostre a telemetria crua → rode a pipeline até o gold → suba um lote novo (streaming) →
treine o modelo no MLflow → pergunte no Genie → abra o App.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small), 1 pipeline ativa por tipo, Model Serving sem GPU/
> provisioned throughput e até 3 apps (encerram após 24h). Ensaie antes e reinicie o app pouco antes
> da apresentação.
