# @module routes.nfse — DANFSe (espelho da NFS-e) nos 3 temas Prime I / II / Tradicional.
"""Gera o PDF do DANFSe a partir de um documento (flat) via o engine ReportLab próprio.

Estado: o módulo de EMISSÃO de NFS-e (nfse_documentos/nfse_config, Sefin/gateway) ainda
NÃO existe; aqui entregamos o GERADOR visual do DANFSe — endpoints de exemplo/preview
(funcionais agora) + a rota por-id já cabeada p/ quando a coleção `nfse_documentos` existir.
Tema selecionável por ?tema=prime1|prime2|tradicional (default prime1).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from db import get_db
from dependencies import get_admin_user
from pdf.templates.registry import gerar_danfse, DANFSE_TEMPLATES_DISPONIVEIS
from pdf.templates.danfse_base import documento_exemplo_59

logger = logging.getLogger("romatec")

router = APIRouter(prefix="/nfse", tags=["NFS-e · DANFSe"])

_FLAT_KEYS = ("valor_servico", "prest_razao", "numero_nfse")


def _tema(t: str | None) -> str:
    t = (t or "prime1").lower().strip()
    return t if t in DANFSE_TEMPLATES_DISPONIVEIS else "prime1"


def _adaptar(nfse_doc: dict) -> dict:
    """Mapa PROVISÓRIO nfse_documentos (aninhado, SPEC) → doc FLAT do DANFSe.
    Se o doc já vier flat (tem chaves do HTML), usa direto."""
    if any(k in nfse_doc for k in _FLAT_KEYS):
        return nfse_doc
    serv = nfse_doc.get("servico") or {}
    tom = nfse_doc.get("tomador") or {}
    return {
        "numero_nfse": nfse_doc.get("numero_nfse") or "0000000000",
        "chave_acesso": nfse_doc.get("chave_acesso") or "",
        "discriminacao": serv.get("discriminacao") or (nfse_doc.get("origem") or {}).get("descricao") or "",
        "cod_atividade": serv.get("codigo_tributacao_municipal") or "",
        "tom_razao": tom.get("razao_nome") or "", "tom_email": tom.get("email") or "",
        "tom_cnpj": tom.get("documento") or "",
        "valor_servico": serv.get("valor_servico") or 0, "deducao": serv.get("valor_deducoes") or 0,
        "desc_incond": serv.get("desconto_incondicionado") or 0, "desc_cond": serv.get("desconto_condicionado") or 0,
        "aliquota_iss": serv.get("aliquota_iss") or 0, "iss_retido_v": serv.get("valor_iss") if serv.get("iss_retido") else 0,
        "ibs_mun": (serv.get("ibscbs") or {}).get("valor_ibs_municipal") or 0,
        "ibs_est": (serv.get("ibscbs") or {}).get("valor_ibs_estadual") or 0,
        "cbs": (serv.get("ibscbs") or {}).get("valor_cbs") or 0,
        "template_danfse": nfse_doc.get("template_danfse") or "prime1",
    }


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/danfse/exemplo")
async def danfse_exemplo(tema: str = Query("prime1"), _admin: str = Depends(get_admin_user)):
    """Preview do DANFSe com o caso real NFS-e 59 (Açailândia) no tema escolhido."""
    pdf = gerar_danfse(documento_exemplo_59(), _tema(tema))
    return _pdf_response(pdf, f"danfse-exemplo-{_tema(tema)}.pdf")


@router.post("/danfse/preview")
async def danfse_preview(doc: dict, tema: str = Query("prime1"), _admin: str = Depends(get_admin_user)):
    """Renderiza um DANFSe a partir de um documento FLAT enviado (modal de emissão)."""
    try:
        pdf = gerar_danfse(doc or {}, _tema(tema))
    except Exception as e:  # noqa: BLE001
        logger.exception("danfse_preview: erro ao gerar")
        raise HTTPException(500, "Falha ao gerar o DANFSe.") from e
    return _pdf_response(pdf, f"danfse-preview-{_tema(tema)}.pdf")


@router.get("/documentos/{doc_id}/danfse")
async def danfse_documento(doc_id: str, tema: str | None = Query(None),
                           db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """DANFSe de um documento de nfse_documentos. (Coleção criada pelo módulo de emissão.)"""
    nfse = await db.nfse_documentos.find_one({"id": doc_id}) or await db.nfse_documentos.find_one({"_id": doc_id})
    if not nfse:
        raise HTTPException(404, "Documento NFS-e não encontrado.")
    flat = _adaptar(nfse)
    escolhido = _tema(tema or flat.get("template_danfse"))
    pdf = gerar_danfse(flat, escolhido)
    return _pdf_response(pdf, f"danfse-{doc_id}-{escolhido}.pdf")
