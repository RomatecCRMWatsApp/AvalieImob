# @module routes.consulta — Consulta rápida CNPJ (Receita Federal) e validação de CPF
"""
Consulta CNPJ com fallback em cascata e validação matemática de CPF.

CNPJ:  ProspectaBR (VPS própria) -> CNPJ.ws (público) -> ReceitaWS (público)
CPF:   validação local dos dígitos verificadores (sem base nominal)

O server.py registra todos os routers sob o prefixo /api, então os caminhos
finais expostos são:
    GET /api/consulta/cnpj/{cnpj}
    GET /api/consulta/cpf/validar?cpf=...&data_nascimento=YYYY-MM-DD
"""
import os
import re
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber
from services.pdf_consulta import gerar_pdf_cnpj, gerar_pdf_cpf
from services.integracoes_util import carregar_integracoes

router = APIRouter(prefix="/consulta", tags=["Consulta"])
logger = logging.getLogger("romatec")


# ------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------
def limpar_digitos(valor: str) -> str:
    return re.sub(r"[^\d]", "", valor or "")


def formatar_cnpj(cnpj: str) -> str:
    c = limpar_digitos(cnpj)
    if len(c) != 14:
        return cnpj
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def validar_cnpj(cnpj: str) -> bool:
    c = limpar_digitos(cnpj)
    if len(c) != 14 or c == c[0] * 14:
        return False

    def calc(base: str, pesos: list[int]) -> int:
        s = sum(int(base[i]) * pesos[i] for i in range(len(pesos)))
        r = s % 11
        return 0 if r < 2 else 11 - r

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return calc(c, p1) == int(c[12]) and calc(c, p2) == int(c[13])


def validar_cpf(cpf: str) -> bool:
    c = limpar_digitos(cpf)
    if len(c) != 11 or c == c[0] * 11:
        return False

    def calc(base: str, n: int) -> int:
        s = sum(int(base[i]) * (n - i) for i in range(n - 1))
        r = s % 11
        return 0 if r < 2 else 11 - r

    return calc(c, 10) == int(c[9]) and calc(c, 11) == int(c[10])


def _float_safe(valor) -> float:
    """Converte capital_social para float, tolerando os 3 formatos das fontes:
    número puro (120000000000.0), string BR ("1.000.000,00") e
    string com ponto decimal ("120000000000.00")."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = re.sub(r"[^\d.,]", "", str(valor)).strip()  # mantém dígitos, ponto e vírgula
    if not s:
        return 0.0
    if "," in s and "." in s:
        # formato BR: ponto = milhar, vírgula = decimal -> "1.000.000,00"
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # só vírgula = separador decimal -> "1000000,00"
        s = s.replace(",", ".")
    # só ponto (ou só dígitos): ponto já é o decimal -> "120000000000.00"
    try:
        return float(s)
    except ValueError:
        return 0.0


# ------------------------------------------------------------------
# Fontes CNPJ (fallback em cascata)
# ------------------------------------------------------------------
async def consultar_cnpj_prospectabr(cnpj: str) -> dict | None:
    host = os.getenv("PROSPECTABR_HOST", "").strip()
    if not host:
        return None
    token = os.getenv("PROSPECTABR_TOKEN", "").strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{host.rstrip('/')}/api/cnpj/{cnpj}",
                headers={"Authorization": f"Bearer {token}"} if token else {},
            )
            if r.status_code != 200:
                return None
            d = r.json()
            nat = d.get("natureza_juridica")
            return {
                "cnpj": cnpj,
                "razao_social": d.get("razao_social", ""),
                "nome_fantasia": d.get("nome_fantasia", ""),
                "situacao": d.get("situacao_cadastral", ""),
                "data_abertura": d.get("data_inicio_atividade", ""),
                "natureza_juridica": nat.get("descricao", "") if isinstance(nat, dict) else str(nat or ""),
                "atividade_principal": d.get("cnae_fiscal_descricao", ""),
                "logradouro": d.get("logradouro", ""),
                "numero": d.get("numero", ""),
                "bairro": d.get("bairro", ""),
                "municipio": d.get("municipio", ""),
                "uf": d.get("uf", ""),
                "cep": d.get("cep", ""),
                "telefone": d.get("ddd_telefone_1", ""),
                "email": d.get("email", ""),
                "capital_social": _float_safe(d.get("capital_social")),
                "porte": d.get("porte", ""),
                "fonte": "prospectabr",
            }
    except Exception as e:
        logger.warning("ProspectaBR falhou para %s: %s", cnpj, e)
        return None


async def consultar_cnpj_cnpjws(cnpj: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"https://publica.cnpj.ws/cnpj/{cnpj}")
            if r.status_code != 200:
                return None
            d = r.json()
            est = d.get("estabelecimento", {}) or {}
            ativ = est.get("atividade_principal", {})
            ativ_desc = ativ.get("descricao", "") if isinstance(ativ, dict) else ""
            nat = d.get("natureza_juridica")
            cidade = est.get("cidade")
            estado = est.get("estado")
            tel = f"{est.get('ddd1', '')}{est.get('telefone1', '')}" if est.get("telefone1") else ""
            return {
                "cnpj": cnpj,
                "razao_social": d.get("razao_social", ""),
                "nome_fantasia": est.get("nome_fantasia", ""),
                "situacao": est.get("situacao_cadastral", ""),
                "data_abertura": est.get("data_inicio_atividade", ""),
                "natureza_juridica": nat.get("descricao", "") if isinstance(nat, dict) else "",
                "atividade_principal": ativ_desc,
                "logradouro": est.get("logradouro", ""),
                "numero": est.get("numero", ""),
                "bairro": est.get("bairro", ""),
                "municipio": cidade.get("nome", "") if isinstance(cidade, dict) else "",
                "uf": estado.get("sigla", "") if isinstance(estado, dict) else "",
                "cep": est.get("cep", ""),
                "telefone": tel,
                "email": est.get("email", ""),
                "capital_social": _float_safe(d.get("capital_social")),
                "porte": d.get("porte", {}).get("descricao", "") if isinstance(d.get("porte"), dict) else "",
                "fonte": "cnpjws",
            }
    except Exception as e:
        logger.warning("CNPJ.ws falhou para %s: %s", cnpj, e)
        return None


async def consultar_cnpj_receitaws(cnpj: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"https://receitaws.com.br/v1/cnpj/{cnpj}")
            if r.status_code != 200:
                return None
            d = r.json()
            if d.get("status") == "ERROR":
                return None
            ativ = d.get("atividade_principal", [{}]) or [{}]
            ativ_desc = ativ[0].get("text", "") if ativ else ""
            return {
                "cnpj": cnpj,
                "razao_social": d.get("nome", ""),
                "nome_fantasia": d.get("fantasia", ""),
                "situacao": d.get("situacao", ""),
                "data_abertura": d.get("abertura", ""),
                "natureza_juridica": d.get("natureza_juridica", ""),
                "atividade_principal": ativ_desc,
                "logradouro": d.get("logradouro", ""),
                "numero": d.get("numero", ""),
                "bairro": d.get("bairro", ""),
                "municipio": d.get("municipio", ""),
                "uf": d.get("uf", ""),
                "cep": d.get("cep", ""),
                "telefone": d.get("telefone", ""),
                "email": d.get("email", ""),
                "capital_social": _float_safe(d.get("capital_social")),
                "porte": d.get("porte", ""),
                "fonte": "receitaws",
            }
    except Exception as e:
        logger.warning("ReceitaWS falhou para %s: %s", cnpj, e)
        return None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.get("/cnpj/{cnpj}")
async def get_cnpj(cnpj: str):
    c = limpar_digitos(cnpj)
    if not validar_cnpj(c):
        raise HTTPException(status_code=400, detail="CNPJ inválido")

    resultado = (
        await consultar_cnpj_prospectabr(c)
        or await consultar_cnpj_cnpjws(c)
        or await consultar_cnpj_receitaws(c)
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado")

    resultado["cnpj"] = formatar_cnpj(resultado.get("cnpj", c))
    return resultado


@router.get("/cpf/validar")
async def validar_cpf_endpoint(cpf: str, data_nascimento: str | None = None):
    """Valida CPF localmente (dígitos verificadores). Não consulta base nominal."""
    c = limpar_digitos(cpf)
    valido = validar_cpf(c)
    formatado = f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else cpf

    return {
        "cpf": formatado,
        "valido": valido,
        "mensagem": "CPF válido" if valido else "CPF inválido — dígitos verificadores incorretos",
        "data_nascimento_informada": data_nascimento,
        "observacao": "Validação matemática local. Para consulta nominal, integre com Serpro/GOV.BR.",
    }


# ------------------------------------------------------------------
# PDF da consulta CNPJ — visualizar / baixar / enviar (WhatsApp, Telegram)
# Recebem o `dados` já normalizado pelo frontend (evita refetch nas fontes).
# ------------------------------------------------------------------
class CnpjPdfRequest(BaseModel):
    dados: dict


class CnpjWhatsAppRequest(BaseModel):
    dados: dict
    phone: str
    legenda: Optional[str] = ""


class CnpjTelegramRequest(BaseModel):
    dados: dict
    chat_id: Optional[str] = ""
    legenda: Optional[str] = ""


async def _perfil_avaliador(db, uid: str) -> dict:
    p = await db.perfil_avaliador.find_one({"user_id": uid})
    if p:
        p.pop("_id", None)
    return p or {}


def _nome_arquivo_cnpj(dados: dict) -> str:
    c = limpar_digitos(dados.get("cnpj", "") or "")
    return f"CNPJ_{c or 'consulta'}.pdf"


def _legenda_padrao(dados: dict) -> str:
    razao = (dados.get("razao_social") or "").strip()
    cnpj = (dados.get("cnpj") or "").strip()
    return f"Consulta CNPJ — {razao} ({cnpj})".strip(" —()")


@router.post("/cnpj/pdf")
async def cnpj_pdf(
    body: CnpjPdfRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera o PDF do resultado da consulta CNPJ (inline para visualizar/baixar)."""
    perfil = await _perfil_avaliador(db, uid)
    pdf = gerar_pdf_cnpj(body.dados, perfil)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{_nome_arquivo_cnpj(body.dados)}"'},
    )


@router.post("/cnpj/whatsapp")
async def cnpj_whatsapp(
    body: CnpjWhatsAppRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia o PDF da consulta CNPJ via WhatsApp do usuário (Z-API ou Meta)."""
    from services import zapi_service
    from services import meta_whatsapp_service as meta

    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail="Nenhum provedor WhatsApp configurado. Cadastre Z-API ou Meta em Configurações → Integrações.",
        )
    perfil = await _perfil_avaliador(db, uid)
    pdf = gerar_pdf_cnpj(body.dados, perfil)
    nome = _nome_arquivo_cnpj(body.dados)
    legenda = body.legenda or _legenda_padrao(body.dados)
    provider = (cfg.get("whatsapp_provider") or "zapi").lower()

    if provider == "meta":
        if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
            raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada. Cadastre em Configurações → Integrações.")
        try:
            resp = await meta.send_pdf(
                phone_number_id=cfg["meta_phone_number_id"],
                access_token=cfg["meta_access_token"],
                phone=body.phone, pdf_bytes=pdf, filename=nome, caption=legenda,
            )
            return {"ok": True, "provider": "meta", "response": resp}
        except Exception as e:
            logger.error("Erro Meta WhatsApp (consulta): %s", e)
            raise HTTPException(status_code=502, detail=f"Erro Meta WhatsApp: {e}")

    if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurada. Cadastre em Configurações → Integrações.")
    try:
        resp = await zapi_service.send_document_pdf(
            instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=body.phone, pdf_bytes=pdf, filename=nome, caption=legenda,
        )
        return {"ok": True, "provider": "zapi", "response": resp}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erro Z-API (consulta): %s", e)
        raise HTTPException(status_code=502, detail=f"Erro Z-API: {e}")


@router.post("/cnpj/telegram")
async def cnpj_telegram(
    body: CnpjTelegramRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia o PDF da consulta CNPJ via bot Telegram do usuário."""
    cfg = await carregar_integracoes(db, uid)
    bot_token = (cfg or {}).get("telegram_bot_token")
    if not bot_token:
        raise HTTPException(status_code=400, detail="Telegram não configurado. Cadastre seu bot_token em Configurações → Integrações.")
    chat_id = (body.chat_id or "").strip() or (cfg or {}).get("telegram_chat_id_default")
    if not chat_id:
        raise HTTPException(status_code=400, detail="Informe um chat_id ou configure um padrão em Configurações → Integrações.")

    perfil = await _perfil_avaliador(db, uid)
    pdf = gerar_pdf_cnpj(body.dados, perfil)
    nome = _nome_arquivo_cnpj(body.dados)
    legenda = body.legenda or _legenda_padrao(body.dados)

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            files = {"document": (nome, pdf, "application/pdf")}
            data = {"chat_id": chat_id, "caption": legenda}
            r = await client.post(url, data=data, files=files)
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Telegram erro {r.status_code}: {r.text[:200]}")
            return {"ok": True, "telegram_response": r.json()}
    except httpx.HTTPError as e:
        logger.error("Erro ao enviar Telegram (consulta): %s", e)
        raise HTTPException(status_code=502, detail=f"Erro de rede ao enviar Telegram: {e}")


# ------------------------------------------------------------------
# Helpers de envio compartilhados (WhatsApp / Telegram) — usados pelo CPF
# ------------------------------------------------------------------
async def _enviar_whatsapp_pdf(db, uid: str, phone: str, pdf: bytes, nome: str, legenda: str):
    from services import zapi_service
    from services import meta_whatsapp_service as meta

    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(status_code=400, detail="Nenhum provedor WhatsApp configurado. Cadastre Z-API ou Meta em Configurações → Integrações.")
    provider = (cfg.get("whatsapp_provider") or "zapi").lower()
    if provider == "meta":
        if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
            raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada. Cadastre em Configurações → Integrações.")
        try:
            resp = await meta.send_pdf(
                phone_number_id=cfg["meta_phone_number_id"], access_token=cfg["meta_access_token"],
                phone=phone, pdf_bytes=pdf, filename=nome, caption=legenda,
            )
            return {"ok": True, "provider": "meta", "response": resp}
        except Exception as e:
            logger.error("Erro Meta WhatsApp (consulta): %s", e)
            raise HTTPException(status_code=502, detail=f"Erro Meta WhatsApp: {e}")
    if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurada. Cadastre em Configurações → Integrações.")
    try:
        resp = await zapi_service.send_document_pdf(
            instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=phone, pdf_bytes=pdf, filename=nome, caption=legenda,
        )
        return {"ok": True, "provider": "zapi", "response": resp}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erro Z-API (consulta): %s", e)
        raise HTTPException(status_code=502, detail=f"Erro Z-API: {e}")


async def _enviar_telegram_pdf(db, uid: str, chat_id: str, pdf: bytes, nome: str, legenda: str):
    cfg = await carregar_integracoes(db, uid)
    bot_token = (cfg or {}).get("telegram_bot_token")
    if not bot_token:
        raise HTTPException(status_code=400, detail="Telegram não configurado. Cadastre seu bot_token em Configurações → Integrações.")
    chat = (chat_id or "").strip() or (cfg or {}).get("telegram_chat_id_default")
    if not chat:
        raise HTTPException(status_code=400, detail="Informe um chat_id ou configure um padrão em Configurações → Integrações.")
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            files = {"document": (nome, pdf, "application/pdf")}
            data = {"chat_id": chat, "caption": legenda}
            r = await client.post(url, data=data, files=files)
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Telegram erro {r.status_code}: {r.text[:200]}")
            return {"ok": True, "telegram_response": r.json()}
    except httpx.HTTPError as e:
        logger.error("Erro ao enviar Telegram (consulta): %s", e)
        raise HTTPException(status_code=502, detail=f"Erro de rede ao enviar Telegram: {e}")


# ------------------------------------------------------------------
# PDF da validação de CPF — visualizar / baixar / enviar
# ------------------------------------------------------------------
class CpfPdfRequest(BaseModel):
    dados: dict


class CpfWhatsAppRequest(BaseModel):
    dados: dict
    phone: str
    legenda: Optional[str] = ""


class CpfTelegramRequest(BaseModel):
    dados: dict
    chat_id: Optional[str] = ""
    legenda: Optional[str] = ""


def _nome_arquivo_cpf(dados: dict) -> str:
    c = limpar_digitos(dados.get("cpf", "") or "")
    return f"CPF_{c or 'validacao'}.pdf"


def _legenda_cpf(dados: dict) -> str:
    cpf = (dados.get("cpf") or "").strip()
    st = "válido" if dados.get("valido") else "inválido"
    return f"Validação de CPF {cpf} — {st}".strip()


@router.post("/cpf/pdf")
async def cpf_pdf(
    body: CpfPdfRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    perfil = await _perfil_avaliador(db, uid)
    pdf = gerar_pdf_cpf(body.dados, perfil)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{_nome_arquivo_cpf(body.dados)}"'},
    )


@router.post("/cpf/whatsapp")
async def cpf_whatsapp(
    body: CpfWhatsAppRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    perfil = await _perfil_avaliador(db, uid)
    pdf = gerar_pdf_cpf(body.dados, perfil)
    legenda = body.legenda or _legenda_cpf(body.dados)
    return await _enviar_whatsapp_pdf(db, uid, body.phone, pdf, _nome_arquivo_cpf(body.dados), legenda)


@router.post("/cpf/telegram")
async def cpf_telegram(
    body: CpfTelegramRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    perfil = await _perfil_avaliador(db, uid)
    pdf = gerar_pdf_cpf(body.dados, perfil)
    legenda = body.legenda or _legenda_cpf(body.dados)
    return await _enviar_telegram_pdf(db, uid, body.chat_id, pdf, _nome_arquivo_cpf(body.dados), legenda)
