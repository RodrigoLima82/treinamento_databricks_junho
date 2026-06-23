# Caso 1 — Torre de Controle de Suprimentos (Runbook Genie Code)

## O que é
Uma **torre de controle de Suprimentos** para uma mineradora (fictícia): um painel único que reúne
compras MRO, contratos, entregas e fornecedores para responder, em um só lugar, *"quanto gastamos,
com quem, no prazo e dentro de contrato?"*.

## A dor
Hoje esses dados vivem espalhados (ERP de compras, planilhas de contratos, controles de recebimento)
e a área não enxerga o quadro completo: entregas atrasadas sem visão de OTIF, gasto fora de contrato,
savings invisíveis e risco de fornecedor único — e perguntas simples levam dias para responder.

## Como o Databricks resolve
Construímos a solução **0→100 numa única plataforma governada**, do dado cru à decisão:
Lakehouse / medalhão (Bronze → Silver → Gold) → AI Functions → AI/BI Dashboard → Genie Space →
Databricks App, tudo sobre o Unity Catalog. Do CSV cru à decisão, em minutos.

---

## Como construir (Genie Code)

Construa este caso **conversando com o Databricks Genie Code** (Free Edition). Vá **uma fase por
vez**: cole o texto em destaque no Genie, espere terminar e confira o resultado antes de seguir.

> 💬 Os textos são um ponto de partida — adapte com suas palavras. Se algo der errado, cole a
> mensagem de erro e peça ao Genie para corrigir antes de continuar.

---

## Fase 0 — Fundação
> "Vou montar um caso de uso de Suprimentos e gostaria que você seguisse as convenções das
> skills `dbx-foundation` e `dbx-genie-code-playbook` deste repositório. Para começar, prepare
> a base no Unity Catalog: crie um catálogo `treinamento_databricks`, um schema `suprimentos`
> e um volume `raw` para eu enviar os arquivos. Faça de forma que eu possa executar novamente
> sem erros e, ao final, confirme o que foi criado usando `SHOW SCHEMAS IN treinamento_databricks`
> e `SHOW VOLUMES IN treinamento_databricks.suprimentos` — não use o `information_schema` para essa
> conferência."

**Carregue os dados** (os 6 CSVs já estão no Git folder do workshop):
> "Este repositório do workshop já está clonado como Git folder no meu workspace, e os 6 arquivos
> CSV estão na pasta `casos/01-suprimentos-torre-controle/data`. Copie esses 6 arquivos para dentro
> do volume `raw` de suprimentos que acabamos de criar. Ao terminar, liste os arquivos que ficaram
> no volume para eu conferir os 6."

✅ **Confira:** os 6 arquivos aparecem no volume `raw`.

---

## Fase 1 — Pipeline (Bronze → Silver → Gold)
Todo o medalhão já está versionado como uma **Lakeflow Declarative Pipeline (SDP)**:
`casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql`. Você só cria a pipeline
apontando para esse arquivo e roda.

> "Neste repositório, que já está clonado como Git folder no meu workspace, há um arquivo SQL pronto
> que define toda a transformação de Suprimentos — as camadas bronze, silver e gold — em
> `casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql`. Crie uma Lakeflow
> Declarative Pipeline serverless usando esse arquivo como código-fonte, tendo como destino o
> catálogo `treinamento_databricks` e o schema `suprimentos`. Em seguida, rode a pipeline com
> **Full refresh** e, ao terminar, me mostre o diagrama (DAG) e a contagem de linhas das tabelas
> gold para eu conferir."

✅ **Confira:** a pipeline cria as tabelas `bronze_*`, `silver_*` e as views `gold_*`, o DAG roda
sem erro e as contagens fazem sentido (ex.: ~800 pedidos, ~2.400 itens).

---

## Fase 2(a) — Um componente de IA (opcional)
> "Para incluir um componente de IA: crie uma visão que utilize os números do mês mais recente —
> gasto total, percentual de economia, OTIF e os principais atrasos — e gere um breve resumo
> executivo em português, usando uma função de IA do Databricks (por exemplo, `ai_query`) com um
> modelo disponível no workspace. Pode ser um único parágrafo."

✅ **Confira:** o resumo cita números reais das tabelas gold.

---

## Fase 2(b) — A mesma ideia, agora No-Code (Lakeflow Designer) (opcional)
Aqui você cria uma view **sem escrever código**, montando a transformação visualmente no
**Lakeflow Designer** — o editor No-Code de pipelines do Databricks. O objetivo é o mesmo da fase
anterior (uma nova view sobre o gold), só que arrastando e conectando blocos em vez de codar.

1. Abra **Jobs & Pipelines → Create → ETL pipeline** e escolha o editor visual (**No-Code / Lakeflow Designer**).
2. Adicione uma **fonte** apontando para uma tabela gold — por exemplo, `gold_gasto_categoria`.
3. Adicione uma **transformação** para filtrar/agregar (por exemplo, manter só o mês mais recente e
   ordenar do maior para o menor gasto).
4. Defina a **saída** como uma nova view no schema `treinamento_databricks.suprimentos`
   (por exemplo, `gold_top_categorias_mes`).
5. **Publique e rode** a pipeline.

✅ **Confira:** a nova view aparece em `treinamento_databricks.suprimentos` e os números batem com o dashboard.

---

## Fase 3 — Dashboard (AI/BI)
> "Crie um dashboard chamado **Torre de Controle de Suprimentos** sobre as tabelas gold. No topo,
> quero os principais indicadores: gasto total, percentual de economia, OTIF e percentual de gasto
> fora de contrato. Abaixo: gasto por categoria e por centro, a evolução mensal do gasto, um ranking
> dos dez maiores fornecedores e uma tabela de alerta com os fornecedores únicos e os pedidos
> atrasados ainda em aberto. Antes de montar cada gráfico, execute a consulta no SQL para garantir
> que funciona."

> 💡 **Visual:** siga a skill `dbx-dashboard-design` (KPIs no topo, regra 60-30-10, paleta da marca, contraste em claro/escuro).

✅ **Confira:** todos os painéis aparecem sem erro.

---

## Fase 4(a) — Genie Space (perguntas em português)
> ⚠️ **Limitação do Free Edition:** o Genie Space **não pode ser criado por código** (API, SDK ou `createAsset`) — falha por permissão. Esta é uma etapa **manual na UI**; o Genie Code ajuda apenas preparando a configuração.

**1. Peça a configuração ao Genie Code:**

> "Quero um Genie Space chamado **Suprimentos** sobre as tabelas gold, para perguntar em linguagem
> natural. Não tente criá-lo por código — em vez disso, me entregue tudo pronto para eu criar pela
> interface: a lista das tabelas gold que devo incluir, um texto de instruções em português
> (responder em reais e nunca inventar números) e cinco perguntas de exemplo, como *'qual o gasto
> com peças de britador na Mina Norte nos últimos seis meses?'* e *'quais fornecedores estão com
> OTIF abaixo de 80%?'*."

**2. Crie o Space na UI** (passo a passo):
1. No menu lateral, abra **Genie** e clique em **New** (novo Space).
2. Em **Tables / Data**, selecione o catálogo `treinamento_databricks` → schema `suprimentos` e marque as tabelas **`gold_*`**.
3. Escolha o **SQL Warehouse** (o 2X-Small do Free Edition) e dê o nome **Suprimentos**.
4. Em **Instructions**, cole o texto que o Genie Code preparou (responder em português, valores em reais, nunca inventar números).
5. Em **Sample questions**, adicione as 5 perguntas sugeridas.
6. **Salve**, abra o Space e teste 2 perguntas, conferindo com o gold.

✅ **Confira:** as respostas batem com a camada gold. **Anote o ID do Space** (aparece na URL, `.../genie/rooms/<ID>`) — a Fase 5 (App) usa.

---

## Fase 4(b) — Multi-Agent Supervisor (Agent Bricks) (opcional)
Um gostinho de **orquestração de agentes**: um **Multi-Agent Supervisor** (Agent Bricks) que decide,
a cada pergunta, se chama o **Genie Space Suprimentos** (perguntas analíticas sobre o gold) ou uma
**ferramenta de cálculo** específica. Com 2 agentes/ferramentas o supervisor tem o que rotear — por
isso faz mais sentido aqui do que com um agente só.

> ⚠️ **Free Edition:** o **Knowledge Assistant não existe**, mas o **Multi-Agent Supervisor está
> disponível**. Como no Genie Space, a criação é **manual na UI** (por código costuma falhar por
> permissão); o Genie Code só prepara a configuração. Depende do Genie Space da Fase 4(a).

**1. Crie uma ferramenta (UC Function) para o supervisor ter o que orquestrar:**
> "Crie uma **UC Function** em `treinamento_databricks.suprimentos` chamada `sup_otif_fornecedor` que
> recebe o nome de um fornecedor e devolve o OTIF dele a partir das tabelas gold. Execute com um
> fornecedor que exista nos dados e me mostre o resultado."

**2. Peça a configuração do supervisor ao Genie Code:**
> "Quero um **Multi-Agent Supervisor** de Suprimentos. Não tente criá-lo por código — me entregue a
> configuração para eu montar na UI: (a) os agentes/ferramentas — o **Genie Space Suprimentos** (use
> o ID que anotei) e a UC Function `sup_otif_fornecedor`; (b) uma descrição de cada um (quando usar);
> (c) instruções de roteamento em português; e (d) 3 perguntas de exemplo, uma que vá para o Genie e
> outra para a função."

**3. Crie o Supervisor na UI** (passos em nível de objetivo — a UI do Agent Bricks pode variar):
1. Abra **Agents (Agent Bricks)** e crie um **Multi-Agent Supervisor**.
2. Adicione o **Genie Space Suprimentos** como agente e a **UC Function** `sup_otif_fornecedor` como ferramenta.
3. Cole as **descrições** e as **instruções de roteamento** que o Genie Code preparou.
4. **Salve** e abra o playground do supervisor (aguarde alguns minutos até ficar *online*).

✅ **Confira:** uma pergunta analítica (*"gasto por categoria no último mês"*) cai no **Genie**; uma
pergunta pontual (*"qual o OTIF do fornecedor X?"*) aciona a **função** — e o supervisor combina os dois.

---

## Fase 5 — App (Databricks App)
> "Para finalizar, crie um **Databricks App em Streamlit** chamado **Torre de Controle de
> Suprimentos**, seguindo as skills `dbx-app` (build/deploy) e `dbx-brand` (logo e paleta Databricks). Quero uma tela com os
> principais indicadores (gasto, economia, OTIF e percentual fora de contrato), um gráfico de gasto
> por categoria e uma lista de 'pedidos em risco' (atrasados ou em aberto), lendo das tabelas gold.
> Inclua uma aba de chat conectada ao Genie Space **Suprimentos** (use o ID que anotei). O app
> precisa subir de primeira: deixe o Streamlit usar a porta padrão do ambiente (não fixe 8080),
> autentique com `Config()` do SDK e conecte ao warehouse só quando a tela precisar (não no import),
> de forma cacheada. Envolva cada consulta em `st.spinner` com `try/except` mostrando o erro real
> (`st.error`) e um timeout curto — o app nunca pode travar mudo em 'Carregando…'. Anexe o **SQL
> Warehouse como resource** do app e me diga o **nome do service principal** do app para eu liberar
> o acesso às tabelas gold. Em seguida, faça o deploy."

**Depois do deploy (2 passos de UI/SQL — é o que destrava o "Carregando…"):**
1. **Anexe o SQL Warehouse** ao app como *resource* (App → Edit → Resources → SQL Warehouse,
   serverless). Sem isso o app (que roda como service principal) não tem como consultar e trava.
2. **Libere os dados ao service principal do app** (nome em App → Authorization), no SQL Editor:
   ```sql
   GRANT USE CATALOG ON CATALOG treinamento_databricks TO `<app-sp>`;
   GRANT USE SCHEMA  ON SCHEMA  treinamento_databricks.suprimentos TO `<app-sp>`;
   GRANT SELECT      ON SCHEMA  treinamento_databricks.suprimentos TO `<app-sp>`;
   ```

> 💡 **"Carregando…" sem fim ou "Nenhum SQL Warehouse disponível"?** É o app sem o warehouse anexado
> (passo 1) ou sem GRANT no service principal (passo 2) — e **editar só o `app.yaml` não resolve**.
> Faça os 2 passos acima; se persistir, abra os **logs** do app para ver o erro real.

✅ **Confira:** o app abre com o logo, os indicadores corretos e o chat do Genie respondendo.

---

## Fase 6 — Conclusão
- [ ] Pipeline (Bronze, Silver, Gold) criada e conferida
- [ ] Dashboard funcionando · Genie respondendo · App no ar

No treino: mostre o CSV cru → rode a pipeline até o gold → pergunte no Genie → abra o App.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small) e até 3 apps (encerram após 24h). Ensaie antes e
> reinicie o app pouco antes da apresentação.
