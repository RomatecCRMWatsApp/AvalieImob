# @module models.cupom — Kit Promocional de Captação: cupons de desconto + link único.
#
# Convenções do projeto: id = uuid str (NÃO ObjectId), datas via _now, isolamento por
# criado_por (admin). Z-API reaproveitada via services.zapi_service (config por usuário).
import secrets
import string
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field
from models.common import _id, _now


def gerar_slug(n: int = 10) -> str:
    """Slug único para URL: abc123xyz."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(n))


def gerar_codigo(prefixo: str = "ROMATEC") -> str:
    """Código alfanumérico legível: ROMATEC-A3F9."""
    sufixo = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"{(prefixo or 'ROMATEC').upper().strip()}-{sufixo}"


class CupomBase(BaseModel):
    # IDENTIFICAÇÃO
    codigo: Optional[str] = None          # ROMATEC-A3F9 (gerado se vazio)
    prefixo_codigo: Optional[str] = "ROMATEC"
    # DESCONTO
    tipo_desconto: Literal["valor_fixo", "percentual"] = "valor_fixo"
    valor_desconto: float = 20.00
    valor_plano_normal: float = 89.90
    aplicar_em: Literal["primeira_mensalidade"] = "primeira_mensalidade"
    # DESTINATÁRIO (opcional)
    nome_destinatario: Optional[str] = None
    telefone_destinatario: Optional[str] = None
    email_destinatario: Optional[str] = None
    # CONTROLE
    limite_usos: int = 1
    validade: Optional[datetime] = None     # None = sem validade (aceita ISO string)
    # MENSAGEM
    mensagem_customizada: Optional[str] = None


class Cupom(CupomBase):
    id: str = Field(default_factory=_id)
    slug_unico: str = Field(default_factory=gerar_slug)
    valor_com_desconto: float = 60.00
    usos_realizados: int = 0
    status: Literal["ativo", "utilizado", "expirado", "cancelado"] = "ativo"
    # RASTREIO
    whatsapp_enviado: bool = False
    whatsapp_enviado_em: Optional[datetime] = None
    usado_por_usuario_id: Optional[str] = None
    usado_em: Optional[datetime] = None
    # CONTROLE INTERNO
    criado_por: str = ""
    criado_em: datetime = Field(default_factory=_now)
    atualizado_em: datetime = Field(default_factory=_now)
