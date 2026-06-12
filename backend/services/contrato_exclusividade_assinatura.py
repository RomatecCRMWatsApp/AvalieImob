# @module services.contrato_exclusividade_assinatura — tokens, hash e tempo (aceite eletrônico)
"""
Helpers de integridade do Contrato de Exclusividade com aceite eletrônico.
- token individual por signatário (imprevisível, 256 bits)
- hash SHA-256 do conteúdo canônico (qualquer alteração invalida o hash)
"""
import hashlib
import json
import secrets
from datetime import datetime, timezone


def gerar_token() -> str:
    """Token único por signatário, imprevisível (256 bits)."""
    return secrets.token_urlsafe(32)


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def gerar_hash_documento(contrato: dict) -> str:
    """
    SHA-256 do conteúdo canônico do contrato. Calculado UMA vez (na criação) e
    nunca recalculado — alterar o contrato exige cancelar e criar outro.
    """
    def _norm(dt):
        return dt.isoformat() if isinstance(dt, datetime) else dt

    def _dig(v):
        return "".join(filter(str.isdigit, str(v or "")))

    proprietarios = [
        {
            "nome": p.get("nome"),
            "cpf_cnpj": _dig(p.get("cpf_cnpj")),
            "fracao_percentual": p.get("fracao_percentual"),
            "conjuge_cpf": _dig((p.get("conjuge") or {}).get("cpf")),
        }
        for p in (contrato.get("proprietarios") or [])
    ]
    im = contrato.get("imovel") or {}
    imovel_canon = {
        "matricula": im.get("matricula"),
        "cartorio": im.get("cartorio"),
        "endereco": im.get("endereco"),
        "descricao_geral": im.get("descricao_geral"),
        "area_total_m2": im.get("area_total_m2"),
        "area_hectares": im.get("area_hectares"),
        "confrontacoes": im.get("confrontacoes"),
        "latitude": im.get("latitude"),
        "longitude": im.get("longitude"),
        "valor_anunciado": im.get("valor_anunciado"),
    }  # fotos/documentos NÃO entram no hash (anexos mutáveis pré-envio)

    conteudo_canonico = json.dumps(
        {
            "proprietarios": proprietarios,
            "imovel": imovel_canon,
            "comissao_percentual": contrato.get("comissao_percentual"),
            "prazo_meses": contrato.get("prazo_meses"),
            "criado_em": _norm(contrato.get("criado_em")),
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(conteudo_canonico.encode("utf-8")).hexdigest()
