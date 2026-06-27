# Testes do módulo Documentos Externos — funções puras (sem mongo).
import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from models.documento_externo import (
    PosicaoAssinatura, Signatario, recalcular_status, novo_signatario,
)


def test_posicao_defaults_tipo_assinatura():
    p = PosicaoAssinatura(pagina=0, x_pt=10, y_pt=20, larg_pt=200, alt_pt=60)
    assert p.tipo == "assinatura"


def test_posicao_rejeita_tipo_invalido():
    with pytest.raises(Exception):
        PosicaoAssinatura(pagina=0, x_pt=0, y_pt=0, larg_pt=1, alt_pt=1, tipo="carimbo")


def test_novo_signatario_gera_id_e_token():
    s = novo_signatario({"nome": "Antônio", "cpf_cnpj": "12345678901",
                         "papel": "Vendedor", "whatsapp": "5599991204706"})
    assert s["id"] and s["token"] and s["status"] == "pendente"
    assert s["whatsapp"] == "5599991204706"


def test_recalcular_status_progressao():
    base = {"requer_icp_rt": True}
    assert recalcular_status({**base, "signatarios": []}) == "rascunho"
    s_pend = [{"status": "enviado"}, {"status": "enviado"}]
    assert recalcular_status({**base, "signatarios": s_pend}) == "aguardando"
    s_parc = [{"status": "assinado"}, {"status": "enviado"}]
    assert recalcular_status({**base, "signatarios": s_parc}) == "parcial"
    s_all = [{"status": "assinado"}, {"status": "assinado"}]
    assert recalcular_status({**base, "signatarios": s_all}) == "clientes_ok"


def test_recalcular_status_sem_icp_finaliza_direto():
    s_all = [{"status": "assinado"}]
    assert recalcular_status({"requer_icp_rt": False, "signatarios": s_all}) == "finalizado"
