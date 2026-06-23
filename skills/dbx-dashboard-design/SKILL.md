---
name: dbx-dashboard-design
description: >-
  Boas práticas de design para dashboards AI/BI (Lakeview) no Databricks: layout
  por audiência, tipografia legível, regra de cor 60-30-10, paletas acessíveis e
  workspace themes. Use na fase de Dashboard de qualquer caso para gerar painéis
  bonitos, legíveis e on-brand. Baseada no artigo oficial "Design Beautiful
  Dashboards in AI/BI".
---

# dbx-dashboard-design — Dashboards AI/BI bonitos e on-brand

Guia rápido para a **fase de Dashboard (AI/BI / Lakeview)** de qualquer caso. Combine com
`dbx-brand` (cores/logo Databricks) e com a skill do caso.

Fonte: https://www.databricks.com/blog/design-beautiful-dashboards-aibi

## Princípios

1. **Layout pela audiência (grid de 12 colunas)**
   - Executivos: layout mais simples (~3 colunas), poucos KPIs grandes.
   - Técnicos: layout mais denso (~6 colunas), com mais detalhe.
   - Organize no padrão de leitura **F/Z**: KPIs e filtros principais no topo/à esquerda, onde o
     olhar chega primeiro; dê tamanho maior às métricas mais importantes.

2. **Tipografia legível e on-brand**
   - Prefira **sans-serif** em telas densas; escolha a fonte conforme o público (mais sóbria para
     executivos).
   - Pense no contraste para **modo claro e escuro**.

3. **Cor com a regra 60-30-10**
   - **60%** neutro (canvas, widgets, bordas) · **30%** secundária (texto, paleta de gráficos) ·
     **10%** destaque (filtros, abas, botões/CTAs).
   - Use tons quase-neutros para separar widgets; "esconda" bordas igualando-as ao fundo; destaque
     só os widgets-chave (ex.: cartões de KPI).

4. **Paletas de visualização acessíveis**
   - Monte uma paleta de **5–9 cores** partindo da cor da marca; refine com harmonias de cor.
   - **Teste para daltonismo** e para claro/escuro; evite cores muito saturadas/escuras e
     **vermelho/verde adjacentes**.

5. **Escale com Workspace Themes**
   - Defina layout, fonte e cores uma vez como **tema do workspace** e propague para todos os
     dashboards; sobrescreva localmente só quando necessário.

## Como aplicar no Genie Code
- Na fase de Dashboard, peça para **agrupar os KPIs no topo** e usar uma **paleta derivada da cor
  da marca** (Databricks), com bom contraste em claro/escuro.
- Sempre **teste cada query no SQL antes** de virar gráfico (já é regra do playbook).
- Se for repetir em vários dashboards, peça para salvar como **Workspace Theme**.

## Checklist rápido
- [ ] KPIs principais no topo e maiores que o resto.
- [ ] ~5–9 cores, derivadas da marca, testadas para daltonismo.
- [ ] Regra 60-30-10 respeitada (fundo neutro, destaque só no essencial).
- [ ] Fonte legível (sans-serif) e contraste OK em claro/escuro.
- [ ] Layout coerente com a audiência (executivo × técnico).
