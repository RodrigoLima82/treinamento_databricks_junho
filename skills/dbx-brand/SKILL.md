---
name: dbx-brand
description: >-
  Identidade visual dos casos do workshop — logo, paleta (regra 60-30-10) e
  tipografia Databricks. Use ao estilizar o app ou os dashboards para um visual
  consistente e on-brand. Para o build/deploy do app, veja `dbx-app`; para o
  layout dos dashboards, `dbx-dashboard-design`.
---

# dbx-brand — Identidade visual Databricks

Define o visual de marca reutilizado pelo **app** (skill `dbx-app`) e pelos **dashboards**
(skill `dbx-dashboard-design`): logo, paleta e tipografia. Esta skill é só visual — a mecânica de
subir/conectar o app vive em `dbx-app`.

## 1. Logo
- Reutilize `assets/databricks_logo.png` (logo oficial); mantenha o mesmo caminho/nome ao atualizar.
- No app Streamlit: primeiro comando
  `st.set_page_config(page_title="<Caso> · Databricks Workshop", layout="wide")`, e no topo da página
  `st.image("databricks_logo.png", width=180)` (copie o png para `app/databricks_logo.png`).
- Não recrie nem distorça o logo — é ativo compartilhado.

## 2. Paleta da marca
- **Lava** `#FF3621` — primária/acento.
- **Navy** `#1B3139` — texto.
- **Verde** `#00A972` — acento positivo (OTIF, saving). Mantenha contraste AA.
- Fundo branco `#FFFFFF`; secundário `#F5F5F5`.
- Siga a **regra 60-30-10** (ver `dbx-dashboard-design`): ~60% neutro, ~30% navy, ~10% Lava.
- No Streamlit (`.streamlit/config.toml`):
```toml
[theme]
primaryColor = "#FF3621"          # Databricks "Lava"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#1B3139"             # navy
font = "sans serif"
```

## 3. Tipografia
- Sans-serif, legível, com hierarquia clara (títulos > rótulos > corpo).
- KPIs maiores no topo; rótulos curtos e descritivos.

## 4. Regra
Mesma identidade no **app** e nos **dashboards**. Visual aqui; build/deploy em `dbx-app`; layout de
painéis em `dbx-dashboard-design`.
