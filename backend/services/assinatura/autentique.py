# @module services.assinatura.autentique — Adapter Autentique (BYOK, GraphQL v2).
# Upload via multipart GraphQL (jaydenseric spec). Rate limit 60/min → backoff (tenacity).
from __future__ import annotations

import json
import logging
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from services.assinatura.base import (
    SignatureProvider, TesteConexaoResult, EnvioResult, StatusResult, WebhookEvent,
    OpcoesEnvio, SignatarioEnvio, ProviderError, safe_json,
)

logger = logging.getLogger("romatec")
_URL = "https://api.autentique.com.br/v2/graphql"
_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


def _sig_status(sig: dict) -> str:
    if sig.get("signed"):
        return "assinado"
    if sig.get("rejected"):
        return "recusado"
    return "pendente"


def _is_429(e: BaseException) -> bool:
    return isinstance(e, ProviderError) and e.status_code == 429


class AutentiqueProvider(SignatureProvider):
    slug = "autentique"
    nome_exibicao = "Autentique"
    suporta_whatsapp = True
    suporta_ordem_assinatura = False
    suporta_icp_brasil = True

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.credenciais.get('api_token', '')}"}

    @retry(stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=1, min=1, max=20),
           retry=retry_if_exception(_is_429), reraise=True)
    async def _gql(self, query: str, variables: dict = None, upload=None) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            if upload is not None:
                operations = json.dumps({"query": query, "variables": variables or {}})
                data = {"operations": operations, "map": json.dumps({"0": ["variables.file"]})}
                r = await c.post(_URL, headers=self._headers(), data=data, files={"0": upload})
            else:
                r = await c.post(_URL, headers=self._headers(),
                                 json={"query": query, "variables": variables or {}})
            if r.status_code == 429:
                raise ProviderError("Autentique: rate limit (429)", 429, safe_json(r))
            if r.status_code in (401, 403):
                raise ProviderError("API token Autentique inválido ou sem permissão", r.status_code, safe_json(r))
            if r.status_code >= 400:
                raise ProviderError(f"Autentique erro {r.status_code}", r.status_code, safe_json(r))
            body = r.json()
            if body.get("errors"):
                raise ProviderError(f"Autentique: {body['errors'][0].get('message', 'erro')}", raw=body)
            return body.get("data") or {}

    async def testar_conexao(self) -> TesteConexaoResult:
        try:
            data = await self._gql("query { me { id name email } }")
            me = data.get("me") or {}
            return TesteConexaoResult(bool(me.get("id")),
                                      "Conexão OK" if me.get("id") else "Sem dados de conta", {"me": me})
        except ProviderError as e:
            return TesteConexaoResult(False, str(e))
        except Exception as e:  # noqa: BLE001
            return TesteConexaoResult(False, f"Falha ao conectar: {e}")

    async def enviar_documento(self, pdf_bytes, nome, signatarios: List[SignatarioEnvio],
                               opcoes: OpcoesEnvio) -> EnvioResult:
        signers = []
        for s in signatarios:
            sg = {"action": "SIGN"}
            if s.email:
                sg["email"] = s.email
            elif s.whatsapp:
                sg["phone"] = s.whatsapp
            signers.append(sg)
        query = ("mutation($document: DocumentInput!, $signers: [SignerInput!]!, $file: Upload!, $sandbox: Boolean) {"
                 " createDocument(document: $document, signers: $signers, file: $file, sandbox: $sandbox)"
                 " { id name } }")
        variables = {"document": {"name": nome}, "signers": signers,
                     "file": None, "sandbox": self.ambiente == "sandbox"}
        data = await self._gql(query, variables, upload=(nome, pdf_bytes, "application/pdf"))
        doc = data.get("createDocument") or {}
        if not doc.get("id"):
            raise ProviderError("Autentique não retornou id do documento", raw=data)
        return EnvioResult(provider_doc_id=doc["id"], raw=doc)

    async def consultar_status(self, provider_doc_id: str) -> StatusResult:
        query = ("query($id: UUID!) { document(id: $id) { id signatures {"
                 " public_id email signed { created_at } rejected { created_at } } } }")
        data = await self._gql(query, {"id": provider_doc_id})
        doc = data.get("document") or {}
        sigs = doc.get("signatures") or []
        out = [{"signatario": s.get("email") or s.get("public_id"), "status": _sig_status(s)} for s in sigs]
        if out and all(s["status"] == "assinado" for s in out):
            status = "assinado"
        elif any(s["status"] == "recusado" for s in out):
            status = "recusado"
        elif any(s["status"] == "assinado" for s in out):
            status = "parcialmente_assinado"
        else:
            status = "enviado"
        return StatusResult(status=status, signatarios=out, raw=doc)

    async def baixar_assinado(self, provider_doc_id: str) -> bytes:
        data = await self._gql("query($id: UUID!) { document(id: $id) { files { signed original } } }",
                               {"id": provider_doc_id})
        files = (data.get("document") or {}).get("files") or {}
        url = files.get("signed") or files.get("original")
        if not url:
            raise ProviderError("Autentique: arquivo assinado indisponível", raw=data)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            dl = await c.get(url)
            if dl.status_code >= 400:
                raise ProviderError(f"Falha ao baixar o assinado ({dl.status_code})", dl.status_code)
            return dl.content

    async def cancelar(self, provider_doc_id: str, motivo: str = "") -> bool:
        # Autentique não tem cancelamento — deleta e registramos como cancelado.
        await self._gql("mutation($id: UUID!) { deleteDocument(id: $id) }", {"id": provider_doc_id})
        return True

    def parse_webhook(self, headers: dict, body: dict) -> WebhookEvent:
        b = body or {}
        tipo = str(b.get("event") or b.get("type") or "atualizacao").lower()
        doc = b.get("document") or {}
        return WebhookEvent(tipo=tipo, provider_doc_id=doc.get("id") or b.get("document_id"), raw=b)
