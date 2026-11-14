# @module services.inss_obra.motor — Simulação da aferição indireta de obra predial (SERO).
#
# Reproduz a ORDEM do Capítulo III do Manual do SERO v3.0:
#   áreas → equivalência/redução → custo da obra por destinação (COD = área × VAU)
#   → RMT = COD × % mão de obra × % categoria × % destinação × fator social (PF)
#   → RMT não decadente → crédito do usinado → débito por código de receita.
#
# Regras do motor:
#   - Decimal em tudo (nunca float); arredondamento HALF_UP em 2 casas nos mesmos
#     pontos que a memória de cálculo do SERO mostra (COD, RMT por área, crédito,
#     débito por código).
#   - Função PURA: recebe um dict, devolve um dict. Não lê banco nem relógio
#     (a data da aferição vem na entrada).
#   - O resultado é SEMPRE uma simulação. O valor oficial é o do SERO no e-CAC.
#   - Erro de dado → ErroSimulacao com mensagem para o usuário, nunca zero silencioso.
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal as D, InvalidOperation

from services.inss_obra import params as P

AVISO = ("SIMULAÇÃO — não é o resultado oficial. O valor devido é o apurado pelo SERO "
         "(e-CAC) e declarado na DCTFWeb Aferição de Obras.")


class ErroSimulacao(ValueError):
    """Dado de entrada inválido ou insuficiente para simular."""


def _r2(v: D) -> D:
    return v.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _dec(valor, campo: str) -> D:
    if valor is None or valor == "":
        raise ErroSimulacao(f"Informe {campo}.")
    try:
        if isinstance(valor, str):
            s = valor.strip()
            if "," in s:
                s = s.replace(".", "").replace(",", ".")
            return D(s)
        return D(str(valor))
    except (InvalidOperation, ValueError):
        raise ErroSimulacao(f"{campo}: valor inválido ({valor!r}).")


def _data(valor, campo: str) -> date:
    if isinstance(valor, date):
        return valor
    if not valor:
        raise ErroSimulacao(f"Informe {campo}.")
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        raise ErroSimulacao(f"{campo}: data inválida ({valor!r}). Use AAAA-MM-DD.")


# ── Decadência (item 20 / 20.1) ──────────────────────────────────────────────
def competencias(inicio: date, fim: date) -> list[tuple[int, int]]:
    """Meses (ano, mês) tocados pelo período — 31/12 a 10/01 conta 2 meses (p.97)."""
    if fim < inicio:
        raise ErroSimulacao("A data de fim da obra é anterior à data de início.")
    out, a, m = [], inicio.year, inicio.month
    while (a, m) <= (fim.year, fim.month):
        out.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def competencia_decadente(ano: int, data_afericao: date) -> bool:
    """5 anos contados do 1º dia do exercício seguinte (p.92): competência do ano Y
    decai em 1º/01/(Y+6). Reproduz o exemplo p.96 (aferição 08/2020 → 2012–2014)."""
    return data_afericao >= date(ano + 6, 1, 1)


def decadencia(inicio: date, fim: date, data_afericao: date) -> dict:
    meses = competencias(inicio, fim)
    dec = sum(1 for a, _ in meses if competencia_decadente(a, data_afericao))
    total = len(meses)
    nao_dec = total - dec
    return {"meses_total": total, "meses_decadentes": dec, "meses_nao_decadentes": nao_dec,
            "percentual_nao_decadente": D(nao_dec) / D(total)}


# ── Normalização das áreas ───────────────────────────────────────────────────
def _normalizar_areas(areas: list) -> list[dict]:
    if not areas:
        raise ErroSimulacao("Informe ao menos uma área da obra.")
    out = []
    for i, a in enumerate(areas, 1):
        dest, cat = a.get("destinacao"), a.get("categoria")
        tipo, classe = a.get("tipo") or "alvenaria", a.get("classe") or "principal"
        if dest not in P.DESTINACOES:
            raise ErroSimulacao(f"Área {i}: destinação inválida.")
        if cat not in P.CATEGORIAS:
            raise ErroSimulacao(f"Área {i}: categoria inválida.")
        if tipo not in P.TIPOS:
            raise ErroSimulacao(f"Área {i}: tipo de material inválido.")
        if classe not in P.CLASSES_AREA:
            raise ErroSimulacao(f"Área {i}: classe de área inválida.")
        m2 = _dec(a.get("area_m2"), f"a metragem da área {i}")
        if m2 <= 0:
            raise ErroSimulacao(f"Área {i}: a metragem precisa ser maior que zero.")
        out.append({"n": i, "descricao": (a.get("descricao") or "").strip(),
                    "destinacao": dest, "categoria": cat, "tipo": tipo,
                    "classe": classe, "area_m2": m2})
    return out


# ── Motor ────────────────────────────────────────────────────────────────────
def simular(entrada: dict) -> dict:
    """entrada = {responsavel 'PF'|'PJ', uf, vau {destinacao: R$/m²}, data_inicio,
    data_fim, data_afericao, areas [...], usinado bool}."""
    resp = (entrada.get("responsavel") or "PF").upper()
    if resp not in ("PF", "PJ"):
        raise ErroSimulacao("Responsável deve ser pessoa física (PF) ou jurídica (PJ).")
    uf = (entrada.get("uf") or "").upper()
    if uf not in P.USINADO_UF:
        raise ErroSimulacao("Informe a UF da obra.")
    areas = _normalizar_areas(entrada.get("areas") or [])
    inicio = _data(entrada.get("data_inicio"), "a data de início da obra")
    fim = _data(entrada.get("data_fim"), "a data de fim da obra")
    afericao = _data(entrada.get("data_afericao"), "a data da aferição")
    usinado = bool(entrada.get("usinado"))

    vau_in = entrada.get("vau") or {}
    vau = {}
    for dest in {a["destinacao"] for a in areas}:
        v = _dec(vau_in.get(dest), f"o VAU de {P.DESTINACOES[dest]} (R$/m²)")
        if v <= 0:
            raise ErroSimulacao(f"O VAU de {P.DESTINACOES[dest]} precisa ser maior que zero.")
        vau[dest] = v

    usados: dict[str, dict] = {}

    def _usa(nome, bloco):
        usados[nome] = {"status": bloco["status"], "fonte": bloco["fonte"]}

    # Equivalência: soma das áreas PRINCIPAIS de cada destinação no projeto (17.1)
    princ_por_dest: dict[str, D] = {}
    for a in areas:
        if a["classe"] == "principal":
            princ_por_dest[a["destinacao"]] = princ_por_dest.get(a["destinacao"], D(0)) + a["area_m2"]
    # Fator social: área total (principal + complementar) por CATEGORIA (19.4)
    area_por_cat: dict[str, D] = {}
    for a in areas:
        area_por_cat[a["categoria"]] = area_por_cat.get(a["categoria"], D(0)) + a["area_m2"]

    linhas = []
    for a in areas:
        dest, cat, tipo, classe = a["destinacao"], a["categoria"], a["tipo"], a["classe"]
        if classe == "principal":
            red = P.equivalencia(dest, princ_por_dest[dest])
            _usa(f"equivalencia:{dest}", P.EQUIVALENCIA[dest])
        else:
            red = P.COMPLEMENTAR[classe]
            _usa("complementar", P.COMPLEMENTAR)
        area_calc = a["area_m2"] * red
        cod = _r2(area_calc * vau[dest])

        pmo = P.percentual_mao_de_obra(dest, tipo)
        _usa("mao_de_obra", P.MAO_DE_OBRA)
        pcat = P.CATEGORIA_PCT[cat]
        _usa("categoria", P.CATEGORIA_PCT)
        pdest = P.DESTINACAO_PCT.get(dest, D(1))
        if dest in P.DESTINACAO_PCT:
            _usa("destinacao", P.DESTINACAO_PCT)
        fs = P.fator_social(area_por_cat[cat]) if resp == "PF" else D(1)
        if resp == "PF":
            _usa("fator_social", P.FATOR_SOCIAL)
        rmt = _r2(cod * pmo * pcat * pdest * fs)

        linhas.append({
            **a, "area_m2": str(a["area_m2"]),
            "reducao_area": str(red), "area_calculo": str(area_calc),
            "vau": str(vau[dest]), "cod": str(cod),
            "pct_mao_de_obra": str(pmo), "pct_categoria": str(pcat),
            "pct_destinacao": str(pdest), "fator_social": str(fs),
            "fator_social_area_categoria": str(area_por_cat[cat]) if resp == "PF" else None,
            "rmt": str(rmt),
        })

    cod_total = sum((D(l["cod"]) for l in linhas), D(0))
    rmt_total = sum((D(l["rmt"]) for l in linhas), D(0))

    dec = decadencia(inicio, fim, afericao)
    pnd = dec["percentual_nao_decadente"]
    rmt_nd = _r2(rmt_total * pnd)

    credito_usinado = D(0)
    usinado_linhas = []
    if usinado:
        _usa("usinado", P.USINADO_STATUS)
        for l in linhas:
            pct_uf = P.USINADO_UF[uf][l["destinacao"]]
            pcat_u = P.USINADO_CATEGORIA[l["categoria"]]
            cr = _r2(D(l["cod"]) * pct_uf * pcat_u * P.USINADO_FATOR * pnd)
            credito_usinado += cr
            usinado_linhas.append({"n": l["n"], "cod": l["cod"], "pct_uf": str(pct_uf),
                                   "pct_categoria": str(pcat_u), "credito": str(cr)})

    base = max(D(0), rmt_nd - credito_usinado)

    _usa("aliquotas", P.ALIQUOTAS_STATUS)
    debitos = []
    for codigo, nome, aliq in P.ALIQUOTAS:
        debitos.append({"codigo": codigo, "nome": nome, "aliquota": str(aliq),
                        "valor": str(_r2(base * aliq))})
    total = sum((D(d["valor"]) for d in debitos), D(0))

    a_conferir = sorted({k for k, v in usados.items() if v["status"] == "conferir"})
    alertas = []
    if any(l["destinacao"] == "casa_popular" for l in linhas) and resp != "PF":
        alertas.append("Casa popular é enquadramento de obra de pessoa física (Manual item 29).")
    if dec["meses_decadentes"] and dec["meses_nao_decadentes"] == 0:
        alertas.append("Obra inteira em período decadente: a DCTFWeb Aferição sai zerada, "
                       "mas precisa ser transmitida para emitir a certidão (Manual p.93-94). "
                       "As datas de início e fim podem ter de ser comprovadas (IN RFB 2.021, art. 42).")
    elif dec["meses_decadentes"]:
        alertas.append("Parte da obra está em período decadente: a data de início pode ter de ser "
                       "comprovada com documento (IN RFB 2.021/2021, art. 42).")
    if resp == "PJ":
        alertas.append("Pessoa jurídica: simulação sem desoneração e sem fator social. "
                       "PJ com contabilidade regular pode aferir pela escrituração (Manual item 26.2).")

    return {
        "aviso": AVISO,
        "versao_manual": P.VERSAO_MANUAL,
        "entrada": {"responsavel": resp, "uf": uf, "data_inicio": inicio.isoformat(),
                    "data_fim": fim.isoformat(), "data_afericao": afericao.isoformat(),
                    "competencia_afericao": f"{afericao.month:02d}/{afericao.year}",
                    "usinado": usinado, "vau": {k: str(v) for k, v in vau.items()}},
        "linhas": linhas,
        "cod_total": str(cod_total),
        "rmt_total": str(rmt_total),
        "decadencia": {**dec, "percentual_nao_decadente": str(pnd)},
        "rmt_nao_decadente": str(rmt_nd),
        "usinado": {"aplicado": usinado, "linhas": usinado_linhas, "credito": str(credito_usinado)},
        "base_calculo": str(base),
        "debitos": debitos,
        "total": str(total),
        "parametros": usados,
        "parametros_a_conferir": a_conferir,
        "alertas": alertas,
    }
