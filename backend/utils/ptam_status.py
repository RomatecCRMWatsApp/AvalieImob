# @module utils.ptam_status — Cálculo automático do status do PTAM (NBR 14653)
"""
Status em cascata (prioridade): assinado > concluido > rascunho.

    assinado  -> icp_status == "assinado" OU d4sign_status == "assinado"
    concluido -> valor final > 0 E todas as 12 seções do wizard preenchidas
    rascunho  -> qualquer outro caso

Os nomes de campo foram mapeados contra o model real (models/ptam.py:PtamBase)
e os 12 steps do wizard (components/dashboard/ptam/steps/*). Cada seção aceita
ALTERNATIVAS: basta UM dos campos estar preenchido para a seção contar como ok.

Para calibrar contra dados reais use migrate_ptam_status.py --inspect.
"""
from __future__ import annotations

from typing import Any, Mapping

STATUS_RASCUNHO = "rascunho"
STATUS_CONCLUIDO = "concluido"
STATUS_ASSINADO = "assinado"

# ── Assinatura ────────────────────────────────────────────────────────────────
# A rota routes/assinatura.py grava esses campos como "assinado".
def _tem_assinatura(p: Mapping[str, Any]) -> bool:
    return p.get("icp_status") == "assinado" or p.get("d4sign_status") == "assinado"


# ── Valor final avaliado ──────────────────────────────────────────────────────
CAMPOS_VALOR = (
    "resultado_valor_total",
    "total_indemnity",
    "ponderancia_valor_final",
    "valor_total_metodo",
    "resultado_valor_unitario",
)


def _to_float(v: Any) -> float:
    if v is None or isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace("R$", "").replace(" ", "").replace("\xa0", "")
        if not s:
            return 0.0
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0
    return 0.0


def _valor_final(p: Mapping[str, Any]) -> float:
    for campo in CAMPOS_VALOR:
        v = _to_float(p.get(campo))
        if v > 0:
            return v
    return 0.0


# ── 12 seções do wizard (rótulo, campos-alternativos) ─────────────────────────
# Edite aqui para afrouxar/endurecer qualquer seção.
SECOES_OBRIGATORIAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("1.Solicitante", ("solicitante", "solicitante_nome")),
    ("2.Objetivo", ("purpose", "finalidade")),
    ("3.Imóvel", ("property_label", "property_address", "property_type", "property_matricula")),
    ("4.Região", (
        "regiao_infraestrutura", "regiao_servicos_publicos", "regiao_uso_predominante",
        "regiao_padrao_construtivo", "regiao_tendencia_mercado", "regiao_observacoes",
    )),
    ("5.Caracterização", (
        "imovel_area_terreno", "imovel_area_construida", "imovel_area_a_considerar",
        "imovel_estado_conservacao", "imovel_padrao_acabamento", "property_description",
    )),
    ("6.Amostras", ("market_samples", "impact_areas")),
    ("7.Metodologia", ("methodology",)),
    ("8.Cálculos", (
        "calc_media", "calc_mediana", "calc_n_validas",
        "resultado_valor_unitario", "calc_grau_fundamentacao",
    )),
    # 9 e 10 incluem o valor final como alternativa: laudos pelo método comparativo
    # (sem ponderância/depreciação explícita) não ficam presos em "rascunho".
    ("9.Ponderância", (
        "ponderancia_valor_final", "ponderancia_media",
        "resultado_valor_total", "total_indemnity",
    )),
    ("10.Dep./Valoriz.", (
        "metodo_avaliacao", "depreciacao_percentual", "valor_total_metodo",
        "valor_benfeitoria", "resultado_valor_total", "total_indemnity",
    )),
    ("11.Resultado", ("resultado_valor_total", "resultado_valor_unitario", "total_indemnity")),
    ("12.Conclusão", (
        "conclusion_text", "consideracoes_ressalvas",
        "consideracoes_limitacoes", "total_indemnity_words",
    )),
)


def _preenchido(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) > 0
    if isinstance(v, (int, float)):
        return v != 0
    return True


def _secao_ok(p: Mapping[str, Any], campos: tuple[str, ...]) -> bool:
    return any(_preenchido(p.get(c)) for c in campos)


def _secoes_faltando(p: Mapping[str, Any]) -> list[str]:
    return [rotulo for rotulo, campos in SECOES_OBRIGATORIAS if not _secao_ok(p, campos)]


# ── API pública ───────────────────────────────────────────────────────────────
def calcular_status_ptam(ptam: Mapping[str, Any]) -> str:
    """Calcula o status do PTAM. Prioridade: assinado > concluído > rascunho.

    A conclusão é MANUAL: o avaliador marca `concluido_manual` na etapa 12.
      - assinado            -> assinatura ICP/D4Sign (sempre prevalece)
      - concluido_manual=True  -> concluído
      - concluido_manual=False -> rascunho (avaliador reabriu)
      - concluido_manual=None  -> legado: cai no cálculo automático (valor + 12 seções)
    """
    if not isinstance(ptam, Mapping):
        return STATUS_RASCUNHO
    # Assinatura sempre prevalece.
    if _tem_assinatura(ptam):
        return STATUS_ASSINADO
    # Conclusão é EXCLUSIVAMENTE manual: o avaliador decide na etapa 12.
    # O sistema nunca conclui sozinho — sem o flag, segue rascunho.
    if ptam.get("concluido_manual") is True:
        return STATUS_CONCLUIDO
    return STATUS_RASCUNHO


def diagnostico_status(ptam: Mapping[str, Any]) -> dict[str, Any]:
    """Versão verbosa pra calibrar os nomes de campo contra um PTAM real."""
    faltando = _secoes_faltando(ptam)
    return {
        "status": calcular_status_ptam(ptam),
        "assinado": _tem_assinatura(ptam),
        "valor_final": _valor_final(ptam),
        "secoes_completas": not faltando,
        "secoes_faltando": faltando,
    }
