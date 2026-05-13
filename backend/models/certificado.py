# @module models.certificado — Certificado Digital ICP-Brasil A1 (.pfx) por usuário
# Armazenado criptografado AES-256-GCM. Senha nunca persistida em claro.
# Usado para assinatura PAdES (PDF) com validade jurídica equivalente ao gov.br/validar.
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from models.common import _id, _now


class CertificadoBase(BaseModel):
    """Metadados públicos do certificado (sem .pfx nem senha)."""
    label: str = Field(..., description="Apelido pra identificar (ex: 'Romatec 2026')")
    perfil: str = Field("PF", description="PF (e-CPF) | PJ (e-CNPJ)")
    titular: Optional[str] = None       # Nome do titular extraído do certificado
    documento: Optional[str] = None     # CPF/CNPJ extraído do certificado
    valido_de: Optional[datetime] = None
    valido_ate: Optional[datetime] = None
    emissor: Optional[str] = None       # ex: "AC INTERCERT v5"
    serial_number: Optional[str] = None
    ativo: bool = True


class Certificado(CertificadoBase):
    id: str = Field(default_factory=_id)
    user_id: str
    pfx_encrypted: bytes                 # .pfx criptografado AES-256-GCM
    password_encrypted: bytes            # senha criptografada AES-256-GCM
    nonce_pfx: bytes                     # nonce AES-GCM do .pfx
    nonce_password: bytes                # nonce AES-GCM da senha
    fingerprint_sha256: Optional[str] = None  # SHA-256 do .pfx (pra detectar re-upload)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class CertificadoPublic(CertificadoBase):
    """Versão segura pra retornar nas APIs — sem .pfx nem senha."""
    id: str
    user_id: str
    fingerprint_sha256: Optional[str] = None
    created_at: datetime
    updated_at: datetime
