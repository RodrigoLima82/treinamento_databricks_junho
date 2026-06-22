# Caso 1 — Torre de Controle de Suprimentos (Runbook Genie Code)

## O que é
Uma **torre de controle de Suprimentos** para uma mineradora (fictícia): um painel único que reúne
compras MRO, contratos, entregas e fornecedores para responder, em um só lugar, *"quanto gastamos,
com quem, no prazo e dentro de contrato?"*.

## A dor
Hoje esses dados vivem espalhados (ERP de compras, planilhas de contratos, controles de recebimento)
e a área não enxerga o quadro completo:
- **Entregas atrasadas** sem visão consolidada de lead time e OTIF por fornecedor.
- **Gasto fora de contrato** difícil de medir — perde-se poder de negociação e compliance.
- **Savings invisíveis** — não se sabe quanto se economiza (ou se perde) frente ao preço de referência.
- **Risco de fornecedor único** concentrando itens críticos (ex.: peças de britador) sem nenhum alarme.
- Perguntas simples (*"gasto com peças de britador na Mina Norte nos últimos 6 meses?"*) exigem
  extração manual e demoram dias.

## Como o Databricks resolve
Construímos a solução **0→100 numa única plataforma governada**, do dado cru à entrega:
- **Lakehouse / medalhão (Bronze → Silver → Gold):** ingere os arquivos crus, trata e enriquece, e
  monta marts por pergunta de negócio (gasto, OTIF, saving, aderência a contrato, fornecedor único).
- **AI Functions (`ai_query`):** gera um resumo executivo do mês em linguagem natural sobre os números reais.
- **AI/BI Dashboard:** KPIs e gráficos de gasto, OTIF, savings e gasto fora de contrato.
- **Genie Space:** perguntas em português (*"quais fornecedores com OTIF abaixo de 80%?"*) com resposta confiável.
- **Databricks App:** entrega tudo numa interface única (KPIs + "pedidos em risco" + chat do Genie).
- **Unity Catalog:** governança, catálogo e volumes do início ao fim.

Resultado: do CSV cru à decisão, em minutos — o "0→100" do Lakehouse.

---

## Como construir (Genie Code)

Construa este caso **0→100 conversando com o Databricks Genie Code** (Free Edition).
Os blocos abaixo são **sugestões de conversa** — fale com o Genie de forma natural e direta,
em português claro. Vá **uma fase por vez** e confira o resultado antes de seguir.

- **Catálogo/schema:** `treinamento_databricks.suprimentos`
- **Volume:** `/Volumes/treinamento_databricks/suprimentos/raw`
- **Pipeline (medalhão):** `casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql` (ver `pipeline/README.md`)
- **Skills:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-brand`, `suprimentos-torre-controle`
- **Dados:** `casos/01-suprimentos-torre-controle/data/*.csv` (ver `data/DICIONARIO.md`)

> 💬 Os textos são apenas um ponto de partida — adapte com suas palavras. Se algo der errado,
> cole a mensagem de erro e peça ao Genie para corrigir antes de continuar.

---

## Fase 0 — Fundação
**Converse com o Genie Code:**
> "Vou montar um caso de uso de Suprimentos e gostaria que você seguisse as convenções das
> skills `dbx-foundation` e `dbx-genie-code-playbook` deste repositório. Para começar, prepare
> a base no Unity Catalog: crie um catálogo `treinamento_databricks`, um schema `suprimentos`
> e um volume `raw` para eu enviar os arquivos. Faça de forma que eu possa executar novamente
> sem erros e, ao final, confirme o que foi criado usando `SHOW SCHEMAS IN treinamento_databricks`
> e `SHOW VOLUMES IN treinamento_databricks.suprimentos` — não use o `information_schema` para essa
> conferência."

**Carregue os dados automaticamente** (sem upload manual). Como este repositório já está clonado
como Git folder no workspace, os 6 CSVs já estão lá — peça ao Genie Code para copiá-los para o volume:
> "Este repositório do workshop já está clonado como Git folder no meu workspace, e os 6 arquivos
> CSV estão na pasta `casos/01-suprimentos-torre-controle/data`. Copie esses 6 arquivos para dentro
> do volume `raw` de suprimentos que acabamos de criar. Ao terminar, liste os arquivos que ficaram
> no volume para eu conferir os 6."

*Alternativas:* enviar pela UI (Catalog → `treinamento_databricks` → `suprimentos` → `raw` →
**Upload to this volume**) ou pedir ao Genie para gerar os dados executando `data/gen_suprimentos_data.py` em um notebook.

✅ **Verifique:** os 6 arquivos aparecem dentro do volume `raw`.

> ⚠️ **Se a verificação falhar com erro de coluna** (ex.: *"column `catalog_name` cannot be resolved"*,
> sugerindo `volume_name`): é só a consulta de conferência usando o nome de coluna errado em
> `information_schema.volumes` (a coluna certa é `volume_catalog`). O catálogo, o schema e o volume
> **foram criados normalmente**. Confirme com `SHOW SCHEMAS IN treinamento_databricks`,
> `SHOW VOLUMES IN treinamento_databricks.suprimentos` e
> `LIST '/Volumes/treinamento_databricks/suprimentos/raw'`, que não dependem dos nomes de coluna do
> `information_schema`.

---

## Fase 1 — Pipeline (Bronze → Silver → Gold)
Em vez de montar as tabelas uma a uma conversando, todo o medalhão já está versionado neste
repositório como uma **Lakeflow Declarative Pipeline (SDP)**: o arquivo
`casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql`. Você só cria **uma**
pipeline serverless apontando para ele e roda.

**Converse com o Genie Code:**
> "Neste repositório, que já está clonado como Git folder no meu workspace, há um arquivo SQL pronto
> que define toda a transformação de Suprimentos — as camadas bronze, silver e gold — em
> `casos/01-suprimentos-torre-controle/pipeline/suprimentos_pipeline.sql`. Crie uma Lakeflow
> Declarative Pipeline serverless usando esse arquivo como código-fonte, tendo como destino o
> catálogo `treinamento_databricks` e o schema `suprimentos`. Em seguida, rode a pipeline com
> **Full refresh** e, ao terminar, me mostre o diagrama (DAG) e a contagem de linhas das tabelas
> gold para eu conferir."

✅ **Verifique:** a pipeline cria as tabelas `bronze_*`, `silver_*` e as views `gold_*`; o DAG
roda sem erro e as contagens fazem sentido (ex.: ~800 pedidos, ~2.400 itens).

---

## Fase 2 — Um componente de IA (opcional)
**Converse com o Genie Code:**
> "Para incluir um componente de IA: crie uma visão que utilize os números do mês mais recente —
> gasto total, percentual de economia, OTIF e os principais atrasos — e gere um breve resumo
> executivo em português, usando uma função de IA do Databricks (por exemplo, `ai_query`) com um
> modelo disponível no workspace. Pode ser um único parágrafo."

✅ **Verifique:** o resumo cita números reais das tabelas gold.

---

## Fase 3 — Dashboard (AI/BI)
**Converse com o Genie Code:**
> "Crie um dashboard chamado **Torre de Controle de Suprimentos** sobre as tabelas gold. No topo,
> quero os principais indicadores: gasto total, percentual de economia, OTIF e percentual de gasto
> fora de contrato. Abaixo: gasto por categoria e por centro, a evolução mensal do gasto, um ranking
> dos dez maiores fornecedores e uma tabela de alerta com os fornecedores únicos e os pedidos
> atrasados ainda em aberto. Antes de montar cada gráfico, execute a consulta no SQL para garantir
> que funciona."

✅ **Verifique:** todos os painéis aparecem sem erro.

---

## Fase 4 — Genie Space (perguntas em português)
**Converse com o Genie Code:**
> "Crie um Genie Space chamado **Suprimentos** sobre as tabelas gold, para que eu possa perguntar
> em linguagem natural. Configure-o para responder em português, com valores em reais, e oriente-o
> a nunca inventar números. Inclua algumas perguntas de exemplo, como *'qual o gasto com peças de
> britador na Mina Norte nos últimos seis meses?'* e *'quais fornecedores estão com OTIF abaixo de
> 80%?'*, e teste se as respostas conferem com os dados."

✅ **Verifique:** as perguntas retornam números coerentes com a camada gold. Anote o ID do Genie Space.

---

## Fase 5 — App (Databricks App)
**Converse com o Genie Code:**
> "Para finalizar, crie um aplicativo web (Databricks App) chamado **Torre de Controle de
> Suprimentos**, usando o visual da skill `dbx-brand` (com o logo do Databricks). Quero uma tela
> inicial com os principais indicadores (gasto, economia, OTIF e percentual fora de contrato), um
> gráfico de gasto por categoria e uma lista de 'pedidos em risco' (atrasados ou em aberto),
> consultando os dados do warehouse. Inclua também uma aba de chat conectada ao Genie Space criado,
> para perguntas em linguagem natural. Em seguida, faça o deploy no próprio workspace."

✅ **Verifique:** o app abre com o logo, os indicadores corretos e o chat do Genie respondendo.

---

## Fase 6 — Conclusão e como apresentar
- [ ] Pipeline (Bronze, Silver e Gold) criada e conferida
- [ ] Dashboard funcionando · Genie respondendo · App no ar
- **No treino:** mostre o CSV cru → rode a pipeline até a tabela gold → faça uma pergunta no Genie → abra o App.
  É o "0→100" do Lakehouse em poucos minutos.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small), até 3 apps (encerram sozinhos após 24h) e cota
> diária de uso. Ensaie com antecedência e reinicie o app pouco antes da apresentação.
