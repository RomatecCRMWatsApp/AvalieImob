"""Composição do Dossiê de protocolo do ONR (SIG-RI) + geração do dossiê PDF."""
import io

from services.onr_sigri import composicao as C
from services.onr_sigri import dossie as D


def _job(**kw):
    base = {
        "numero": "ONR-2026-0001", "denominacao_imovel": "CHACARA BOA VISTA",
        "municipio": "Acailandia", "uf": "MA", "area_declarada_m2": 65077.0,
        "perimetro_m": 1035.13, "fuso": 23, "hemisferio": "S",
        "vertices": [{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}],
        "matriculas": [{"matricula": "9809"}], "partes": [{"nome": "Sergio Leite", "cpf": "1"}],
        "cartorio": {"nome": "RI Acailandia", "comarca": "Acailandia"},
        "anexos": [
            {"id": "a1", "tipo": "Certidão de Matrícula", "nome": "Matricula", "ordem": 0, "key": "k1"},
            {"id": "a2", "tipo": "Comprovante", "nome": "Comprovante", "ordem": 1, "key": "k2"},
            {"id": "a3", "tipo": "Mapa / Planta", "nome": "Mapa", "ordem": 2, "key": "k3"},
        ],
    }
    base.update(kw)
    return base


def _pdf_bytes(txt="X"):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b, pagesize=A4)
    c.drawString(100, 700, txt)
    c.showPage()
    c.save()
    return b.getvalue()


def _png_bytes():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (400, 300), (200, 180, 90)).save(b, "PNG")
    return b.getvalue()


def test_opcoes_presets_e_pecas_fixas():
    op = C.opcoes()
    assert op["presets"] == ["COMPLETO", "PROTOCOLO", "SIMPLIFICADO", "PERSONALIZADO"]
    chaves = {p["chave"] for p in op["pecas_fixas"]}
    assert chaves == {"capa", "descricao_poligono"}


def test_default_tudo_ligado_retrocompativel():
    r = C.resolver_composicao(_job())  # sem composicao salva
    assert r["capa"] and r["descricao_poligono"]
    assert all(a["ligada"] for a in r["anexos"])
    assert r["total_no_dossie"] == 5   # capa + descrição + 3 anexos


def test_preset_protocolo_exclui_comprovante():
    j = _job()
    j["composicao"] = {"preset": "PROTOCOLO", "capa": True, "descricao_poligono": True,
                       "anexos_off": C.anexos_off_do_preset(j, "PROTOCOLO")}
    ligados = [a["nome"] for a in C.resolver_composicao(j)["anexos"] if a["ligada"]]
    assert ligados == ["Matricula", "Mapa"]        # Comprovante fora


def test_preset_simplificado_desliga_por_tipo():
    j = _job()
    off = C.anexos_off_do_preset(j, "SIMPLIFICADO")
    assert off == ["a2"]                            # só Comprovante fora


def test_anexos_ligados_respeita_off():
    j = _job(composicao={"anexos_off": ["a2"]})
    ids = [a["id"] for a in C.anexos_ligados(j)]
    assert ids == ["a1", "a3"]


def test_descricao_habilitada_exige_poligonal():
    j = _job(vertices=[])                           # sem vértices
    assert C.resolver_composicao(j)["descricao_habilitada"] is False


def test_descricao_poligono_texto():
    t = D.descricao_poligono(_job())
    assert "matrícula nº 9809" in t
    assert "SIRGAS 2000" in t and "UTM fuso 23S" in t
    assert "NBR 17047" in t


def test_gerar_dossie_capa_descricao_e_anexos():
    j = _job()
    anexos = [
        {"nome": "Matricula", "mime": "application/pdf", "bytes": _pdf_bytes("MATRICULA")},
        {"nome": "Comprovante", "mime": "image/png", "bytes": _png_bytes()},
    ]
    pdf = D.gerar_dossie(j, True, True, anexos)
    assert pdf[:5] == b"%PDF-"
    from pypdf import PdfReader
    n = len(PdfReader(io.BytesIO(pdf)).pages)
    assert n == 4                                   # capa + descrição + PDF(1) + imagem(1)


def test_gerar_dossie_sem_capa_nem_descricao_so_anexos():
    j = _job()
    pdf = D.gerar_dossie(j, False, False, [{"nome": "M", "mime": "application/pdf", "bytes": _pdf_bytes()}])
    from pypdf import PdfReader
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 1
