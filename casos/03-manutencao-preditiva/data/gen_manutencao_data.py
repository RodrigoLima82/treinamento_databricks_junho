#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de dados sintéticos — Caso 3: Manutenção Preditiva de Ativos (uma mineradora).

Cria CSVs realistas (porém 100% fictícios) para o treinamento Databricks
Free Edition. Determinístico (seed=42) e re-executável (sobrescreve os arquivos).

Saída (no MESMO diretório deste script):
  - ativos.csv                      cadastro dos ativos monitorados
  - falhas.csv                      eventos de falha (com causa/componente/severidade)
  - ordens_manutencao.csv           ordens corretivas e preventivas (custo, downtime)
  - leituras_sensores_lote01.csv    telemetria — dias 1..30   (MAIOR volume)
  - leituras_sensores_lote02.csv    telemetria — dias 31..60
  - leituras_sensores_lote03.csv    telemetria — dias 61..90

A telemetria é dividida em 3 LOTES por janela de tempo para SIMULAR ingestão
incremental tipo streaming: sobe-se um lote por vez no Volume e o Auto Loader
(STREAMING TABLE) ingere só os arquivos novos. Ver runbook do caso.

Sinais embutidos (para o modelo de ML aprender):
  - Ativos críticos com VIBRAÇÃO e TEMPERATURA subindo (rampa) ANTES de uma falha.
  - Alguns ativos em DEGRADAÇÃO ATUAL (rampa até o fim da janela) e ainda SEM falha
    registrada — são os que o score de saúde / o modelo devem sinalizar a tempo.

Uso:
    pip install --quiet pandas faker numpy
    python3 gen_manutencao_data.py
"""

import os
import math
import random
from datetime import date, datetime, timedelta

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


# ----------------------------------------------------------------------------
# Parâmetros do domínio
# ----------------------------------------------------------------------------
SITES = ["Mina Norte", "Mina Sul", "Mina Central", "Mina Leste", "Mina Oeste", "Terminal Portuário"]

FABRICANTES = ["Metso", "Sandvik", "WEG", "Atlas Copco", "FLSmidth",
               "Weir Minerals", "Siemens", "Thyssenkrupp"]

CRITICIDADES = ["Alta", "Média", "Baixa"]

# Tipo de ativo -> baselines de sensor (temperatura °C, vibração mm/s, pressão bar, rotação rpm)
# e prefixo de tag.
TIPOS = {
    "Bomba de polpa":         dict(temp=55, vib=3.5, pres=5.0, rpm=1450, tag="BP"),
    "Motor elétrico":         dict(temp=65, vib=2.5, pres=1.5, rpm=1780, tag="ME"),
    "Britador de mandíbula":  dict(temp=60, vib=6.0, pres=2.0, rpm=300,  tag="BR"),
    "Correia transportadora": dict(temp=42, vib=1.8, pres=1.2, rpm=90,   tag="CT"),
    "Compressor de ar":       dict(temp=72, vib=3.2, pres=8.0, rpm=1200, tag="CP"),
    "Peneira vibratória":     dict(temp=48, vib=7.5, pres=1.0, rpm=1000, tag="PV"),
    "Moinho de bolas":        dict(temp=68, vib=5.0, pres=2.5, rpm=18,   tag="MO"),
    "Ventilador industrial":  dict(temp=50, vib=3.0, pres=1.8, rpm=1100, tag="VE"),
}
TIPOS_LIST = list(TIPOS.keys())

N_ATIVOS = 40

# Janela de telemetria
DATA_FIM = date(2026, 6, 22)
WINDOW_DIAS = 90
HORAS = [0, 3, 6, 9, 12, 15, 18, 21]            # 8 leituras/dia (a cada 3h)
START_DT = datetime.combine(DATA_FIM, datetime.min.time()) - timedelta(days=WINDOW_DIAS - 1)

# Linha do tempo de leituras (compartilhada por todos os ativos)
TS = [START_DT + timedelta(days=d, hours=h) for d in range(WINDOW_DIAS) for h in HORAS]
N_TS = len(TS)                                   # 90 * 8 = 720 por ativo
TS_DIAS = np.array([(t - START_DT).total_seconds() / 86400.0 for t in TS])
TS_HORA = np.array([t.hour for t in TS])

RAMP_DIAS = 12                                   # duração da rampa de degradação antes da falha

# --- Quem falha (histórico) e quem está degradando agora -------------------
# Falhas registradas: ativo -> lista de dias (offset desde START_DT) em que falhou.
# Alguns ativos falham 2x (para o MTBF ter intervalo real entre falhas).
FALHAS_SPEC = {
    "ATV001": [28, 74],   # 2 falhas (MTBF ~46 dias)
    "ATV004": [52],
    "ATV007": [33, 79],   # 2 falhas (MTBF ~46 dias)
    "ATV010": [61],
    "ATV013": [26, 68],   # 2 falhas (MTBF ~42 dias)
    "ATV016": [45],
    "ATV019": [71],
    "ATV022": [30, 76],   # 2 falhas (MTBF ~46 dias)
    "ATV025": [57],
    "ATV028": [40],
}
# Ativos em degradação ATUAL (rampa até o fim da janela), ainda SEM falha registrada.
# Severidades variadas → score de saúde com mix Crítico/Atenção (não tudo no extremo).
# id_ativo -> (fator_vibracao, fator_temperatura)
ONGOING = {
    "ATV031": (2.2, 0.50),   # forte -> Crítico
    "ATV034": (1.6, 0.42),   # forte -> Crítico
    "ATV037": (1.0, 0.32),   # leve  -> Atenção
    "ATV040": (0.8, 0.28),   # leve  -> Atenção
}
# Todos os ativos-problema recebem criticidade Alta (narrativa).
ATIVOS_CRITICOS = set(FALHAS_SPEC.keys()) | set(ONGOING.keys())

CAUSA_COMPONENTE = [
    ("Desgaste de rolamento", "Rolamento"),
    ("Superaquecimento", "Motor"),
    ("Falha de lubrificação", "Mancal"),
    ("Desalinhamento de eixo", "Eixo"),
    ("Cavitação", "Impelidor"),
    ("Fadiga de material", "Estrutura"),
    ("Falha elétrica", "Bobina"),
    ("Obstrução de selo", "Selo mecânico"),
]


# ============================================================================
# 1) ativos.csv
# ============================================================================
def gen_ativos() -> pd.DataFrame:
    rows = []
    contador_tag = {k: 0 for k in TIPOS}
    for i in range(1, N_ATIVOS + 1):
        aid = f"ATV{i:03d}"
        tipo = TIPOS_LIST[(i - 1) % len(TIPOS_LIST)]   # distribui os tipos de forma equilibrada
        contador_tag[tipo] += 1
        tag = f"{TIPOS[tipo]['tag']}-{contador_tag[tipo]:03d}"
        if aid in ATIVOS_CRITICOS:
            criticidade = "Alta"
        else:
            criticidade = random.choices(CRITICIDADES, weights=[0.25, 0.45, 0.30])[0]
        ano = random.randint(2012, 2023)
        instal = date(ano, random.randint(1, 12), random.randint(1, 28))
        rows.append({
            "id_ativo": aid,
            "tag": tag,
            "tipo": tipo,
            "fabricante": random.choice(FABRICANTES),
            "modelo": fake.bothify("??-####").upper(),
            "site": random.choice(SITES),
            "criticidade": criticidade,
            "data_instalacao": instal.isoformat(),
            "potencia_kw": int(random.choice([75, 110, 150, 220, 300, 450, 600, 900, 1200])),
        })
    return pd.DataFrame(rows)


# ============================================================================
# 2) falhas.csv  (+ eventos de degradação para a telemetria)
# ============================================================================
def gen_falhas():
    rows = []
    fid = 0
    # deg_events: id_ativo -> lista de (dia_pico, ramp_dias, fator_vib, fator_temp)
    deg_events = {}

    for aid, dias in FALHAS_SPEC.items():
        for d in dias:
            fid += 1
            dt = (START_DT + timedelta(days=d)).date()
            causa, comp = random.choice(CAUSA_COMPONENTE)
            sev = random.choices(["Alta", "Média", "Baixa"], weights=[0.40, 0.40, 0.20])[0]
            rows.append({
                "id_falha": f"FAL{fid:04d}",
                "id_ativo": aid,
                "data_falha": dt.isoformat(),
                "causa": causa,
                "componente": comp,
                "severidade": sev,
            })
            # rampa de degradação que ANTECEDE essa falha (quanto maior a severidade, maior a subida)
            if sev == "Alta":
                fv, ft = random.uniform(1.6, 2.2), random.uniform(0.45, 0.65)
            elif sev == "Média":
                fv, ft = random.uniform(1.1, 1.6), random.uniform(0.30, 0.45)
            else:
                fv, ft = random.uniform(0.7, 1.1), random.uniform(0.20, 0.32)
            deg_events.setdefault(aid, []).append((float(d), RAMP_DIAS, fv, ft))

    falhas = pd.DataFrame(rows)

    # Ativos em degradação atual: rampa termina no fim da janela, SEM falha registrada.
    for aid, (fv, ft) in ONGOING.items():
        deg_events.setdefault(aid, []).append((float(WINDOW_DIAS), 14, fv, ft))

    return falhas, deg_events


# ============================================================================
# 3) ordens_manutencao.csv  (corretivas: 1 por falha; preventivas: agendadas)
# ============================================================================
def gen_ordens(ativos: pd.DataFrame, falhas: pd.DataFrame) -> pd.DataFrame:
    rows = []
    oid = 0

    # --- Corretivas: uma por falha (abre no dia da falha, custo/downtime ~ severidade)
    for _, f in falhas.iterrows():
        oid += 1
        abertura = date.fromisoformat(f["data_falha"]) + timedelta(days=random.randint(0, 1))
        sev = f["severidade"]
        if sev == "Alta":
            downtime = random.uniform(24, 96)
            custo = random.uniform(80_000, 350_000)
        elif sev == "Média":
            downtime = random.uniform(8, 36)
            custo = random.uniform(30_000, 120_000)
        else:
            downtime = random.uniform(4, 16)
            custo = random.uniform(15_000, 45_000)
        fechamento = abertura + timedelta(days=max(1, round(downtime / 24)))
        rows.append({
            "id_ordem": f"OM{oid:05d}",
            "id_ativo": f["id_ativo"],
            "tipo": "Corretiva",
            "data_abertura": abertura.isoformat(),
            "data_fechamento": fechamento.isoformat(),
            "custo": brl(custo),
            "downtime_horas": round(downtime, 1),
            "descricao": f"Reparo corretivo - {f['causa'].lower()}",
        })

    # --- Preventivas: 1 a 3 por ativo, espalhadas na janela (baixo custo/downtime)
    for _, a in ativos.iterrows():
        n_prev = random.choice([1, 2, 2, 3])
        dias = sorted(random.sample(range(5, WINDOW_DIAS - 2), n_prev))
        for d in dias:
            oid += 1
            abertura = (START_DT + timedelta(days=d)).date()
            downtime = random.uniform(2, 10)
            custo = random.uniform(2_000, 28_000)
            fechamento = abertura + timedelta(days=1)
            rows.append({
                "id_ordem": f"OM{oid:05d}",
                "id_ativo": a["id_ativo"],
                "tipo": "Preventiva",
                "data_abertura": abertura.isoformat(),
                "data_fechamento": fechamento.isoformat(),
                "custo": brl(custo),
                "downtime_horas": round(downtime, 1),
                "descricao": "Manutenção preventiva programada",
            })

    return pd.DataFrame(rows)


# ============================================================================
# 4) leituras_sensores  (telemetria — maior volume, vetorizado por ativo)
# ============================================================================
def gen_leituras(ativos: pd.DataFrame, deg_events: dict) -> pd.DataFrame:
    daily = np.sin(2 * np.pi * (TS_HORA - 15) / 24.0)    # ciclo diário (pico ~15h)
    rows = []
    leitura_id = 0

    for _, a in ativos.iterrows():
        prof = TIPOS[a["tipo"]]
        tb, vb, pb, rb = prof["temp"], prof["vib"], prof["pres"], prof["rpm"]

        # operação normal: baseline + ciclo diário (só na temperatura) + ruído gaussiano
        temp = tb + 0.06 * tb * daily + np.random.normal(0, 0.03 * tb, N_TS)
        vib = vb + np.random.normal(0, 0.10 * vb, N_TS)
        pres = pb + np.random.normal(0, 0.07 * pb, N_TS)
        rpm = rb + np.random.normal(0, 0.02 * rb, N_TS)

        # rampas de degradação (antecedem falhas / degradação atual)
        for (dia_pico, ramp_dias, fv, ft) in deg_events.get(a["id_ativo"], []):
            inicio = dia_pico - ramp_dias
            mask = (TS_DIAS >= inicio) & (TS_DIAS <= dia_pico)
            prog = np.zeros(N_TS)
            prog[mask] = (TS_DIAS[mask] - inicio) / ramp_dias        # 0..1
            ramp = prog ** 1.5                                       # sobe mais forte perto da falha
            vib = vib + fv * vb * ramp
            temp = temp + ft * tb * ramp
            pres = pres + 0.15 * pb * ramp
            rpm = rpm - 0.05 * rb * ramp                            # rotação cai levemente sob estresse

        temp = np.clip(temp, 0, None)
        vib = np.clip(vib, 0.05, None)
        pres = np.clip(pres, 0.0, None)
        rpm = np.clip(rpm, 0.0, None)

        for k in range(N_TS):
            leitura_id += 1
            rows.append({
                "id_leitura": f"LE{leitura_id:07d}",
                "id_ativo": a["id_ativo"],
                "data_hora": TS[k].strftime("%Y-%m-%d %H:%M:%S"),
                "temperatura": round(float(temp[k]), 1),
                "vibracao": round(float(vib[k]), 2),
                "pressao": round(float(pres[k]), 2),
                "rpm": int(round(float(rpm[k]))),
                "_dia": int(TS_DIAS[k]),
            })

    return pd.DataFrame(rows)


# ============================================================================
# Execução
# ============================================================================
def main():
    ativos = gen_ativos()
    falhas, deg_events = gen_falhas()
    ordens = gen_ordens(ativos, falhas)
    leituras = gen_leituras(ativos, deg_events)

    # ---- divide a telemetria em 3 lotes por janela de tempo (simula streaming)
    lote01 = leituras[leituras["_dia"] < 30].drop(columns="_dia")
    lote02 = leituras[(leituras["_dia"] >= 30) & (leituras["_dia"] < 60)].drop(columns="_dia")
    lote03 = leituras[leituras["_dia"] >= 60].drop(columns="_dia")
    leituras_full = leituras.drop(columns="_dia")

    # ---- grava CSVs (UTF-8, com header)
    arquivos = {
        "ativos.csv": ativos,
        "falhas.csv": falhas,
        "ordens_manutencao.csv": ordens,
        "leituras_sensores_lote01.csv": lote01,
        "leituras_sensores_lote02.csv": lote02,
        "leituras_sensores_lote03.csv": lote03,
    }
    for nome, df in arquivos.items():
        df.to_csv(out(nome), index=False, encoding="utf-8")

    # ------------------------------------------------------------------
    # VALIDAÇÃO + RELATÓRIO
    # ------------------------------------------------------------------
    print("=" * 72)
    print("DADOS GERADOS — Caso 3: Manutenção Preditiva de Ativos (uma mineradora)")
    print("=" * 72)

    print("\n[1] Contagem de linhas:")
    for nome, df in arquivos.items():
        print(f"    {nome:<32} {len(df):>7} linhas")
    print(f"    {'(telemetria total)':<32} {len(leituras_full):>7} linhas")

    print("\n[2] Integridade referencial (orfaos = 0 esperado):")
    set_ativos = set(ativos["id_ativo"])
    orf_leit = int((~leituras_full["id_ativo"].isin(set_ativos)).sum())
    orf_falha = int((~falhas["id_ativo"].isin(set_ativos)).sum())
    orf_ordem = int((~ordens["id_ativo"].isin(set_ativos)).sum())
    print(f"    leituras.id_ativo sem ativo          : {orf_leit}")
    print(f"    falhas.id_ativo sem ativo            : {orf_falha}")
    print(f"    ordens.id_ativo sem ativo            : {orf_ordem}")
    dup_leit = int(leituras_full.duplicated(subset=["id_ativo", "data_hora"]).sum())
    print(f"    leituras duplicadas (ativo,data_hora): {dup_leit}")

    print("\n[3] Cobertura / distribuicoes:")
    print(f"    ativos                               : {len(ativos)}")
    print(f"    ativos por tipo                      : {ativos['tipo'].nunique()} tipos")
    print(f"    ativos criticidade Alta              : {(ativos['criticidade']=='Alta').sum()}")
    print(f"    falhas registradas                   : {len(falhas)}")
    print(f"    ativos com >=1 falha                 : {falhas['id_ativo'].nunique()}")
    print(f"    ativos com 2 falhas (p/ MTBF)        : {(falhas['id_ativo'].value_counts()==2).sum()}")
    n_corr = int((ordens['tipo'] == 'Corretiva').sum())
    n_prev = int((ordens['tipo'] == 'Preventiva').sum())
    print(f"    ordens corretivas / preventivas      : {n_corr} / {n_prev}")
    print(f"    custo total manutencao (BRL)         : {ordens['custo'].sum():,.2f}")

    print("\n[4] Sinal de degradacao (telemetria):")
    leituras_full["_dia"] = leituras["_dia"].values    # reaproveita o offset de dia para o relatório
    # média de vibração normal (ativos sem evento) vs janela pré-falha
    sem_evento = [a for a in set_ativos if a not in deg_events]
    vib_normal = leituras_full[leituras_full["id_ativo"].isin(sem_evento)]["vibracao"].mean()
    print(f"    vibracao media (ativos sem evento)   : {vib_normal:.2f} mm/s")
    # para cada falha, compara vib na janela [pico-RAMP, pico] vs baseline do ativo
    exemplos = 0
    for aid, evs in deg_events.items():
        for (dia_pico, ramp_dias, fv, ft) in evs:
            sub = leituras_full[leituras_full["id_ativo"] == aid]
            base_mask = (sub["_dia"] < (dia_pico - ramp_dias))
            ramp_mask = (sub["_dia"] >= (dia_pico - ramp_dias)) & (sub["_dia"] <= dia_pico)
            if base_mask.sum() == 0 or ramp_mask.sum() == 0:
                continue
            vib_base = sub[base_mask]["vibracao"].mean()
            vib_ramp = sub[ramp_mask]["vibracao"].mean()
            if exemplos < 4:
                marca = "(degradacao atual)" if dia_pico >= WINDOW_DIAS else f"(falha dia {int(dia_pico)})"
                print(f"      {aid} {marca:<20} vib baseline {vib_base:5.2f} -> pre-evento {vib_ramp:5.2f} "
                      f"({vib_ramp/vib_base*100-100:+.0f}%)")
                exemplos += 1
    leituras_full.drop(columns="_dia", inplace=True)

    print("\n[5] Amostras (ate 3 linhas por arquivo):")
    for nome, df in arquivos.items():
        print(f"\n--- {nome} ---")
        print(df.head(3).to_string(index=False))

    print("\n" + "=" * 72)
    print(f"OK — {len(arquivos)} CSVs gravados em: {OUTDIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
