---
name: dbx-brand
description: >-
  Identidade visual (logo, paleta, tipografia) e scaffold de Databricks App em
  Streamlit para os casos do workshop. Use ao criar/estilizar o app de qualquer
  caso, para um visual consistente e um deploy que sobe de primeira no Free Edition.
---

# dbx-brand — App em Streamlit (visual Databricks)

Os apps do workshop são **Databricks Apps em Streamlit** — pré-instalado no runtime e com a porta
auto-configurada, é o caminho mais robusto no Free Edition. Esta skill define o visual da marca e as
regras técnicas para o app subir **sem o erro "App Not Available"**.

## 1. Estrutura mínima
```
app/
├─ app.py                  # app Streamlit (uma tela: KPIs + gráfico + aba de chat)
├─ app.yaml                # comando de inicialização
├─ requirements.txt        # deps extras (se necessário)
├─ databricks_logo.png     # copie de assets/databricks_logo.png
└─ .streamlit/config.toml  # tema da marca
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
        rows = query_df("SELECT ... FROM treinamento_databricks.suprimentos.gold_...")
    except Exception as e:
        st.error(f"Falha ao consultar o warehouse: {e}")
        st.stop()
```

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
2. **GRANT ao service principal do app** (nome em App → Authorization), no SQL Editor como dono:
   ```sql
   GRANT USE CATALOG ON CATALOG treinamento_databricks TO `<app-sp>`;
   GRANT USE SCHEMA  ON SCHEMA  treinamento_databricks.suprimentos TO `<app-sp>`;
   GRANT SELECT      ON SCHEMA  treinamento_databricks.suprimentos TO `<app-sp>`;
   ```
- `requirements.txt`: inclua `databricks-sql-connector` (e `databricks-sdk` se não estiver disponível).
  Streamlit é pré-instalado.

## 4. Logo
- Copie `assets/databricks_logo.png` do repo para `app/databricks_logo.png`.
- Primeiro comando Streamlit: `st.set_page_config(page_title="<Caso> · Databricks Workshop", layout="wide")`.
- No topo da página: `st.image("databricks_logo.png", width=180)`.

## 5. Paleta da marca (`.streamlit/config.toml`)
```toml
[theme]
primaryColor = "#FF3621"          # Databricks "Lava"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#1B3139"             # navy
font = "sans serif"
```
- Acento positivo (OTIF, saving): verde `#00A972`. Mantenha bom contraste (AA).

## 6. Layout e chat
- Uma tela: **KPIs** no topo (`st.metric`), um **gráfico** (gasto por categoria) e uma **lista** de
  pedidos em risco. Siga `dbx-dashboard-design` (KPIs no topo, regra 60-30-10).
- **Aba de chat do Genie:** conecte ao Genie Space pelo **ID** via **Conversation API** do Genie
  (SDK `w.genie`). O Space é criado na UI (ver fase Genie). Para o código da conversa, siga a skill
  oficial `databricks-genie` do ai-dev-kit.

## 7. Regra
Reutilize `assets/databricks_logo.png` (logo oficial); mantenha o mesmo caminho/nome ao atualizar.
Limite do Free Edition: **até 3 apps** (auto-stop em 24h) — reinicie pouco antes da apresentação.
