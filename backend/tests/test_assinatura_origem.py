# Testes do resolver de PDF de origem do BYOK: cada origem_tipo despacha p/ a coleção
# e o gerador certos (geradores mockados p/ não renderizar ReportLab real).
import asyncio

import pytest

from services.assinatura import origem_pdf as OP


# ── Fake DB minimalista ─────────────────────────────────────────────────────────
class _Coll:
    def __init__(self):
        self.docs = []

    async def find_one(self, flt):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in flt.items())), None)


class _FakeDB:
    def __init__(self):
        self._colls = {}

    def _c(self, name):
        return self._colls.setdefault(name, _Coll())

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._c(name)

    def __getitem__(self, name):
        return self._c(name)


def _seed(db, coll, doc):
    db._c(coll).docs.append(doc)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def db():
    return _FakeDB()


# ── PTAM ────────────────────────────────────────────────────────────────────────
def test_ptam(db, monkeypatch):
    import services.ptam_pdf_v2 as P
    monkeypatch.setattr(P, "generate_ptam_pdf_v2", lambda doc, perfil: b"%PDF-ptam", raising=True)
    _seed(db, "ptam_documents", {"id": "x", "user_id": "u", "number": "PTAM 12/2026"})
    pdf, nome = _run(OP.resolver(db, "u", "ptam", "x"))
    assert pdf == b"%PDF-ptam"
    assert nome == "PTAM_PTAM 12-2026.pdf"  # barra vira hífen


# ── Recibo ────────────────────────────────────────────────────────────────────────
def test_recibo(db, monkeypatch):
    import pdf.recibo_pdf as R
    import services.recibo_anexos as A
    monkeypatch.setattr(R, "gerar_recibo_pdf", lambda **k: b"%PDF-rec", raising=True)

    async def _anx(db_, doc, pdf_bytes):
        return pdf_bytes + b"+anx"
    monkeypatch.setattr(A, "anexar_anexos_ao_pdf", _anx, raising=True)

    _seed(db, "recibos", {"id": "r1", "user_id": "u", "numero": "REC-2026/007"})
    pdf, nome = _run(OP.resolver(db, "u", "recibo", "r1"))
    assert pdf == b"%PDF-rec+anx"          # anexos embutidos
    assert nome == "Recibo_REC-2026-007.pdf"


# ── Contrato de exclusividade ─────────────────────────────────────────────────────
def test_contrato_exclusividade(db, monkeypatch):
    import services.contrato_exclusividade_pdf as C
    monkeypatch.setattr(C, "gerar_pdf_rascunho", lambda doc: b"%PDF-excl", raising=True)
    _seed(db, "contratos_exclusividade", {"id": "c1", "user_id": "u", "numero": "EXCL-1"})
    pdf, nome = _run(OP.resolver(db, "u", "contrato_exclusividade", "c1"))
    assert pdf == b"%PDF-excl"
    assert nome == "Contrato_Exclusividade_EXCL-1.pdf"


# ── Documento externo (bytes do R2) ───────────────────────────────────────────────
def test_documento_externo(db, monkeypatch):
    from services.documento_externo_service import COL
    import services.r2_storage as S
    monkeypatch.setattr(S, "download_bytes", lambda key: b"%PDF-ext", raising=True)
    _seed(db, COL, {"id": "d1", "user_id": "u", "nome": "Termo/Vistoria", "pdf_key": "doc-ext/u/d1.pdf"})
    pdf, nome = _run(OP.resolver(db, "u", "documento_externo", "d1"))
    assert pdf == b"%PDF-ext"
    assert nome == "Termo-Vistoria.pdf"


def test_documento_externo_sem_pdf(db):
    from services.documento_externo_service import COL
    _seed(db, COL, {"id": "d2", "user_id": "u", "nome": "x"})  # sem pdf_key
    with pytest.raises(OP.OrigemNaoSuportada):
        _run(OP.resolver(db, "u", "documento_externo", "d2"))


# ── Laudo de agrimensura ──────────────────────────────────────────────────────────
def test_laudo_agrimensura(db, monkeypatch):
    from services.georef.generators import pdf as PDF
    monkeypatch.setattr(PDF, "gerar_pdf", lambda tipo, doc, tema: b"%PDF-laudo", raising=True)
    _seed(db, "georef_projetos", {"id": "g1", "user_id": "u", "numero": "GEO-2026-0001"})
    pdf, nome = _run(OP.resolver(db, "u", "laudo_agrimensura", "g1"))
    assert pdf == b"%PDF-laudo"
    assert nome == "Laudo_Agrimensura_GEO-2026-0001.pdf"


# ── Erros ─────────────────────────────────────────────────────────────────────────
def test_origem_nao_encontrada(db, monkeypatch):
    import services.ptam_pdf_v2 as P
    monkeypatch.setattr(P, "generate_ptam_pdf_v2", lambda doc, perfil: b"x", raising=True)
    with pytest.raises(OP.OrigemNaoSuportada):
        _run(OP.resolver(db, "u", "ptam", "inexistente"))


def test_isolamento_por_user(db, monkeypatch):
    import services.ptam_pdf_v2 as P
    monkeypatch.setattr(P, "generate_ptam_pdf_v2", lambda doc, perfil: b"x", raising=True)
    _seed(db, "ptam_documents", {"id": "x", "user_id": "OUTRO", "number": "1"})
    with pytest.raises(OP.OrigemNaoSuportada):
        _run(OP.resolver(db, "u", "ptam", "x"))  # dono diferente → não acha


def test_outro_nao_suportado(db):
    with pytest.raises(OP.OrigemNaoSuportada):
        _run(OP.resolver(db, "u", "outro", "z"))
