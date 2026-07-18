# @module tests.test_reativacao — sequência de reativação de cadastros que não ativaram
from datetime import datetime, timedelta

from services.reativacao import (
    ETAPAS_DIAS, DIAS_MIN_ENTRE_ENVIOS, etapa_devida, assunto_e_corpo,
)

AGORA = datetime(2026, 7, 18, 12, 0, 0)


def _user(dias_cadastro=10, enviadas=None, **kw):
    base = {
        "id": "u1",
        "name": "Fulano",
        "email": "f@x.com",
        "plan_status": "inactive",
        "created_at": AGORA - timedelta(days=dias_cadastro),
        "reativacao_enviadas": enviadas if enviadas is not None else [],
    }
    base.update(kw)
    return base


# ── Quem NÃO deve receber ───────────────────────────────────────────────────
def test_assinante_ativo_nunca_recebe():
    assert etapa_devida(_user(plan_status="active"), AGORA) is None


def test_opt_out_nunca_recebe():
    assert etapa_devida(_user(reativacao_opt_out=True), AGORA) is None


def test_sem_email_nao_recebe():
    assert etapa_devida(_user(email=""), AGORA) is None


def test_cadastrado_hoje_ainda_nao_recebe():
    """A etapa 1 é no dia seguinte — ninguém recebe no mesmo dia do cadastro."""
    assert etapa_devida(_user(dias_cadastro=0), AGORA) is None


def test_sequencia_terminada_para_de_enviar():
    todas = list(range(len(ETAPAS_DIAS)))
    u = _user(dias_cadastro=60, enviadas=todas)
    assert etapa_devida(u, AGORA) is None


# ── Progressão da sequência ─────────────────────────────────────────────────
def test_primeira_etapa_no_dia_1():
    assert etapa_devida(_user(dias_cadastro=1), AGORA) == 0


def test_nao_repete_etapa_ja_enviada():
    u = _user(dias_cadastro=1, enviadas=[0],
              reativacao_ultimo_envio=AGORA - timedelta(days=5))
    assert etapa_devida(u, AGORA) is None, "etapa 2 so vence no dia 3"


def test_avanca_para_proxima_etapa_quando_vence():
    u = _user(dias_cadastro=4, enviadas=[0],
              reativacao_ultimo_envio=AGORA - timedelta(days=3))
    assert etapa_devida(u, AGORA) == 1


def test_cadastro_antigo_comeca_do_inicio_da_sequencia():
    """REGRA: quem esta na fila ha meses recebe a etapa 1 primeiro, nao a ultima."""
    assert etapa_devida(_user(dias_cadastro=200), AGORA) == 0


def test_respeita_intervalo_minimo_entre_envios():
    """Cadastro antigo nao pode receber a sequencia toda em rajada."""
    u = _user(dias_cadastro=200, enviadas=[0],
              reativacao_ultimo_envio=AGORA - timedelta(days=1))
    assert etapa_devida(u, AGORA) is None

    u["reativacao_ultimo_envio"] = AGORA - timedelta(days=DIAS_MIN_ENTRE_ENVIOS)
    assert etapa_devida(u, AGORA) == 1


# ── Conteúdo ────────────────────────────────────────────────────────────────
def test_cada_etapa_tem_conteudo_proprio():
    vistos = set()
    for i in range(len(ETAPAS_DIAS)):
        assunto, html = assunto_e_corpo(i, _user(), "https://app/x", "https://unsub/x")
        assert assunto and html
        assert assunto not in vistos, "cada etapa precisa de assunto proprio"
        vistos.add(assunto)


def test_texto_muda_para_quem_parou_no_checkout():
    """Quem chegou ao pagamento tem objecao diferente de quem nunca entrou."""
    nunca = _user(status_funil="never_started")
    checkout = _user(status_funil="checkout_started")
    a1, _ = assunto_e_corpo(0, nunca, "u", "s")
    a2, _ = assunto_e_corpo(0, checkout, "u", "s")
    assert a1 != a2


def test_todo_email_traz_link_de_descadastro():
    for i in range(len(ETAPAS_DIAS)):
        _, html = assunto_e_corpo(i, _user(), "https://app/x", "https://unsub/abc")
        assert "https://unsub/abc" in html, "LGPD: opt-out obrigatorio"


def test_cadastro_sem_data_entra_na_sequencia():
    """REGRESSAO: user sem created_at sumia da fila em silencio (nunca recebia)."""
    u = _user()
    del u["created_at"]
    assert etapa_devida(u, AGORA) == 0


def test_cadastro_com_data_invalida_tambem_entra():
    assert etapa_devida(_user(created_at="data-quebrada"), AGORA) == 0


def test_sem_data_ainda_respeita_opt_out_e_plano_ativo():
    """A tolerancia com a data nao pode furar as travas que importam."""
    u = _user(plan_status="active"); del u["created_at"]
    assert etapa_devida(u, AGORA) is None
    u2 = _user(reativacao_opt_out=True); del u2["created_at"]
    assert etapa_devida(u2, AGORA) is None
