# @module services.assinatura.d4sign — Adapter D4Sign (BYOK).
# Auth: tokenAPI + cryptKey na query string. Fluxo: upload → webhook → createlist → sendtosigner.
from __future__ import annotations

import logging
from typing import List

import httpx

from services.assinatura.base import (
    SignatureProvider, TesteConexaoResult, EnvioResult, StatusResult, WebhookEvent,
    OpcoesEnvio, SignatarioEnvio, ProviderError, safe_json,
)

logger = logging.getLogger("romatec")
_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


def _map_status(txt: str) -> str:
    t = (txt or "").lower()
    if "finaliz" in t or "assinad" in t or "concluí" in t or "conclui" in t:
        return "assinado"
    if "cancel" in t:
        return "cancelado"
    if "expir" in t:
        return "expirado"
    if "recus" in t:
        return "recusado"
    return "enviado"


class D4SignProvider(SignatureProvider):
    slug = "d4sign"
    nome_exibicao = "D4Sign"
    suporta_whatsapp = True
    suporta_ordem_assinatura = True
    suporta_icp_brasil = True

    def _base(self) -> str:
        return ("https://sandbox.d4sign.com.br/api/v1" if self.ambiente == "sandbox"
                else "https://secure.d4sign.com.br/api/v1")

    def _auth(self) -> dict:
        return {"tokenAPI": self.credenciais.get("token_api", ""),
                "cryptKey": self.credenciais.get("crypt_key", "")}

    async def _req(self, client: httpx.AsyncClient, method: str, path: str, **kw) -> httpx.Response:
        params = {**self._auth(), **(kw.pop("params", None) or {})}
        r = await client.request(method, self._base() + path, params=params, **kw)
        if r.status_code in (401, 403):
            raise ProviderError("Credenciais D4Sign inválidas ou sem permissão", r.status_code, safe_json(r))
        if r.status_code >= 400:
            raise ProviderError(f"D4Sign erro {r.status_code}", r.status_code, safe_json(r))
        return r

    @staticmethod
    def _cofres(data) -> List[dict]:
        items = data if isinstance(data, list) else (data or {}).get("safes", [])
        return [{"uuid": s.get("uuid_safe") or s.get("uuid"),
                 "nome": s.get("name_safe") or s.get("name")} for s in items]

    async def testar_conexao(self) -> TesteConexaoResult:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await self._req(c, "GET", "/safes")
                return TesteConexaoResult(True, "Conexão OK", {"cofres": self._cofres(r.json())})
        except ProviderError as e:
            return TesteConexaoResult(False, str(e))
        except Exception as e:  # noqa: BLE001
            return TesteConexaoResult(False, f"Falha ao conectar: {e}")

    async def listar_cofres(self) -> List[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await self._req(c, "GET", "/safes")
            return self._cofres(r.json())

    async def enviar_documento(self, pdf_bytes, nome, signatarios: List[SignatarioEnvio],
                               opcoes: OpcoesEnvio) -> EnvioResult:
        cofre = self.credenciais.get("uuid_safe")
        if not cofre:
            raise ProviderError("Cofre (uuid_safe) não configurado")
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            up = await self._req(c, "POST", f"/documents/{cofre}/upload",
                                 files={"file": (nome, pdf_bytes, "application/pdf")})
            uuid_doc = (up.json() or {}).get("uuid")
            if not uuid_doc:
                raise ProviderError("D4Sign não retornou uuid do documento", raw=safe_json(up))
            if opcoes and opcoes.webhook_url:
                try:
                    await self._req(c, "POST", f"/documents/{uuid_doc}/webhooks",
                                    data={"url": opcoes.webhook_url})
                except ProviderError:
                    logger.warning("D4Sign: falha ao cadastrar webhook — polling cobre")
            signers = []
            for s in signatarios:
                signer = {"email": s.email or "", "act": "1", "foreign": "0",
                          "certificadoicpbr": "1" if "icp" in (s.autenticacao or []) else "0",
                          "assinatura_presencial": "0"}
                if s.whatsapp and "whatsapp" in (s.autenticacao or []):
                    signer["whatsapp_number"] = s.whatsapp
                signers.append(signer)
            await self._req(c, "POST", f"/documents/{uuid_doc}/createlist", json={"signers": signers})
            await self._req(c, "POST", f"/documents/{uuid_doc}/sendtosigner",
                            json={"message": (opcoes.mensagem if opcoes else "") or "",
                                  "workflow": "1" if (opcoes and opcoes.ordem_sequencial) else "0",
                                  "skip_email": "0"})
            return EnvioResult(provider_doc_id=uuid_doc, raw=up.json())

    async def consultar_status(self, provider_doc_id: str) -> StatusResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await self._req(c, "GET", f"/documents/{provider_doc_id}")
            data = r.json()
            doc = data[0] if isinstance(data, list) and data else data
            return StatusResult(status=_map_status(str((doc or {}).get("statusName", ""))), raw=doc)

    async def baixar_assinado(self, provider_doc_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await self._req(c, "POST", f"/documents/{provider_doc_id}/download", json={"type": "PDF"})
            url = (r.json() or {}).get("url")
            if not url:
                raise ProviderError("D4Sign não retornou URL de download", raw=safe_json(r))
            dl = await c.get(url)
            if dl.status_code >= 400:
                raise ProviderError(f"Falha ao baixar o assinado ({dl.status_code})", dl.status_code)
            return dl.content

    async def cancelar(self, provider_doc_id: str, motivo: str = "") -> bool:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            await self._req(c, "POST", f"/documents/{provider_doc_id}/cancel", json={"comment": motivo or ""})
            return True

    def parse_webhook(self, headers: dict, body: dict) -> WebhookEvent:
        b = body or {}
        uuid_doc = b.get("uuid") or b.get("uuidDoc") or b.get("uuid_doc")
        tipo = str(b.get("type") or b.get("post_message") or b.get("message") or "atualizacao").lower()
        return WebhookEvent(tipo=tipo, provider_doc_id=uuid_doc, signatario=b.get("email"),
                            novo_status=_map_status(tipo), raw=b)
