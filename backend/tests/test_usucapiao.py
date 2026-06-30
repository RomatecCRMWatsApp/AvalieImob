# Testes do serviço de Usucapião Extrajudicial (Geo Urbano) — modelo, modalidades,
# validação de posse, checklist dinâmica, anuentes, geradores e dossiê.
import io
import pytest
from pypdf import PdfReader
from models.geo_urbano import GeoUrbanoProjeto


def _paginas(data: bytes) -> int:
    assert data[:5] == b"%PDF-"
    return len(PdfReader(io.BytesIO(data)).pages)


def test_modelo_usucapiao_valido():
    p = GeoUrbanoProjeto(
        denominacao_imovel="Lote 12 — Quadra 8 — Vila São Francisco",
        tipo_servico="usucapiao",
        modalidade_usucapiao="extraordinaria",
        situacao_registral="nao_matriculado",
        valor_atribuido=85000.0,
        soma_posses=[
            {"possuidor_nome": "Maria das Dores", "vinculo": "de_cujus",
             "inicio": "2008", "fim": "2018"},
            {"possuidor_nome": "João Filho", "vinculo": "proprio",
             "inicio": "2018", "fim": "atual"},
        ],
        provas_posse=[{"tipo": "iptu", "ano": "2010", "descricao": "Carnê de IPTU 2010"}],
        anuentes=[{"papel": "confrontante", "nome": "Vizinho Norte",
                   "lado": "fundo", "tipo": "particular", "canal": "presencial"}],
        checklist=[{"bloco": "A", "chave": "requerimento", "label": "Requerimento",
                    "obrigatorio": True, "status": "pendente"}],
        partes=[{"papel": "advogado", "tipo_pessoa": "fisica", "nome": "Dra. Ana",
                 "oab": "OAB/MA 12345"}],
    )
    assert p.modalidade_usucapiao == "extraordinaria"
    assert p.posse.natureza.startswith("mansa")
    assert len(p.soma_posses) == 2 and p.soma_posses[0].vinculo == "de_cujus"
    assert len(p.provas_posse) == 1 and p.provas_posse[0].tipo == "iptu"
    assert p.anuentes[0].anuencia.status == "pendente"
    assert p.partes[0].oab == "OAB/MA 12345"


from services.geo_urbano import usucapiao as USU


def test_modalidades_catalogo():
    assert set(USU.MODALIDADES) == {
        "extraordinaria", "ordinaria", "especial_urbana", "especial_rural",
        "familiar", "coletiva", "outra",
    }
    assert USU.MODALIDADES["extraordinaria"]["prazo_anos"] == 15
    assert USU.MODALIDADES["especial_urbana"]["area_max_m2"] == 250.0
    assert USU.MODALIDADES["ordinaria"]["exige_justo_titulo"] is True


def test_validar_posse_soma_alcanca_prazo():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [
                {"vinculo": "de_cujus", "inicio": "2008", "fim": "2018"},
                {"vinculo": "proprio", "inicio": "2018", "fim": "atual"}]}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["anos_cobertos"] == 18
    assert r["prazo_exigido"] == 15
    assert r["prazo_ok"] is True
    assert r["faltam_anos"] == 0


def test_validar_posse_soma_nao_alcanca():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [{"vinculo": "proprio", "inicio": "2018", "fim": "atual"}]}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["anos_cobertos"] == 8
    assert r["prazo_ok"] is False
    assert r["faltam_anos"] == 7


def test_validar_posse_area_excede():
    proj = {"modalidade_usucapiao": "especial_urbana", "area_declarada_m2": 320.0,
            "posse": {"inicio": "2015"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["area_ok"] is False
    assert r["area_max"] == 250.0


def test_validar_posse_tema_815_nao_trava_modulo_municipal():
    # STF Tema 815: especial urbana NÃO se condiciona ao módulo mínimo municipal.
    proj = {"modalidade_usucapiao": "especial_urbana", "area_declarada_m2": 120.0,
            "lote_minimo_municipal_m2": 250.0, "posse": {"inicio": "2018"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["area_ok"] is True
    assert r["ignora_modulo_municipal"] is True
    assert any("815" in a or "módulo" in a.lower() for a in r["avisos"])


def test_validar_posse_ordinaria_exige_justo_titulo():
    proj = {"modalidade_usucapiao": "ordinaria",
            "posse": {"inicio": "2010"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["exige_justo_titulo"] is True
    assert r["justo_titulo_ok"] is False
    proj["posse"]["justo_titulo"] = "Cessão de direitos hereditários, fls. 12"
    r2 = USU.validar_posse(proj, ano_ref=2026)
    assert r2["justo_titulo_ok"] is True
