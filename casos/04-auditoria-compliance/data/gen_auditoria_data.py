#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de dados sintéticos — Caso 4: Auditoria Contínua & Compliance (GRC).

Cria, de forma 100% fictícia, os insumos do caso de uso de auditoria contínua de
uma empresa fictícia ("Companhia Andes"):

  ESTRUTURADO (CSVs) — para o pipeline medalhão, o dashboard e o Genie:
    1. fornecedores.csv        — cadastro de fornecedores (contrato, situação, parte relacionada)
    2. aprovadores.csv         — colaboradores com alçada de aprovação (cargo, área, limite)
    3. regras_compliance.csv   — catálogo de regras auditadas (id, descrição, severidade)
    4. transacoes.csv          — pagamentos/lançamentos (valor, fornecedor, aprovador, data)
    5. achados_auditoria.csv   — findings: transação × regra violada (derivado das regras)

  NÃO ESTRUTURADO (.md) — para ai_parse_document + Vector Search + RAG:
    data/documentos/*.md       — ~12 políticas/normas/cláusulas/código de conduta

Determinístico (seed=42) e re-executável (sobrescreve os arquivos).

Uso:
    pip install --quiet pandas faker
    python3 gen_auditoria_data.py

Os arquivos são gravados no MESMO diretório deste script (CSVs) e em data/documentos/ (.md).
"""

import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# ----------------------------------------------------------------------------
# Determinismo
# ----------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("pt_BR")
Faker.seed(SEED)

OUTDIR = os.path.dirname(os.path.abspath(__file__))
DOCDIR = os.path.join(OUTDIR, "documentos")


def out(name: str) -> str:
    return os.path.join(OUTDIR, name)


def brl(x) -> float:
    """Arredonda para 2 casas (centavos)."""
    return float(round(float(x), 2))


def fmt_brl(x) -> str:
    """Formata um valor em reais no padrão pt-BR: 1.234.567,89 (ponto milhar, vírgula decimal)."""
    return f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ----------------------------------------------------------------------------
# Parâmetros do domínio (empresa fictícia "Companhia Andes")
# ----------------------------------------------------------------------------
AREAS = ["Compras", "TI", "Facilities", "Logística", "Marketing", "Jurídico", "RH", "Operações"]

UFS = ["SP", "RJ", "MG", "PR", "RS", "SC", "BA", "PE", "DF", "GO"]

# Cargo -> alçada de aprovação (R$). Espelha a "norma_alcadas_aprovacao.md".
CARGO_ALCADA = {
    "Analista": 10_000,
    "Coordenador": 50_000,
    "Gerente": 200_000,
    "Diretor": 1_000_000,
    "Vice-Presidente": 5_000_000,
}
CARGOS = list(CARGO_ALCADA.keys())
CARGO_W = [0.40, 0.28, 0.20, 0.09, 0.03]  # pirâmide organizacional

CATEGORIAS_DESPESA = [
    "Materiais e suprimentos", "Serviços de TI", "Manutenção predial",
    "Frete e logística", "Marketing e eventos", "Consultoria",
    "Viagens corporativas", "Brindes e hospitalidade", "Licenças de software",
    "Treinamento", "Utilidades",
]

METODOS_PAGAMENTO = ["Transferência", "Boleto", "Cartão corporativo", "Pix"]

# Catálogo de regras (id -> nome, descrição, severidade, categoria, política de referência)
REGRAS = [
    ("R001", "Alçada de aprovação excedida",
     "Pagamento aprovado por colaborador cujo limite de alçada é inferior ao valor da transação.",
     "Alta", "Alçada", "norma_alcadas_aprovacao.md"),
    ("R002", "Pagamento a fornecedor sem contrato vigente",
     "Despesa relevante liquidada a fornecedor que não possui contrato vigente registrado.",
     "Alta", "Contrato", "politica_compras.md"),
    ("R003", "Quebra de segregação de funções",
     "Mesmo colaborador figura como solicitante e aprovador da transação.",
     "Alta", "Segregação de funções", "politica_segregacao_funcoes.md"),
    ("R004", "Pagamento processado em dia não útil",
     "Liquidação financeira realizada em sábado, domingo ou fora da janela de pagamentos.",
     "Baixa", "Pagamento", "politica_pagamentos.md"),
    ("R005", "Fornecedor com situação cadastral irregular",
     "Transação com fornecedor cuja situação cadastral consta como irregular na due diligence.",
     "Alta", "Cadastro", "norma_due_diligence_fornecedores.md"),
    ("R006", "Indício de fracionamento de compra",
     "Três ou mais pagamentos ao mesmo fornecedor logo abaixo de uma alçada, em janela curta.",
     "Média", "Fracionamento", "politica_compras.md"),
    ("R007", "Indício de pagamento em duplicidade",
     "Dois pagamentos de mesmo valor, ao mesmo fornecedor, na mesma semana.",
     "Alta", "Pagamento", "politica_pagamentos.md"),
    ("R008", "Lançamento sem categoria de despesa",
     "Transação registrada sem classificação de categoria contábil/gerencial.",
     "Baixa", "Cadastro", "manual_compliance.md"),
    ("R009", "Brinde ou hospitalidade acima do limite",
     "Despesa de brinde/hospitalidade acima do teto definido no código de conduta.",
     "Média", "Conduta", "politica_brindes_hospitalidade.md"),
    ("R010", "Transação com parte relacionada",
     "Pagamento a fornecedor sinalizado como parte relacionada sem aprovação do comitê de ética.",
     "Alta", "Conduta", "politica_conflito_interesses.md"),
]

N_FORNECEDORES = 40
N_APROVADORES = 25
N_TRANSACOES = 600

DATA_INI = date(2025, 6, 23)
DATA_FIM = date(2026, 6, 22)
SPAN_DIAS = (DATA_FIM - DATA_INI).days

# Limites de negócio (espelham os documentos de política)
LIMITE_CONTRATO_OBRIGATORIO = 50_000   # acima disso, fornecedor precisa de contrato (politica_compras)
LIMITE_BRINDE = 1_000                   # teto de brinde/hospitalidade (politica_brindes_hospitalidade)


# ============================================================================
# 1) fornecedores.csv
# ============================================================================
def gen_fornecedores() -> pd.DataFrame:
    rows = []
    for i in range(1, N_FORNECEDORES + 1):
        fid = f"FOR{i:04d}"
        # ~30% sem contrato vigente; ~10% situação irregular; ~8% parte relacionada
        possui_contrato = random.random() >= 0.30
        situacao = "Irregular" if random.random() < 0.10 else "Regular"
        parte_relacionada = random.random() < 0.08
        contrato_id = f"CTR{i:04d}" if possui_contrato else ""
        rows.append({
            "id_fornecedor": fid,
            "razao_social": fake.company(),
            "cnpj": fake.cnpj(),
            "uf": random.choice(UFS),
            "categoria_fornecimento": random.choice(CATEGORIAS_DESPESA),
            "possui_contrato": bool(possui_contrato),
            "contrato_id": contrato_id,
            "situacao_cadastral": situacao,
            "parte_relacionada": bool(parte_relacionada),
        })
    return pd.DataFrame(rows)


# ============================================================================
# 2) aprovadores.csv  (colaboradores com alçada; também atuam como solicitantes)
# ============================================================================
def gen_aprovadores() -> pd.DataFrame:
    rows = []
    for i in range(1, N_APROVADORES + 1):
        aid = f"APR{i:03d}"
        cargo = random.choices(CARGOS, weights=CARGO_W)[0]
        rows.append({
            "id_aprovador": aid,
            "nome": fake.name(),
            "cargo": cargo,
            "area": random.choice(AREAS),
            "alcada_limite": float(CARGO_ALCADA[cargo]),
        })
    return pd.DataFrame(rows)


# ============================================================================
# 3) regras_compliance.csv
# ============================================================================
def gen_regras() -> pd.DataFrame:
    rows = []
    for rid, nome, desc, sev, cat, pol in REGRAS:
        rows.append({
            "id_regra": rid,
            "nome": nome,
            "descricao": desc,
            "severidade": sev,
            "categoria": cat,
            "politica_referencia": pol,
        })
    return pd.DataFrame(rows)


# ============================================================================
# 4) transacoes.csv
# ============================================================================
def gen_transacoes(fornecedores: pd.DataFrame, aprovadores: pd.DataFrame) -> pd.DataFrame:
    forn = fornecedores.to_dict("records")
    aprs = aprovadores.to_dict("records")
    forn_com_contrato = [f for f in forn if f["possui_contrato"]]
    forn_sem_contrato = [f for f in forn if not f["possui_contrato"]]
    forn_irregular = [f for f in forn if f["situacao_cadastral"] == "Irregular"]
    forn_parte_rel = [f for f in forn if f["parte_relacionada"]]

    status_opts = ["Pago", "Pendente", "Estornado"]
    status_w = [0.78, 0.15, 0.07]

    rows = []
    for i in range(1, N_TRANSACOES + 1):
        tid = f"TX{i:06d}"
        aprovador = random.choice(aprs)
        area = aprovador["area"]

        # ---- escolha do fornecedor: injeta sinais de risco em proporções plausíveis
        r = random.random()
        if r < 0.10 and forn_irregular:
            fornecedor = random.choice(forn_irregular)             # ~10% irregular
        elif r < 0.15 and forn_parte_rel:
            fornecedor = random.choice(forn_parte_rel)             # ~5% parte relacionada
        else:
            # maioria com contrato; ~22% do restante sem contrato -> ~25% no total
            if random.random() < 0.78 and forn_com_contrato:
                fornecedor = random.choice(forn_com_contrato)
            else:
                fornecedor = random.choice(forn_sem_contrato)

        # ---- categoria de despesa (R008: ~5% sem categoria) --------------
        if random.random() < 0.05:
            categoria = ""
        else:
            categoria = random.choice(CATEGORIAS_DESPESA)

        # ---- valor: a maioria sob a alçada; ~15% acima (R001) ------------
        limite = aprovador["alcada_limite"]
        if random.random() < 0.15:
            valor = brl(limite * random.uniform(1.05, 2.5))        # acima da alçada
        else:
            valor = brl(limite * random.uniform(0.02, 0.92))       # dentro da alçada
        # brindes/hospitalidade tendem a valores menores, mas alguns furam o teto (R009)
        if categoria == "Brindes e hospitalidade":
            if random.random() < 0.45:
                valor = brl(random.uniform(LIMITE_BRINDE * 1.1, LIMITE_BRINDE * 6))
            else:
                valor = brl(random.uniform(80, LIMITE_BRINDE))

        # ---- solicitante: ~8% == aprovador (R003 segregação) -------------
        if random.random() < 0.08:
            solicitante = aprovador["id_aprovador"]
        else:
            outro = random.choice([a for a in aprs if a["id_aprovador"] != aprovador["id_aprovador"]])
            solicitante = outro["id_aprovador"]

        # ---- data: maioria em dia útil; ~12% em fim de semana (R004) -----
        data_tx = DATA_INI + timedelta(days=random.randint(0, SPAN_DIAS))
        if random.random() < 0.12:
            while data_tx.weekday() < 5:        # empurra para sábado/domingo
                data_tx += timedelta(days=1)
        else:
            while data_tx.weekday() >= 5:       # senão, ajusta para dia útil
                data_tx += timedelta(days=1)

        status = random.choices(status_opts, weights=status_w)[0]

        rows.append({
            "id_transacao": tid,
            "data_transacao": data_tx.isoformat(),
            "id_fornecedor": fornecedor["id_fornecedor"],
            "id_solicitante": solicitante,
            "id_aprovador": aprovador["id_aprovador"],
            "area": area,
            "categoria_despesa": categoria,
            "valor": valor,
            "metodo_pagamento": random.choice(METODOS_PAGAMENTO),
            "contrato_id": fornecedor["contrato_id"],
            "status": status,
        })

    df = pd.DataFrame(rows)

    # ---- injeta um cluster de FRACIONAMENTO (R006) -----------------------
    # 4 pagamentos ao mesmo fornecedor (com contrato), logo abaixo de 50k, em 6 dias.
    forn_frac = random.choice([f for f in forn if f["possui_contrato"]])["id_fornecedor"]
    apr_frac = random.choice([a for a in aprs if a["cargo"] in ("Coordenador", "Gerente")])
    base_day = DATA_INI + timedelta(days=random.randint(30, SPAN_DIAS - 30))
    frac_rows = []
    for k in range(4):
        i = N_TRANSACOES + k + 1
        frac_rows.append({
            "id_transacao": f"TX{i:06d}",
            "data_transacao": (base_day + timedelta(days=k + k)).isoformat(),
            "id_fornecedor": forn_frac,
            "id_solicitante": random.choice([a["id_aprovador"] for a in aprs if a["id_aprovador"] != apr_frac["id_aprovador"]]),
            "id_aprovador": apr_frac["id_aprovador"],
            "area": apr_frac["area"],
            "categoria_despesa": "Materiais e suprimentos",
            "valor": brl(random.uniform(46_000, 49_500)),
            "metodo_pagamento": "Transferência",
            "contrato_id": next(f["contrato_id"] for f in forn if f["id_fornecedor"] == forn_frac),
            "status": "Pago",
        })

    # ---- injeta um par DUPLICADO (R007) ----------------------------------
    forn_dup = random.choice([f for f in forn if f["possui_contrato"]])["id_fornecedor"]
    apr_dup = random.choice(aprs)
    val_dup = brl(random.uniform(8_000, 25_000))
    day_dup = DATA_INI + timedelta(days=random.randint(30, SPAN_DIAS - 30))
    dup_rows = []
    for k in range(2):
        i = N_TRANSACOES + 4 + k + 1
        dup_rows.append({
            "id_transacao": f"TX{i:06d}",
            "data_transacao": (day_dup + timedelta(days=k * 2)).isoformat(),
            "id_fornecedor": forn_dup,
            "id_solicitante": random.choice([a["id_aprovador"] for a in aprs if a["id_aprovador"] != apr_dup["id_aprovador"]]),
            "id_aprovador": apr_dup["id_aprovador"],
            "area": apr_dup["area"],
            "categoria_despesa": "Serviços de TI",
            "valor": val_dup,
            "metodo_pagamento": "Boleto",
            "contrato_id": next(f["contrato_id"] for f in forn if f["id_fornecedor"] == forn_dup),
            "status": "Pago",
        })

    extra = pd.DataFrame(frac_rows + dup_rows)
    df = pd.concat([df, extra], ignore_index=True)
    return df


# ============================================================================
# 5) achados_auditoria.csv  (DERIVADO — aplica as 10 regras às transações)
# ============================================================================
def gen_achados(transacoes: pd.DataFrame, fornecedores: pd.DataFrame, aprovadores: pd.DataFrame):
    forn_idx = fornecedores.set_index("id_fornecedor").to_dict("index")
    apr_idx = aprovadores.set_index("id_aprovador").to_dict("index")
    sev_por_regra = {rid: sev for rid, _, _, sev, _, _ in REGRAS}

    status_achado = ["Aberto", "Em análise", "Resolvido", "Falso positivo"]
    status_w = [0.45, 0.25, 0.22, 0.08]

    achados = []
    seq = 0

    def add(tx, regra_id, descricao, valor_risco):
        nonlocal seq
        seq += 1
        achados.append({
            "id_achado": f"AC{seq:06d}",
            "id_transacao": tx["id_transacao"],
            "id_regra": regra_id,
            "severidade": sev_por_regra[regra_id],
            "data_deteccao": tx["data_transacao"],
            "status_achado": random.choices(status_achado, weights=status_w)[0],
            "valor_em_risco": brl(valor_risco),
            "descricao": descricao,
        })

    # índices auxiliares para fracionamento/duplicidade
    txs = transacoes.to_dict("records")
    for t in txs:
        t["_d"] = date.fromisoformat(t["data_transacao"])

    for t in txs:
        forn = forn_idx[t["id_fornecedor"]]
        apr = apr_idx[t["id_aprovador"]]
        valor = float(t["valor"])

        # R001 — alçada excedida
        if valor > float(apr["alcada_limite"]):
            add(t, "R001",
                f"Valor de R$ {fmt_brl(valor)} acima da alçada do aprovador ({apr['cargo']}, "
                f"limite R$ {fmt_brl(apr['alcada_limite'])}).", valor - float(apr["alcada_limite"]))

        # R002 — fornecedor sem contrato em despesa relevante
        if (not forn["possui_contrato"]) and valor >= LIMITE_CONTRATO_OBRIGATORIO:
            add(t, "R002",
                f"Pagamento de R$ {fmt_brl(valor)} a fornecedor sem contrato vigente "
                f"(acima do limite de R$ {fmt_brl(LIMITE_CONTRATO_OBRIGATORIO)}).", valor)

        # R003 — segregação de funções
        if t["id_solicitante"] == t["id_aprovador"]:
            add(t, "R003",
                "Solicitante e aprovador são o mesmo colaborador.", valor)

        # R004 — pagamento em dia não útil
        if t["_d"].weekday() >= 5 and t["status"] == "Pago":
            add(t, "R004",
                f"Pagamento liquidado em {['seg','ter','qua','qui','sex','sábado','domingo'][t['_d'].weekday()]}.",
                0.0)

        # R005 — fornecedor irregular
        if forn["situacao_cadastral"] == "Irregular":
            add(t, "R005",
                "Fornecedor com situação cadastral irregular na due diligence.", valor)

        # R008 — sem categoria
        if (t["categoria_despesa"] or "").strip() == "":
            add(t, "R008", "Lançamento sem categoria de despesa.", 0.0)

        # R009 — brinde acima do limite
        if t["categoria_despesa"] == "Brindes e hospitalidade" and valor > LIMITE_BRINDE:
            add(t, "R009",
                f"Brinde/hospitalidade de R$ {fmt_brl(valor)} acima do teto de R$ {fmt_brl(LIMITE_BRINDE)}.",
                valor - LIMITE_BRINDE)

        # R010 — parte relacionada
        if forn["parte_relacionada"]:
            add(t, "R010",
                "Pagamento a fornecedor sinalizado como parte relacionada.", valor)

    # R006 — fracionamento: >=3 pagamentos ao mesmo fornecedor abaixo do limite em 10 dias
    by_forn = {}
    for t in txs:
        if float(t["valor"]) < LIMITE_CONTRATO_OBRIGATORIO:
            by_forn.setdefault(t["id_fornecedor"], []).append(t)
    for fid, lst in by_forn.items():
        lst = sorted(lst, key=lambda x: x["_d"])
        for a in range(len(lst)):
            janela = [x for x in lst if 0 <= (x["_d"] - lst[a]["_d"]).days <= 10]
            if len(janela) >= 3:
                soma = sum(float(x["valor"]) for x in janela)
                if soma >= LIMITE_CONTRATO_OBRIGATORIO:  # juntos furam o limite
                    for x in janela:
                        add(x, "R006",
                            f"Possível fracionamento: {len(janela)} pagamentos ao mesmo "
                            f"fornecedor em 10 dias somando R$ {fmt_brl(soma)}.", float(x["valor"]))
                    break  # registra o cluster uma vez por fornecedor

    # R007 — duplicidade: mesmo fornecedor + mesmo valor + mesma semana (>1 ocorrência)
    seen = {}
    for t in txs:
        iso_year, iso_week, _ = t["_d"].isocalendar()
        key = (t["id_fornecedor"], round(float(t["valor"]), 2), iso_year, iso_week)
        seen.setdefault(key, []).append(t)
    for key, lst in seen.items():
        if len(lst) >= 2:
            for x in lst:
                add(x, "R007",
                    f"Pagamento de R$ {fmt_brl(x['valor'])} ao mesmo fornecedor repetido na semana.",
                    float(x["valor"]))

    df = pd.DataFrame(achados)
    # ordena por transação para leitura estável
    df = df.sort_values(["id_transacao", "id_regra"]).reset_index(drop=True)
    df["id_achado"] = [f"AC{i:06d}" for i in range(1, len(df) + 1)]  # re-sequencia limpo
    return df


# ============================================================================
# DOCUMENTOS (.md) — não estruturados, para ai_parse_document + Vector Search
# ============================================================================
def documentos() -> dict:
    """Retorna {nome_arquivo: conteúdo}. Texto curado (não aleatório) e determinístico."""
    docs = {}

    docs["politica_compras.md"] = """# Política de Compras e Contratação — Companhia Andes

**Código:** POL-COMP-001 · **Versão:** 3.2 · **Área responsável:** Suprimentos

## 1. Objetivo
Estabelecer as regras para aquisição de bens e serviços, assegurando competitividade,
conformidade e rastreabilidade de todas as compras da Companhia Andes.

## 2. Contrato obrigatório
Toda despesa **igual ou superior a R$ 50.000,00** com um mesmo fornecedor exige
**contrato vigente** registrado no sistema de gestão de fornecedores. Pagamentos acima
desse limite a fornecedores sem contrato são considerados **não conformes** e devem ser
bloqueados pela tesouraria.

## 3. Vedação ao fracionamento
É **proibido fracionar** uma compra em vários pedidos de menor valor com o objetivo de
evitar a exigência de contrato ou de alçada superior. Três ou mais pagamentos ao mesmo
fornecedor, em janela de até 10 dias, cuja soma ultrapasse R$ 50.000,00, serão tratados
como **indício de fracionamento** e encaminhados à auditoria.

## 4. Cotação e seleção
Compras acima de R$ 20.000,00 exigem no mínimo três cotações. A seleção deve privilegiar
fornecedores com **situação cadastral regular** e aprovados na due diligence (ver
norma de due diligence de fornecedores).

## 5. Conformidade
O descumprimento desta política sujeita os responsáveis às medidas do Código de Conduta.
"""

    docs["norma_alcadas_aprovacao.md"] = """# Norma de Alçadas de Aprovação — Companhia Andes

**Código:** NRM-ALC-002 · **Versão:** 2.0 · **Área responsável:** Controladoria

## 1. Princípio
Nenhum pagamento pode ser aprovado por colaborador cujo **limite de alçada** seja inferior
ao valor da transação. A alçada é pessoal e intransferível.

## 2. Tabela de alçadas
| Cargo | Limite de aprovação (R$) |
|---|---|
| Analista | 10.000,00 |
| Coordenador | 50.000,00 |
| Gerente | 200.000,00 |
| Diretor | 1.000.000,00 |
| Vice-Presidente | 5.000.000,00 |

## 3. Aprovação acima da alçada
Valores acima de R$ 5.000.000,00 exigem aprovação colegiada do Comitê de Investimentos.
Transações aprovadas **acima do limite** do aprovador são **não conformes** (severidade alta)
e geram achado de auditoria automático.

## 4. Segregação
A aprovação observa a segregação de funções: quem solicita não pode aprovar (ver política
de segregação de funções).
"""

    docs["politica_segregacao_funcoes.md"] = """# Política de Segregação de Funções (SoD) — Companhia Andes

**Código:** POL-SOD-003 · **Versão:** 1.4 · **Área responsável:** Compliance

## 1. Objetivo
Prevenir fraude e erro garantindo que **nenhuma pessoa** controle todas as etapas de um
processo financeiro sensível.

## 2. Regra central
O **solicitante** de um pagamento **não pode ser o seu aprovador**. Transações em que o
mesmo colaborador figura como solicitante e aprovador representam **quebra de segregação
de funções** e são classificadas como severidade alta.

## 3. Funções incompatíveis
São incompatíveis entre si, para uma mesma transação: solicitar, aprovar, cadastrar
fornecedor e liquidar o pagamento. O sistema deve impedir a concentração dessas funções.

## 4. Exceções
Exceções temporárias (ex.: férias) exigem aprovação formal do Compliance e registro em ata.
"""

    docs["politica_pagamentos.md"] = """# Política de Pagamentos e Tesouraria — Companhia Andes

**Código:** POL-PAG-004 · **Versão:** 2.1 · **Área responsável:** Tesouraria

## 1. Janela de pagamentos
Os pagamentos são processados em **dias úteis**, das 9h às 17h. Liquidações em
**sábados, domingos e feriados** são exceções e exigem justificativa registrada;
caso contrário, geram achado de auditoria de severidade baixa.

## 2. Prevenção de duplicidade
Antes de liquidar, a tesouraria deve verificar **pagamentos em duplicidade**: dois
lançamentos de **mesmo valor, ao mesmo fornecedor, na mesma semana** devem ser retidos
e investigados (severidade alta).

## 3. Meios de pagamento
São aceitos transferência, boleto, Pix e cartão corporativo. Pagamentos em espécie são
vedados.

## 4. Conciliação
Toda liquidação é conciliada diariamente; divergências são reportadas ao Compliance.
"""

    docs["norma_due_diligence_fornecedores.md"] = """# Norma de Due Diligence de Fornecedores — Companhia Andes

**Código:** NRM-DDF-005 · **Versão:** 1.8 · **Área responsável:** Compliance

## 1. Objetivo
Assegurar que a Companhia Andes só transacione com fornecedores **idôneos** e de
**situação cadastral regular**.

## 2. Situação cadastral
Fornecedores com situação **irregular** (CNPJ inativo, pendências fiscais, sanções) ficam
**bloqueados** para novas transações. Pagamentos a fornecedores irregulares são achados de
**severidade alta**.

## 3. Reavaliação
A due diligence é renovada anualmente e sempre que houver alerta de mídia adversa ou
inclusão em listas restritivas.

## 4. Partes relacionadas
Fornecedores identificados como **parte relacionada** a colaboradores exigem aprovação do
Comitê de Ética antes de qualquer pagamento (ver política de conflito de interesses).
"""

    docs["codigo_conduta.md"] = """# Código de Conduta e Ética — Companhia Andes

**Código:** COD-ETI-006 · **Versão:** 4.0 · **Aprovação:** Conselho de Administração

## 1. Nossos princípios
Agimos com **integridade, transparência e respeito** às leis. Não toleramos fraude,
corrupção, suborno ou conflito de interesses.

## 2. Conflito de interesses
Colaboradores devem declarar qualquer relação que possa influenciar decisões de negócio,
inclusive vínculos com fornecedores (ver política de conflito de interesses).

## 3. Brindes e hospitalidade
A oferta e o recebimento de brindes seguem limites específicos (ver política de brindes e
hospitalidade). Vantagens em dinheiro são proibidas.

## 4. Canal de denúncias
Suspeitas de violação devem ser reportadas ao **Canal de Ética**, com garantia de
confidencialidade e não retaliação.

## 5. Sanções
Violações estão sujeitas a medidas disciplinares, podendo chegar à rescisão e a
responsabilização legal.
"""

    docs["politica_conflito_interesses.md"] = """# Política de Conflito de Interesses — Companhia Andes

**Código:** POL-CON-007 · **Versão:** 1.2 · **Área responsável:** Compliance

## 1. Definição
Há conflito de interesses quando interesses pessoais de um colaborador podem influenciar,
direta ou indiretamente, decisões em nome da Companhia.

## 2. Partes relacionadas
Transações com **partes relacionadas** (familiares, sócios, empresas ligadas a
colaboradores) só podem ocorrer com **aprovação prévia do Comitê de Ética** e em condições
de mercado. Pagamentos a partes relacionadas sem essa aprovação são achados de severidade
alta.

## 3. Declaração anual
Todos os colaboradores preenchem anualmente a declaração de conflito de interesses.

## 4. Abstenção
Quem tiver conflito deve se **abster** de participar da decisão correspondente.
"""

    docs["politica_brindes_hospitalidade.md"] = """# Política de Brindes e Hospitalidade — Companhia Andes

**Código:** POL-BRH-008 · **Versão:** 1.1 · **Área responsável:** Compliance

## 1. Limite
Brindes e hospitalidades oferecidos ou recebidos não podem exceder **R$ 1.000,00** por
evento ou por contraparte, sem aprovação prévia do Compliance.

## 2. Vedações
São proibidos brindes em dinheiro, presentes a agentes públicos fora dos limites legais e
qualquer cortesia que possa caracterizar vantagem indevida.

## 3. Registro
Brindes acima de R$ 200,00 devem ser registrados no sistema de compliance, com descrição,
valor e contraparte.

## 4. Não conformidade
Despesas de brinde/hospitalidade acima de R$ 1.000,00 sem aprovação geram achado de
auditoria de severidade média.
"""

    docs["manual_compliance.md"] = """# Manual de Compliance e Auditoria Contínua — Companhia Andes

**Código:** MAN-CMP-009 · **Versão:** 2.3 · **Área responsável:** Auditoria Interna

## 1. Auditoria contínua
A Companhia Andes adota **auditoria contínua**: todas as transações são testadas
automaticamente contra o catálogo de regras de compliance, gerando **achados** quando há
indício de não conformidade.

## 2. Catálogo de regras
As regras cobrem alçada, contrato, segregação de funções, situação cadastral, pagamentos,
fracionamento, duplicidade, brindes e partes relacionadas. Cada regra tem uma
**severidade** (alta, média ou baixa).

## 3. Classificação obrigatória
Todo lançamento deve ter **categoria de despesa**. Lançamentos sem categoria geram achado
de severidade baixa e devem ser regularizados pela área responsável.

## 4. Tratamento de achados
Cada achado tem um ciclo de vida: **Aberto → Em análise → Resolvido** (ou **Falso
positivo**). Achados de severidade alta têm prazo de tratamento de 5 dias úteis.

## 5. Indicadores
A área de auditoria acompanha: nº de achados por severidade, valor em risco, % de
conformidade por área e tempo médio de tratamento.
"""

    docs["politica_privacidade_lgpd.md"] = """# Política de Privacidade e Proteção de Dados (LGPD) — Companhia Andes

**Código:** POL-LGPD-010 · **Versão:** 1.0 · **Área responsável:** DPO

## 1. Objetivo
Garantir o tratamento de dados pessoais conforme a Lei Geral de Proteção de Dados
(Lei 13.709/2018).

## 2. Princípios
Tratamos dados com **finalidade, necessidade e transparência**, pelo tempo estritamente
necessário. Dados de fornecedores e colaboradores são acessados apenas por quem tem
necessidade de negócio.

## 3. Auditoria de acessos
Acessos a dados sensíveis são registrados e auditados. Compartilhamento com terceiros exige
base legal e cláusula contratual de proteção de dados.

## 4. Incidentes
Incidentes de segurança são comunicados ao DPO em até 24h e, quando aplicável, à ANPD.
"""

    docs["clausulas_contratuais_padrao.md"] = """# Cláusulas Contratuais Padrão de Fornecimento — Companhia Andes

**Código:** CLA-FOR-011 · **Versão:** 2.5 · **Área responsável:** Jurídico

## Cláusula 1 — Objeto
O fornecedor obriga-se a entregar os bens/serviços conforme especificação e prazos
acordados, mantendo sua **situação cadastral regular** durante toda a vigência.

## Cláusula 2 — Anticorrupção
O fornecedor declara conhecer e cumprir a Lei 12.846/2013 (Lei Anticorrupção) e o Código de
Conduta da Companhia Andes, abstendo-se de qualquer prática de suborno ou vantagem indevida.

## Cláusula 3 — Conflito de interesses
O fornecedor declara não ser **parte relacionada** a colaboradores da Companhia; havendo
vínculo, este deve ser informado para aprovação do Comitê de Ética.

## Cláusula 4 — Pagamentos
Os pagamentos seguem a política de pagamentos da Companhia, vedada a liquidação em espécie e
exigida a emissão de documento fiscal idôneo.

## Cláusula 5 — Auditoria
A Companhia pode auditar o cumprimento do contrato; o descumprimento sujeita o fornecedor a
penalidades e à rescisão.
"""

    docs["politica_viagens_despesas.md"] = """# Política de Viagens e Despesas Corporativas — Companhia Andes

**Código:** POL-VIA-012 · **Versão:** 1.3 · **Área responsável:** Facilities

## 1. Aprovação prévia
Viagens corporativas exigem aprovação prévia do gestor imediato e observam a tabela de
alçadas para os custos envolvidos.

## 2. Reembolso
Despesas reembolsáveis exigem **comprovante fiscal** e classificação na **categoria de
despesa** correta. Lançamentos sem categoria são bloqueados na prestação de contas.

## 3. Limites
Hospedagem e refeições seguem tetos por cidade. Despesas de hospitalidade observam a
política de brindes e hospitalidade.

## 4. Prazo
A prestação de contas deve ocorrer em até 10 dias úteis após o retorno.
"""

    return docs


# ============================================================================
# Execução
# ============================================================================
def main():
    fornecedores = gen_fornecedores()
    aprovadores = gen_aprovadores()
    regras = gen_regras()
    transacoes = gen_transacoes(fornecedores, aprovadores)
    achados = gen_achados(transacoes, fornecedores, aprovadores)

    # ---- grava CSVs (UTF-8, com header)
    arquivos = {
        "fornecedores.csv": fornecedores,
        "aprovadores.csv": aprovadores,
        "regras_compliance.csv": regras,
        "transacoes.csv": transacoes.drop(columns=[c for c in transacoes.columns if c.startswith("_")], errors="ignore"),
        "achados_auditoria.csv": achados,
    }
    for nome, df in arquivos.items():
        df.to_csv(out(nome), index=False, encoding="utf-8")

    # ---- grava documentos .md
    os.makedirs(DOCDIR, exist_ok=True)
    docs = documentos()
    for nome, conteudo in docs.items():
        with open(os.path.join(DOCDIR, nome), "w", encoding="utf-8") as f:
            f.write(conteudo)

    # ------------------------------------------------------------------
    # VALIDAÇÃO + RELATÓRIO
    # ------------------------------------------------------------------
    print("=" * 72)
    print("DADOS GERADOS — Caso 4: Auditoria Contínua & Compliance (Companhia Andes)")
    print("=" * 72)

    print("\n[1] Contagem de linhas (CSVs):")
    for nome, df in arquivos.items():
        print(f"    {nome:<26} {len(df):>6} linhas")
    print(f"    documentos/*.md            {len(docs):>6} arquivos")

    print("\n[2] Integridade referencial (orfaos = 0):")
    set_forn = set(fornecedores["id_fornecedor"])
    set_apr = set(aprovadores["id_aprovador"])
    set_regra = set(regras["id_regra"])
    set_tx = set(transacoes["id_transacao"])

    orf_tx_forn = int((~transacoes["id_fornecedor"].isin(set_forn)).sum())
    orf_tx_apr = int((~transacoes["id_aprovador"].isin(set_apr)).sum())
    orf_tx_sol = int((~transacoes["id_solicitante"].isin(set_apr)).sum())
    orf_ach_tx = int((~achados["id_transacao"].isin(set_tx)).sum())
    orf_ach_regra = int((~achados["id_regra"].isin(set_regra)).sum())

    print(f"    transacoes.id_fornecedor sem fornecedor : {orf_tx_forn}")
    print(f"    transacoes.id_aprovador sem aprovador   : {orf_tx_apr}")
    print(f"    transacoes.id_solicitante sem colaborador: {orf_tx_sol}")
    print(f"    achados.id_transacao sem transacao      : {orf_ach_tx}")
    print(f"    achados.id_regra sem regra              : {orf_ach_regra}")

    print("\n[3] Sinais de negocio embutidos:")
    n_tx = len(transacoes)
    apr_lim = aprovadores.set_index("id_aprovador")["alcada_limite"].to_dict()
    acima = transacoes.apply(lambda r: float(r["valor"]) > apr_lim[r["id_aprovador"]], axis=1).sum()
    sod = (transacoes["id_solicitante"] == transacoes["id_aprovador"]).sum()
    sem_cat = (transacoes["categoria_despesa"].fillna("").str.strip() == "").sum()
    forn_sem_contr = set(fornecedores[~fornecedores["possui_contrato"]]["id_fornecedor"])
    tx_sem_contr = transacoes["id_fornecedor"].isin(forn_sem_contr).sum()
    print(f"    transacoes acima da alcada (R001)       : {acima} ({acima/n_tx*100:.1f}%)")
    print(f"    transacoes com SoD solicitante=aprovador: {sod} ({sod/n_tx*100:.1f}%)")
    print(f"    transacoes sem categoria (R008)         : {sem_cat} ({sem_cat/n_tx*100:.1f}%)")
    print(f"    transacoes c/ fornecedor sem contrato   : {tx_sem_contr} ({tx_sem_contr/n_tx*100:.1f}%)")
    print(f"    fornecedores sem contrato               : {len(forn_sem_contr)}")
    print(f"    fornecedores irregulares                : {(fornecedores['situacao_cadastral']=='Irregular').sum()}")
    print(f"    fornecedores parte relacionada          : {fornecedores['parte_relacionada'].sum()}")

    print("\n[4] Achados por regra (severidade):")
    sev_map = {rid: sev for rid, _, _, sev, _, _ in REGRAS}
    nome_map = {rid: nome for rid, nome, _, _, _, _ in REGRAS}
    contagem = achados.groupby("id_regra").size().to_dict()
    for rid, _, _, sev, _, _ in REGRAS:
        print(f"    {rid} [{sev:<5}] {nome_map[rid][:42]:<42} {contagem.get(rid, 0):>4}")
    print(f"    {'TOTAL de achados':<54} {len(achados):>4}")
    print(f"    valor_em_risco total (R$)               : {achados['valor_em_risco'].sum():,.2f}")

    print("\n[5] Achados por severidade:")
    print(achados.groupby("severidade").size().to_string())

    print("\n[6] Amostras (ate 3 linhas por CSV):")
    for nome, df in arquivos.items():
        print(f"\n--- {nome} ---")
        print(df.head(3).to_string(index=False))

    print("\n[7] Documentos gerados:")
    for nome in docs:
        print(f"    documentos/{nome}")

    print("\n" + "=" * 72)
    print(f"OK — 5 CSVs em: {OUTDIR}")
    print(f"OK — {len(docs)} documentos .md em: {DOCDIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
