# @module services.d4sign_service — Cliente D4Sign para assinatura digital com validade juridica
# Lei 14.063/2020 + MP 2.200-2/2001
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger("romatec")

D4SIGN_BASE_URL = os.environ.get(
    "D4SIGN_BASE_URL", "https://sandbox.d4sign.com.br/api/v1"
)
D4SIGN_TOKEN = os.environ.get("D4SIGN_TOKEN", "")
D4SIGN_CRYPT_KEY = os.environ.get("D4SIGN_CRYPT_KEY", "")
D4SIGN_SAFE_UUID = os.environ.get("D4SIGN_SAFE_UUID", "")


def _check_configured():
    if not D4SIGN_TOKEN:
        raise ValueError(
            "D4Sign nao configurado. Configure D4SIGN_TOKEN no painel de administracao."
        )


def _headers() -> dict:
    return {
        "tokenAPI": D4SIGN_TOKEN,
        "cryptKey": D4SIGN_CRYPT_KEY,
    }


async def upload_documento(pdf_bytes: bytes, nome_arquivo: str) -> str:
    """Faz upload do PDF para o cofre D4Sign e retorna o document_uuid."""
    _check_configured()
    url = f"{D4SIGN_BASE_URL}/documents/{D4SIGN_SAFE_UUID}/upload"
    logger.info("D4Sign: uploading document '%s'", nome_arquivo)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers=_headers(),
            files={"file": (nome_arquivo, pdf_bytes, "application/pdf")},
        )
        response.raise_for_status()
        data = response.json()
        doc_uuid = data.get("uuid") or data.get("uuidDoc") or (data.get("documents") or [{}])[0].get("uuidDoc", "")
        logger.info("D4Sign: document uploaded, uuid=%s", doc_uuid)
        return doc_uuid


async def adicionar_signatario(
    document_uuid: str,
    email: str,
    nome: str,
    tipo: str = "1",
) -> str:
    """Adiciona signatario ao documento e retorna signer_uuid.

    tipo: '1'=assinar, '2'=aprovar, '3'=reconhecer, '4'=testemunha
    """
    _check_configured()
    url = f"{D4SIGN_BASE_URL}/documents/{document_uuid}/createlist"
    payload = {
        "email": email,
        "act": tipo,
        "foreign": "0",
        "certificadoicpbrasil": "0",
        "skipemail": "0",
    }
    logger.info("D4Sign: adding signer email=%s tipo=%s to doc=%s", email, tipo, document_uuid)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=_headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        signer_uuid = data.get("uuid") or data.get("uuidSigner", "")
        logger.info("D4Sign: signer added, uuid=%s", signer_uuid)
        return signer_uuid


async def enviar_para_assinatura(document_uuid: str, mensagem: str = "") -> bool:
    """Envia documento para assinatura (workflow=0)."""
    _check_configured()
    url = f"{D4SIGN_BASE_URL}/documents/{document_uuid}/sendtosigner"
    payload = {"message": mensagem, "workflow": "0"}
    logger.info("D4Sign: sending doc=%s to signers", document_uuid)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=_headers(), json=payload)
        response.raise_for_status()
        logger.info("D4Sign: doc=%s sent to signers", document_uuid)
        return True


async def status_documento(document_uuid: str) -> dict:
    """Retorna status e lista de signatarios do documento."""
    _check_configured()
    url = f"{D4SIGN_BASE_URL}/documents/{document_uuid}"
    logger.info("D4Sign: checking status for doc=%s", document_uuid)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=_headers())
        response.raise_for_status()
        data = response.json()
        # Normaliza campos da resposta D4Sign
        docs = data.get("documents") or []
        doc = docs[0] if docs else data
        status_map = {
            "1": "aguardando",
            "2": "aguardando",
            "3": "assinado",
            "4": "cancelado",
        }
        raw_status = str(doc.get("statusId", doc.get("status", "1")))
        status = status_map.get(raw_status, "aguardando")
        signatarios = []
        for s in doc.get("list", []):
            signed_at = s.get("signed_at") or s.get("assinado_em")
            signatarios.append({
                "email": s.get("email", ""),
                "nome": s.get("name", s.get("nome", "")),
                "tipo": s.get("act", "1"),
                "assinado": bool(signed_at),
                "assinado_em": signed_at,
            })
        logger.info("D4Sign: doc=%s status=%s signers=%d", document_uuid, status, len(signatarios))
        return {"status": status, "signatarios": signatarios}


async def download_documento_assinado(document_uuid: str) -> bytes:
    """Baixa o PDF assinado."""
    _check_configured()
    url = f"{D4SIGN_BASE_URL}/documents/{document_uuid}/download"
    logger.info("D4Sign: downloading signed doc=%s", document_uuid)
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=_headers())
        response.raise_for_status()
        logger.info("D4Sign: downloaded %d bytes for doc=%s", len(response.content), document_uuid)
        return response.content


async def cancelar_documento(document_uuid: str) -> bool:
    """Cancela processo de assinatura."""
    _check_configured()
    url = f"{D4SIGN_BASE_URL}/documents/{document_uuid}/cancel"
    logger.info("D4Sign: canceling doc=%s", document_uuid)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=_headers())
        response.raise_for_status()
        logger.info("D4Sign: doc=%s canceled", document_uuid)
        return True
