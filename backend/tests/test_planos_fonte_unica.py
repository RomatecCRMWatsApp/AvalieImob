"""Guarda da fonte única de planos (services/planos.py).

Preço e dias de teste aparecem também em textos fixos que não dá para tornar
dinâmicos (dados do Google, folders, páginas de serviço, blog). Este teste falha
e aponta o arquivo quando algum desses textos diverge da fonte única — evita o
site mostrar um preço e o Mercado Pago cobrar outro.
"""
import re
from pathlib import Path

from services import planos as P
from services.mercadopago_service import PLAN_CONFIG

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"

# Arquivos que citam os valores da assinatura (e só eles — sem outros valores em R$).
ARQUIVOS_PRECO = [
    "frontend/src/pages/Planos.jsx",
    "frontend/src/pages/ServicoPTAM.jsx",
    "frontend/src/pages/ServicoLaudoTecnico.jsx",
    "frontend/src/pages/admin/DivulgacaoPage.jsx",
    "frontend/public/index.html",
    "frontend/public/folder/geral.html",
    "frontend/public/folder/index.html",
    "frontend/public/folder/avaliacao.html",
]

_RE_BRL = re.compile(r"R\$ ?(\d[\d.]*,\d{2})")
_RE_DIAS = re.compile(
    r"(\d+) dias (?:grátis|de teste)|grátis (?:por|de) (\d+) dias"
    r"|[Tt]este (?:grátis )?(?:de|por) (\d+) dias|\*(\d+) dias\*"
)


def _ler(rel: str) -> str:
    return (RAIZ / rel).read_text(encoding="utf-8")


def test_cobranca_usa_a_fonte_unica():
    for pid, p in P.PLANOS.items():
        assert PLAN_CONFIG[pid]["unit_price"] == p["preco"]
        assert PLAN_CONFIG[pid]["days"] == p["dias"]


def test_economia_calculada_bate_com_os_valores_atuais():
    assert P.economia_pct("mensal") == 0
    assert P.economia_pct("trimestral") == 21
    assert P.economia_pct("anual") == 47


def test_dias_teste_respeita_variavel(monkeypatch):
    monkeypatch.delenv("TRIAL_CADASTRO_DIAS", raising=False)
    assert P.dias_teste() == P.TRIAL_DIAS_PADRAO
    monkeypatch.setenv("TRIAL_CADASTRO_DIAS", "3")
    assert P.dias_teste() == 3
    monkeypatch.setenv("TRIAL_CADASTRO_DIAS", "99")
    assert P.dias_teste() == P.TRIAL_DIAS_TETO
    monkeypatch.setenv("TRIAL_CADASTRO_DIAS", "abc")
    assert P.dias_teste() == P.TRIAL_DIAS_PADRAO


def test_resumo_publico_tem_os_tres_planos():
    r = P.resumo_publico()
    assert [x["id"] for x in r["planos"]] == ["mensal", "trimestral", "anual"]
    assert r["planos"][2]["preco_fmt"] == "R$ 1.199,00"
    assert isinstance(r["teste_dias"], int)


def test_textos_fixos_citam_so_os_precos_atuais():
    validos = {P.brl(p["preco"])[3:] for p in P.PLANOS.values()}
    erros = []
    for rel in ARQUIVOS_PRECO:
        for valor in _RE_BRL.findall(_ler(rel)):
            if valor not in validos:
                erros.append(f"{rel}: R$ {valor}")
    assert not erros, "Preço divergente de services/planos.py:\n" + "\n".join(erros)


def test_preco_dos_dados_do_google_e_o_mensal():
    esperado = f"{P.preco_mensal():.2f}"
    for rel, padrao in [
        ("frontend/public/index.html", r'"price":\s*"([\d.]+)"'),
        ("frontend/src/pages/LandingPage.jsx", r"price:\s*'([\d.]+)'"),
        ("frontend/src/pages/ServicoTemplate.jsx", r"price:\s*'([\d.]+)'"),
    ]:
        achados = re.findall(padrao, _ler(rel))
        assert achados and all(a == esperado for a in achados), f"{rel}: {achados} ≠ {esperado}"


def test_mock_do_front_bate_com_a_fonte_unica():
    # mock.PLANS é a reserva da tela quando GET /api/planos falha.
    txt = _ler("frontend/src/mock/mock.js")
    precos = [float(x) for x in re.findall(r"price:\s*([\d.]+)", txt)[:3]]
    assert precos == [p["preco"] for p in P.PLANOS.values()]


def test_textos_fixos_citam_os_dias_de_teste_padrao():
    erros = []
    alvos = [p for p in (FRONT / "src").rglob("*") if p.suffix in (".js", ".jsx")]
    alvos += list((FRONT / "public").rglob("*.html"))
    alvos.append(RAIZ / "backend" / "server.py")
    for arq in alvos:
        txt = arq.read_text(encoding="utf-8", errors="ignore")
        for m in _RE_DIAS.finditer(txt):
            n = next(g for g in m.groups() if g)
            if int(n) != P.TRIAL_DIAS_PADRAO:
                erros.append(f"{arq.relative_to(RAIZ)}: '{m.group(0)}'")
    assert not erros, (
        f"Dias de teste divergentes do padrão ({P.TRIAL_DIAS_PADRAO}) de services/planos.py:\n"
        + "\n".join(erros)
    )
