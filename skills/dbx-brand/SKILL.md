---
name: dbx-brand
description: >-
  Identidade visual (logo, paleta, tipografia) para aplicar nos Databricks Apps
  (FastAPI + Next.js) dos casos de uso do workshop. Use ao criar/estilizar
  qualquer frontend para deixá-lo com visual consistente e profissional.
---

# dbx-brand — Identidade visual dos Apps

Aplicar em todos os apps do workshop (stack: **FastAPI BFF + Next.js 14 + Tailwind**,
servido como static export).

## 1. Logo
- Arquivo fonte no repo: **`assets/databricks_logo.png`**.
- Copie para o frontend em **`client/public/databricks_logo.png`** → servido na raiz como **`/databricks_logo.png`**.
- Usos:
  - Favicon/metadata: `app/layout.tsx` → `icons: { icon: "/databricks_logo.png" }`, `title: "<Caso> · Databricks Workshop"`.
  - Barra superior (`components/Layout.tsx`): `<img src="/databricks_logo.png" alt="Databricks" className="h-7 w-auto object-contain" />`

## 2. Paleta (Tailwind)
Adicionar em `client/tailwind.config.ts` → `theme.extend.colors`:
```ts
brand: {
  red: "#FF3621",        // Databricks "Lava"
  navy: "#1B3139",       // texto/realce escuro
  green: "#00A972",      // acento de sucesso/positivo
  50: "#FFF1EF",
  100: "#FFE3DE",
}
```
- Uso: `text-brand-navy`, `bg-brand-red`, `ring-brand-red/20`, acento positivo `text-brand-green`.
- Cinzas: escala `slate`. Mantenha bom contraste (acessibilidade AA).

## 3. Tipografia
- Fonte **Inter** (Google Font), carregada em `app/layout.tsx`.

## 4. Convenções de UI
- Título do app: **"<Nome do Caso> · Databricks Workshop"**.
- Header com logo à esquerda + nome do app; botão/realce primário em `brand-red`.
- Componentes de chat (Genie/agente): `react-markdown` + `remark-gfm`; carregamento com toast (`react-hot-toast`).
- Cards de KPI com borda sutil, número grande, rótulo em cinza; acento em `brand-red`.

## 5. Regra
Reutilize `assets/databricks_logo.png` deste repo. (É um placeholder em SVG — pode ser
substituído pelo logo oficial em PNG/SVG, mantendo o mesmo caminho e nome.)
