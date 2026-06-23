# @module services.nfse.abrasf.resposta — Parser das respostas SOAP do SpeedGov (ABRASF).
"""Extrai do envelope SOAP o conteúdo de <return> (XML escapado), desescapa e lê os campos
úteis: Sucesso, mensagens de erro (Codigo/Mensagem/Correcao) e, no sucesso, número/código de
verificação/protocolo da NFS-e. Namespace-agnóstico (regex por localname)."""
from __future__ import annotations

import re
from html import unescape


def _tag(xml: str, nome: str):
    m = re.search(rf"<(?:\w+:)?{nome}\b[^>]*>(.*?)</(?:\w+:)?{nome}>", xml, re.S)
    return m.group(1).strip() if m else None


def parse_resposta(soap_text: str) -> dict:
    """Retorna {sucesso, mensagens:[{codigo,mensagem,correcao}], numero_nfse, codigo_verificacao,
    protocolo, inner} a partir do envelope SOAP cru do SpeedGov."""
    m = re.search(r"<return>(.*?)</return>", soap_text or "", re.S)
    inner = unescape(m.group(1)).strip() if m else (soap_text or "")

    sucesso_txt = (_tag(inner, "Sucesso") or "").lower()
    sucesso = sucesso_txt == "true"

    mensagens = []
    for mr in re.finditer(r"<(?:\w+:)?MensagemRetorno>(.*?)</(?:\w+:)?MensagemRetorno>", inner, re.S):
        b = mr.group(1)
        mensagens.append({
            "codigo": _tag(b, "Codigo") or "",
            "mensagem": _tag(b, "Mensagem") or "",
            "correcao": _tag(b, "Correcao") or "",
        })

    # Dados da NFS-e (quando gerada): pegar de dentro do bloco InfNfse
    numero = codigo_verif = None
    inf = re.search(r"<(?:\w+:)?InfNfse\b[^>]*>(.*?)</(?:\w+:)?InfNfse>", inner, re.S)
    if inf:
        numero = _tag(inf.group(1), "Numero")
        codigo_verif = _tag(inf.group(1), "CodigoVerificacao")

    return {
        "sucesso": sucesso,
        "mensagens": mensagens,
        "numero_nfse": numero,
        "codigo_verificacao": codigo_verif,
        "protocolo": _tag(inner, "Protocolo"),
        "inner": inner[:9000],
    }
