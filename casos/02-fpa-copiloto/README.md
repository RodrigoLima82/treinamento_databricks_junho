# Caso 2 — Copiloto de FP&A (Runbook Genie Code)

## O que é
Um **copiloto de FP&A** (planejamento financeiro & análise) para uma empresa de mineração
(fictícia): um painel e um assistente que reúnem **orçado vs. realizado** por centro de custo,
conta contábil e mês para responder, em um só lugar, *"onde estouramos o orçamento, quanto sobra
de resultado e o que esperar dos próximos meses?"*.

## A dor
Hoje o acompanhamento orçamentário vive em planilhas: o fechamento do mês é lento, a variância
(orçado × realizado) só aparece tarde, os **estouros** se escondem entre centenas de linhas e a
**projeção** de receita/despesa é um chute manual. Perguntas simples — *"qual conta mais estourou
na Mina Norte?"*, *"a receita vai fechar o ano no plano?"* — levam dias e dependem de quem domina a
planilha.

## Como o Databricks resolve
Construímos a solução **0→100 numa única plataforma governada**, do dado cru à decisão:
Lakehouse / medalhão (Bronze → Silver → Gold) → **Metric View** (métricas de negócio reutilizáveis)
→ **AI Functions** (`ai_forecast` para projetar, `ai_query` para resumir) → AI/BI Dashboard →
Genie Space → Multi-Agent Supervisor → Databricks App, tudo sobre o Unity Catalog.
Do CSV cru à projeção do próximo trimestre, em minutos.

---

## Como construir (Genie Code)

Construa este caso **conversando com o Databricks Genie Code** (Free Edition). Vá **uma fase por
vez**: cole o texto em destaque no Genie, espere terminar e confira o resultado antes de seguir.

> 💬 Os textos são um ponto de partida — adapte com suas palavras. Se algo der errado, cole a
> mensagem de erro e peça ao Genie para corrigir antes de continuar.

---

## Fase 0 — Fundação
> "Vou montar um caso de uso de FP&A (Finanças) e gostaria que você seguisse as convenções das
> skills `dbx-foundation` e `dbx-genie-code-playbook` deste repositório. Para começar, prepare
> a base no Unity Catalog: crie um catálogo `treinamento_databricks`, um schema `financas`
> e um volume `raw` para eu enviar os arquivos. Faça de forma que eu possa executar novamente
> sem erros e, ao final, confirme o que foi criado usando `SHOW SCHEMAS IN treinamento_databricks`
> e `SHOW VOLUMES IN treinamento_databricks.financas` — não use o `information_schema` para essa
> conferência."

**Carregue os dados** (os 4 CSVs já estão no Git folder do workshop):
> "Este repositório do workshop já está clonado como Git folder no meu workspace, e os 4 arquivos
> CSV estão na pasta `casos/02-fpa-copiloto/data`. Copie esses 4 arquivos para dentro do volume
> `raw` de finanças que acabamos de criar. Ao terminar, liste os arquivos que ficaram no volume
> para eu conferir os 4."

✅ **Confira:** os 4 arquivos (`centros_custo.csv`, `contas_contabeis.csv`, `orcamento.csv`,
`lancamentos.csv`) aparecem no volume `raw`.

---

## Fase 1 — Pipeline (Bronze → Silver → Gold)
Todo o medalhão já está versionado como uma **Lakeflow Declarative Pipeline (SDP)**:
`casos/02-fpa-copiloto/pipeline/fpa_pipeline.sql`. Você só cria a pipeline apontando para esse
arquivo e roda.

> "Neste repositório, que já está clonado como Git folder no meu workspace, há um arquivo SQL pronto
> que define toda a transformação de FP&A — as camadas bronze, silver e gold — em
> `casos/02-fpa-copiloto/pipeline/fpa_pipeline.sql`. Crie uma Lakeflow Declarative Pipeline
> serverless usando esse arquivo como código-fonte, tendo como destino o catálogo
> `treinamento_databricks` e o schema `financas`. Em seguida, rode a pipeline com **Full refresh**
> e, ao terminar, me mostre o diagrama (DAG) e a contagem de linhas das tabelas gold para eu conferir."

✅ **Confira:** a pipeline cria as tabelas `bronze_*`, `silver_*` e as views `gold_*`, o DAG roda
sem erro e as contagens fazem sentido (ex.: ~4.200 linhas em `gold_orcado_vs_realizado`, sendo os
meses futuros com realizado nulo; algumas dezenas de estouros em `gold_topo_estouros`).

---

## Fase 2 — Componentes de IA

A IA deste caso vem em três peças: **(a) métricas reutilizáveis** (Metric View),
**(b) projeção** dos próximos meses (`ai_forecast`) e **(c) um resumo executivo** em linguagem
natural (`ai_query`). Faça uma de cada vez.

### Fase 2(a) — Metric View (métricas de negócio reutilizáveis)
Uma **Metric View** define métricas como **orçado**, **realizado** e **variância %** uma única vez,
de forma governada, para o dashboard, o Genie e o SQL usarem com a mesma definição. Siga a skill
`databricks-metric-views`.

> "Crie uma **Metric View** chamada `treinamento_databricks.financas.fin_orcamento` sobre a tabela
> `gold_orcado_vs_realizado`. As **dimensões** devem ser mês, tipo (Receita/Despesa/CAPEX), grupo,
> área, centro e conta. As **medidas** devem ser: orçado (soma do valor orçado), realizado (soma do
> valor realizado), variância (realizado − orçado) e variância % (variância sobre o orçado, em
> porcentagem). Depois faça uma consulta de teste agrupando a variância % por tipo e por mês, e me
> mostre o resultado."

Configuração pronta (cole se preferir criar direto pelo editor YAML do Catalog):
```sql
CREATE OR REPLACE VIEW treinamento_databricks.financas.fin_orcamento
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: treinamento_databricks.financas.gold_orcado_vs_realizado
comment: "Métricas de FP&A — orçado, realizado e variância (reutilizáveis em dashboard, Genie e SQL)."
dimensions:
  - name: Mês
    expr: mes
  - name: Tipo
    expr: tipo
  - name: Grupo
    expr: grupo
  - name: Área
    expr: area
  - name: Centro
    expr: centro_nome
  - name: Conta
    expr: conta_nome
measures:
  - name: Orçado
    expr: SUM(valor_orcado)
  - name: Realizado
    expr: SUM(valor_realizado)
  - name: Variância
    expr: SUM(valor_realizado) - SUM(valor_orcado)
  - name: Variância %
    expr: 100 * (SUM(valor_realizado) - SUM(valor_orcado)) / NULLIF(SUM(valor_orcado), 0)
$$
```
Para consultar uma Metric View, as medidas vão dentro de `MEASURE()` e não existe `SELECT *`:
```sql
SELECT `Tipo`, `Mês`,
       MEASURE(`Realizado`)   AS realizado,
       MEASURE(`Variância %`) AS variancia_pct
FROM treinamento_databricks.financas.fin_orcamento
GROUP BY ALL ORDER BY ALL;
```

✅ **Confira:** a consulta de teste roda e a variância % por tipo bate com o gold (Despesa um pouco
acima de 0, Receita levemente positiva).

### Fase 2(b) — Projeção com `ai_forecast`
A tabela `gold_receita_mensal` tem 30 meses de receita realizada (a `gold_orcado_vs_realizado` tem
o orçamento até 6 meses à frente, ainda sem realizado). Vamos **projetar** esses próximos meses.

> "Quero projetar a receita dos próximos seis meses a partir da série mensal de receita realizada.
> Use a função `ai_forecast` do Databricks sobre a tabela `gold_receita_mensal`, usando o mês como
> coluna de tempo e a receita realizada como valor, com horizonte até novembro de 2026. Grave o
> resultado numa tabela `gold_receita_projecao` no schema `financas` e me mostre os meses projetados
> com os limites do intervalo de confiança."

Exemplo de como o `ai_forecast` é chamado (precisa de warehouse serverless — temos no Free Edition):
```sql
CREATE OR REPLACE TABLE treinamento_databricks.financas.gold_receita_projecao AS
SELECT * FROM ai_forecast(
  observed  => TABLE(
    SELECT mes, receita_realizada
    FROM treinamento_databricks.financas.gold_receita_mensal
    WHERE receita_realizada IS NOT NULL
  ),
  horizon   => '2026-11-30',
  time_col  => 'mes',
  value_col => 'receita_realizada'
);
-- Retorna: mes, receita_realizada_forecast, receita_realizada_upper, receita_realizada_lower
```

> 💡 **Bônus:** como o orçamento já existe para esses mesmos meses futuros, dá para comparar a
> **projeção** com o **orçado** (`gold_receita_mensal.receita_orcada`) e responder *"a receita
> tende a fechar no plano?"*. Você pode pedir o mesmo para a **despesa** (série mensal de despesa
> realizada), trocando a fonte na chamada.

✅ **Confira:** a tabela `gold_receita_projecao` tem ~6 meses futuros (jun→nov/2026) com
`*_forecast`, `*_upper` e `*_lower`, e os valores seguem a tendência/sazonalidade do histórico.

### Fase 2(c) — Resumo executivo com `ai_query`
> "Crie uma view `gold_resumo_executivo_mes` que pegue os números do **mês fechado mais recente**
> (use `MAX(mes)` das tabelas gold, não a data de hoje) — receita realizada, despesa realizada,
> resultado (receita − despesa), variância de despesa contra o orçado e o maior estouro do mês — e
> gere um **resumo executivo** em português, em um único parágrafo, usando uma função de IA do
> Databricks (por exemplo, `ai_query`) com um modelo disponível no workspace. O texto deve citar
> apenas os números reais que vierem das tabelas, em reais (BRL), e não inventar nada."

✅ **Confira:** o parágrafo cita números reais das tabelas gold (resultado positivo, despesa um
pouco acima do orçado, e o estouro líder — tipicamente energia/combustíveis na Mina Norte).

---

## Fase 3 — Dashboard (AI/BI)
> "Crie um dashboard chamado **Copiloto de FP&A** sobre as tabelas gold (e a Metric View
> `fin_orcamento`). No topo, quero os principais indicadores: receita realizada, despesa realizada,
> resultado (receita − despesa) e variância de despesa contra o orçado (%). Abaixo: orçado vs.
> realizado por mês, despesa por categoria (grupo), a evolução mensal da receita com a projeção dos
> próximos meses, um ranking das contas/centros com maiores estouros e uma tabela de variância por
> centro de custo. Antes de montar cada gráfico, execute a consulta no SQL para garantir que funciona."

> 💡 **Visual:** siga a skill `dbx-dashboard-design` (KPIs no topo, regra 60-30-10, paleta da marca, contraste em claro/escuro).

✅ **Confira:** todos os painéis aparecem sem erro; a linha de receita mostra histórico + projeção e
o ranking de estouros traz os pares conta × centro esperados.

---

## Fase 4(a) — Genie Space (perguntas em português)
> ⚠️ **Limitação do Free Edition:** o Genie Space **não pode ser criado por código** (API, SDK ou `createAsset`) — falha por permissão. Esta é uma etapa **manual na UI**; o Genie Code ajuda apenas preparando a configuração.

**1. Peça a configuração ao Genie Code:**

> "Quero um Genie Space chamado **FP&A** sobre as tabelas gold e a Metric View `fin_orcamento`, para
> perguntar em linguagem natural. Não tente criá-lo por código — em vez disso, me entregue tudo
> pronto para eu criar pela interface: a lista das tabelas gold e da Metric View que devo incluir, um
> texto de instruções em português (responder em reais, mês no formato AAAA-MM, tratar variância
> positiva em despesa como estouro, e nunca inventar números) e cinco perguntas de exemplo, como
> *'qual conta mais estourou o orçamento na Mina Norte?'* e *'qual a variância de despesa por centro
> de custo neste ano?'*."

**2. Crie o Space na UI** (passo a passo):
1. No menu lateral, abra **Genie** e clique em **New** (novo Space).
2. Em **Tables / Data**, selecione o catálogo `treinamento_databricks` → schema `financas` e marque
   as tabelas **`gold_*`** (e a Metric View **`fin_orcamento`**).
3. Escolha o **SQL Warehouse** (o 2X-Small do Free Edition) e dê o nome **FP&A**.
4. Em **Instructions**, cole o texto que o Genie Code preparou (responder em português, valores em
   reais, variância positiva em despesa = estouro, nunca inventar números).
5. Em **Sample questions**, adicione as 5 perguntas sugeridas.
6. **Salve**, abra o Space e teste 2 perguntas, conferindo com o gold.

✅ **Confira:** as respostas batem com a camada gold. **Anote o ID do Space** (aparece na URL,
`.../genie/rooms/<ID>`) — a Fase 5 (App) usa.

---

## Fase 4(b) — Multi-Agent Supervisor (Agent Bricks) (opcional)
Um gostinho de **orquestração de agentes**: um **Multi-Agent Supervisor** (Agent Bricks) que decide,
a cada pergunta, se chama o **Genie Space FP&A** (perguntas analíticas sobre o gold) ou uma
**ferramenta de cálculo** específica (a variância de uma conta). Com 2 agentes/ferramentas o
supervisor tem o que rotear — por isso faz mais sentido aqui do que com um agente só.

> ⚠️ **Free Edition:** o **Knowledge Assistant não existe**, mas o **Multi-Agent Supervisor está
> disponível**. Como no Genie Space, a criação é **manual na UI** (por código costuma falhar por
> permissão); o Genie Code só prepara a configuração. Depende do Genie Space da Fase 4(a).

**1. Crie uma ferramenta (UC Function) para o supervisor ter o que orquestrar:**
> "Crie uma **UC Function** em `treinamento_databricks.financas` chamada `fin_variancia_conta` que
> recebe o nome de uma conta contábil e devolve a variância dela (orçado, realizado, variância e
> variância %) a partir da tabela `gold_variacao_budget`. Execute com uma conta que exista nos dados
> (por exemplo, *Energia elétrica*) e me mostre o resultado."

**2. Peça a configuração do supervisor ao Genie Code:**
> "Quero um **Multi-Agent Supervisor** de FP&A. Não tente criá-lo por código — me entregue a
> configuração para eu montar na UI: (a) os agentes/ferramentas — o **Genie Space FP&A** (use o ID
> que anotei) e a UC Function `fin_variancia_conta`; (b) uma descrição de cada um (quando usar); (c)
> instruções de roteamento em português; e (d) 3 perguntas de exemplo, uma que vá para o Genie
> (análise ampla) e outra para a função (variância de uma conta específica)."

**3. Crie o Supervisor na UI** (passos em nível de objetivo — a UI do Agent Bricks pode variar):
1. Abra **Agents (Agent Bricks)** e crie um **Multi-Agent Supervisor**.
2. Adicione o **Genie Space FP&A** como agente e a **UC Function** `fin_variancia_conta` como ferramenta.
3. Cole as **descrições** e as **instruções de roteamento** que o Genie Code preparou.
4. **Salve** e abra o playground do supervisor (aguarde alguns minutos até ficar *online*).

✅ **Confira:** uma pergunta analítica (*"despesa por categoria no último mês"*) cai no **Genie**; uma
pergunta pontual (*"qual a variância da conta Energia elétrica?"*) aciona a **função** — e o
supervisor combina os dois.

---

## Fase 5 — App (Databricks App)
> "Para finalizar, crie um **Databricks App em Streamlit** chamado **Copiloto de FP&A**, seguindo as
> skills `dbx-app` (build/deploy) e `dbx-brand` (logo e paleta Databricks). Quero uma tela com os
> principais indicadores (receita, despesa, resultado e variância de despesa %), um gráfico de
> orçado vs. realizado por mês (com a projeção dos próximos meses) e uma lista das contas/centros com
> maiores estouros, lendo das tabelas gold. Inclua uma aba de chat conectada ao Genie Space **FP&A**
> (use o ID que anotei). O app precisa subir de primeira: deixe o Streamlit usar a porta padrão do
> ambiente (não fixe 8080), autentique com `Config()` do SDK e conecte ao warehouse só quando a tela
> precisar (não no import), de forma cacheada. Envolva cada consulta em `st.spinner` com `try/except`
> mostrando o erro real (`st.error`) e um timeout curto — o app nunca pode travar mudo em
> 'Carregando…'. Anexe o **SQL Warehouse como resource** do app e me diga o **nome do service
> principal** do app para eu liberar o acesso às tabelas gold. Em seguida, faça o deploy."

**Depois do deploy (2 passos de UI/SQL — é o que destrava o "Carregando…"):**
1. **Anexe o SQL Warehouse** ao app como *resource* (App → Edit → Resources → SQL Warehouse,
   serverless). Sem isso o app (que roda como service principal) não tem como consultar e trava.
2. **Libere os dados ao service principal do app** (nome em App → Authorization), no SQL Editor:
   ```sql
   GRANT USE CATALOG ON CATALOG treinamento_databricks TO `<app-sp>`;
   GRANT USE SCHEMA  ON SCHEMA  treinamento_databricks.financas TO `<app-sp>`;
   GRANT SELECT      ON SCHEMA  treinamento_databricks.financas TO `<app-sp>`;
   ```

> 💡 **"Carregando…" sem fim ou "Nenhum SQL Warehouse disponível"?** É o app sem o warehouse anexado
> (passo 1) ou sem GRANT no service principal (passo 2) — e **editar só o `app.yaml` não resolve**.
> Faça os 2 passos acima; se persistir, abra os **logs** do app para ver o erro real.

✅ **Confira:** o app abre com o logo, os indicadores corretos e o chat do Genie respondendo.

---

## Fase 6 — Conclusão
- [ ] Pipeline (Bronze, Silver, Gold) criada e conferida
- [ ] Metric View `fin_orcamento` consultável · projeção `ai_forecast` gravada · resumo `ai_query` gerado
- [ ] Dashboard funcionando · Genie respondendo · App no ar

No treino: mostre o CSV cru → rode a pipeline até o gold → projete a receita com o `ai_forecast` →
pergunte no Genie → abra o App.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small) e até 3 apps (encerram após 24h). Ensaie antes e
> reinicie o app pouco antes da apresentação.
