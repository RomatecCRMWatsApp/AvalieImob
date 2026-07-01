# @module services.geo_urbano.assinatura_proprietario — assinatura DESENHADA do
# proprietário (Requerimento 2 vias + ART/TRT) via WhatsApp. REUSA a infra do
# doc-ext: carimbar_multi (carimbo do traço), gerar_token, Z-API e renderização.
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timezone

from services import r2_storage
from services.assinatura_cliente_carimbo import carimbar_multi
from services.contrato_exclusividade_assinatura import gerar_token
from services.geo_urbano import aprovacao as APROVACAO

logger = logging.getLogger("romatec")

# Peças que o PROPRIETÁRIO assina + rótulo. art_trt só entra se houver upload.
PECAS_PROPRIETARIO = [
    ("requerimento_cartorio", "Requerimento — Via Cartório"),
    ("requerimento_superintendencia", "Requerimento — Via Superintendência"),
    ("art_trt", "ART / TRT"),
]
# Usucapião vai ao Cartório de RI (sem Superintendência); a Ata é do tabelião (não
# entra na assinatura desenhada). O possuidor/advogado assina o Requerimento + ART/TRT.
PECAS_PROPRIETARIO_USUCAPIAO = [
    ("requerimento_usucapiao", "Requerimento de Usucapião"),
    ("art_trt", "ART / TRT"),
]


def pecas_proprietario(projeto: dict):
    """Peças que o proprietário/possuidor assina, conforme o tipo de serviço."""
    if (projeto.get("tipo_servico") or "remembramento") == "usucapiao":
        return PECAS_PROPRIETARIO_USUCAPIAO
    return PECAS_PROPRIETARIO


def _agora_iso():
    return datetime.now(timezone.utc).isoformat()


def signatarios_de(projeto: dict) -> list:
    """Quem assina por WhatsApp: requerente/possuidor (e herdeiro-usucapiente), cônjuge,
    representante/sócio E o ADVOGADO(A). Cada signatário traz `pecas` = as peças que
    ELE assina — o advogado assina SOMENTE o Requerimento; os demais, Requerimento +
    ART/TRT. (PJ requerente assina pelo representante legal.)"""
    todas = [k for k, _ in pecas_proprietario(projeto)]
    req_pecas = [k for k in todas if k.startswith("requerimento")]
    # QUEM assina o Requerimento por WhatsApp: requerente/possuidor, herdeiro, cônjuge,
    # representante/sócio (PJ) e o advogado. O PROPRIETÁRIO REGISTRAL (titular tabular —
    # muitas vezes FALECIDO) e as TESTEMUNHAS NÃO assinam aqui.
    ASSINAM = {"requerente", "herdeiro", "conjuge", "representante", "socio", "advogado"}
    out = []
    for p in projeto.get("partes") or []:
        papel = p.get("papel")
        if papel == "requerente" and p.get("tipo_pessoa") == "juridica":
            continue
        if p.get("falecido"):                                   # falecido não assina
            continue
        if not (papel in ASSINAM or p.get("usucapiente")):      # titular tabular/testemunha fora
            continue
        nome = p.get("nome") or p.get("razao_social")
        if not nome:
            continue
        pecas = req_pecas if papel == "advogado" else todas
        out.append({
            "parte_id": p.get("id"), "nome": nome, "papel": papel or "requerente",
            "cpf_cnpj": p.get("cpf") or p.get("cnpj"), "telefone": p.get("telefone"),
            "pecas": pecas,   # peças que ESTE signatário assina
        })
    return out


async def zapi_cfg(db, uid: str) -> dict:
    from services.integracoes_util import carregar_integracoes
    try:
        return await carregar_integracoes(db, uid, fallback_zapi=True)
    except TypeError:
        return await carregar_integracoes(db, uid)


def _guia_url() -> str:
    """URL pública do guia 'Como assinar' — reusa a mesma base do link de assinatura.
    Fallback seguro: '' quando a base não está configurada (envia só o link)."""
    try:
        from routes.assinatura_cliente import APP_URL
        base = (APP_URL or "").rstrip("/")
        return f"{base}/como-assinar" if base else ""
    except Exception:  # noqa: BLE001
        return ""


async def enviar_link(cfg: dict, telefone: str, nome: str, titulo: str, url: str):
    from services import zapi_service
    msg = (f"Olá, {nome}! Para assinar eletronicamente o(s) documento(s) do processo "
           f"de {titulo}, acesse o link e assine no celular (você pode DIGITAR ou DESENHAR):\n{url}")
    guia = _guia_url()
    if guia:
        msg += (f"\n\n👉 Primeira vez assinando? Veja o passo a passo (leva 1 minuto):\n{guia}")
    await zapi_service.send_text(
        instance_id=cfg.get("zapi_instance_id"), token=cfg.get("zapi_token"),
        security_token=cfg.get("zapi_security_token"), phone=telefone, message=msg)


def _parse_dt(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:  # noqa: BLE001
        return None


async def processar_carimbo(db, sessao: dict) -> dict:
    """Quando todos assinam: carimba o traço de cada signatário em cada peça,
    sobe os finais no R2 e marca a aprovação dos proprietários."""
    assinados = [s for s in (sessao.get("signatarios") or [])
                 if s.get("status") == "assinado" and s.get("traco_b64")]
    pdf_keys_final = {}
    for d in (sessao.get("documentos") or []):
        try:
            base = await asyncio.to_thread(r2_storage.download_bytes, d["pdf_key_base"])
        except Exception:  # noqa: BLE001
            continue
        sig_list = []
        for s in assinados:
            pos = (s.get("posicoes") or {}).get(d["doc"]) or []
            if not pos:
                continue
            sig_list.append({
                "nome": s.get("nome"), "cpf": s.get("cpf_cnpj") or "",
                "role": s.get("papel") or "proprietario",
                "traco_png": base64.b64decode(s["traco_b64"]),
                "ip": s.get("ip"), "geo_lat": s.get("geo_lat"), "geo_lng": s.get("geo_lng"),
                "user_agent": s.get("user_agent"),
                "assinado_em": _parse_dt(s.get("assinado_em")) or datetime.now(timezone.utc),
                "posicoes": pos,
            })
        if not sig_list:
            continue
        try:
            final, _sha = await asyncio.to_thread(carimbar_multi, base, sig_list)
            key = d["pdf_key_base"].replace("_base.pdf", "_final.pdf")
            await asyncio.to_thread(r2_storage.upload_bytes, final, key, "application/pdf")
            pdf_keys_final[d["doc"]] = key
        except Exception as e:  # noqa: BLE001
            logger.warning("Geo Urbano: carimbo da peça %s falhou: %s", d.get("doc"), e)

    await _marcar_aprovacao(db, sessao)
    await db.geo_urbano_assinatura_sessoes.update_one(
        {"id": sessao["id"]},
        {"$set": {"pdf_keys_final": pdf_keys_final, "status": "concluido", "updated_at": _agora_iso()}})
    return pdf_keys_final


async def _marcar_aprovacao(db, sessao: dict):
    """Marca aprovacao.proprietarios[].requerimento/art_trt no projeto + status."""
    pid = sessao.get("projeto_id")
    proj = await db.geo_urbano_projetos.find_one({"id": pid})
    if not proj:
        return
    docs = {d["doc"] for d in (sessao.get("documentos") or [])}
    tem_req = bool(docs & {"requerimento_cartorio", "requerimento_superintendencia", "requerimento_usucapiao"})
    tem_art = "art_trt" in docs
    aprov = dict(proj.get("aprovacao") or {})
    props = {p.get("parte_id"): dict(p) for p in (aprov.get("proprietarios") or [])}
    for s in (sessao.get("signatarios") or []):
        if s.get("status") != "assinado":
            continue
        pid_parte = s.get("parte_id") or s.get("id")
        rec = props.get(pid_parte) or {"parte_id": pid_parte, "requerimento": False, "art_trt": False}
        if tem_req:
            rec["requerimento"] = True
        if tem_art:
            rec["art_trt"] = True
        props[pid_parte] = rec
    aprov["proprietarios"] = list(props.values())
    aprov["status_geral"] = APROVACAO.status_geral(aprov)
    await db.geo_urbano_projetos.update_one(
        {"id": pid}, {"$set": {"aprovacao": aprov, "updated_at": _agora_iso()}})
