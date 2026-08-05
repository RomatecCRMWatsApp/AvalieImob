# @module services.assinatura.catalogo — Catálogo estático dos provedores BYOK.
# Descritor consumido pelo frontend p/ renderizar o formulário de credenciais
# dinamicamente (§4.1 do spec). NENHUM segredo aqui — só metadados.
from __future__ import annotations

PROVEDORES = [
    {
        "slug": "d4sign",
        "nome": "D4Sign",
        "suporta_whatsapp": True,
        "suporta_ordem_assinatura": True,
        "suporta_icp_brasil": True,
        "tutorial_url": "https://docs.d4sign.com.br/",
        "campos_credenciais": [
            {"key": "token_api", "label": "Token API", "tipo": "password", "obrigatorio": True},
            {"key": "crypt_key", "label": "Crypt Key", "tipo": "password", "obrigatorio": True},
            {"key": "uuid_safe", "label": "Cofre de destino", "tipo": "select_cofre", "obrigatorio": True,
             "ajuda": "Selecionado da lista de cofres após o teste de conexão."},
        ],
        "ajuda": [
            "Sandbox: crie a conta em sandbox.d4sign.com.br/criar.",
            "Envie e-mail a suporte@d4sign.com.br pedindo a ATIVAÇÃO da API (informe o e-mail da conta).",
            "Produção exige plano ativo — o administrador solicita as chaves ao mesmo suporte.",
            "Copie o tokenAPI e o cryptKey, cole aqui, teste e selecione o cofre.",
        ],
    },
    {
        "slug": "clicksign",
        "nome": "Clicksign",
        "suporta_whatsapp": True,
        "suporta_ordem_assinatura": True,
        "suporta_icp_brasil": True,
        "tutorial_url": "https://developers.clicksign.com/",
        "campos_credenciais": [
            {"key": "access_token", "label": "Access Token", "tipo": "password", "obrigatorio": True},
        ],
        "ajuda": [
            "Sandbox: crie a conta grátis em sandbox.clicksign.com/signup.",
            "No painel: Configurações → API → Gerar Access Token; dê um nome e confirme.",
            "Produção: gere o token no mesmo caminho, dentro da conta paga.",
            "Cole o Access Token aqui e teste a conexão.",
        ],
    },
    {
        "slug": "autentique",
        "nome": "Autentique",
        "suporta_whatsapp": True,
        "suporta_ordem_assinatura": False,
        "suporta_icp_brasil": True,
        "tutorial_url": "https://docs.autentique.com.br/",
        "campos_credenciais": [
            {"key": "api_token", "label": "API Token", "tipo": "password", "obrigatorio": True},
        ],
        "ajuda": [
            "No painel Autentique → Chaves de API → gerar chave.",
            "Opcional: habilite a exibição de documentos sandbox na mesma tela.",
            "Cole o token aqui e teste. Testes com sandbox NÃO consomem créditos do plano.",
        ],
    },
]

CAMPOS_OBRIGATORIOS = {
    p["slug"]: [c["key"] for c in p["campos_credenciais"] if c.get("obrigatorio")]
    for p in PROVEDORES
}
SLUGS = [p["slug"] for p in PROVEDORES]


def provedor(slug: str):
    return next((p for p in PROVEDORES if p["slug"] == slug), None)


def catalogo_publico():
    """Catálogo sem segredos — seguro para expor no GET /provedores."""
    return [dict(p) for p in PROVEDORES]
