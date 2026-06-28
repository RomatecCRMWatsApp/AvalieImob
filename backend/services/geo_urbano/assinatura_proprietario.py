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


def _agora_iso():
    return datetime.now(timezone.utc).isoformat()


def signatarios_de(projeto: dict) -> list:
    """Quem assina pelo proprietário: PF requerente, representante, sócio, cônjuge.
    (PJ requerente assina pelo representante legal.)"""
    out = []
    for p in projeto.get("partes") or []:
        papel = p.get("papel")
        if papel == "requerente" and p.get("tipo_pessoa") == "juridica":
            continue
        nome = p.get("nome") or p.get("razao_social")
        if not nome:
            continue
        out.append({
            "parte_id": p.get("id"), "nome": nome, "papel": papel or "requerente",
            "cpf_cnpj": p.get("cpf") or p.get("cnpj"), "telefone": p.get("telefone"),
        })
    return out


async def zapi_cfg(db, uid: str) -> dict:
    from services.integracoes_util import carregar_integracoes
    try:
        return await carregar_integracoes(db, uid, fallback_zapi=True)
    except TypeError:
        return await carregar_integracoes(db, uid)


async def enviar_link(cfg: dict, telefone: str, nome: str, titulo: str, url: str):
    from services import zapi_service
    msg = (f"Olá, {nome}! Para assinar eletronicamente o(s) documento(s) do processo "
           f"de {titulo}, acesse o link e desenhe sua assinatura no celular:\n{url}")
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
    tem_req = bool(docs & {"requerimento_cartorio", "requerimento_superintendencia"})
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
