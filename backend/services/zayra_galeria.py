"""
Integração com a Galeria do ZAYRA (Feature 04 — Vistoria de Campo).

O AvalieImob NÃO acessa o MySQL do ZAYRA. Ele chama um endpoint de exportação
do ZAYRA, autenticado por uma API key de serviço (X-API-Key), passando o
identificador do avaliador (e-mail) para o ZAYRA casar o usuário.

Decisão de auth: tratamos os dois como sistemas SEPARADOS (segredos/IDs próprios).
Se mais tarde optarem por JWT compartilhado, basta trocar o header aqui.

Env (Railway do AvalieImob):
  ZAYRA_API_URL   https://seu-zayra.up.railway.app
  ZAYRA_API_KEY   chave de serviço combinada entre os dois sistemas

httpx é importado de forma tardia para não impactar o startup do app.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException

ZAYRA_API_URL = os.environ.get("ZAYRA_API_URL", "").rstrip("/")
ZAYRA_API_KEY = os.environ.get("ZAYRA_API_KEY", "")


def _ensure_config() -> None:
    if not ZAYRA_API_URL or not ZAYRA_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Integração ZAYRA não configurada (defina ZAYRA_API_URL e ZAYRA_API_KEY).",
        )


async def buscar_fotos_zayra(
    identificador: str, desde: Optional[str] = None, limit: int = 50
) -> list:
    """
    Lista as fotos sincronizadas do avaliador no ZAYRA.
    `identificador` é o e-mail (ou login) do avaliador, usado pelo ZAYRA para
    resolver o user_id dele no MySQL.
    """
    _ensure_config()
    import httpx

    params = {"limit": min(int(limit or 50), 200), "user": identificador}
    if desde:
        params["desde"] = desde

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ZAYRA_API_URL}/api/galeria/export",
                params=params,
                headers={"X-API-Key": ZAYRA_API_KEY},
            )
    except httpx.RequestError as exc:
        raise HTTPException(502, f"ZAYRA inacessível: {exc}")

    if resp.status_code in (401, 403):
        raise HTTPException(502, "ZAYRA recusou a API key de serviço.")
    if resp.status_code >= 400:
        raise HTTPException(502, f"Erro ao buscar fotos do ZAYRA: HTTP {resp.status_code}")

    try:
        return resp.json().get("fotos", [])
    except Exception:
        raise HTTPException(502, "Resposta inválida do ZAYRA (esperado JSON).")


async def baixar_foto_bytes(url: str) -> tuple[bytes, str]:
    """
    Baixa os bytes de uma foto do ZAYRA. Aceita URL absoluta (storage próprio do
    ZAYRA) ou relativa ao ZAYRA_API_URL. Retorna (bytes, content_type).
    """
    _ensure_config()
    import httpx

    full = url if url.startswith("http") else f"{ZAYRA_API_URL}/{url.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(full, headers={"X-API-Key": ZAYRA_API_KEY})
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Falha ao baixar foto do ZAYRA: {exc}")

    if resp.status_code >= 400:
        raise HTTPException(502, f"Foto do ZAYRA indisponível (HTTP {resp.status_code}).")

    ctype = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
    if not ctype.startswith("image/"):
        ctype = "image/jpeg"
    return resp.content, ctype
