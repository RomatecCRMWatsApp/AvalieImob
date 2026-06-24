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


# ===========================================================================
# Emissão — config por município, teste de certificado, preview da DPS, emitir.
# SEGURANÇA: a transmissão real é travada (sefin.transmissao_habilitada). Estes
# endpoints montam/validam/persistem; emitir() NÃO transmite até habilitar.
# ===========================================================================
async def _carregar_config(db, config_id: str):
    from models.nfse import NFSeConfig
    doc = await db.nfse_config.find_one({"id": config_id})
    if not doc:
        raise HTTPException(404, "Configuração NFS-e não encontrada.")
    doc.pop("_id", None)
    return NFSeConfig(**doc)


@router.get("/config")
async def listar_config(db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    from services.nfse.repository import listar_configs
    return [{k: v for k, v in c.items() if k != "_id"} for c in await listar_configs(db)]


@router.post("/config")
async def criar_config(body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    from models.nfse import NFSeConfig
    from services.nfse.repository import criar_config as repo_criar
    data = dict(body or {})
    for k in ("id", "_id", "created_at", "updated_at"):  # gerados pelo modelo; null quebra a validação
        if not data.get(k):
            data.pop(k, None)
    try:
        cfg = NFSeConfig(**data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, f"Config inválida: {e}")
    await repo_criar(db, cfg.model_dump(mode="json"))
    return cfg.model_dump(mode="json")


@router.put("/config/{config_id}")
async def atualizar_config(config_id: str, body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    from services.nfse.repository import atualizar_config as repo_upd
    body.pop("id", None); body.pop("_id", None)
    doc = await repo_upd(db, config_id, body)
    if not doc:
        raise HTTPException(404, "Configuração não encontrada.")
    doc.pop("_id", None)
    return doc


@router.post("/config/{config_id}/testar-cert")
async def testar_cert(config_id: str, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """Carrega o e-CNPJ já cadastrado (db.certificados, perfil PJ) — sem transmitir nada."""
    from services.nfse.sefin.certificado import carregar_para_emissao
    cfg = await _carregar_config(db, config_id)
    try:
        cc = await carregar_para_emissao(db, _admin, cfg.sefin.model_dump())
        return {"ok": True, "titular": cc.titular}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "erro": str(e)}


def _doc_de_body(cfg, body: dict):
    """Constrói NFSeDocumento (sem persistir) a partir do corpo {tomador, servico, origem}."""
    from models.nfse import NFSeDocumento, Servico, Tomador, Origem, DPS
    serv = Servico(**(body.get("servico") or {}))
    tom = Tomador(**(body.get("tomador") or {}))
    org = Origem(**(body.get("origem") or {"tipo": "servico_avulso"}))
    return NFSeDocumento(config_id=cfg.id, provider=cfg.provider, ambiente=cfg.ambiente,
                         origem=org, tomador=tom, servico=serv,
                         dps=DPS(serie=cfg.sefin.serie_dps or "1", numero=0, id_dps="DPS-PREVIEW"),
                         template_danfse=cfg.template_danfse)


@router.post("/dps/preview")
async def dps_preview(body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """Monta o XML da DPS (sem assinar/transmitir) e valida contra o XSD (se NFSE_DPS_XSD)."""
    import os
    from services.nfse.sefin.dps_xml import montar_dps_xml, validar_dps_xsd
    cfg = await _carregar_config(db, body.get("config_id"))
    doc = _doc_de_body(cfg, body)
    xml = montar_dps_xml(doc, cfg, pretty=True)
    valido, erros = None, []
    xsd = os.environ.get("NFSE_DPS_XSD")
    if xsd and os.path.exists(xsd):
        valido, erros = validar_dps_xsd(xml, xsd)
    return {"xml": xml, "valido": valido, "erros": erros[:8]}


@router.post("/abrasf/preview")
async def abrasf_preview(body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """Monta o XML do RPS/Lote (ABRASF 1.0) sem assinar/transmitir + valida contra o XSD oficial."""
    from services.nfse.abrasf.rps_xml import montar_lote_rps_xml, validar_rps_xsd
    cfg = await _carregar_config(db, body.get("config_id"))
    doc = _doc_de_body(cfg, body)
    xml = montar_lote_rps_xml(doc, cfg, pretty=True)
    valido, erros = validar_rps_xsd(xml)
    return {"xml": xml, "valido": valido, "erros": erros}


@router.post("/abrasf/testar-envio")
async def abrasf_testar_envio(body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """Envia 1 RPS ao webservice de TESTE do SpeedGov (homologação) e devolve a resposta CRUA.
    NÃO persiste nota fiscal e usa SEMPRE `abrasf.url_ws` (ambiente de teste, nunca produção)."""
    from datetime import datetime, timezone
    from services.nfse.abrasf.rps_xml import montar_lote_rps_xml, montar_cabecalho
    from services.nfse.abrasf.assinatura_abrasf import assinar_lote_rps
    from services.nfse.abrasf.soap_client import AbrasfClient, montar_envelope_soap
    from services.nfse.sefin.certificado import carregar_para_emissao
    cfg = await _carregar_config(db, body.get("config_id"))
    a = cfg.abrasf
    url_ws = a.url_ws or "http://speedgov.com.br/wsmod/Nfes"   # fallback p/ o endpoint de teste
    doc = _doc_de_body(cfg, body)
    doc.dps.numero = int(body.get("numero") or 1)
    doc.dps.data_emissao = datetime.now(timezone.utc)
    try:
        cc = await carregar_para_emissao(db, _admin, {"certificado_id": a.certificado_id})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "etapa": "certificado", "erro": str(e)[:800]}
    try:
        xml = montar_lote_rps_xml(doc, cfg)
        # Manual SpeedGov: o XML DEVE ser assinado digitalmente (produção). Sempre assina.
        xml = assinar_lote_rps(xml, cc.key_pem, cc.cert_pem,
                               sha=a.assinatura_sha, namespace=a.namespace)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "etapa": "assinatura", "erro": str(e)[:800]}
    try:
        header = montar_cabecalho()
        envelope = montar_envelope_soap(a.operacao_envio, header, xml, a.namespace_ws)
        resp = await AbrasfClient(url_ws, None).chamar(a.soap_action, envelope)
        from services.nfse.abrasf.resposta import parse_resposta
        # xml_enviado = os bytes EXATOS do EnviarLoteRpsEnvio assinado (p/ validar na ferramenta oficial)
        return {"ok": True, "url": url_ws, "resposta": resp[:9000],
                "parsed": parse_resposta(resp), "xml_enviado": xml}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "etapa": "envio", "url": url_ws, "erro": str(e)[:1200], "xml_enviado": xml}


@router.post("/abrasf/consultar-rps")
async def abrasf_consultar_rps(body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """Consulta no SpeedGov se uma NFS-e foi gerada a partir de um RPS (ConsultarNfsePorRps).
    Útil p/ investigar o retorno vazio do RecepcionarLoteRps. Devolve a resposta crua."""
    from services.nfse.abrasf.rps_xml import montar_consultar_nfse_rps_xml, montar_cabecalho
    from services.nfse.abrasf.soap_client import AbrasfClient, montar_envelope_soap
    cfg = await _carregar_config(db, body.get("config_id"))
    a = cfg.abrasf
    url_ws = a.url_ws or "http://speedgov.com.br/wsmod/Nfes"
    numero = body.get("numero") or 1
    xml = montar_consultar_nfse_rps_xml(cfg, numero, a.serie_rps or "1", a.tipo_rps or "1")
    header = montar_cabecalho()
    envelope = montar_envelope_soap(a.operacao_consulta_rps or "ConsultarNfsePorRps", header, xml, a.namespace_ws)
    try:
        resp = await AbrasfClient(url_ws, None).chamar(a.soap_action, envelope)
        from services.nfse.abrasf.resposta import parse_resposta
        return {"ok": True, "resposta": resp[:9000], "parsed": parse_resposta(resp)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "erro": str(e)[:1200]}


@router.post("/emitir")
async def emitir(body: dict, db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    """Prepara a DPS (numera + calcula + persiste pendente) e tenta emitir.
    A transmissão é TRAVADA (status volta 'erro' com a mensagem) até habilitar."""
    from services.nfse import service as nfse_service
    cfg = await _carregar_config(db, body.get("config_id"))
    base = _doc_de_body(cfg, body)
    doc = await nfse_service.preparar_documento(db, cfg, base.origem, base.tomador, base.servico)
    resultado = await nfse_service.emitir(db, cfg, doc, owner_uid=_admin)
    return resultado.model_dump(mode="json")


@router.get("/documentos")
async def listar_documentos(status: str | None = Query(None), db=Depends(get_db), _admin: str = Depends(get_admin_user)):
    from services.nfse.repository import listar_documentos as repo_list
    filtro = {"status": status} if status else {}
    return [{k: v for k, v in d.items() if k != "_id"} for d in await repo_list(db, filtro)]
