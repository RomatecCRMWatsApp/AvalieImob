# @module services.planos — FONTE ÚNICA dos planos da assinatura e do teste grátis.
"""Preços, períodos e dias de teste do AvalieImob num lugar só.

Quem lê daqui: a cobrança no Mercado Pago (`mercadopago_service.PLAN_CONFIG`), o
cadastro (`routes/auth._dias_trial_cadastro`), o robô do site
(`atendimento/conhecimento`), o valor de referência dos cupons e a rota pública
`GET /api/planos` (que a tela de planos do site consome).

Textos fixos que não dá para tornar dinâmicos (dados do Google em `index.html`,
folders, blog, páginas de serviço) são conferidos contra este arquivo pelo teste
`tests/test_planos_fonte_unica.py` — se mudar um preço aqui e esquecer um texto,
a suíte acusa o arquivo.

Sem imports do projeto: pode ser importado por models, services e routes sem ciclo.
"""
import os

# id → (título da cobrança, preço em R$, dias de acesso, meses equivalentes)
PLANOS = {
    "mensal":     {"nome": "Mensal",     "titulo": "AvalieImob - Plano Mensal",     "preco": 189.90,  "dias": 30,  "meses": 1},
    "trimestral": {"nome": "Trimestral", "titulo": "AvalieImob - Plano Trimestral", "preco": 449.90,  "dias": 90,  "meses": 3},
    "anual":      {"nome": "Anual",      "titulo": "AvalieImob - Plano Anual",      "preco": 1199.00, "dias": 365, "meses": 12},
}

# Padrão do teste grátis no cadastro. A variável TRIAL_CADASTRO_DIAS (Railway)
# sobrepõe; 0 desliga o teste; teto 30.
TRIAL_DIAS_PADRAO = 7
TRIAL_DIAS_TETO = 30


def dias_teste() -> int:
    """Dias de teste grátis dados no cadastro (lê TRIAL_CADASTRO_DIAS a cada chamada)."""
    try:
        return max(0, min(TRIAL_DIAS_TETO,
                          int(os.environ.get("TRIAL_CADASTRO_DIAS", str(TRIAL_DIAS_PADRAO)))))
    except (TypeError, ValueError):
        return TRIAL_DIAS_PADRAO


def preco(plano_id: str) -> float:
    return PLANOS[plano_id]["preco"]


def preco_mensal() -> float:
    """Valor cheio do plano mensal — referência dos cupons de desconto."""
    return PLANOS["mensal"]["preco"]


def economia_pct(plano_id: str) -> int:
    """Economia sobre pagar o mensal pelo mesmo período (0 no próprio mensal)."""
    p = PLANOS[plano_id]
    cheio = PLANOS["mensal"]["preco"] * p["meses"]
    if p["meses"] <= 1 or cheio <= 0:
        return 0
    return round((1 - p["preco"] / cheio) * 100)


def brl(v: float) -> str:
    """'R$ 1.199,00' — mesma formatação usada nos textos do site."""
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resumo_publico() -> dict:
    """Payload da rota pública GET /api/planos (sem nada sensível)."""
    return {
        "planos": [
            {
                "id": pid,
                "nome": p["nome"],
                "preco": p["preco"],
                "preco_fmt": brl(p["preco"]),
                "dias": p["dias"],
                "meses": p["meses"],
                "economia_pct": economia_pct(pid),
            }
            for pid, p in PLANOS.items()
        ],
        "teste_dias": dias_teste(),
    }
