# @module services.receita_rtc.mapper — modelo do sistema <-> JSON oficial (funções puras).
#
# Valores monetários: Decimal internamente. Na ida, viram número JSON só no último passo (2 casas,
# o float tem representação exata o bastante para o texto do JSON); na volta, ficam como a STRING
# que a calculadora devolveu ("6.30"), sem recalcular nem arredondar.
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

REGIMES = ("REGULAR", "SIMPLES")
VERSAO_ENTRADA_REGULAR = "1.0.0"
VERSAO_ENTRADA_SIMPLES = "2.0.0"
TPDOC_NFSE_SIMPLES = "91"  # tipo de documento de serviço no catálogo de atividades do Simples


class EntradaInvalida(ValueError):
    pass


def _so_dig(v, n: int, campo: str) -> str:
    s = "".join(ch for ch in str(v or "") if ch.isdigit())
    if len(s) != n:
        raise EntradaInvalida(f"{campo}: informe {n} dígitos.")
    return s


def valor_monetario(v, campo: str = "valor") -> Decimal:
    try:
        d = Decimal(str(v).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise EntradaInvalida(f"{campo}: informe um valor numérico.")
    if not d.is_finite():
        raise EntradaInvalida(f"{campo}: valor inválido.")
    if d <= 0:
        raise EntradaInvalida(f"{campo}: o valor deve ser maior que zero.")
    if -d.as_tuple().exponent > 2:
        raise EntradaInvalida(f"{campo}: no máximo 2 casas decimais.")
    if d > Decimal("999999999999.99"):
        raise EntradaInvalida(f"{campo}: valor acima do limite.")
    return d


def percentual(v, campo: str) -> Decimal:
    try:
        d = Decimal(str(v).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise EntradaInvalida(f"{campo}: informe o percentual.")
    if not d.is_finite() or d < 0 or d > 100:
        raise EntradaInvalida(f"{campo}: percentual entre 0 e 100.")
    return d


def validar_entrada(e: dict) -> dict:
    """Normaliza a entrada. A data da operação é OBRIGATÓRIA: nunca assumir "hoje"."""
    regime = str(e.get("regime", "")).upper()
    if regime not in REGIMES:
        raise EntradaInvalida("regime: use REGULAR ou SIMPLES.")
    if not e.get("data_operacao"):
        raise EntradaInvalida("data_operacao: informe a data do fato gerador (não é preenchida automaticamente).")
    try:
        data_op = date.fromisoformat(str(e["data_operacao"])[:10])
    except ValueError:
        raise EntradaInvalida("data_operacao: data inválida (use AAAA-MM-DD).")
    uf = str(e.get("uf") or "").strip().upper()
    if len(uf) != 2 or not uf.isalpha():
        raise EntradaInvalida("uf: sigla de 2 letras.")
    municipio = _so_dig(e.get("codigo_municipio"), 7, "codigo_municipio")
    itens_in = e.get("itens") or []
    if not itens_in:
        raise EntradaInvalida("itens: informe ao menos um item.")
    if len(itens_in) > 50:
        raise EntradaInvalida("itens: no máximo 50 itens por simulação.")
    itens = []
    for i, it in enumerate(itens_in, start=1):
        base = {"numero": i, "valor": valor_monetario(it.get("valor"), f"itens[{i}].valor"),
                "cClassTrib": _so_dig(it.get("cClassTrib"), 6, f"itens[{i}].cClassTrib"),
                "nbs": _so_dig(it.get("nbs"), 9, f"itens[{i}].nbs")}
        if regime == "REGULAR":
            base["cst"] = _so_dig(it.get("cst"), 3, f"itens[{i}].cst")
        itens.append(base)
    out = {"regime": regime, "data_operacao": data_op, "uf": uf, "codigo_municipio": municipio, "itens": itens}
    if regime == "SIMPLES":
        sn = e.get("simples") or {}
        crt = str(sn.get("crt") or "1")
        if crt not in ("1", "2"):
            raise EntradaInvalida("simples.crt: 1 (Simples Nacional) ou 2 (excesso de sublimite). MEI não é calculado.")
        out["simples"] = {
            "crt": crt,
            "cAtivSN": _so_dig(sn.get("cAtivSN"), 2, "simples.cAtivSN"),
            "pIBSSN": percentual(sn.get("pIBSSN"), "simples.pIBSSN"),
            "pCBSSN": percentual(sn.get("pCBSSN"), "simples.pCBSSN"),
        }
    return out


def _num(d: Decimal) -> float:
    return float(d)


def montar_regular(ent: dict, id_operacao: str, aliquotas: Optional[dict]) -> dict:
    """Operação do regime regular. `aliquotas` só é enviado a partir de 2027 (contrato da calculadora)."""
    itens = []
    for it in ent["itens"]:
        item = {"numero": it["numero"], "nbs": it["nbs"], "cst": it["cst"], "cClassTrib": it["cClassTrib"],
                "baseCalculo": _num(it["valor"])}
        if aliquotas:
            item["aliquotasNominais"] = {
                "cbs": _num(Decimal(aliquotas["CBS"]["aliquota"])),
                "ibsEstadual": _num(Decimal(aliquotas["IBS_UF"]["aliquota"])),
                "ibsMunicipal": _num(Decimal(aliquotas["IBS_MUN"]["aliquota"])),
            }
        itens.append(item)
    return {"id": id_operacao, "versao": VERSAO_ENTRADA_REGULAR,
            "dhFatoGerador": f"{ent['data_operacao'].isoformat()}T12:00:00-03:00",
            "municipio": int(ent["codigo_municipio"]), "uf": ent["uf"], "itens": itens}


def montar_simples(ent: dict, id_operacao: str) -> dict:
    sn = ent["simples"]
    return {"id": id_operacao, "versao": VERSAO_ENTRADA_SIMPLES,
            "data": ent["data_operacao"].isoformat(), "tpDoc": TPDOC_NFSE_SIMPLES, "CRT": sn["crt"],
            "itens": [{"numero": it["numero"], "cAtivSN": sn["cAtivSN"], "cClassTrib": it["cClassTrib"],
                       "nbs": it["nbs"], "baseCalculo": f"{it['valor']:.2f}", "valorImpostoSeletivo": "0.00",
                       "pIBSSN": str(sn["pIBSSN"]), "pCBSSN": str(sn["pCBSSN"])} for it in ent["itens"]]}


def _g(d, *caminho):
    for c in caminho:
        if not isinstance(d, dict):
            return None
        d = d.get(c)
    return d


def _erros(lista) -> list:
    return [{"codigo": x.get("code"), "titulo": x.get("title"), "detalhe": x.get("detail"),
             "campo": x.get("pointer")} for x in (lista or []) if isinstance(x, dict)]


def ler_regular(status: int, corpo: dict, headers: dict) -> dict:
    itens = []
    for o in (corpo or {}).get("objetos") or []:
        ibscbs = _g(o, "tribCalc", "IBSCBS") or {}
        g = ibscbs.get("gIBSCBS") or {}
        itens.append({
            "numero": o.get("nObj"), "estado": o.get("estadoItem"),
            "calculado": o.get("estadoItem") in ("CALCULADO", "CALCULO_SIMULADO"),
            "cst": ibscbs.get("CST"), "cClassTrib": ibscbs.get("cClassTrib"),
            "base_calculo": g.get("vBC"),
            "cbs": {"aliquota": _g(g, "gCBS", "pCBS"), "aliquota_efetiva": _g(g, "gCBS", "gRed", "pAliqEfet"),
                    "reducao": _g(g, "gCBS", "gRed", "pRedAliq"), "valor": _g(g, "gCBS", "vCBS")},
            "ibs_uf": {"aliquota": _g(g, "gIBSUF", "pIBSUF"), "aliquota_efetiva": _g(g, "gIBSUF", "gRed", "pAliqEfet"),
                       "reducao": _g(g, "gIBSUF", "gRed", "pRedAliq"), "valor": _g(g, "gIBSUF", "vIBSUF")},
            "ibs_mun": {"aliquota": _g(g, "gIBSMun", "pIBSMun"), "aliquota_efetiva": _g(g, "gIBSMun", "gRed", "pAliqEfet"),
                        "reducao": _g(g, "gIBSMun", "gRed", "pRedAliq"), "valor": _g(g, "gIBSMun", "vIBSMun")},
            "ibs": g.get("vIBS"), "is": _g(o, "tribCalc", "IS", "vIS"),
            "memoria": ibscbs.get("memoriaCalculo"),
            "erros": _erros(o.get("erros")),
        })
    tot = _g(corpo, "total", "tribCalc") or {}
    ibscbs_tot = tot.get("IBSCBSTot") or {}
    return {
        "itens": itens,
        "totais": {"base_calculo": ibscbs_tot.get("vBCIBSCBS"),
                   "cbs": _g(ibscbs_tot, "gCBS", "vCBS"), "ibs": _g(ibscbs_tot, "gIBS", "vIBS"),
                   "is": _g(tot, "ISTot", "vIS")},
        "simulado": "x-warning-dados-simulados" in (headers or {}),
        "erros_gerais": _erros((corpo or {}).get("errors")) if status >= 400 else [],
    }


def ler_simples(status: int, corpo: dict, headers: dict) -> dict:
    corpo = corpo or {}
    itens = []
    for o in corpo.get("objetos") or []:
        t = o.get("tribCalc") or {}
        itens.append({
            "numero": o.get("nObj"), "estado": o.get("estadoItem"),
            "calculado": o.get("estadoItem") in ("CALCULADO", "CALCULO_SIMULADO"),
            "base_calculo": t.get("vBC"),
            "cbs": {"aliquota": t.get("pCBSSN"), "valor": t.get("vCBSSN")},
            "ibs": t.get("vIBSSN"), "ibs_aliquota": t.get("pIBSSN"),
            "total_item": t.get("totalItem"), "memoria": t.get("memoriaCalculo"),
            "erros": _erros(o.get("erros")),
        })
    tot = corpo.get("total") or {}
    return {
        "itens": itens,
        "totais": {"base_calculo": tot.get("vBC"), "cbs": tot.get("vCBSSNtot"), "ibs": tot.get("vIBSSNtot"),
                   "is": tot.get("totalIs"), "total": tot.get("totalTributos")},
        "simulado": "x-warning-dados-simulados" in (headers or {}),
        "erros_gerais": _erros(corpo.get("errors")) if status >= 400 else [],
    }
