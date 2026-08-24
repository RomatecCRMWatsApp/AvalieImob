# @module tests.test_qr_divulgacao — QR das peças de divulgação em PDF vetorial.
#
# O ponto sensível é o badge da marca no centro: quanto mais longa a URL (a
# marcação de origem alongou todas), mais denso o QR — e um badge de tamanho
# fixo passa a cobrir um padrão de alinhamento e o código deixa de ser lido.
# Foi o que aconteceu com a peça de topografia. Por isso o badge é medido em
# módulos, e os testes abaixo cobrem justamente esse limite.
import pytest

from services.qr_divulgacao import (UrlNaoPermitida, _fracao_badge, gerar_pdf,
                                    validar_url)

BASE = "https://www.romatecavalieimob.com.br"

# As mesmas peças do painel (DivulgacaoPage), já com a marcação de origem.
PECAS = [
    ("geral", f"{BASE}/folder/"),
    ("avaliacao", f"{BASE}/folder/avaliacao.html"),
    ("contratos", f"{BASE}/folder/contratos.html"),
    ("topografia", f"{BASE}/folder/topografia.html"),
    ("calculadora", f"{BASE}/quanto-vale-meu-imovel"),
    ("pagamento", f"{BASE}/pagamento/"),
    # Estresse: mais longa que qualquer peça real (URL de artigo do blog).
    ("estresse", f"{BASE}/blog/inferencia-estatistica-avaliacao-imoveis-tratamento-cientifico"),
]


def marcada(url: str, arquivo: str) -> str:
    sep = "&" if "?" in url else "?"
    return (f"{url}{sep}utm_source=qrcode&utm_medium=impresso"
            f"&utm_campaign=folder-{arquivo}")


def test_gera_pdf_valido():
    pdf = gerar_pdf(marcada(f"{BASE}/folder/", "geral"), "Geral")
    assert pdf.startswith(b"%PDF-") and len(pdf) > 1000


def test_recusa_endereco_de_fora():
    """O endpoint é administrativo, mas não pode virar gerador de QR aberto."""
    for ruim in ("https://exemplo.com/x", "javascript:alert(1)", "", "ftp://x.com"):
        with pytest.raises(UrlNaoPermitida):
            validar_url(ruim)


def test_aceita_o_proprio_dominio_com_e_sem_www():
    assert validar_url(f"{BASE}/folder/")
    assert validar_url("https://romatecavalieimob.com.br/pagamento/")


def test_badge_encolhe_quando_o_codigo_fica_mais_denso():
    """É a regra que impede o badge de comer um padrão de alinhamento."""
    assert _fracao_badge(41) > _fracao_badge(61) > _fracao_badge(77)
    assert _fracao_badge(21) <= 0.19          # teto em código curto
    assert _fracao_badge(61) * 61 * 1.32 <= 12  # área branca em módulos


def test_pdf_e_vetorial_sem_imagem_embutida():
    """Se entrar bitmap, a gráfica amplia e serrilha — o ponto do PDF é ser vetor."""
    fitz = pytest.importorskip("fitz")
    pdf = gerar_pdf(marcada(f"{BASE}/folder/topografia.html", "topografia"), "Topografia")
    pagina = fitz.open(stream=pdf, filetype="pdf")[0]
    assert pagina.get_images(full=True) == []
    assert pagina.get_drawings()


@pytest.mark.parametrize("arquivo,url", PECAS)
def test_todas_as_pecas_sao_lidas_por_um_leitor(arquivo, url):
    """Prova de ponta: rasteriza o PDF e lê o QR, como faria um celular."""
    fitz = pytest.importorskip("fitz")
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    alvo = marcada(url, arquivo)
    pdf = gerar_pdf(alvo, arquivo)
    # 200 dpi é mais duro que a impressão real — se passa aqui, passa no papel.
    pix = fitz.open(stream=pdf, filetype="pdf")[0].get_pixmap(dpi=200)
    img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
    lido, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    assert (lido or "").strip() == alvo
