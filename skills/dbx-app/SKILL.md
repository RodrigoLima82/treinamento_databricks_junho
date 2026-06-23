---
name: dbx-app
description: >-
  Build e deploy do Databricks App em Streamlit dos casos do workshop — scaffold,
  autenticação, conexão ao SQL Warehouse e chat do Genie. Use ao criar/subir o app
  de qualquer caso, para um deploy que sobe de primeira no Free Edition. Para o
  visual (logo, paleta), combine com `dbx-brand`.
---

# dbx-app — Databricks App em Streamlit (build + deploy)

Os apps do workshop são **Databricks Apps em Streamlit** — pré-instalado no runtime e com a porta
auto-configurada, é o caminho mais robusto no Free Edition. Esta skill cobre **estrutura, auth,
conexão a dados, chat e deploy**. Para o visual da marca (logo, paleta, tipografia), siga `dbx-brand`;
para o layout dos painéis, `dbx-dashboard-design`.

## 1. Estrutura mínima
```
app/
├─ app.py                  # app Streamlit (uma tela: KPIs + gráfico + aba de chat)
├─ app.yaml                # comando de inicialização
├─ requirements.txt        # deps extras (se necessário)
├─ databricks_logo.png     # copie de assets/databricks_logo.png (ver dbx-brand)
└─ .streamlit/config.toml  # tema da marca (ver dbx-brand)
```

## 2. app.yaml (porta correta de graça)
```yaml
command: ["streamlit", "run", "app.py"]
```
O Streamlit já escuta na porta do ambiente (`DATABRICKS_APP_PORT`). **Nunca fixe 8080 nem outra porta.**

## 3. Autenticação e dados (sem token hardcoded)
- Autentique com **`Config()`** (`databricks.sdk.core`) — o app usa o service principal (envs
  `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` são injetados).
- Conecte ao SQL Warehouse **sob demanda e cacheado** (nunca no import), para o app subir mesmo com
  o warehouse frio:
```python
import os, streamlit as st
from databricks.sdk.core import Config
from databricks import sql

@st.cache_resource
def get_conn():
    cfg = Config()
    return sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        credentials_provider=lambda: cfg.authenticate,
    )
```
- **Toda consulta com spinner, timeout e erro visível** — o app nunca pode travar mudo em
  "Carregando…". Use `try/except` e mostre o erro real (assim você vê a causa em vez de ficar preso):
```python
@st.cache_data(ttl=300)
def query_df(q: str):
    with get_conn().cursor() as cur:
        cur.execute(q)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

with st.spinner("Carregando KPIs…"):
    try:
        rows = query_df("SELECT ... FROM treinamento_databricks.<schema>.gold_...")
    except Exception as e:
        st.error(f"Falha ao consultar o warehouse: {e}")
        st.stop()
```
- `requirements.txt`: inclua `databricks-sql-connector` (e `databricks-sdk` se não estiver disponível).
  Streamlit é pré-instalado.

### Deploy: warehouse + permissões do service principal (a causa #1 de travar em "Carregando…")
O app roda como um **service principal (SP)** — não como você. Sem o warehouse anexado **e** sem
GRANT, a conexão fica tentando para sempre (trava em "Carregando…"). Garanta os dois:
1. **Anexe o SQL Warehouse como _resource_ do app** (App → Edit → Resources → SQL Warehouse,
   serverless). Receba o id por env com `valueFrom` (nunca hardcode); o valor é a *chave* que você
   deu ao resource:
   ```yaml
   command: ["streamlit", "run", "app.py"]
   env:
     - name: "DATABRICKS_WAREHOUSE_ID"
       valueFrom: "sql_warehouse"
   ```
2. **GRANT ao service principal do app** (nome em App → Authorization), no SQL Editor como dono. Troque `<schema>` pelo schema do caso (`suprimentos`/`financas`/`manutencao`/`auditoria`):
   ```sql
   GRANT USE CATALOG ON CATALOG treinamento_databricks TO `<app-sp>`;
   GRANT USE SCHEMA  ON SCHEMA  treinamento_databricks.<schema> TO `<app-sp>`;
   GRANT SELECT      ON SCHEMA  treinamento_databricks.<schema> TO `<app-sp>`;
   ```

## 4. Chat do Genie
- Aba de chat conectada ao Genie Space pelo **ID** via **Conversation API** do Genie (SDK `w.genie`).
  O Space é criado na **UI** (ver fase Genie do playbook — no Free Edition não dá para criar por código).
  Para o código da conversa, siga a skill oficial `databricks-genie` do ai-dev-kit.

## 5. Os 5 muros do deploy no Free Edition (em ordem)
Cada erro abaixo é um degrau — resolva de cima para baixo:
1. **App Not Available** (status RUNNING) — porta errada ou quebra no startup. Use Streamlit (porta
   auto, **nunca 8080**) e conexão sob demanda (não no import).
2. **Trava em "Carregando…"** — app roda como SP. Anexe o warehouse como resource + GRANT (§3) e
   envolva a query em `st.spinner`/`try/except`/timeout (nunca travar mudo).
3. **"Nenhum SQL Warehouse disponível"** — warehouse não está **anexado como _resource_**. Editar só
   o `app.yaml` não resolve: anexe na UI (injeta o id via `valueFrom` **e** dá `CAN USE` ao SP).
4. **KPIs/gráficos vazios (sem erro)** — a query rodou e voltou 0 linhas. Diagnostique
   volume→bronze→silver→gold; se o gold tem dados, é filtro de data no app.
5. **"Nenhum dado" mascarando `StatementState.FAILED`** — a query **falhou** (a Statement Execution
   API não lança exceção; volta com `status.state == FAILED`). Mostre `status.error.message` com
   `st.error`. Causa nº 1: **SP sem `SELECT`** nas tabelas gold → aplique os GRANTs do §3.

## 6. Regra
Limite do Free Edition: **até 3 apps** (auto-stop em 24h) — reinicie pouco antes da apresentação.
