# @module services.completude_perfil — o que o assinante ainda precisa configurar.
#
# FONTE ÚNICA da checklist: alimenta o assistente pós-pagamento E o aviso ao
# gerar PTAM. Duas listas separadas divergiriam no primeiro ajuste.
#
# Cada item diz o IMPACTO no documento, não só o nome do campo — "sai sem sua
# assinatura" faz alguém preencher; "assinatura_visual_b64" não.
#
# ESSENCIAL = afeta o conteúdo do laudo. Integrações (Z-API, Telegram) e
# certificado ICP ficam FORA dos essenciais de propósito: exigem credencial
# externa que o cliente raramente tem em mãos no primeiro acesso, e travar o
# início nisso faz ele abandonar a configuração.
from typing import Any, Dict, List

CONFIG = "/dashboard/config"
CURRICULO = "/dashboard/curriculo"
MARCA = "/dashboard/marca"

# chave: (grupo, título, essencial, impacto, rota)
_ITENS = [
    ("nome_completo", "Identificação", "Seu nome completo", True,
     "O laudo sai com a linha de assinatura em branco", CONFIG),
    ("registros", "Identificação", "Registros profissionais (CRECI, CNAI, CFT)", True,
     "O rodapé e o carimbo do laudo saem sem seu número de registro", CONFIG),
    ("assinatura", "Identificação", "Assinatura gráfica", True,
     "O PTAM e os contratos saem sem sua assinatura sobre a linha", CONFIG),
    ("telefone", "Identificação", "Telefone de contato", True,
     "Seus dados de contato ficam vazios no laudo e nas propostas", CONFIG),
    ("local", "Identificação", "Cidade e UF", True,
     "O local de emissão do laudo sai incompleto", CONFIG),

    ("cpf", "Identificação", "CPF", False,
     "Usado na qualificação em contratos e procurações", CONFIG),
    ("endereco", "Identificação", "Endereço do escritório", False,
     "Aparece na qualificação completa em contratos", CONFIG),
    ("email_profissional", "Identificação", "E-mail profissional", False,
     "Sai no rodapé do laudo e nas propostas", CONFIG),

    ("curriculo", "Currículo", "Currículo (formação e experiência)", False,
     "O Anexo IV do laudo — seu currículo — sai vazio", CURRICULO),
    ("cartao_regularidade", "Documentos", "Cartão de regularidade do CRECI", False,
     "O Anexo V do laudo não é anexado", CONFIG),
    ("certidao_regularidade", "Documentos", "Certidão de regularidade", False,
     "O Anexo VI do laudo não é anexado", CONFIG),
    ("certificado_cnai", "Documentos", "Certificado CNAI", False,
     "Não aparece no seu currículo dentro do laudo", CONFIG),

    ("logo", "Marca", "Logo da empresa", False,
     "Seus documentos saem com a marca padrão em vez da sua", MARCA),

    ("certificado_icp", "Assinatura digital", "Certificado ICP-Brasil (A1)", False,
     "Você não consegue assinar digitalmente com validade jurídica", CONFIG),
    ("zapi", "Integrações", "WhatsApp (Z-API)", False,
     "Não dá para enviar laudo, contrato ou recibo por WhatsApp", CONFIG),
    ("telegram", "Integrações", "Telegram", False,
     "Não dá para receber notificações por Telegram", CONFIG),
]

ESSENCIAIS = [c for c, _g, _t, ess, _i, _r in _ITENS if ess]


def _preenchido(chave: str, perfil: Dict[str, Any], tem_logo: bool,
                tem_certificado_icp: bool, integ: Dict[str, Any]) -> bool:
    p = perfil or {}
    integ = integ or {}
    txt = lambda k: bool(str(p.get(k) or "").strip())  # noqa: E731

    if chave == "nome_completo":
        return txt("nome_completo")
    if chave == "registros":
        regs = p.get("registros") or []
        return any(str(r.get("numero") or "").strip() for r in regs if isinstance(r, dict))
    if chave == "assinatura":
        return bool(p.get("assinatura_visual_b64") or p.get("assinatura_tecnico_b64"))
    if chave == "telefone":
        return txt("telefone")
    if chave == "local":
        return txt("cidade") and txt("uf")
    if chave == "cpf":
        return txt("cpf")
    if chave == "endereco":
        return txt("endereco_escritorio")
    if chave == "email_profissional":
        return txt("email_profissional")
    if chave == "curriculo":
        return bool(p.get("formacoes") or p.get("experiencias") or txt("bio_resumo"))
    if chave == "cartao_regularidade":
        return bool(p.get("cartao_regularidade_b64") or p.get("cartao_regularidade_paginas_b64"))
    if chave == "certidao_regularidade":
        return bool(p.get("certidao_regularidade_b64") or p.get("certidao_regularidade_paginas_b64"))
    if chave == "certificado_cnai":
        return bool(p.get("certificado_cnai_b64") or p.get("certificado_cnai_paginas_b64"))
    if chave == "logo":
        return bool(tem_logo)
    if chave == "certificado_icp":
        return bool(tem_certificado_icp)
    if chave == "zapi":
        return bool(integ.get("zapi_ativo")) and bool(integ.get("zapi_instance_id")) \
            and bool(integ.get("zapi_token"))
    if chave == "telegram":
        return bool(integ.get("telegram_ativo")) and bool(integ.get("telegram_bot_token"))
    return False


def calcular(perfil: Dict[str, Any], *, tem_logo: bool = False,
             tem_certificado_icp: bool = False,
             integracoes: Dict[str, Any] = None) -> Dict[str, Any]:
    """Checklist de configuração. Função PURA — recebe tudo pronto, não lê banco."""
    itens: List[Dict[str, Any]] = []
    for chave, grupo, titulo, essencial, impacto, rota in _ITENS:
        itens.append({
            "chave": chave,
            "grupo": grupo,
            "titulo": titulo,
            "essencial": essencial,
            "impacto": impacto,
            "rota": rota,
            "ok": _preenchido(chave, perfil, tem_logo, tem_certificado_icp, integracoes),
        })

    # Essenciais primeiro — é a ordem em que o assistente conduz.
    itens.sort(key=lambda i: (not i["essencial"],))

    total = len(itens) or 1
    feitos = sum(1 for i in itens if i["ok"])
    ess = [i for i in itens if i["essencial"]]
    ess_ok = sum(1 for i in ess if i["ok"])

    return {
        "pct": round(feitos * 100 / total),
        "pct_essencial": round(ess_ok * 100 / (len(ess) or 1)),
        "itens": itens,
        "faltando_essencial": [i["chave"] for i in ess if not i["ok"]],
        "completo": feitos == total,
    }
