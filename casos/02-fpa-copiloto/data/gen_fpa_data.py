#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de dados sintéticos — Caso 2: Copiloto de FP&A (uma empresa de mineração).

Cria 4 CSVs realistas (porém 100% fictícios) para o treinamento Databricks
Free Edition. Determinístico (seed=42) e re-executável (sobrescreve os arquivos).

Modelo (planejamento financeiro & análise):
    centros_custo      — dimensão: centros de custo por área.
    contas_contabeis   — dimensão: plano de contas (Receita / Despesa / CAPEX).
    orcamento          — fato: orçado por conta × centro × mês (36 meses).
    lancamentos        — fato: realizado por conta × centro × mês (30 meses fechados).

O orçamento cobre 6 meses a MAIS que o realizado (meses ainda não fechados) —
é esse "vão" que o `ai_forecast` preenche na Fase 2 do runbook. Os 30 meses de
histórico mensal dão série suficiente para a projeção funcionar.

Uso:
    pip install --quiet pandas faker
    python3 gen_fpa_data.py

Os CSVs são gravados no MESMO diretório deste script.
"""

import os
import math
import random
from datetime import date

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


def out(name: str) -> str:
    return os.path.join(OUTDIR, name)


def brl(x) -> float:
    """Arredonda para 2 casas (centavos)."""
    return float(round(float(x), 2))


def brl_cem(x) -> float:
    """Arredonda para a centena mais próxima (orçamentos costumam ser redondos)."""
    return float(round(float(x) / 100.0) * 100.0)


# ----------------------------------------------------------------------------
# Janela temporal
# ----------------------------------------------------------------------------
# Histórico fechado: 30 meses terminando em 2026-05 (mês fechado anterior a "hoje").
# Orçamento: os mesmos 30 meses + 6 meses futuros (2026-06 .. 2026-11), ainda sem
# realizado — é o intervalo que a projeção (ai_forecast) vai cobrir.
MES_INI = date(2023, 12, 1)
N_MESES_HIST = 30   # 2023-12 .. 2026-05
N_MESES_FUT = 6     # 2026-06 .. 2026-11 (apenas orçamento)
N_MESES_ORC = N_MESES_HIST + N_MESES_FUT  # 36


def add_meses(d: date, n: int) -> date:
    """Primeiro dia do mês d + n meses."""
    total = (d.year * 12 + (d.month - 1)) + n
    ano, mes = divmod(total, 12)
    return date(ano, mes + 1, 1)


MESES_ORC = [add_meses(MES_INI, i) for i in range(N_MESES_ORC)]
MESES_HIST = MESES_ORC[:N_MESES_HIST]


def sazonal(d: date, amp: float) -> float:
    """Fator sazonal anual (pico por volta do meio do ano)."""
    if amp <= 0:
        return 1.0
    return 1.0 + amp * math.sin(2 * math.pi * (d.month - 3) / 12.0)


# ----------------------------------------------------------------------------
# Dimensão: centros de custo
# (id_centro, nome, area, regiao, peso)  — peso escala o tamanho do orçamento
# ----------------------------------------------------------------------------
CENTROS_DEF = [
    ("CC01", "Operações Mina Norte",        "Operações",   "PA", 1.40),
    ("CC02", "Operações Mina Sul",          "Operações",   "MG", 1.20),
    ("CC03", "Operações Mina Central",      "Operações",   "MG", 1.00),
    ("CC04", "Logística e Ferrovia",        "Logística",   "MA", 1.10),
    ("CC05", "Terminal Portuário",          "Logística",   "ES", 0.90),
    ("CC06", "Diretoria Comercial",         "Comercial",   "RJ", 1.00),
    ("CC07", "Tecnologia da Informação",    "TI",          "SP", 0.60),
    ("CC08", "Recursos Humanos",            "RH",          "MG", 0.50),
    ("CC09", "Diretoria Financeira",        "Corporativo", "RJ", 0.80),
    ("CC10", "Manutenção Industrial",       "Operações",   "PA", 0.70),
]
CENTRO_PESO = {c[0]: c[4] for c in CENTROS_DEF}
CENTRO_AREA = {c[0]: c[2] for c in CENTROS_DEF}


# ----------------------------------------------------------------------------
# Dimensão: plano de contas
# (id_conta, nome, tipo, grupo, base_mensal, areas, trend, amp_sazonal)
#   base_mensal  — orçado típico/mês para um centro de peso 1.0 (BRL)
#   areas        — "ALL" ou lista de áreas que usam a conta
#   trend        — crescimento mensal composto (inflação/expansão)
#   amp_sazonal  — amplitude da sazonalidade anual (0 = sem)
# ----------------------------------------------------------------------------
CONTAS_DEF = [
    # ---- Receita ----
    ("310001", "Receita de venda de minério",     "Receita", "Receita operacional", 18_000_000, ["Operações", "Comercial"],               0.006, 0.12),
    ("310002", "Receita de serviços logísticos",  "Receita", "Receita operacional",  4_000_000, ["Logística", "Comercial"],               0.004, 0.10),
    ("320001", "Receita financeira",              "Receita", "Receita financeira",     800_000, ["Corporativo"],                          0.002, 0.00),
    # ---- Despesa ----
    ("410001", "Salários e ordenados",            "Despesa", "Pessoal",              1_200_000, "ALL",                                    0.003, 0.00),
    ("410002", "Encargos sociais",                "Despesa", "Pessoal",                600_000, "ALL",                                    0.003, 0.00),
    ("410003", "Benefícios",                      "Despesa", "Pessoal",                220_000, ["Corporativo", "Comercial", "TI", "RH"], 0.003, 0.00),
    ("420001", "Energia elétrica",                "Despesa", "Utilidades",             900_000, ["Operações", "Logística"],               0.005, 0.08),
    ("420002", "Combustíveis e lubrificantes",    "Despesa", "Utilidades",             700_000, ["Operações", "Logística"],               0.004, 0.08),
    ("430001", "Serviços de terceiros",           "Despesa", "Serviços",               800_000, "ALL",                                    0.002, 0.00),
    ("430002", "Consultoria e auditoria",         "Despesa", "Serviços",               200_000, ["Corporativo", "Comercial"],             0.000, 0.00),
    ("440001", "Manutenção de equipamentos",      "Despesa", "Manutenção",             600_000, ["Operações", "Logística"],               0.003, 0.00),
    ("440002", "Materiais de manutenção",         "Despesa", "Manutenção",             300_000, ["Operações"],                            0.003, 0.00),
    ("450001", "Fretes e transportes",            "Despesa", "Logística",            1_500_000, ["Logística", "Comercial"],               0.003, 0.10),
    ("460001", "Viagens e estadias",              "Despesa", "Administrativas",         90_000, ["Comercial", "Corporativo", "Operações"], 0.000, 0.08),
    ("460002", "Aluguéis e locações",             "Despesa", "Administrativas",        120_000, ["Corporativo", "Comercial", "TI", "RH"], 0.001, 0.00),
    ("460003", "Despesas com TI e software",      "Despesa", "Administrativas",        180_000, "ALL",                                    0.004, 0.00),
    ("470001", "Treinamento e desenvolvimento",   "Despesa", "Pessoal",                 60_000, ["RH", "Operações"],                      0.000, 0.00),
    ("480001", "Depreciação e amortização",       "Despesa", "Não-caixa",            1_000_000, ["Operações", "Logística"],               0.000, 0.00),
    # ---- CAPEX ----
    ("510001", "Aquisição de equipamentos",       "CAPEX",   "Investimentos",        2_500_000, ["Operações", "Logística"],               0.000, 0.00),
    ("510002", "Obras civis",                     "CAPEX",   "Investimentos",        3_000_000, ["Operações"],                            0.000, 0.00),
    ("510003", "Projetos de expansão",            "CAPEX",   "Investimentos",        5_000_000, ["Operações", "Corporativo"],             0.000, 0.00),
    ("510004", "Tecnologia e automação",          "CAPEX",   "Investimentos",          800_000, ["TI"],                                   0.000, 0.00),
]

# Pares (conta, centro) com estouro CRÔNICO de orçamento — viram os "topo estouros".
# (estes pares recebem viés positivo forte e crescente ao longo do tempo)
CRONICOS = {
    ("420001", "CC01"),  # Energia elétrica — Mina Norte
    ("420002", "CC01"),  # Combustíveis — Mina Norte
    ("440001", "CC02"),  # Manutenção de equipamentos — Mina Sul
    ("430001", "CC04"),  # Serviços de terceiros — Logística e Ferrovia
    ("440002", "CC10"),  # Materiais de manutenção — Manutenção Industrial
    ("430002", "CC09"),  # Consultoria e auditoria — Diretoria Financeira
    ("450001", "CC05"),  # Fretes e transportes — Terminal Portuário
}


# ============================================================================
# 1) centros_custo.csv
# ============================================================================
def gen_centros() -> pd.DataFrame:
    rows = []
    for cid, nome, area, regiao, _peso in CENTROS_DEF:
        rows.append({
            "id_centro": cid,
            "nome": nome,
            "area": area,
            "responsavel": fake.name(),
            "regiao": regiao,
        })
    return pd.DataFrame(rows)


# ============================================================================
# 2) contas_contabeis.csv
# ============================================================================
def gen_contas() -> pd.DataFrame:
    rows = []
    for (cid, nome, tipo, grupo, *_rest) in CONTAS_DEF:
        rows.append({
            "id_conta": cid,
            "nome": nome,
            "tipo": tipo,
            "grupo": grupo,
        })
    return pd.DataFrame(rows)


# ============================================================================
# Pares ativos (conta × centro) a partir do mapeamento por área
# ============================================================================
def build_pares():
    """Retorna lista de (id_conta, id_centro) que existem no orçamento."""
    pares = []
    for (cid, _nome, _tipo, _grupo, _base, areas, _trend, _amp) in CONTAS_DEF:
        for (centro_id, _n, area, _r, _p) in CENTROS_DEF:
            if areas == "ALL" or area in areas:
                pares.append((cid, centro_id))
    return pares


# ============================================================================
# 3) orcamento.csv + 4) lancamentos.csv
# ============================================================================
def gen_orcamento_lancamentos(pares):
    conta_idx = {c[0]: c for c in CONTAS_DEF}

    # Viés estrutural por par (conta×centro), sorteado UMA vez:
    #   - cada par desvia do orçado de forma consistente no tempo.
    bias_par = {}
    for (cid, centro) in pares:
        tipo = conta_idx[cid][2]
        if (cid, centro) in CRONICOS:
            bias_par[(cid, centro)] = random.uniform(0.15, 0.30)   # estouro crônico
        elif tipo == "Receita":
            bias_par[(cid, centro)] = random.gauss(0.015, 0.03)    # receita ~ no plano / leve alta
        elif tipo == "CAPEX":
            bias_par[(cid, centro)] = random.gauss(-0.02, 0.06)    # CAPEX costuma atrasar/subexecutar
        else:  # Despesa comum
            bias_par[(cid, centro)] = random.gauss(0.01, 0.03)

    orc_rows = []
    lanc_rows = []
    n_orc = 0
    n_lanc = 0

    for (cid, centro) in pares:
        _id, _nome, tipo, _grupo, base, _areas, trend, amp = conta_idx[cid]
        peso = CENTRO_PESO[centro]
        cron = (cid, centro) in CRONICOS

        for idx, mes in enumerate(MESES_ORC):
            # ---- Orçado: base × peso × tendência × sazonalidade × ruído leve
            fator_trend = (1.0 + trend) ** idx
            fator_saz = sazonal(mes, amp)
            ruido_orc = random.gauss(0.0, 0.015)
            valor_orc = base * peso * fator_trend * fator_saz * (1.0 + ruido_orc)
            valor_orc = max(0.0, valor_orc)

            n_orc += 1
            orc_rows.append({
                "id_orcamento": f"ORC{n_orc:06d}",
                "id_centro": centro,
                "id_conta": cid,
                "mes": mes.isoformat(),
                "valor_orcado": brl_cem(valor_orc),
            })

            # ---- Realizado: só nos meses fechados (histórico)
            if idx < N_MESES_HIST:
                bias = bias_par[(cid, centro)]
                if cron:
                    # estouro piora com o tempo (inflação/escopo)
                    bias = bias + 0.004 * idx
                ruido_mes = random.gauss(0.0, 0.025)
                fator_real = 1.0 + bias + ruido_mes
                valor_real = valor_orc * max(0.0, fator_real)

                n_lanc += 1
                lanc_rows.append({
                    "id_lancamento": f"LAN{n_lanc:06d}",
                    "id_centro": centro,
                    "id_conta": cid,
                    "mes": mes.isoformat(),
                    "valor_realizado": brl(valor_real),
                })

    return pd.DataFrame(orc_rows), pd.DataFrame(lanc_rows)


# ============================================================================
# Execução + validação/relatório
# ============================================================================
def main():
    centros = gen_centros()
    contas = gen_contas()
    pares = build_pares()
    orcamento, lancamentos = gen_orcamento_lancamentos(pares)

    arquivos = {
        "centros_custo.csv": centros,
        "contas_contabeis.csv": contas,
        "orcamento.csv": orcamento,
        "lancamentos.csv": lancamentos,
    }
    for nome, df in arquivos.items():
        df.to_csv(out(nome), index=False, encoding="utf-8")

    # ------------------------------------------------------------------
    print("=" * 72)
    print("DADOS GERADOS — Caso 2: Copiloto de FP&A (mineradora fictícia)")
    print("=" * 72)

    print("\n[1] Contagem de linhas:")
    for nome, df in arquivos.items():
        print(f"    {nome:<24} {len(df):>6} linhas")
    print(f"    pares ativos (conta x centro)        : {len(pares)}")
    print(f"    janela orçamento : {MESES_ORC[0].isoformat()} .. {MESES_ORC[-1].isoformat()} ({N_MESES_ORC} meses)")
    print(f"    janela realizado : {MESES_HIST[0].isoformat()} .. {MESES_HIST[-1].isoformat()} ({N_MESES_HIST} meses)")

    print("\n[2] Integridade referencial (esperado 0 órfãos):")
    set_centro = set(centros["id_centro"])
    set_conta = set(contas["id_conta"])
    orf_orc_centro = int((~orcamento["id_centro"].isin(set_centro)).sum())
    orf_orc_conta = int((~orcamento["id_conta"].isin(set_conta)).sum())
    orf_lanc_centro = int((~lancamentos["id_centro"].isin(set_centro)).sum())
    orf_lanc_conta = int((~lancamentos["id_conta"].isin(set_conta)).sum())
    print(f"    orcamento.id_centro sem centro       : {orf_orc_centro}")
    print(f"    orcamento.id_conta sem conta         : {orf_orc_conta}")
    print(f"    lancamentos.id_centro sem centro     : {orf_lanc_centro}")
    print(f"    lancamentos.id_conta sem conta       : {orf_lanc_conta}")

    # todo lançamento deve casar com uma linha de orçamento (mesmo centro/conta/mês)
    chave_orc = set(zip(orcamento["id_centro"], orcamento["id_conta"], orcamento["mes"]))
    chave_lanc = list(zip(lancamentos["id_centro"], lancamentos["id_conta"], lancamentos["mes"]))
    lanc_sem_orc = sum(1 for k in chave_lanc if k not in chave_orc)
    print(f"    lançamentos sem orçamento (chave)    : {lanc_sem_orc}")
    # chave única em cada fato?
    dup_orc = int(orcamento.duplicated(subset=["id_centro", "id_conta", "mes"]).sum())
    dup_lanc = int(lancamentos.duplicated(subset=["id_centro", "id_conta", "mes"]).sum())
    print(f"    orçamento: chaves duplicadas         : {dup_orc}")
    print(f"    realizado: chaves duplicadas         : {dup_lanc}")

    print("\n[3] Sinais de negócio embutidos:")
    # junta tipo da conta
    tipo_por_conta = dict(zip(contas["id_conta"], contas["tipo"]))
    orc = orcamento.copy()
    lanc = lancamentos.copy()
    orc["tipo"] = orc["id_conta"].map(tipo_por_conta)
    lanc["tipo"] = lanc["id_conta"].map(tipo_por_conta)

    receita_real = lanc[lanc["tipo"] == "Receita"]["valor_realizado"].sum()
    despesa_real = lanc[lanc["tipo"] == "Despesa"]["valor_realizado"].sum()
    capex_real = lanc[lanc["tipo"] == "CAPEX"]["valor_realizado"].sum()
    print(f"    receita realizada (hist.)            : R$ {receita_real/1e9:8.3f} bi")
    print(f"    despesa realizada (hist.)            : R$ {despesa_real/1e9:8.3f} bi")
    print(f"    CAPEX realizado (hist.)              : R$ {capex_real/1e9:8.3f} bi")
    print(f"    resultado (receita - despesa)        : R$ {(receita_real-despesa_real)/1e9:8.3f} bi (esperado > 0)")

    # variância global de despesa (realizado vs orçado nos meses fechados)
    j = orc.merge(
        lanc[["id_centro", "id_conta", "mes", "valor_realizado"]],
        on=["id_centro", "id_conta", "mes"], how="inner",
    )
    j["tipo"] = j["id_conta"].map(tipo_por_conta)
    desp = j[j["tipo"] == "Despesa"]
    var_desp = (desp["valor_realizado"].sum() - desp["valor_orcado"].sum()) / desp["valor_orcado"].sum() * 100
    print(f"    variância de DESPESA (realiz/orç)    : {var_desp:+.1f}%  (estouro médio)")
    rec = j[j["tipo"] == "Receita"]
    var_rec = (rec["valor_realizado"].sum() - rec["valor_orcado"].sum()) / rec["valor_orcado"].sum() * 100
    print(f"    variância de RECEITA (realiz/orç)    : {var_rec:+.1f}%")

    # nº de pares de despesa acima do orçamento (no acumulado)
    desp_par = desp.groupby(["id_conta", "id_centro"]).agg(
        orc=("valor_orcado", "sum"), real=("valor_realizado", "sum")).reset_index()
    desp_par["estouro"] = desp_par["real"] - desp_par["orc"]
    n_estouro = int((desp_par["estouro"] > 0).sum())
    print(f"    pares de despesa acima do orçamento  : {n_estouro} de {len(desp_par)}")

    print("\n    Top 5 estouros (conta × centro, acumulado):")
    nome_conta = dict(zip(contas["id_conta"], contas["nome"]))
    nome_centro = dict(zip(centros["id_centro"], centros["nome"]))
    top = desp_par.sort_values("estouro", ascending=False).head(5)
    for _, r in top.iterrows():
        pct = r["estouro"] / r["orc"] * 100
        print(f"      {nome_conta[r['id_conta']][:28]:<28} | {nome_centro[r['id_centro']][:22]:<22} "
              f"| +R$ {r['estouro']/1e6:6.2f} mi ({pct:+.0f}%)")

    print("\n[4] Prontidão para forecast (série mensal de receita realizada):")
    serie = lanc[lanc["tipo"] == "Receita"].groupby("mes")["valor_realizado"].sum()
    print(f"    pontos na série mensal               : {len(serie)} (>= 24 p/ ai_forecast)")
    print(f"    primeiro / último mês com realizado  : {serie.index.min()} / {serie.index.max()}")

    print("\n[5] Amostras (até 3 linhas por arquivo):")
    for nome, df in arquivos.items():
        print(f"\n--- {nome} ---")
        print(df.head(3).to_string(index=False))

    print("\n" + "=" * 72)
    print(f"OK — 4 CSVs gravados em: {OUTDIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
