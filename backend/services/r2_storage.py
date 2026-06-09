"""
Cloudflare R2 storage (S3-compatible) para uploads do AvalieImob.

Usa boto3. Credenciais vêm de variáveis de ambiente (Railway Variables):
  R2_ENDPOINT        https://<ACCOUNT_ID>.r2.cloudflarestorage.com
  R2_ACCESS_KEY      Access Key ID
  R2_SECRET_KEY      Secret Access Key
  R2_BUCKET          avalieimob-assets
  R2_PUBLIC_BASE     (opcional) base pública/CDN p/ servir os objetos,
                     ex.: https://assets.romatecavalieimob.com.br
                     Se ausente, gera-se URL pré-assinada com validade longa.

Instalar: pip install boto3
"""
from __future__ import annotations

import os
import threading
from typing import Optional

# boto3/botocore são importados de forma tardia (dentro das funções) para não
# quebrar o startup do app caso a dependência ainda não esteja instalada.

_PRESIGN_TTL = 7 * 24 * 3600  # 7 dias para URL pré-assinada (fallback)

_client_lock = threading.Lock()
_client = None


class StorageError(RuntimeError):
    """Falha ao falar com o R2 (rede, credencial, permissão)."""


def _env(name: str, required: bool = True) -> Optional[str]:
    val = os.getenv(name)
    if required and not val:
        raise StorageError(f"variável de ambiente ausente: {name}")
    return val


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                try:
                    import boto3
                    from botocore.client import Config
                except ImportError as exc:  # pragma: no cover
                    raise StorageError("boto3 não instalado (pip install boto3)") from exc
                _client = boto3.client(
                    "s3",
                    endpoint_url=_env("R2_ENDPOINT"),
                    aws_access_key_id=_env("R2_ACCESS_KEY"),
                    aws_secret_access_key=_env("R2_SECRET_KEY"),
                    config=Config(
                        signature_version="s3v4",
                        retries={"max_attempts": 3, "mode": "standard"},
                    ),
                    region_name="auto",
                )
    return _client


def _boto_errors():
    from botocore.exceptions import BotoCoreError, ClientError
    return (BotoCoreError, ClientError)


def _bucket() -> str:
    return _env("R2_BUCKET")


def upload_bytes(
    data: bytes,
    key: str,
    content_type: str,
    cache_control: str = "public, max-age=31536000, immutable",
) -> str:
    """
    Sobe `data` em `key` no bucket e devolve a URL pública (ou pré-assinada).
    `key` deve já vir sanitizado, ex.: 'branding/{tenant_id}/{uuid}.png'.
    """
    try:
        _get_client().put_object(
            Bucket=_bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl=cache_control,
        )
    except _boto_errors() as exc:
        raise StorageError(f"falha no upload para R2 ({key}): {exc}") from exc
    return public_url(key)


def delete_object(key_or_url: str) -> None:
    """Remove um objeto. Aceita a key ou a URL pública completa."""
    key = _key_from_url(key_or_url)
    if not key:
        return
    try:
        _get_client().delete_object(Bucket=_bucket(), Key=key)
    except _boto_errors() as exc:
        raise StorageError(f"falha ao remover objeto R2 ({key}): {exc}") from exc


def public_url(key: str) -> str:
    """URL pública via CDN (se R2_PUBLIC_BASE) ou pré-assinada de longa validade."""
    base = os.getenv("R2_PUBLIC_BASE")
    if base:
        return f"{base.rstrip('/')}/{key.lstrip('/')}"
    try:
        return _get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": key},
            ExpiresIn=_PRESIGN_TTL,
        )
    except _boto_errors() as exc:
        raise StorageError(f"falha ao gerar URL para {key}: {exc}") from exc


def _key_from_url(key_or_url: str) -> Optional[str]:
    if not key_or_url:
        return None
    base = os.getenv("R2_PUBLIC_BASE")
    if base and key_or_url.startswith(base):
        return key_or_url[len(base):].lstrip("/")
    if key_or_url.startswith("http://") or key_or_url.startswith("https://"):
        # URL pré-assinada: tira query string e domínio, mantém o path como key
        path = key_or_url.split("?", 1)[0]
        # remove esquema + host
        without_scheme = path.split("://", 1)[-1]
        return without_scheme.split("/", 1)[-1] if "/" in without_scheme else None
    return key_or_url.lstrip("/")
