#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de dados sintéticos — Caso 1: Torre de Controle de Suprimentos (uma mineradora).

Cria 6 CSVs realistas (porém 100% fictícios) para o treinamento Databricks
Free Edition. Determinístico (seed=42) e re-executável (sobrescreve os arquivos).

Uso:
    pip install --quiet pandas faker
    python3 gen_suprimentos_data.py

Os CSVs são gravados no MESMO diretório deste script.
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


def out(name: str) -> str:
    return os.path.join(OUTDIR, name)


def brl(x) -> float:
    """Arredonda para 2 casas (centavos)."""
    return float(round(float(x), 2))


# ----------------------------------------------------------------------------
# Parâmetros do domínio
# ----------------------------------------------------------------------------
CENTROS = ["Mina Norte", "Mina Sul", "Mina Central", "Mina Leste", "Mina Oeste", "Terminal Portuário"]

# UFs onde a uma mineradora tem operações relevantes (peso maior para MG/PA/ES)
UFS = ["MG", "PA", "ES", "MG", "PA", "RJ", "SP", "BA", "MA", "MG", "PA", "SC", "PR", "RS"]

# 12 categorias fixas (nome -> tipo)
CATEGORIAS = [
    ("Peças de britador", "MRO"),
    ("Correias transportadoras", "MRO"),
    ("Lubrificantes e fluidos", "MRO"),
    ("EPI", "MRO"),
    ("Pneus OTR", "MRO"),
    ("Explosivos e acessórios", "MRO"),
    ("Serviços de manutenção", "Serviço"),
    ("Material elétrico", "MRO"),
    ("Bombas e válvulas", "MRO"),
    ("Equipamentos de perfuração", "CAPEX"),
    ("Refratários", "MRO"),
    ("Serviços de transporte", "Serviço"),
]
CAT_IDS = [f"CAT{i:02d}" for i in range(1, len(CATEGORIAS) + 1)]
CAT_NOME_TO_ID = {nome: cid for cid, (nome, _) in zip(CAT_IDS, CATEGORIAS)}
CAT_BRITADOR = CAT_NOME_TO_ID["Peças de britador"]  # CAT01

# Perfil por categoria: (qtd_min, qtd_max, preco_min, preco_max, [descrições])
CAT_PERFIL = {
    "Peças de britador": (1, 8, 8000, 60000, [
        "Mandíbula fixa para britador", "Manta de revestimento de britador",
        "Cone de britagem", "Rolamento de britador",
        "Eixo principal de britador", "Placa de desgaste do britador",
    ]),
    "Correias transportadoras": (1, 12, 1500, 25000, [
        "Correia transportadora EP630 3 lonas", "Rolete de carga",
        "Tambor de acionamento", "Emenda de correia vulcanizada",
        "Raspador de correia primário",
    ]),
    "Lubrificantes e fluidos": (5, 200, 25, 900, [
        "Óleo hidráulico ISO VG 68", "Graxa de lítio EP2",
        "Óleo de engrenagem ISO 320", "Fluido refrigerante concentrado",
        "Óleo de motor 15W40",
    ]),
    "EPI": (10, 500, 8, 350, [
        "Capacete de segurança classe B", "Luva de raspa de couro",
        "Protetor auricular tipo plug", "Óculos de segurança ampla visão",
        "Bota de segurança com biqueira", "Respirador semifacial",
    ]),
    "Pneus OTR": (1, 6, 18000, 90000, [
        "Pneu OTR 27.00R49", "Pneu OTR 40.00R57",
        "Câmara de ar para pneu OTR", "Protetor de pneu OTR",
    ]),
    "Explosivos e acessórios": (10, 400, 12, 600, [
        "Emulsão explosiva bombeada", "Cordel detonante 10g/m",
        "Espoleta eletrônica", "Booster 450g", "Estopim de segurança",
    ]),
    "Serviços de manutenção": (1, 4, 5000, 120000, [
        "Serviço de manutenção preventiva de britador", "Reforma de redutor industrial",
        "Inspeção preditiva por análise de vibração", "Serviço de solda especializada",
        "Manutenção corretiva de bomba de polpa",
    ]),
    "Material elétrico": (1, 30, 200, 45000, [
        "Cabo de potência 0,6/1kV 240mm²", "Disjuntor caixa moldada 400A",
        "Motor elétrico 250cv", "Inversor de frequência 75kW",
        "Transformador a seco 500kVA",
    ]),
    "Bombas e válvulas": (1, 10, 2500, 70000, [
        "Bomba de polpa 8/6", "Válvula gaveta 12\"",
        "Bomba centrífuga multiestágio", "Válvula borboleta 24\"",
        "Selo mecânico para bomba de polpa",
    ]),
    "Equipamentos de perfuração": (1, 3, 80000, 1200000, [
        "Perfuratriz hidráulica de superfície", "Haste de perfuração T45",
        "Bit de perfuração 4 1/2\"", "Compressor para perfuração",
        "Punho de perfuração",
    ]),
    "Refratários": (5, 150, 80, 2500, [
        "Tijolo refratário sílico-aluminoso", "Concreto refratário denso",
        "Massa de socaria refratária", "Argamassa refratária",
        "Bloco refratário magnesiano",
    ]),
    "Serviços de transporte": (1, 5, 4000, 80000, [
        "Frete rodoviário de minério", "Transporte de equipamento pesado",
        "Serviço de movimentação logística interna", "Frete de cargas indivisíveis",
        "Locação de caminhão fora de estrada",
    ]),
}

CRITICIDADES = ["Alta", "Média", "Baixa"]

N_FORNECEDORES = 60
N_UNICOS = 4
N_CONTRATOS = 30
N_PEDIDOS = 800

DATA_INI = date(2025, 6, 22)
DATA_FIM = date(2026, 6, 22)
SPAN_DIAS = (DATA_FIM - DATA_INI).days

# preenchido em main(); usado por gen_recebimentos
FORN_PRAZO = {}


# ============================================================================
# 1) categorias_compra.csv
# ============================================================================
def gen_categorias() -> pd.DataFrame:
    rows = []
    for cid, (nome, tipo) in zip(CAT_IDS, CATEGORIAS):
        rows.append({"id_categoria": cid, "nome": nome, "tipo": tipo})
    return pd.DataFrame(rows)


# ============================================================================
# 2) fornecedores.csv
# ============================================================================
def gen_fornecedores() -> pd.DataFrame:
    nomes_outras_categorias = [n for (n, _) in CATEGORIAS if n != "Peças de britador"]
    rows = []
    for i in range(1, N_FORNECEDORES + 1):
        fid = f"FOR{i:04d}"
        unico = i <= N_UNICOS  # os 4 primeiros são fornecedores únicos
        if unico:
            categoria = "Peças de britador"
            criticidade = "Alta"
            rating = round(random.uniform(4.0, 5.0), 1)
            prazo = random.randint(20, 55)
        else:
            categoria = random.choice(nomes_outras_categorias)
            criticidade = random.choices(CRITICIDADES, weights=[0.25, 0.45, 0.30])[0]
            rating = round(random.uniform(2.5, 5.0), 1)
            prazo = random.randint(5, 60)
        rows.append({
            "id_fornecedor": fid,
            "razao_social": fake.company(),
            "cnpj": fake.cnpj(),
            "categoria_principal": categoria,
            "uf": random.choice(UFS),
            "criticidade": criticidade,
            "rating": rating,
            "prazo_medio_dias": prazo,
            "fornecedor_unico": bool(unico),
        })
    return pd.DataFrame(rows)


# ============================================================================
# 3) contratos.csv
# ============================================================================
def gen_contratos(fornecedores: pd.DataFrame):
    fids = fornecedores["id_fornecedor"].tolist()
    unicos = fids[:N_UNICOS]
    # Garante contrato para todos os fornecedores únicos; demais sorteados.
    outros = [f for f in fids if f not in unicos]
    random.shuffle(outros)
    donos = list(unicos) + outros[: (N_CONTRATOS - len(unicos))]
    # Se sobrarem contratos, repete alguns donos (fornecedor com >1 contrato)
    while len(donos) < N_CONTRATOS:
        donos.append(random.choice(fids))
    random.shuffle(donos)

    rows = []
    contratos_por_forn = {}
    for i in range(1, N_CONTRATOS + 1):
        cid = f"CT{i:03d}"
        dono = donos[i - 1]
        valor = brl(random.uniform(200_000, 6_000_000))
        saldo = brl(valor * random.uniform(0.05, 0.85))  # saldo <= valor_contratado
        inicio = date(2024, 1, 1) + timedelta(days=random.randint(0, 450))
        fim = inicio + timedelta(days=random.choice([365, 540, 730, 1095]))
        rows.append({
            "contrato_id": cid,
            "id_fornecedor": dono,
            "valor_contratado": valor,
            "vigencia_inicio": inicio.isoformat(),
            "vigencia_fim": fim.isoformat(),
            "saldo": saldo,
        })
        contratos_por_forn.setdefault(dono, []).append(cid)

    return pd.DataFrame(rows), contratos_por_forn


# ============================================================================
# 4 + 5) pedidos_compra.csv + itens_pedido.csv
# ============================================================================
def gen_pedidos_itens(fornecedores: pd.DataFrame, contratos_por_forn: dict):
    fids = fornecedores["id_fornecedor"].tolist()
    unicos = fids[:N_UNICOS]
    forn_idx = {r["id_fornecedor"]: r for _, r in fornecedores.iterrows()}
    contratados = list(contratos_por_forn.keys())

    pedidos_rows = []
    itens_rows = []

    status_opts = ["Aberto", "Aprovado", "Recebido", "Cancelado"]
    status_w = [0.15, 0.20, 0.55, 0.10]  # ~10% Cancelado -> ~720 recebimentos

    for i in range(1, N_PEDIDOS + 1):
        pid = f"PC{i:06d}"

        # ---- Tipo do pedido: concentra gasto dos únicos em "Peças de britador"
        is_unico_britador = random.random() < 0.15
        if is_unico_britador:
            forn = random.choice(unicos)
            cat_nome = "Peças de britador"
            # único quase sempre opera dentro de contrato
            in_contract = random.random() < 0.70
        else:
            in_contract = random.random() < 0.70
            if in_contract and contratados:
                forn = random.choice(contratados)
            else:
                forn = random.choice(fids)
            # categoria: 75% a principal do fornecedor, 25% aleatória
            if random.random() < 0.75:
                cat_nome = forn_idx[forn]["categoria_principal"]
            else:
                cat_nome = random.choice([n for (n, _) in CATEGORIAS])

        cat_id = CAT_NOME_TO_ID[cat_nome]

        # ---- contrato_id (~70% preenchido; integridade: mesmo fornecedor)
        contrato_id = ""
        if in_contract and forn in contratos_por_forn:
            contrato_id = random.choice(contratos_por_forn[forn])

        # ---- itens do pedido (1-5)
        n_itens = random.randint(1, 5)
        if is_unico_britador:
            n_itens = random.randint(2, 5)  # pedidos maiores -> mais gasto
        qmin, qmax, pmin, pmax, descs = CAT_PERFIL[cat_nome]

        valor_total = 0.0
        for j in range(1, n_itens + 1):
            qtd = random.randint(qmin, qmax)
            baseline = brl(random.uniform(pmin, pmax))
            # ~40% com saving (preco_unitario < baseline); ~60% >= baseline
            if random.random() < 0.40:
                preco_unit = brl(baseline * (1 - random.uniform(0.02, 0.15)))
            else:
                preco_unit = brl(baseline * (1 + random.uniform(0.0, 0.12)))
            valor_total += preco_unit * qtd
            itens_rows.append({
                "id_pedido": pid,
                "id_item": j,
                "descricao": random.choice(descs),
                "qtd": qtd,
                "preco_unitario": preco_unit,
                "preco_baseline": baseline,
            })

        # ---- cabeçalho do pedido
        data_pedido = DATA_INI + timedelta(days=random.randint(0, SPAN_DIAS))
        status = random.choices(status_opts, weights=status_w)[0]

        pedidos_rows.append({
            "id_pedido": pid,
            "id_fornecedor": forn,
            "id_categoria": cat_id,
            "data_pedido": data_pedido.isoformat(),
            "centro": random.choice(CENTROS),
            "valor_total": brl(valor_total),
            "status": status,
            "contrato_id": contrato_id,
        })

    pedidos = pd.DataFrame(pedidos_rows)
    itens = pd.DataFrame(itens_rows)
    return pedidos, itens


# ============================================================================
# 6) recebimentos.csv  (um por pedido NÃO-Cancelado)
# ============================================================================
def gen_recebimentos(pedidos: pd.DataFrame, itens: pd.DataFrame):
    qtd_por_pedido = itens.groupby("id_pedido")["qtd"].sum().to_dict()

    rows = []
    for _, p in pedidos.iterrows():
        if p["status"] == "Cancelado":
            continue
        pid = p["id_pedido"]
        data_pedido = date.fromisoformat(p["data_pedido"])
        total_qtd = int(qtd_por_pedido.get(pid, 0))

        # data_prometida = data_pedido + prazo do fornecedor (com ruído)
        prazo = int(FORN_PRAZO.get(p["id_fornecedor"], 30))
        prazo = max(3, prazo + random.randint(-5, 10))
        data_prometida = data_pedido + timedelta(days=prazo)

        if p["status"] == "Recebido":
            # ~22% atrasadas (data_recebida > data_prometida)
            if random.random() < 0.22:
                atraso = random.randint(1, 30)
            else:
                atraso = random.randint(-7, 0)
            data_recebida = (data_prometida + timedelta(days=atraso)).isoformat()
            # maioria recebe completo; ~12% recebimento parcial
            if random.random() < 0.12:
                qtd_receb = max(1, int(total_qtd * random.uniform(0.5, 0.95)))
            else:
                qtd_receb = total_qtd
            ok = random.random() < 0.90  # ~10% reprova qualidade
        else:
            data_recebida = ""       # Aberto/Aprovado: ainda não recebido
            qtd_receb = 0
            ok = True                # sem inspeção ainda

        rows.append({
            "id_pedido": pid,
            "data_prometida": data_prometida.isoformat(),
            "data_recebida": data_recebida,
            "qtd_recebida": qtd_receb,
            "ok_qualidade": bool(ok),
        })

    return pd.DataFrame(rows)


# ============================================================================
# Execução
# ============================================================================
def main():
    global FORN_PRAZO

    categorias = gen_categorias()
    fornecedores = gen_fornecedores()

    # prazo por fornecedor (usado nos recebimentos)
    FORN_PRAZO = dict(zip(fornecedores["id_fornecedor"], fornecedores["prazo_medio_dias"]))

    contratos, contratos_por_forn = gen_contratos(fornecedores)
    pedidos, itens = gen_pedidos_itens(fornecedores, contratos_por_forn)
    recebimentos = gen_recebimentos(pedidos, itens)

    # ---- grava CSVs (UTF-8, com header)
    arquivos = {
        "fornecedores.csv": fornecedores,
        "categorias_compra.csv": categorias,
        "contratos.csv": contratos,
        "pedidos_compra.csv": pedidos,
        "itens_pedido.csv": itens,
        "recebimentos.csv": recebimentos,
    }
    for nome, df in arquivos.items():
        df.to_csv(out(nome), index=False, encoding="utf-8")

    # ------------------------------------------------------------------
    # VALIDAÇÃO + RELATÓRIO
    # ------------------------------------------------------------------
    print("=" * 70)
    print("DADOS GERADOS — Caso 1: Torre de Controle de Suprimentos (uma mineradora)")
    print("=" * 70)

    print("\n[1] Contagem de linhas:")
    for nome, df in arquivos.items():
        print(f"    {nome:<24} {len(df):>6} linhas")

    print("\n[2] Integridade referencial (orfaos = 0 e o esperado):")
    set_forn = set(fornecedores["id_fornecedor"])
    set_cat = set(categorias["id_categoria"])
    set_contr = set(contratos["contrato_id"])
    set_ped = set(pedidos["id_pedido"])

    orf_ped_forn = int((~pedidos["id_fornecedor"].isin(set_forn)).sum())
    orf_ped_cat = int((~pedidos["id_categoria"].isin(set_cat)).sum())
    ped_com_contr = pedidos[pedidos["contrato_id"] != ""]
    orf_ped_contr = int((~ped_com_contr["contrato_id"].isin(set_contr)).sum())
    orf_contr_forn = int((~contratos["id_fornecedor"].isin(set_forn)).sum())
    orf_itens_ped = int((~itens["id_pedido"].isin(set_ped)).sum())
    orf_receb_ped = int((~recebimentos["id_pedido"].isin(set_ped)).sum())

    print(f"    pedidos.id_fornecedor sem fornecedor : {orf_ped_forn}")
    print(f"    pedidos.id_categoria sem categoria   : {orf_ped_cat}")
    print(f"    pedidos.contrato_id sem contrato     : {orf_ped_contr}")
    print(f"    contratos.id_fornecedor sem forn.    : {orf_contr_forn}")
    print(f"    itens.id_pedido sem pedido           : {orf_itens_ped}")
    print(f"    recebimentos.id_pedido sem pedido    : {orf_receb_ped}")

    # valor_total == soma dos itens
    soma_itens = (itens["preco_unitario"] * itens["qtd"]).groupby(itens["id_pedido"]).sum()
    check = pedidos.set_index("id_pedido")["valor_total"].sub(soma_itens.round(2)).abs()
    max_diff = float(check.max())
    print(f"    max |valor_total - soma_itens|       : {max_diff:.4f} (esperado ~0)")

    print("\n[3] Verificacao dos sinais de negocio:")
    rec_receb = recebimentos[recebimentos["data_recebida"] != ""].copy()
    rec_receb["atraso"] = (
        pd.to_datetime(rec_receb["data_recebida"]) - pd.to_datetime(rec_receb["data_prometida"])
    ).dt.days
    pct_atraso = (rec_receb["atraso"] > 0).mean() * 100
    otif = ((rec_receb["atraso"] <= 0) & (rec_receb["ok_qualidade"])).mean() * 100
    print(f"    entregas atrasadas (Recebido)        : {pct_atraso:.1f}%  (alvo 20-25%)")
    print(f"    OTIF (no prazo & qualidade)          : {otif:.1f}%")

    pct_saving = (itens["preco_unitario"] < itens["preco_baseline"]).mean() * 100
    print(f"    itens com saving (preco<baseline)    : {pct_saving:.1f}%  (alvo ~40%)")

    pct_fora = (pedidos["contrato_id"] == "").mean() * 100
    print(f"    pedidos fora de contrato (vazio)     : {pct_fora:.1f}%  (alvo ~30%)")

    unicos = set(fornecedores[fornecedores["fornecedor_unico"]]["id_fornecedor"])
    gasto_total = pedidos["valor_total"].sum()
    gasto_unicos = pedidos[pedidos["id_fornecedor"].isin(unicos)]["valor_total"].sum()
    gasto_brit = pedidos[pedidos["id_categoria"] == CAT_BRITADOR]["valor_total"].sum()
    print(f"    no de fornecedores unicos            : {len(unicos)}")
    print(f"    gasto dos unicos / gasto total       : {gasto_unicos/gasto_total*100:.1f}%")
    print(f"    gasto em 'Pecas de britador' / total : {gasto_brit/gasto_total*100:.1f}%")

    print("\n[4] Amostras (ate 3 linhas por arquivo):")
    for nome, df in arquivos.items():
        print(f"\n--- {nome} ---")
        print(df.head(3).to_string(index=False))

    print("\n" + "=" * 70)
    print(f"OK — 6 CSVs gravados em: {OUTDIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
