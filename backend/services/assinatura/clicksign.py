# @module services.assinatura.clicksign — Adapter Clicksign (BYOK, modelo Envelope, API v3 JSON:API).
from __future__ import annotations

import base64
import logging
from typing import List

import httpx

from services.assinatura.base import (
    SignatureProvider, TesteConexaoResult, EnvioResult, StatusResult, WebhookEvent,
    OpcoesEnvio, SignatarioEnvio, ProviderError, safe_json,
)

logger = logging.getLogger("romatec")
_TIMEOUT = httpx.Timeout(60.0, connect=15.0)
_MAX_DOC = 10 * 1024 * 1024  # 10 MB por arquivo


def _map_status(txt: str) -> str:
    t = (txt or "").lower()
    if t in ("finished", "closed") or "assin" in t or "finaliz" in t:
        return "assinado"
    if "cancel" in t:
        return "cancelado"
    if "draft" in t:
        return "rascunho"
    if "running" in t or "pending" in t or "sent" in t:
        return "enviado"
    return "enviado"


class ClicksignProvider(SignatureProvider):
    slug = "clicksign"
    nome_exibicao = "Clicksign"
    suporta_whatsapp = True
    suporta_ordem_assinatura = True
    suporta_icp_brasil = True

    def _base(self) -> str:
        return ("https://sandbox.clicksign.com/api/v3" if self.ambiente == "sandbox"
                else "https://app.clicksign.com/api/v3")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.credenciais.get('access_token', '')}",
                "Content-Type": "application/vnd.api+json", "Accept": "application/vnd.api+json"}

    async def _req(self, c: httpx.AsyncClient, method: str, path: str, **kw) -> httpx.Response:
        r = await c.request(method, self._base() + path, headers=self._headers(), **kw)
        if r.status_code in (401, 403):
            raise ProviderError("Access Token Clicksign inválido ou sem permissão", r.status_code, safe_json(r))
        if r.status_code >= 400:
            raise ProviderError(f"Clicksign erro {r.status_code}", r.status_code, safe_json(r))
        return r

    async def testar_conexao(self) -> TesteConexaoResult:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                await self._req(c, "GET", "/envelopes", params={"page[size]": "1"})
                return TesteConexaoResult(True, "Conexão OK")
        except ProviderError as e:
            return TesteConexaoResult(False, str(e))
        except Exception as e:  # noqa: BLE001
            return TesteConexaoResult(False, f"Falha ao conectar: {e}")

    async def enviar_documento(self, pdf_bytes, nome, signatarios: List[SignatarioEnvio],
                               opcoes: OpcoesEnvio) -> EnvioResult:
        if len(pdf_bytes) > _MAX_DOC:
            raise ProviderError("PDF excede 10 MB (limite do Clicksign por arquivo)")
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            env = await self._req(c, "POST", "/envelopes",
                                  json={"data": {"type": "envelopes",
                                                 "attributes": {"name": nome, "locale": "pt-BR"}}})
            env_id = (((env.json() or {}).get("data") or {}).get("id"))
            if not env_id:
                raise ProviderError("Clicksign não retornou id do envelope", raw=safe_json(env))
            try:
                b64 = base64.b64encode(pdf_bytes).decode()
                await self._req(c, "POST", f"/envelopes/{env_id}/documents",
                                json={"data": {"type": "documents", "attributes": {
                                    "filename": nome,
                                    "content_base64": f"data:application/pdf;base64,{b64}"}}})
                for s in signatarios:
                    await self._req(c, "POST", f"/envelopes/{env_id}/signers",
                                    json={"data": {"type": "signers", "attributes": {
                                        "name": s.nome, "email": s.email,
                                        "phone_number": s.whatsapp,
                                        "has_documentation": bool(s.cpf_cnpj),
                                        "documentation": s.cpf_cnpj,
                                        "qualification": s.papel}}})
                await self._req(c, "PATCH", f"/envelopes/{env_id}",
                                json={"data": {"id": env_id, "type": "envelopes",
                                               "attributes": {"status": "running"}}})
            except ProviderError:
                # rollback — descarta o envelope draft p/ não deixar lixo na conta do cliente
                try:
                    await self._req(c, "PATCH", f"/envelopes/{env_id}",
                                    json={"data": {"id": env_id, "type": "envelopes",
                                                   "attributes": {"status": "canceled"}}})
                except Exception:  # noqa: BLE001
                    logger.warning("Clicksign: rollback do envelope %s falhou", env_id)
                raise
            return EnvioResult(provider_doc_id=env_id, raw=env.json())

    async def consultar_status(self, provider_doc_id: str) -> StatusResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await self._req(c, "GET", f"/envelopes/{provider_doc_id}")
            attrs = (((r.json() or {}).get("data") or {}).get("attributes") or {})
            return StatusResult(status=_map_status(attrs.get("status", "")), raw=r.json())

    async def baixar_assinado(self, provider_doc_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await self._req(c, "GET", f"/envelopes/{provider_doc_id}/documents")
            url = None
            for d in ((r.json() or {}).get("data") or []):
                a = d.get("attributes") or {}
                url = a.get("signed_file_url") or a.get("file_url") or url
            if not url:
                raise ProviderError("Clicksign: URL do assinado indisponível", raw=safe_json(r))
            dl = await c.get(url)
            if dl.status_code >= 400:
                raise ProviderError(f"Falha ao baixar o assinado ({dl.status_code})", dl.status_code)
            return dl.content

    async def cancelar(self, provider_doc_id: str, motivo: str = "") -> bool:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            await self._req(c, "PATCH", f"/envelopes/{provider_doc_id}",
                            json={"data": {"id": provider_doc_id, "type": "envelopes",
                                           "attributes": {"status": "canceled"}}})
            return True

    def parse_webhook(self, headers: dict, body: dict) -> WebhookEvent:
        b = body or {}
        ev = b.get("event") or {}
        tipo = str(ev.get("name") or b.get("type") or "atualizacao").lower()
        data = b.get("data") or {}
        env_id = data.get("id") or (b.get("envelope") or {}).get("id")
        return WebhookEvent(tipo=tipo, provider_doc_id=env_id, novo_status=_map_status(tipo), raw=b)
