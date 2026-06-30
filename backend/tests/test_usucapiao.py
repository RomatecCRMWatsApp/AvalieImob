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
