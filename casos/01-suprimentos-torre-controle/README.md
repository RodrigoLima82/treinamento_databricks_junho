# Caso 1 — Torre de Controle de Suprimentos (Runbook Genie Code)

Construa este caso **0→100 conversando com o Databricks Genie Code** (Free Edition).
Os blocos abaixo são **sugestões de conversa** — fale com o Genie como você falaria com um
colega. Vá **uma fase por vez** e confira o resultado antes de seguir.

- **Catálogo/schema:** `treinamento_databricks.suprimentos`
- **Volume:** `/Volumes/treinamento_databricks/suprimentos/raw`
- **Skills:** `dbx-foundation`, `dbx-genie-code-playbook`, `dbx-brand`, `suprimentos-torre-controle`
- **Dados:** `casos/01-suprimentos-torre-controle/data/*.csv` (ver `data/DICIONARIO.md`)

> 💬 Os textos são só um ponto de partida — adapte com suas palavras. Se algo der errado,
> cole o erro que apareceu e peça pro Genie corrigir antes de continuar.

---

## Fase 0 — Fundação
**Converse com o Genie Code:**
> "Vou montar um caso de uso de Suprimentos e quero que você siga as convenções que deixei
> nas skills `dbx-foundation` e `dbx-genie-code-playbook` deste repositório. Pra começar,
> me ajuda a preparar a base no Unity Catalog: cria um catálogo `treinamento_databricks`, um
> schema `suprimentos` dentro dele e um volume `raw` pra eu subir uns arquivos. Faz de um
> jeito que eu possa rodar de novo sem quebrar, e no fim me diz o que foi criado."

**Suba os 6 CSVs ao volume** pela interface: Catalog → `treinamento_databricks` → `suprimentos`
→ volume `raw` → **Upload to this volume** → selecione os arquivos de `…/data/*.csv`.
*(Se preferir, pode pedir ao Genie pra gerar os dados rodando o `data/gen_suprimentos_data.py` num notebook.)*

✅ **Confira:** os 6 arquivos aparecem dentro do volume `raw`.

---

## Fase 1 — Bronze (dados crus)
**Converse com o Genie Code:**
> "Subi 6 arquivos CSV no volume `raw` de suprimentos — são fornecedores, categorias,
> contratos, pedidos de compra, itens dos pedidos e recebimentos. Cria a camada bronze pra
> mim: uma tabela pra cada arquivo, só trazendo os dados como estão, sem transformar nada
> ainda. Quando terminar, me mostra quantas linhas ficou cada tabela pra eu conferir."

✅ **Confira:** o número de linhas bate com os arquivos.

---

## Fase 2 — Silver (limpo e enriquecido)
**Converse com o Genie Code:**
> "Agora vamos para a camada silver, mais limpa. Junta cada pedido com as informações do
> fornecedor (razão social, criticidade, se é fornecedor único, UF) e da categoria, e marca
> quais pedidos têm contrato. Nos itens, calcula o valor de cada item e quanto a gente
> economizou (ou gastou a mais) em relação ao preço de referência. E nos recebimentos,
> calcula o atraso em dias e marca o que chegou no prazo e o que veio no prazo **e** com
> qualidade (o famoso OTIF). Me mostra algumas linhas de cada uma pra eu validar."

✅ **Confira:** sem nulos nas chaves; os indicadores (atraso, saving, OTIF) fazem sentido.

---

## Fase 3 — Gold (pronto para análise)
**Converse com o Genie Code:**
> "Bora montar a camada gold, já pensando nas perguntas de negócio que eu quero responder.
> Cria tabelas que me deem: o gasto por categoria, por centro e por mês; o desempenho de
> cada fornecedor (lead time médio, % de entregas no prazo e OTIF); quanto a gente economizou
> por categoria e por mês; quanto do gasto está dentro e quanto está fora de contrato em cada
> centro; e quais fornecedores são fonte única e concentram muito gasto. Me mostra uma
> amostrinha de cada."

✅ **Confira:** OTIF, % de saving e % fora de contrato parecem coerentes.

> 💡 **Quer mostrar o Lakeflow?** Depois peça: *"empacota essas transformações de silver e gold
> como uma Lakeflow Declarative Pipeline serverless"* (lembre: 1 pipeline ativo por tipo no Free Edition).

---

## Fase 4 — Um toque de IA (opcional)
**Converse com o Genie Code:**
> "Pra dar um gostinho de IA: cria uma visão que pega os números do mês mais recente — gasto
> total, % de economia, OTIF e os principais atrasos — e escreve um pequeno resumo executivo
> em português, usando uma função de IA do Databricks (tipo `ai_query`) com um modelo que
> esteja disponível aqui no workspace. Pode ser só um parágrafo."

✅ **Confira:** o resumo cita números reais das tabelas gold.

---

## Fase 5 — Dashboard (AI/BI)
**Converse com o Genie Code:**
> "Monta um dashboard chamado **Torre de Controle de Suprimentos** em cima dessas tabelas gold.
> No topo quero uns números grandes: gasto total, % de economia, OTIF e % de gasto fora de
> contrato. Abaixo: gasto por categoria e por centro, a evolução do gasto mês a mês, um top 10
> de fornecedores e uma tabelinha de alerta com os fornecedores únicos e os pedidos atrasados
> que ainda estão em aberto. Antes de cada gráfico, roda a query no SQL pra garantir que funciona."

✅ **Confira:** todos os painéis aparecem sem erro.

---

## Fase 6 — Genie Space (pergunte em português)
**Converse com o Genie Code:**
> "Cria um Genie Space chamado **Suprimentos** em cima das tabelas gold, pra eu poder perguntar
> em linguagem natural. Deixa ele respondendo em português, com valores em reais, e orienta pra
> nunca inventar número. Já deixa algumas perguntas de exemplo, tipo *'qual o gasto com peças de
> britador na Mina Norte nos últimos 6 meses?'* e *'quais fornecedores estão com OTIF abaixo de
> 80%?'*, e testa pra ver se as respostas batem com os dados."

✅ **Confira:** as perguntas retornam números coerentes com o gold. Anote o ID do Genie Space.

---

## Fase 7 — App (Databricks App)
**Converse com o Genie Code:**
> "Pra fechar, cria um app web (Databricks App) chamado **Torre de Controle de Suprimentos**,
> usando o visual da skill `dbx-brand` (com o logo do Databricks). Quero uma tela inicial com
> os principais indicadores (gasto, economia, OTIF e % fora de contrato), um gráfico de gasto
> por categoria e uma lista de 'pedidos em risco' (atrasados ou ainda em aberto), puxando os
> dados do warehouse. E uma aba de chat ligada no Genie Space que a gente criou, pra perguntar
> em linguagem natural. Depois faz o deploy aqui no próprio workspace."

✅ **Confira:** o app abre com o logo, os indicadores certos e o chat do Genie respondendo.

---

## Fase 8 — Pronto! Como apresentar
- [ ] Bronze, Silver e Gold criados e conferidos
- [ ] Dashboard funcionando · Genie respondendo · App no ar
- **No treino:** mostre o CSV cru → vire a tabela gold → faça uma pergunta no Genie → abra o App.
  É o "0→100" do Lakehouse em poucos minutos.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small), até 3 apps (param sozinhos após 24h) e cota
> diária de uso. Ensaie antes e reinicie o app pouco antes da apresentação.
