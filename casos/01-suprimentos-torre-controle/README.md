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

## Fase 2 — Um componente de IA (opcional)
> "Para incluir um componente de IA: crie uma visão que utilize os números do mês mais recente —
> gasto total, percentual de economia, OTIF e os principais atrasos — e gere um breve resumo
> executivo em português, usando uma função de IA do Databricks (por exemplo, `ai_query`) com um
> modelo disponível no workspace. Pode ser um único parágrafo."

✅ **Confira:** o resumo cita números reais das tabelas gold.

---

## Fase 3 — Dashboard (AI/BI)
> "Crie um dashboard chamado **Torre de Controle de Suprimentos** sobre as tabelas gold. No topo,
> quero os principais indicadores: gasto total, percentual de economia, OTIF e percentual de gasto
> fora de contrato. Abaixo: gasto por categoria e por centro, a evolução mensal do gasto, um ranking
> dos dez maiores fornecedores e uma tabela de alerta com os fornecedores únicos e os pedidos
> atrasados ainda em aberto. Antes de montar cada gráfico, execute a consulta no SQL para garantir
> que funciona."

✅ **Confira:** todos os painéis aparecem sem erro.

---

## Fase 4 — Genie Space (perguntas em português)
> "Crie um Genie Space chamado **Suprimentos** sobre as tabelas gold, para que eu possa perguntar
> em linguagem natural. Configure-o para responder em português, com valores em reais, e oriente-o
> a nunca inventar números. Inclua algumas perguntas de exemplo, como *'qual o gasto com peças de
> britador na Mina Norte nos últimos seis meses?'* e *'quais fornecedores estão com OTIF abaixo de
> 80%?'*, e teste se as respostas conferem com os dados."

✅ **Confira:** as respostas conferem com a camada gold. Anote o ID do Genie Space.

---

## Fase 5 — App (Databricks App)
> "Para finalizar, crie um aplicativo web (Databricks App) chamado **Torre de Controle de
> Suprimentos**, usando o visual da skill `dbx-brand` (com o logo do Databricks). Quero uma tela
> inicial com os principais indicadores (gasto, economia, OTIF e percentual fora de contrato), um
> gráfico de gasto por categoria e uma lista de 'pedidos em risco' (atrasados ou em aberto),
> consultando os dados do warehouse. Inclua também uma aba de chat conectada ao Genie Space criado,
> para perguntas em linguagem natural. Em seguida, faça o deploy no próprio workspace."

✅ **Confira:** o app abre com o logo, os indicadores corretos e o chat do Genie respondendo.

---

## Fase 6 — Conclusão
- [ ] Pipeline (Bronze, Silver, Gold) criada e conferida
- [ ] Dashboard funcionando · Genie respondendo · App no ar

No treino: mostre o CSV cru → rode a pipeline até o gold → pergunte no Genie → abra o App.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small) e até 3 apps (encerram após 24h). Ensaie antes e
> reinicie o app pouco antes da apresentação.
