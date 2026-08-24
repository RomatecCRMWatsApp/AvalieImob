# @module tests.test_origem_trafego — de onde vieram os cadastros (Google, Bing, direto…).
#
# O dado JÁ é gravado no doc do usuário desde o cadastro (routes/auth.py grava
# utm_* + referrer + page_origin). Aqui só classificamos e agregamos.
from datetime import datetime, timedelta

from services import origem_trafego as OT


def u(**kw):
    base = {"id": "u1", "name": "Fulano", "email": "f@x.com", "plan_status": "inactive"}
    base.update(kw)
    return base


# ── Classificação ────────────────────────────────────────────────────────────
def test_busca_organica_pelo_referrer():
    assert OT.classificar(u(referrer="https://www.google.com/"))["canal"] == "google"
    assert OT.classificar(u(referrer="https://www.bing.com/"))["canal"] == "bing"
    assert OT.classificar(u(referrer="https://duckduckgo.com/"))["canal"] == "duckduckgo"


def test_organico_marca_tipo_e_rotulo():
    r = OT.classificar(u(referrer="https://www.bing.com/search?q=avaliacao"))
    assert r["tipo"] == "organico"
    assert r["label"] == "Bing (orgânico)"


def test_sem_referrer_e_sem_utm_e_direto():
    r = OT.classificar(u())
    assert r["canal"] == "direto" and r["label"] == "Direto"


def test_utm_vence_o_referrer():
    """Campanha marcada com UTM manda, mesmo que o referrer diga outra coisa."""
    r = OT.classificar(u(referrer="https://www.google.com/", utm_source="instagram",
                         utm_medium="social", utm_campaign="folder-agosto"))
    assert r["canal"] == "instagram" and r["tipo"] == "social"
    assert r["campanha"] == "folder-agosto"


def test_utm_paga_marca_tipo_pago():
    r = OT.classificar(u(utm_source="google", utm_medium="cpc"))
    assert r["canal"] == "google" and r["tipo"] == "pago"
    assert r["label"] == "Google Ads"


def test_redes_e_mensageria():
    assert OT.classificar(u(referrer="https://l.instagram.com/"))["canal"] == "instagram"
    assert OT.classificar(u(referrer="https://www.facebook.com/"))["canal"] == "facebook"
    assert OT.classificar(u(referrer="https://api.whatsapp.com/x"))["canal"] == "whatsapp"
    assert OT.classificar(u(referrer="https://t.me/canal"))["canal"] == "telegram"


def test_site_desconhecido_vira_referral_com_o_dominio():
    r = OT.classificar(u(referrer="https://portalx.com.br/materia"))
    assert r["canal"] == "referral" and r["detalhe"] == "portalx.com.br"
    assert "portalx.com.br" in r["label"]


def test_navegacao_dentro_do_proprio_site_nao_vira_canal():
    r = OT.classificar(u(referrer="https://www.romatecavalieimob.com.br/blog/ptam"))
    assert r["canal"] == "direto"


def test_pagina_de_entrada_e_preservada():
    r = OT.classificar(u(page_origin="/blog/o-que-e-ptam"))
    assert r["pagina_entrada"] == "/blog/o-que-e-ptam"


# ── Agregação ────────────────────────────────────────────────────────────────
def test_resumo_conta_por_canal_e_ordena_do_maior():
    docs = [u(referrer="https://www.bing.com/") for _ in range(4)]
    docs += [u(referrer="https://www.google.com/") for _ in range(2)]
    docs += [u() for _ in range(6)]
    r = OT.resumo_por_canal(docs)
    assert [c["canal"] for c in r] == ["direto", "bing", "google"]
    assert [c["total"] for c in r] == [6, 4, 2]


def test_resumo_conta_assinantes_e_conversao():
    docs = [
        u(referrer="https://www.google.com/", plan_status="active", plan="mensal"),
        u(referrer="https://www.google.com/", plan_status="inactive"),
        u(referrer="https://www.bing.com/", plan_status="active", plan="trial", trial=True),
    ]
    r = {c["canal"]: c for c in OT.resumo_por_canal(docs)}
    assert r["google"]["assinantes"] == 1 and r["google"]["conversao"] == 50.0
    # trial ativo NÃO conta como assinante pagante — conta como teste
    assert r["bing"]["assinantes"] == 0 and r["bing"]["em_teste"] == 1


def test_resumo_respeita_janela_de_dias():
    agora = datetime.utcnow()
    docs = [
        u(referrer="https://www.bing.com/", created_at=agora - timedelta(days=2)),
        u(referrer="https://www.google.com/", created_at=agora - timedelta(days=90)),
    ]
    r = OT.resumo_por_canal(docs, dias=30, agora=agora)
    assert [c["canal"] for c in r] == ["bing"]


def test_view_de_cadastro_traz_campos_da_tela():
    d = OT.view_cadastro(u(name="Cristiano", referrer="https://www.google.com/",
                           plan="trial", plan_status="active", trial=True,
                           created_at=datetime(2026, 8, 20, 12, 0)))
    assert d["canal_label"] == "Google (orgânico)"
    assert d["situacao"] == "em_teste"
    assert d["cadastrado_em"].startswith("2026-08-20")
    assert "password_hash" not in d


# ── Peças de divulgação: cada canal precisa aparecer legível no painel ───────
def test_folder_pelo_whatsapp():
    r = OT.classificar(u(utm_source="whatsapp", utm_medium="folder",
                         utm_campaign="folder-topografia"))
    assert r["canal"] == "whatsapp" and r["label"] == "WhatsApp"
    assert r["tipo"] == "social" and r["campanha"] == "folder-topografia"


def test_qr_code_impresso_tem_rotulo_legivel():
    r = OT.classificar(u(utm_source="qrcode", utm_medium="impresso",
                         utm_campaign="folder-avaliacao"))
    assert r["canal"] == "qrcode" and r["label"] == "QR Code"
    assert r["campanha"] == "folder-avaliacao"


def test_link_copiado_tem_rotulo_legivel():
    r = OT.classificar(u(utm_source="link", utm_medium="folder",
                         utm_campaign="folder-geral"))
    assert r["label"] == "Link compartilhado"


def test_folders_aparecem_separados_no_ranking():
    """O ponto da marcação: parar de cair tudo em 'Direto'."""
    docs = [u(utm_source="whatsapp", utm_medium="folder", utm_campaign="folder-topografia"),
            u(utm_source="whatsapp", utm_medium="folder", utm_campaign="folder-topografia"),
            u(utm_source="qrcode", utm_medium="impresso", utm_campaign="folder-avaliacao"),
            u()]
    ranking = {c["canal"]: c["total"] for c in OT.resumo_por_canal(docs)}
    assert ranking == {"whatsapp": 2, "qrcode": 1, "direto": 1}
