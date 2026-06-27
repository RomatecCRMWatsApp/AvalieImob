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


def _pdf_uma_pagina() -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 720, "Documento de teste")
    c.showPage()
    c.save()
    return buf.getvalue()


def _png_1x1() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 0, 0, 255)).save(b, format="PNG")
    return b.getvalue()


def test_carimbar_multi_estampa_e_anexa_folha():
    from services.assinatura_cliente_carimbo import carimbar_multi
    from pypdf import PdfReader
    pdf = _pdf_uma_pagina()
    sigs = [{
        "nome": "Antônio", "cpf": "12345678901", "role": "Vendedor",
        "assinado_em": None, "ip": "1.2.3.4", "user_agent": "UA",
        "traco_png": _png_1x1(),
        "posicoes": [
            {"pagina": 0, "x_pt": 60, "y_pt": 80, "larg_pt": 180, "alt_pt": 50, "tipo": "assinatura"},
            {"pagina": 0, "x_pt": 60, "y_pt": 140, "larg_pt": 180, "alt_pt": 20, "tipo": "nome_extenso"},
            {"pagina": 0, "x_pt": 300, "y_pt": 80, "larg_pt": 120, "alt_pt": 20, "tipo": "data"},
        ],
    }]
    out, h = carimbar_multi(pdf, sigs)
    assert out.startswith(b"%PDF-") and len(h) == 64
    # original 1 pág + folha de autoria = 2 páginas
    assert len(PdfReader(io.BytesIO(out)).pages) == 2
