# Caso 4 — Auditoria Contínua & Compliance (Runbook Genie Code)

## O que é
Uma central de **auditoria contínua e compliance** para uma empresa fictícia (*Companhia Andes*):
toda transação financeira é testada automaticamente contra um catálogo de regras (alçada, contrato,
segregação de funções, cadastro, pagamentos, conduta), gerando **achados** priorizados — e um
**assistente** que, além de responder os números, **explica a política** por trás de cada achado
consultando os documentos internos (RAG).

## A dor
As regras de compliance vivem em **documentos** (políticas, normas, código de conduta), enquanto as
transações vivem em **sistemas financeiros** — e ninguém cruza os dois de forma contínua. A auditoria
é amostral e retroativa: descobre o problema meses depois. Perguntas simples — *"este pagamento
respeitou a alçada?"*, *"o que a política diz sobre fornecedor sem contrato?"* — exigem garimpar
planilhas e PDFs, e a resposta depende de quem você pergunta.

## Como o Databricks resolve
Construímos a solução **0→100 numa única plataforma governada**, unindo o **dado estruturado** e o
**documento**: Lakehouse / medalhão (Bronze → Silver → Gold) recalcula as regras a cada transação →
**AI/BI Dashboard** e **Genie** dão a visão analítica → **`ai_parse_document` + Vector Search + RAG**
trazem o texto das políticas → um **Multi-Agent Supervisor** decide, a cada pergunta, se responde com
**dados** (Genie) ou com **política** (RAG) → e um **Databricks App** entrega tudo num chat único.
Do CSV/política crus à decisão, em minutos, sobre o Unity Catalog.

---

## Como construir (Genie Code)

Construa este caso **conversando com o Databricks Genie Code** (Free Edition). Vá **uma fase por
vez**: cole o texto em destaque no Genie, espere terminar e confira o resultado antes de seguir.

> 💬 Os textos são um ponto de partida — adapte com suas palavras. Se algo der errado, cole a
> mensagem de erro e peça ao Genie para corrigir antes de continuar.

> ⚠️ **Limites do Free Edition que pesam neste caso** (ver `dbx-foundation`): Vector Search com
> **1 endpoint / 1 unit**, só **Delta-Sync + embeddings gerenciados**; **Knowledge Assistant não
> existe** (o RAG é um **agente custom**); **Genie e Multi-Agent Supervisor** são criados na **UI**.

---

## Fase 0 — Fundação
> "Vou montar um caso de uso de Auditoria & Compliance e gostaria que você seguisse as convenções
> das skills `dbx-foundation` e `dbx-genie-code-playbook` deste repositório. Para começar, prepare
> a base no Unity Catalog: crie um catálogo `treinamento_databricks`, um schema `auditoria` e um
> volume `raw`. Faça de forma que eu possa executar novamente sem erros e, ao final, confirme o que
> foi criado usando `SHOW SCHEMAS IN treinamento_databricks` e `SHOW VOLUMES IN
> treinamento_databricks.auditoria` — não use o `information_schema` para essa conferência."

**Carregue os dados** (5 CSVs + 12 documentos `.md`, já no Git folder do workshop):
> "Este repositório do workshop já está clonado como Git folder no meu workspace. Na pasta
> `casos/04-auditoria-compliance/data` há **5 arquivos CSV** (fornecedores, aprovadores,
> regras_compliance, transacoes, achados_auditoria) e, em `data/documentos`, **12 documentos `.md`**
> (políticas e normas). Copie os 5 CSVs para a raiz do volume `raw` da auditoria e copie os 12
> documentos `.md` para uma subpasta `documentos/` dentro do mesmo volume. Ao terminar, liste o que
> ficou em `/Volumes/treinamento_databricks/auditoria/raw/` e em `.../raw/documentos/` para eu
> conferir 5 CSVs e 12 documentos."

✅ **Confira:** 5 CSVs na raiz do volume e 12 `.md` em `raw/documentos/`.

---

## Fase 1 — Pipeline (Bronze → Silver → Gold) dos dados estruturados
Todo o medalhão **estruturado** já está versionado como uma **Lakeflow Declarative Pipeline (SDP)**:
`casos/04-auditoria-compliance/pipeline/auditoria_pipeline.sql`. Você só cria a pipeline apontando
para esse arquivo e roda. (Os documentos vêm depois, nas Fases 2–4.)

> "Neste repositório, que já está clonado como Git folder no meu workspace, há um arquivo SQL pronto
> que define toda a transformação estruturada de Auditoria — as camadas bronze, silver e gold das
> transações, regras e achados — em `casos/04-auditoria-compliance/pipeline/auditoria_pipeline.sql`.
> Crie uma Lakeflow Declarative Pipeline serverless usando esse arquivo como código-fonte, tendo como
> destino o catálogo `treinamento_databricks` e o schema `auditoria`. Em seguida, rode a pipeline com
> **Full refresh** e, ao terminar, me mostre o diagrama (DAG) e a contagem de linhas das tabelas gold
> para eu conferir."

✅ **Confira:** a pipeline cria as tabelas `bronze_*`, `silver_*` e as views `gold_*`, o DAG roda
sem erro e as contagens fazem sentido (ex.: ~606 transações, ~484 achados, achados de severidade
Alta dominando `gold_achados`).

> 💡 Repare que o `silver_transacoes` **recalcula** as regras como colunas-flag (`acima_alcada`,
> `sem_contrato_relevante`, `sod_violado`…). É a essência da **auditoria contínua**: a não
> conformidade é re-derivada dos dados, não apenas lida do CSV de achados.

---

## Fase 2 — Parsear e "chunkar" os documentos (`ai_parse_document`)
Agora trazemos os **documentos**. O objetivo é transformar cada `.md` em pedaços de texto (*chunks*)
numa tabela Delta — a base do índice de busca da próxima fase.

> "Quero preparar os documentos de compliance que estão em
> `/Volumes/treinamento_databricks/auditoria/raw/documentos/` para um pipeline de RAG. Esses
> documentos do workshop são arquivos `.md` (texto), então leia-os com `read_files` no formato texto,
> um registro por arquivo, preservando o nome do arquivo. Em seguida, **quebre cada documento em
> seções** (use os títulos de seção `##` do markdown como divisor) e grave o resultado numa tabela
> Delta `treinamento_databricks.auditoria.silver_documento_chunks` com as colunas `chunk_id` (chave),
> `doc_nome`, `secao_idx` e `texto`. **Habilite o Change Data Feed** nessa tabela (é pré-requisito do
> índice Delta-Sync do Vector Search). Ao final, me mostre quantos chunks saíram por documento."

Se preferir, aqui está um SQL de partida (o Genie Code pode ajustar):
```sql
CREATE TABLE IF NOT EXISTS treinamento_databricks.auditoria.silver_documento_chunks (
  chunk_id  STRING,
  doc_nome  STRING,
  secao_idx INT,
  texto     STRING
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

INSERT OVERWRITE treinamento_databricks.auditoria.silver_documento_chunks
WITH docs AS (
  SELECT regexp_extract(_metadata.file_path, '([^/]+)$', 1) AS doc_nome,
         value AS texto_completo
  FROM read_files('/Volumes/treinamento_databricks/auditoria/raw/documentos/',
                  format => 'text', wholeText => true)
),
secoes AS (
  SELECT doc_nome, posexplode(split(texto_completo, '\n## ')) AS (secao_idx, secao)
  FROM docs
)
SELECT concat(doc_nome, '#', secao_idx) AS chunk_id,
       doc_nome,
       secao_idx,
       CASE WHEN secao_idx = 0 THEN secao ELSE concat('## ', secao) END AS texto
FROM secoes
WHERE length(trim(secao)) > 0;
```

> 📄 **E quando o documento for PDF/DOCX (o caso real)?** Aí entra o **`ai_parse_document`**, que
> extrai o texto de binários. O padrão é ler com `binaryFile` e parsear:
> ```sql
> SELECT path,
>        ai_parse_document(content):document.elements AS elementos
> FROM read_files('/Volumes/.../raw/documentos/', format => 'binaryFile');
> ```
> No workshop os documentos já são texto (`.md`), então a leitura direta acima é suficiente — mas o
> fluxo (parsear → chunkar → indexar) é exatamente o mesmo. Para mais padrões, veja a skill
> `databricks-ai-functions`.

✅ **Confira:** `SELECT count(*) FROM treinamento_databricks.auditoria.silver_documento_chunks;`
retorna algumas dezenas de chunks (vários por documento) e nenhum texto vazio.

---

## Fase 3 — Vector Search (índice Delta-Sync com embeddings gerenciados)
Indexamos os chunks para busca semântica. **No Free Edition é 1 endpoint, 1 unit, só Delta-Sync com
embeddings gerenciados** — então criamos **um** endpoint e **um** índice.

> "Vamos criar a busca vetorial sobre `treinamento_databricks.auditoria.silver_documento_chunks`,
> seguindo a skill `databricks-vector-search` e respeitando o Free Edition (1 endpoint, 1 unit,
> Delta-Sync com embeddings gerenciados). Crie um **Vector Search endpoint** chamado
> `aud_vs_endpoint` e, sobre ele, um **índice Delta-Sync gerenciado** chamado
> `treinamento_databricks.auditoria.aud_politicas_idx`, com chave primária `chunk_id`, coluna de
> texto `texto`, embeddings `databricks-gte-large-en` e `pipeline_type = TRIGGERED`. Depois dispare a
> sincronização e, quando o índice ficar *online*, faça uma consulta de teste como *'qual o limite de
> alçada de um gerente?'* e me mostre os trechos retornados."

Esqueleto de referência (o Genie Code adapta; veja a skill oficial):
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

w.vector_search_endpoints.create_endpoint(name="aud_vs_endpoint", endpoint_type="STANDARD")

w.vector_search_indexes.create_index(
    name="treinamento_databricks.auditoria.aud_politicas_idx",
    endpoint_name="aud_vs_endpoint",
    primary_key="chunk_id",
    index_type="DELTA_SYNC",
    delta_sync_index_spec={
        "source_table": "treinamento_databricks.auditoria.silver_documento_chunks",
        "embedding_source_columns": [
            {"name": "texto", "embedding_model_endpoint_name": "databricks-gte-large-en"}
        ],
        "pipeline_type": "TRIGGERED",
    },
)
```

✅ **Confira:** o índice fica *online* e uma consulta semântica (ex.: *"fornecedor sem contrato"*)
retorna os trechos da `politica_compras.md` / `norma_due_diligence_fornecedores.md`.

> ⚠️ **Limite:** não crie um segundo endpoint nem outro índice — o Free Edition tem **1 unit**.
> Sincronize com *sync* (o índice é `TRIGGERED`); não use Direct Access.

---

## Fase 4 — Agente RAG de políticas (custom)
Com o índice pronto, montamos o **agente que responde sobre políticas** citando a fonte. Como o
**Knowledge Assistant não existe no Free Edition**, fazemos um **agente RAG custom**: recupera os
chunks do índice e gera a resposta com um LLM `databricks-*`.

> "Crie um agente RAG simples de políticas de compliance. Ele deve: (1) receber uma pergunta em
> português; (2) buscar os trechos mais relevantes no índice
> `treinamento_databricks.auditoria.aud_politicas_idx` (Vector Search); (3) montar um prompt com
> esses trechos e responder com um modelo `databricks-*` disponível no workspace, **sempre citando o
> documento de origem** (campo `doc_nome`) e **sem inventar regras** — se não houver base nos trechos,
> dizer que não encontrou. Teste com *'um gerente pode aprovar um pagamento de R$ 300 mil?'* e
> *'quando um fornecedor precisa de contrato?'* e me mostre a resposta com as citações."

Esqueleto de referência (recuperação + geração):
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

def rag_politicas(pergunta: str, k: int = 4) -> str:
    res = w.vector_search_indexes.query_index(
        index_name="treinamento_databricks.auditoria.aud_politicas_idx",
        columns=["doc_nome", "texto"],
        query_text=pergunta, num_results=k,
    )
    trechos = "\n\n".join(f"[{r[0]}] {r[1]}" for r in res.result.data_array)
    prompt = (f"Você é um assistente de compliance. Responda em PT-BR usando SOMENTE os trechos "
              f"abaixo e cite o documento de origem entre colchetes. Se não houver base, diga que "
              f"não encontrou.\n\nTRECHOS:\n{trechos}\n\nPERGUNTA: {pergunta}")
    # use um endpoint de chat databricks-* disponível no Playground:
    out = w.serving_endpoints.query(
        name="databricks-claude-3-7-sonnet",
        messages=[{"role": "user", "content": prompt}],
    )
    return out.choices[0].message.content
```

> 💡 **Para o Multi-Agent Supervisor (Fase 6b)**, o agente precisa estar **servido como endpoint**
> (Model Serving + Agent Framework / MLflow `ResponsesAgent`). No Free Edition o serving é
> **pay-per-token** sobre os FMs; siga a skill `databricks-model-serving`. Se servir o agente
> custom não for viável no seu workspace, tudo bem: o **app** (Fase 7) chama a função `rag_politicas`
> diretamente, e o supervisor pode rotear **Genie + uma UC Function** (ver Fase 6b).

✅ **Confira:** a resposta sobre alçada cita `norma_alcadas_aprovacao.md` e bate com a tabela de
alçadas; a resposta sobre contrato cita `politica_compras.md` (limite de R$ 50 mil).

---

## Fase 5 — Dashboard (AI/BI)
> "Crie um dashboard chamado **Auditoria Contínua & Compliance** sobre as tabelas gold. No topo,
> quero os principais indicadores: total de achados, achados de severidade **Alta em aberto**,
> **valor em risco** e **% de conformidade** do mês mais recente. Abaixo: achados por regra e por
> severidade, a evolução mensal de achados (ou da % de conformidade), uma tabela *watchlist* com os
> pagamentos **acima da alçada** (`gold_violacoes_alcada`) e um ranking de **fornecedores sem
> contrato** por valor (`gold_gasto_sem_contrato`). Antes de montar cada gráfico, execute a consulta
> no SQL para garantir que funciona."

> 💡 **Visual:** siga a skill `dbx-dashboard-design` (KPIs no topo, regra 60-30-10, paleta da marca,
> contraste em claro/escuro). Para severidade, use uma escala sóbria (evite vermelho/verde adjacentes).

✅ **Confira:** todos os painéis aparecem sem erro e os números batem com o gold.

---

## Fase 6(a) — Genie Space (perguntas em português sobre os dados)
> ⚠️ **Limitação do Free Edition:** o Genie Space **não pode ser criado por código** (API, SDK ou
> `createAsset`) — falha por permissão. Esta é uma etapa **manual na UI**; o Genie Code ajuda apenas
> preparando a configuração.

**1. Peça a configuração ao Genie Code:**
> "Quero um Genie Space chamado **Auditoria & Compliance** sobre as tabelas gold, para perguntar em
> linguagem natural sobre os dados. Não tente criá-lo por código — me entregue tudo pronto para eu
> criar pela interface: a lista das tabelas gold que devo incluir, um texto de instruções em
> português (responder em reais, mês no formato AAAA-MM, severidades Alta/Média/Baixa, **nunca
> inventar números nem regras**) e cinco perguntas de exemplo, como *'quantos achados de severidade
> alta estão em aberto?'* e *'qual a % de conformidade por área no mês mais recente?'*."

**2. Crie o Space na UI** (passo a passo):
1. No menu lateral, abra **Genie** e clique em **New** (novo Space).
2. Em **Tables / Data**, selecione `treinamento_databricks` → schema `auditoria` e marque as tabelas **`gold_*`**.
3. Escolha o **SQL Warehouse** (o 2X-Small do Free Edition) e dê o nome **Auditoria & Compliance**.
4. Em **Instructions**, cole o texto que o Genie Code preparou (PT-BR, BRL, nunca inventar números/regras).
5. Em **Sample questions**, adicione as 5 perguntas sugeridas.
6. **Salve**, abra o Space e teste 2 perguntas, conferindo com o gold.

✅ **Confira:** as respostas batem com a camada gold. **Anote o ID do Space** (na URL,
`.../genie/rooms/<ID>`) — as Fases 6(b) e 7 usam.

---

## Fase 6(b) — Multi-Agent Supervisor (Agent Bricks)
Agora a peça que dá nome ao caso: um **Multi-Agent Supervisor** que decide, a cada pergunta, se
chama o **agente RAG de políticas** (perguntas sobre regras/normas) ou o **Genie Space Auditoria**
(perguntas analíticas sobre os dados). É a combinação **documento + dado** num assistente só.

> ⚠️ **Free Edition:** o **Knowledge Assistant não existe**, mas o **Multi-Agent Supervisor está
> disponível**. Como no Genie Space, a criação é **manual na UI**; o Genie Code só prepara a
> configuração. Depende do Genie Space (6a) e, idealmente, do agente RAG servido (Fase 4).

**1. (Opcional) Crie uma UC Function como ferramenta pontual de fallback:**
> "Crie uma **UC Function** em `treinamento_databricks.auditoria` chamada `aud_achados_fornecedor`
> que recebe a razão social de um fornecedor e devolve, a partir do gold, quantos achados ele tem e o
> valor em risco. Execute com um fornecedor que exista nos dados e me mostre o resultado."

**2. Peça a configuração do supervisor ao Genie Code:**
> "Quero um **Multi-Agent Supervisor** de Auditoria. Não tente criá-lo por código — me entregue a
> configuração para eu montar na UI: (a) os agentes/ferramentas — o **agente RAG de políticas** (para
> perguntas sobre regras/normas) e o **Genie Space Auditoria** (use o ID que anotei, para perguntas
> analíticas); (b) uma descrição de cada um (quando usar); (c) instruções de roteamento em português
> (pergunta sobre *política/regra/limite* → RAG; pergunta sobre *número/quantidade/valor/período* →
> Genie); e (d) 3 perguntas de exemplo, uma que vá para o RAG e outra para o Genie."

**3. Crie o Supervisor na UI** (passos em nível de objetivo — a UI do Agent Bricks pode variar):
1. Abra **Agents (Agent Bricks)** e crie um **Multi-Agent Supervisor**.
2. Adicione o **Genie Space Auditoria** como agente e o **agente RAG de políticas** (endpoint servido)
   — ou, se não tiver servido o RAG, a **UC Function** `aud_achados_fornecedor` como ferramenta.
3. Cole as **descrições** e as **instruções de roteamento** que o Genie Code preparou.
4. **Salve** e abra o playground do supervisor (aguarde alguns minutos até ficar *online*).

✅ **Confira:** *"qual o limite de alçada de um gerente?"* cai no **RAG** (cita a norma); *"quantos
achados de alçada no último mês?"* cai no **Genie** — e o supervisor combina os dois.

---

## Fase 7 — App (Databricks App)
> "Para finalizar, crie um **Databricks App em Streamlit** chamado **Auditoria Contínua &
> Compliance**, seguindo as skills `dbx-app` (build/deploy) e `dbx-brand` (logo e paleta Databricks).
> Quero uma tela com os principais indicadores (achados de severidade alta em aberto, % de
> conformidade, valor em risco), um gráfico de achados por severidade/regra e uma tabela de
> *watchlist* (pagamentos acima da alçada ou fornecedores sem contrato), lendo das tabelas gold.
> Inclua uma aba de chat conectada ao **Multi-Agent Supervisor** (ou, se eu não tiver criado, ao
> **Genie Space Auditoria** pelo ID que anotei). Faça o app subir de primeira no Free Edition e publique."

> 🔧 A parte técnica do app — porta, autenticação, conexão ao SQL Warehouse, anexar o warehouse como *resource*, liberar acesso (GRANT) ao service principal e o troubleshooting de "Carregando…" — está toda na skill **`dbx-app`**; o Genie Code segue de lá e te pede só as confirmações de UI. (Limite Free Edition: até 3 apps, auto-stop em 24h.)

✅ **Confira:** o app abre com o logo, os indicadores corretos e o chat respondendo tanto sobre
**dados** (achados, valor em risco) quanto sobre **políticas** (alçada, contrato).

---

## Fase 8 — Conclusão
- [ ] Pipeline estruturada (Bronze, Silver, Gold) criada e conferida
- [ ] Documentos parseados/chunkados · Vector Search sincronizado · agente RAG citando a política
- [ ] Dashboard funcionando · Genie respondendo · Multi-Agent Supervisor roteando · App no ar

No treino: mostre uma transação não conforme → rode a pipeline até o gold → pergunte ao supervisor
*"este pagamento respeitou a alçada e o que diz a política?"* (dado **+** política) → abra o App.

> ⚠️ **Free Edition:** 1 SQL warehouse (2X-Small), Vector Search 1 endpoint/1 unit, até 3 apps
> (encerram após 24h). Ensaie antes e reinicie o app pouco antes da apresentação — e cuidado com a
> cota diária ao reindexar/embedar.
