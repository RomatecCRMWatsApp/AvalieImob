# @module routes.geo_urbano_publico — assinatura DESENHADA do proprietário (público).
#
# Espelha documentos_externos_publico: o proprietário abre o link do WhatsApp,
# vê as peças (Requerimento 2 vias + ART/TRT) e desenha a assinatura no celular.
# Quando todos assinam, dispara o carimbo + marca a aprovação no projeto.
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from services import r2_storage
from services.geo_urbano import assinatura_proprietario as PROP

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)
router_publico = APIRouter(prefix="/publico/geo-urbano", tags=["Geo Urbano Público"])


def _agora():
    return datetime.now(timezone.utc)


async def _sessao_por_token(db, token: str):
    s = await db.geo_urbano_assinatura_sessoes.find_one({"signatarios.token": token})
    if not s:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado.")
    sig = next((x for x in s.get("signatarios") or [] if x.get("token") == token), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Assinante não encontrado.")
    return s, sig


@router_publico.get("/{token}")
@limiter.limit("30/minute")
async def obter_por_token(token: str, request: Request, db=Depends(get_db)):
    s, sig = await _sessao_por_token(db, token)
    documentos = []
    for d in s.get("documentos") or []:
        pos = (sig.get("posicoes") or {}).get(d["doc"]) or []
        paginas = d.get("paginas_render")   # cache criado no envio (prop_posicionar)
        if paginas is None:                 # sessão antiga sem cache: renderiza 1x e GUARDA
            from services.pdf_preview import renderizar_paginas
            try:
                raw = await asyncio.to_thread(r2_storage.download_bytes, d["pdf_key_base"])
                paginas = await asyncio.to_thread(renderizar_paginas, raw, 110, 30)
            except Exception:  # noqa: BLE001
                paginas = []
            try:
                await db.geo_urbano_assinatura_sessoes.update_one(
                    {"id": s["id"], "documentos.doc": d["doc"]},
                    {"$set": {"documentos.$.paginas_render": paginas}})
            except Exception:  # noqa: BLE001
                pass
        documentos.append({"doc": d["doc"], "titulo": d["titulo"], "paginas": paginas, "posicoes": pos})
    from services.fontes_assinatura import fontes_disponiveis
    return {"ok": True, "nome": sig.get("nome"), "papel": sig.get("papel"),
            "ja_assinado": sig.get("status") == "assinado",
            "concluido": s.get("status") == "concluido", "documentos": documentos,
            "fontes": fontes_disponiveis(), "modalidades": ["desenhada", "digitada"]}


@router_publico.post("/{token}")
@limiter.limit("10/minute")
async def assinar(token: str, payload: dict, request: Request, db=Depends(get_db)):
    import base64
    from utils.cpf import limpar_cpf, validar_cpf
    s, sig = await _sessao_por_token(db, token)
    if sig.get("status") == "assinado":
        return {"ok": True, "ja_assinado": True, "concluido": s.get("status") == "concluido"}
    p = payload or {}
    if not p.get("concordo"):
        raise HTTPException(status_code=422, detail="É necessário concordar para assinar.")
    tipo = p.get("tipo_assinatura") or "desenhada"
    nome = (p.get("nome_assinante") or sig.get("nome") or "").strip()
    cpf = limpar_cpf(p.get("cpf_assinante"))
    fonte = None
    if tipo == "digitada":
        # DIGITADA: nome na fonte cursiva → PNG (reusa o carimbo do traço)
        from services import fontes_assinatura as FA
        fonte = p.get("fonte_assinatura")
        if fonte not in FA.FONTES_ASSINATURA:
            raise HTTPException(status_code=422, detail="Fonte de assinatura inválida.")
        if len(nome) < 3:
            raise HTTPException(status_code=422, detail="Informe o nome completo.")
        if not validar_cpf(cpf):
            raise HTTPException(status_code=422, detail="CPF inválido.")
        png = await asyncio.to_thread(FA.render_assinatura_png, nome, fonte)
        traco_b64 = base64.b64encode(png).decode()
    else:
        # DESENHADA (legado): traço PNG do canvas; CPF recomendado (validado se informado)
        traco = p.get("traco_base64") or ""
        if not traco.startswith("data:image/png;base64,"):
            raise HTTPException(status_code=422, detail="Assinatura inválida.")
        if cpf and not validar_cpf(cpf):
            raise HTTPException(status_code=422, detail="CPF inválido.")
        traco_b64 = traco.split(",", 1)[1]
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "") or "").split(",")[0].strip()
    ua = (request.headers.get("user-agent") or "")[:255]
    upd = {
        "status": "assinado", "assinado_em": _agora().isoformat(),
        "ip": ip, "user_agent": ua,
        "geo_lat": p.get("geo_lat"), "geo_lng": p.get("geo_lng"),
        "traco_b64": traco_b64,
        "tipo_assinatura": tipo, "nome_assinante": nome or sig.get("nome"),
        "cpf_assinante": cpf or None, "fonte_assinatura": fonte,
    }
    if cpf:
        upd["cpf_cnpj"] = cpf   # p/ o carimbo/folha de autoria exibir o CPF
    for k, v in upd.items():
        sig[k] = v
    await db.geo_urbano_assinatura_sessoes.update_one(
        {"id": s["id"], "signatarios.token": token},
        {"$set": {**{f"signatarios.$.{k}": v for k, v in upd.items()}, "updated_at": _agora().isoformat()}})

    s = await db.geo_urbano_assinatura_sessoes.find_one({"id": s["id"]})
    todos = all(x.get("status") in ("assinado", "recusado") for x in s.get("signatarios") or [])
    algum = any(x.get("status") == "assinado" for x in s.get("signatarios") or [])
    concluido = False
    if todos and algum:
        try:
            await PROP.processar_carimbo(db, s)
            concluido = True
        except Exception as e:  # noqa: BLE001
            logger.error("Geo Urbano: processar_carimbo falhou: %s", e, exc_info=True)
    else:
        await db.geo_urbano_assinatura_sessoes.update_one(
            {"id": s["id"]}, {"$set": {"status": "parcial", "updated_at": _agora().isoformat()}})
    return {"ok": True, "ja_assinado": False, "concluido": concluido}
