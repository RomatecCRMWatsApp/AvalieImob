# @module services.nfse.sefin.certificado — Carga do certificado ICP-Brasil A1 (.pfx).
# O .pfx entra como SECRET (arquivo/volume no Railway); o nfse_config guarda só a REF
# (caminho/env). Extrai chave+cert em PEM p/ o mTLS do httpx e p/ a assinatura XMLDSIG.
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

from services.nfse.exceptions import NFSeConfigError


@dataclass
class CertificadoCarregado:
    key_pem: bytes        # chave privada (PEM, sem senha) — uso interno/efêmero
    cert_pem: bytes       # certificado do titular (PEM)
    chain_pem: bytes      # cadeia adicional (PEM) — pode ser vazia
    titular: str          # CN/sujeito do certificado


def carregar_pfx(pfx_bytes: bytes, senha: str) -> CertificadoCarregado:
    """Carrega um .pfx (PKCS#12) → chave/cert/cadeia em PEM. Levanta NFSeConfigError em falha."""
    try:
        key, cert, extras = pkcs12.load_key_and_certificates(
            pfx_bytes, (senha or "").encode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise NFSeConfigError(f"Falha ao abrir o certificado (.pfx): {e}") from e
    if key is None or cert is None:
        raise NFSeConfigError("Certificado .pfx sem chave privada ou sem certificado.")
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    chain_pem = b"".join(c.public_bytes(serialization.Encoding.PEM) for c in (extras or []))
    titular = ""
    try:
        titular = cert.subject.rfc4514_string()
    except Exception:  # noqa: BLE001
        pass
    return CertificadoCarregado(key_pem, cert_pem, chain_pem, titular)


def carregar_de_config(sefin_cfg: dict) -> CertificadoCarregado:
    """Carrega o certificado a partir das REFs do nfse_config.sefin
    (certificado_ref = caminho do .pfx; certificado_senha_ref = env var da senha)."""
    caminho = (sefin_cfg or {}).get("certificado_ref") or ""
    senha_env = (sefin_cfg or {}).get("certificado_senha_ref") or ""
    if not caminho or not os.path.exists(caminho):
        raise NFSeConfigError("Certificado ICP-Brasil (.pfx) não configurado/encontrado.")
    senha = os.environ.get(senha_env, "")
    with open(caminho, "rb") as f:
        return carregar_pfx(f.read(), senha)
