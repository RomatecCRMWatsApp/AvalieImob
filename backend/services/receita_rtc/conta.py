# @module services.receita_rtc.conta — configuração tributária por conta (assinante).
#
# Cada assinante informa o próprio regime e os códigos do serviço (NBS, CST, cClassTrib) e, no Simples,
# a alíquota efetiva e a atividade. NÃO há código padrão: o simulador fica desativado até a conta
# preencher tudo e declarar que confirmou com o contador (PENDENCIAS.md, decisões 6 e 7; P-08, P-13).
from datetime import datetime
from typing import Optional

from . import mapper as MP

COLECAO = "rtc_config_conta"


def _dig(v) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def normalizar(dados: dict) -> dict:
    """Normaliza sem exigir completude (a conta pode salvar aos poucos). Recusa valor mal formado."""
    regime = str(dados.get("regime") or "").upper() or None
    if regime and regime not in MP.REGIMES:
        raise MP.EntradaInvalida("regime: use REGULAR ou SIMPLES.")
    uf = str(dados.get("uf") or "").strip().upper()
    if uf and (len(uf) != 2 or not uf.isalpha()):
        raise MP.EntradaInvalida("uf: sigla de 2 letras.")
    out = {"regime": regime, "uf": uf, "codigo_municipio": _dig(dados.get("codigo_municipio")),
           "nome_municipio": str(dados.get("nome_municipio") or "")[:120],
           "nbs": _dig(dados.get("nbs")), "cst": _dig(dados.get("cst")),
           "cClassTrib": _dig(dados.get("cClassTrib")),
           "descricao_classificacao": str(dados.get("descricao_classificacao") or "")[:300],
           "confirmado_com_contador": bool(dados.get("confirmado_com_contador"))}
    for campo, n in (("codigo_municipio", 7), ("nbs", 9), ("cst", 3), ("cClassTrib", 6)):
        if out[campo] and len(out[campo]) != n:
            raise MP.EntradaInvalida(f"{campo}: informe {n} dígitos.")
    sn = dados.get("simples") or {}
    simples = {"crt": str(sn.get("crt") or "1"), "cAtivSN": _dig(sn.get("cAtivSN")),
               "pIBSSN": str(sn.get("pIBSSN") or "").replace(",", ".").strip(),
               "pCBSSN": str(sn.get("pCBSSN") or "").replace(",", ".").strip()}
    if simples["crt"] not in ("1", "2"):
        raise MP.EntradaInvalida("simples.crt: 1 (Simples Nacional) ou 2 (excesso de sublimite). MEI não é calculado.")
    for campo in ("pIBSSN", "pCBSSN"):
        if simples[campo]:
            simples[campo] = str(MP.percentual(simples[campo], f"simples.{campo}"))
    if simples["cAtivSN"] and len(simples["cAtivSN"]) != 2:
        raise MP.EntradaInvalida("simples.cAtivSN: código de 2 dígitos.")
    out["simples"] = simples
    return out


def faltantes(cfg: Optional[dict]) -> list:
    """Campos que impedem simular. Lista vazia = pronta."""
    if not cfg:
        return ["regime", "uf", "codigo_municipio", "nbs", "cClassTrib", "confirmado_com_contador"]
    f = [c for c in ("regime", "uf", "codigo_municipio", "nbs", "cClassTrib") if not cfg.get(c)]
    if cfg.get("regime") == "REGULAR" and not cfg.get("cst"):
        f.append("cst")
    if cfg.get("regime") == "SIMPLES":
        sn = cfg.get("simples") or {}
        f += [f"simples.{c}" for c in ("cAtivSN", "pIBSSN", "pCBSSN") if not sn.get(c)]
    if not cfg.get("confirmado_com_contador"):
        f.append("confirmado_com_contador")
    return f


def montar_entrada(cfg: dict, data_operacao: str, valor) -> dict:
    ent = {"regime": cfg["regime"], "data_operacao": data_operacao, "uf": cfg["uf"],
           "codigo_municipio": cfg["codigo_municipio"],
           "itens": [{"valor": valor, "nbs": cfg["nbs"], "cst": cfg.get("cst"), "cClassTrib": cfg["cClassTrib"]}]}
    if cfg["regime"] == "SIMPLES":
        ent["simples"] = cfg["simples"]
    return ent


async def obter(db, uid: str) -> Optional[dict]:
    doc = await db[COLECAO].find_one({"user_id": uid})
    if doc:
        doc = dict(doc)
        doc.pop("_id", None)
    return doc


async def salvar(db, uid: str, dados: dict) -> dict:
    cfg = normalizar(dados)
    cfg["atualizado_em"] = datetime.utcnow()
    await db[COLECAO].update_one({"user_id": uid}, {"$set": {**cfg, "user_id": uid}}, upsert=True)
    return await obter(db, uid)
