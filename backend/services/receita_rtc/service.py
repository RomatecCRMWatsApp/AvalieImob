# @module services.receita_rtc.service — casos de uso: simular, traduzir erros, versão, diagnóstico.
#
# Snapshot imutável em `simulacao_tributaria`: entrada enviada, resposta bruta, alíquotas com origem,
# versão da calculadora, usuário e data. Nunca é recalculado sozinho.
import uuid
from datetime import datetime
from typing import Optional

from . import aliquotas as ALQ
from . import config as cfg
from . import mapper as MP
from .client import CalculadoraClient, CalculadoraIndisponivel

COLECAO = "simulacao_tributaria"
ORIGENS = ("recibo", "ptam", "proposta", "garantia", "avulsa")

ERROS_PATH = {"REGULAR": "/calculadora/observabilidade/erros",
              "SIMPLES": "/calculadora/observabilidade/simples-nacional/erros"}
CALCULO_PATH = {"REGULAR": "/calculadora/observabilidade/regime-geral",
                "SIMPLES": "/calculadora/observabilidade/simples-nacional"}
VERSAO_PATH = {"REGULAR": "/calculadora/dados-abertos/versao", "SIMPLES": "/versao"}


class SimuladorDesativado(Exception):
    pass


class SemAliquota(Exception):
    def __init__(self, mensagem: str, faltantes: list):
        super().__init__(mensagem)
        self.faltantes = faltantes


def clientes(conf: Optional[cfg.Config] = None, transport=None) -> dict:
    conf = conf or cfg.carregar()
    return {"REGULAR": CalculadoraClient(conf.regime_regular_url, conf, transport),
            "SIMPLES": CalculadoraClient(conf.simples_url, conf, transport)}


async def traduzir_erros(client: CalculadoraClient, regime: str, erros: list) -> list:
    """Acrescenta a descrição oficial de cada código (REG-xxx / VSN-xxx), com cache."""
    saida = []
    for e in erros:
        e = dict(e)
        cod = e.get("codigo")
        if cod:
            try:
                r = await client.get_cache(ERROS_PATH[regime], {"codigo": cod})
                if r.ok and isinstance(r.corpo, dict):
                    e["titulo"] = r.corpo.get("titulo") or e.get("titulo")
                    e["descricao"] = r.corpo.get("descricao")
            except CalculadoraIndisponivel:
                pass
        saida.append(e)
    return saida


async def versao(client: CalculadoraClient, regime: str) -> Optional[dict]:
    try:
        r = await client.get_cache(VERSAO_PATH[regime])
    except CalculadoraIndisponivel:
        return None
    if not r.ok or not isinstance(r.corpo, dict):
        return None
    return {"versao_app": r.corpo.get("versaoApp"), "versao_db": r.corpo.get("versaoDb"),
            "data_db": r.corpo.get("dataVersaoDb")}


async def localidade(client: CalculadoraClient, uf: str, municipio: str) -> int:
    """Código IBGE da UF e confirmação de que o município pertence a ela (tabelas da calculadora)."""
    r = await client.get_cache("/calculadora/dados-abertos/ufs")
    ufs = {u.get("sigla"): u.get("codigo") for u in (r.corpo or []) if isinstance(u, dict)} if r.ok else {}
    if uf not in ufs:
        raise MP.EntradaInvalida(f"uf: {uf} não encontrada nas tabelas da calculadora.")
    rm = await client.get_cache("/calculadora/dados-abertos/ufs/municipios", {"siglaUf": uf})
    codigos = {str(m.get("codigo")) for m in (rm.corpo or []) if isinstance(m, dict)} if rm.ok else set()
    if municipio not in codigos:
        raise MP.EntradaInvalida(f"codigo_municipio: {municipio} não pertence a {uf}.")
    return int(ufs[uf])


def _situacao(itens: list) -> str:
    ok = sum(1 for i in itens if i["calculado"])
    if itens and ok == len(itens):
        return "calculado"
    return "calculado_com_erros" if ok else "nao_calculado"


async def simular(db, uid: str, entrada: dict, origem_tipo: str = "avulsa", origem_id: Optional[str] = None,
                  conf: Optional[cfg.Config] = None, transport=None) -> dict:
    conf = conf or cfg.carregar()
    if not conf.enabled:
        raise SimuladorDesativado("Simulador de CBS/IBS desativado.")
    if not conf.configurada:
        raise CalculadoraIndisponivel(cfg.MSG_INDISPONIVEL)
    if origem_tipo not in ORIGENS:
        raise MP.EntradaInvalida("origem_tipo inválida.")
    ent = MP.validar_entrada(entrada)
    regime = ent["regime"]
    cli = clientes(conf, transport)
    c = cli[regime]
    id_op = uuid.uuid4().hex

    aliquotas_info = None
    if regime == "REGULAR":
        codigo_uf = await localidade(c, ent["uf"], ent["codigo_municipio"])
        res = await ALQ.resolver(db, c, ent["data_operacao"], ent["uf"], codigo_uf, ent["codigo_municipio"])
        if res["faltantes"]:
            raise SemAliquota(ALQ.mensagem_faltantes(res["faltantes"], ent["data_operacao"]), res["faltantes"])
        aliquotas_info = res["aliquotas"]
        operacao = MP.montar_regular(ent, id_op, aliquotas_info if res["enviar"] else None)
    else:
        operacao = MP.montar_simples(ent, id_op)

    resp = await c.chamar("POST", CALCULO_PATH[regime], json=operacao)
    if resp.status >= 400 and not (isinstance(resp.corpo, dict) and resp.corpo.get("errors")):
        # 4xx sem lista de erros: pedido rejeitado de forma genérica (não é falha de rede, sem retry).
        raise MP.EntradaInvalida("A calculadora recusou os dados da simulação. Confira os códigos informados.")
    leitura = (MP.ler_regular if regime == "REGULAR" else MP.ler_simples)(resp.status, resp.corpo, resp.headers)
    for it in leitura["itens"]:
        it["erros"] = await traduzir_erros(c, regime, it["erros"])
    leitura["erros_gerais"] = await traduzir_erros(c, regime, leitura["erros_gerais"])

    avisos = [cfg.AVISO_FIXO]
    if aliquotas_info and any(a["origem"] == "TABELA_INTERNA" for a in aliquotas_info.values()):
        avisos.append(cfg.AVISO_TABELA_INTERNA)

    agora = datetime.utcnow()
    situacao = "nao_calculado" if leitura["erros_gerais"] else _situacao(leitura["itens"])
    snap = {
        "id": str(uuid.uuid4()), "user_id": uid, "origem_tipo": origem_tipo, "origem_id": origem_id,
        "regime": regime, "data_operacao": ent["data_operacao"].isoformat(),
        "uf": ent["uf"], "codigo_municipio": ent["codigo_municipio"],
        "situacao": situacao, "simulado": leitura["simulado"],
        "itens": leitura["itens"], "totais": leitura["totais"], "erros_gerais": leitura["erros_gerais"],
        "total_cbs": leitura["totais"].get("cbs"), "total_ibs": leitura["totais"].get("ibs"),
        "total_is": leitura["totais"].get("is"),
        "aliquotas": aliquotas_info, "avisos": avisos,
        "entrada_enviada": operacao, "resultado_bruto": resp.corpo, "http_status": resp.status,
        "versao_calculadora": await versao(c, regime),
        "criado_por": uid, "criado_em": agora,
    }
    await db[COLECAO].insert_one(dict(snap))
    return snap


async def diagnostico(conf: Optional[cfg.Config] = None, transport=None) -> dict:
    """Saúde das calculadoras para a tela do administrador (sem dado de cliente)."""
    conf = conf or cfg.carregar()
    out = {"ativo": conf.enabled, "configurado": conf.configurada, "servicos": {}}
    if not conf.configurada:
        return out
    for regime, c in clientes(conf, transport).items():
        try:
            r = await c.chamar("GET", VERSAO_PATH[regime])
            out["servicos"][regime] = {"no_ar": r.ok, "status": r.status,
                                       "versao": (r.corpo or {}).get("versaoApp") if isinstance(r.corpo, dict) else None,
                                       "versao_db": (r.corpo or {}).get("versaoDb") if isinstance(r.corpo, dict) else None}
        except CalculadoraIndisponivel:
            out["servicos"][regime] = {"no_ar": False, "status": None}
    return out
