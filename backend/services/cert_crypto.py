# @module services.cert_crypto — Cripto AES-256-GCM para .pfx + parser de metadados ICP-Brasil
"""
Criptografia simétrica usando AES-256-GCM (cryptography lib).
Chave em CERT_ENCRYPTION_KEY (env var, base64 de 32 bytes).

O .pfx e a senha são criptografados com nonces separados de 12 bytes.
Nonces ficam armazenados junto com o ciphertext no MongoDB.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

logger = logging.getLogger("romatec")


# ─────────────────────────────────────────────────────────────────────────────
# Chave mestra (env)
# ─────────────────────────────────────────────────────────────────────────────

def _get_master_key() -> bytes:
    """Retorna a chave AES de 32 bytes a partir de CERT_ENCRYPTION_KEY (base64).
    Se não estiver configurada, deriva uma chave temporária do JWT_SECRET pra
    desenvolvimento (e loga aviso). Em produção, defina CERT_ENCRYPTION_KEY.
    """
    raw = os.getenv("CERT_ENCRYPTION_KEY", "").strip()
    if raw:
        try:
            key = base64.b64decode(raw)
            if len(key) != 32:
                raise ValueError(f"CERT_ENCRYPTION_KEY deve ter 32 bytes (tem {len(key)})")
            return key
        except Exception as e:
            logger.error("CERT_ENCRYPTION_KEY inválida: %s", e)
            raise

    # Fallback dev — derivar de JWT_SECRET. NÃO usar em produção.
    secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    derived = hashlib.sha256(("cert-fallback:" + secret).encode()).digest()
    logger.warning(
        "CERT_ENCRYPTION_KEY não configurada — usando derivação de JWT_SECRET (NÃO usar em produção). "
        "Gere uma chave com: python -c 'import os,base64; print(base64.b64encode(os.urandom(32)).decode())'"
    )
    return derived


def encrypt_bytes(plaintext: bytes) -> Tuple[bytes, bytes]:
    """Criptografa bytes com AES-256-GCM. Retorna (ciphertext, nonce)."""
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return ct, nonce


def decrypt_bytes(ciphertext: bytes, nonce: bytes) -> bytes:
    """Descriptografa bytes com AES-256-GCM."""
    key = _get_master_key()
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)


# ─────────────────────────────────────────────────────────────────────────────
# Parser .pfx — extrair metadados ICP-Brasil
# ─────────────────────────────────────────────────────────────────────────────

def _format_documento(raw: str, perfil: str) -> str:
    """Formata CPF/CNPJ a partir dos dígitos. Aceita string com ou sem máscara."""
    digits = "".join(c for c in raw if c.isdigit())
    if perfil == "PF" and len(digits) == 11:
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    if perfil == "PJ" and len(digits) == 14:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    return raw


def parse_pfx_metadata(pfx_bytes: bytes, password: str) -> dict:
    """Extrai metadados de um certificado ICP-Brasil A1 (.pfx).

    Retorna dict com: titular, documento, valido_de, valido_ate, emissor,
    serial_number, perfil_detectado (PF|PJ), fingerprint_sha256.

    Levanta ValueError se a senha estiver errada ou o arquivo for inválido.
    """
    try:
        password_bytes = (password or "").encode("utf-8")
        private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
            pfx_bytes, password_bytes
        )
    except Exception as e:
        # cryptography levanta ValueError ou outros tipos dependendo da causa
        raise ValueError(f"Não foi possível abrir o .pfx: {e}") from e

    if cert is None:
        raise ValueError("Arquivo .pfx não contém certificado")

    # ─── Titular ──────────────────────────────────────────────
    subject_attrs = {attr.oid: attr.value for attr in cert.subject}
    titular = subject_attrs.get(NameOID.COMMON_NAME, "")
    # ICP-Brasil costuma colocar "NOME:CPF" no CN do e-CPF.
    if titular and ":" in titular:
        titular = titular.split(":")[0].strip()

    # ─── Detectar PF vs PJ ────────────────────────────────────
    cn_raw = subject_attrs.get(NameOID.COMMON_NAME, "") or ""
    perfil_detectado = "PJ" if "CNPJ" in cn_raw.upper() else "PF"

    # ─── Documento (CPF / CNPJ) ───────────────────────────────
    # Padrão ICP-Brasil: SAN otherName com OID 2.16.76.1.3.1 (PF) ou 2.16.76.1.3.3 (PJ)
    # A lib cryptography não expõe esses campos diretamente; vamos tentar via
    # serialNumber ou regex no CN.
    documento = ""
    try:
        from cryptography import x509
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        for entry in san_ext.value:
            if isinstance(entry, x509.OtherName):
                # ICP-Brasil: bytes começam com tag DER da string. Pulamos tag+len.
                raw = entry.value
                # raw começa tipicamente com b'\x13\x37' (PrintableString len 0x37)
                # contendo: data nascimento (8) + CPF (11) + ... ou CNPJ similar
                # Vamos só pegar dígitos e tentar extrair 11 (CPF) ou 14 (CNPJ).
                digits_only = "".join(c for c in raw.decode("latin-1", errors="ignore") if c.isdigit())
                if perfil_detectado == "PJ":
                    cnpj_match = digits_only[:14] if len(digits_only) >= 14 else ""
                    if len(cnpj_match) == 14:
                        documento = _format_documento(cnpj_match, "PJ")
                        break
                else:
                    # PF — pular 8 dígitos da data de nascimento se houver, pegar 11 do CPF
                    if len(digits_only) >= 19:
                        cpf_match = digits_only[8:19]
                    else:
                        cpf_match = digits_only[:11]
                    if len(cpf_match) == 11:
                        documento = _format_documento(cpf_match, "PF")
                        break
    except Exception as e:
        logger.debug("Falha ao parsear SAN para CPF/CNPJ: %s", e)

    # Fallback — tentar pegar do serialNumber do subject
    if not documento:
        sn = subject_attrs.get(NameOID.SERIAL_NUMBER, "")
        if sn:
            documento = _format_documento(sn, perfil_detectado)

    # ─── Validade ─────────────────────────────────────────────
    valido_de = cert.not_valid_before
    valido_ate = cert.not_valid_after

    # ─── Emissor ──────────────────────────────────────────────
    issuer_attrs = {attr.oid: attr.value for attr in cert.issuer}
    emissor = issuer_attrs.get(NameOID.COMMON_NAME, "Desconhecido")

    # ─── Serial e fingerprint ────────────────────────────────
    serial_number = format(cert.serial_number, "X")
    fingerprint = hashlib.sha256(pfx_bytes).hexdigest()

    return {
        "titular": titular,
        "documento": documento,
        "valido_de": valido_de,
        "valido_ate": valido_ate,
        "emissor": emissor,
        "serial_number": serial_number,
        "perfil_detectado": perfil_detectado,
        "fingerprint_sha256": fingerprint,
    }


def validar_pfx(pfx_bytes: bytes, password: str) -> bool:
    """Apenas valida que o .pfx abre com a senha. Não retorna metadados."""
    try:
        password_bytes = (password or "").encode("utf-8")
        pkcs12.load_key_and_certificates(pfx_bytes, password_bytes)
        return True
    except Exception:
        return False
