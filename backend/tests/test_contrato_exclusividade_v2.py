# @module tests.test_contrato_exclusividade_v2 — multiproprietários + ficha (validações)
import pytest
from pydantic import ValidationError

from models.contrato_exclusividade import (
    ContratoExclusividadeCreate, ProprietarioInput, cpf_valido, cnpj_valido,
)

# CPFs/CNPJ válidos para os testes
CPF_A = "39053344705"
CPF_B = "11144477735"
CPF_C = "52998224725"
CPF_CONJ = "16899535009"
CNPJ = "11222333000181"


def _prop(cpf, frac, **extra):
    base = {"nome": f"Dono {cpf[:3]}", "cpf_cnpj": cpf, "whatsapp": "5599" + cpf[:8],
            "fracao_percentual": frac, "estado_civil": "solteiro"}
    base.update(extra)
    return base


def _imovel():
    return {"endereco": "Rua A, 10", "bairro": "Centro", "descricao_geral": "Casa",
            "valor_anunciado": 300000}


def _contrato(props):
    return {"proprietarios": props, "imovel": _imovel(),
            "comissao_percentual": 6, "prazo_meses": 6}


def test_validadores_documento():
    assert cpf_valido(CPF_A) and not cpf_valido("12345678900")
    assert cnpj_valido(CNPJ) and not cnpj_valido("11111111111111")


def test_fracoes_fecham_100_ok():
    c = ContratoExclusividadeCreate(**_contrato([_prop(CPF_A, 60), _prop(CPF_B, 40)]))
    assert len(c.proprietarios) == 2


def test_fracoes_dizimas_aceitas():
    # 33,33 × 3 = 99,99 → dentro da tolerância
    c = ContratoExclusividadeCreate(**_contrato(
        [_prop(CPF_A, 33.33), _prop(CPF_B, 33.33), _prop(CPF_C, 33.34)]))
    assert len(c.proprietarios) == 3


def test_fracoes_nao_fecham_bloqueia():
    with pytest.raises(ValidationError):
        ContratoExclusividadeCreate(**_contrato([_prop(CPF_A, 40), _prop(CPF_B, 40)]))


def test_cpf_duplicado_bloqueia():
    with pytest.raises(ValidationError):
        ContratoExclusividadeCreate(**_contrato([_prop(CPF_A, 50), _prop(CPF_A, 50)]))


def test_casado_sem_conjuge_bloqueia():
    with pytest.raises(ValidationError):
        ProprietarioInput(**_prop(CPF_A, 100, estado_civil="casado",
                                  regime_bens="comunhao_parcial"))


def test_casado_separacao_total_dispensa_conjuge():
    p = ProprietarioInput(**_prop(CPF_A, 100, estado_civil="casado",
                                  regime_bens="separacao_total"))
    assert p.conjuge is None


def test_pj_nao_exige_conjuge():
    p = ProprietarioInput(**_prop(CNPJ, 100, estado_civil="casado",
                                  regime_bens="comunhao_parcial"))
    assert p.cpf_cnpj == CNPJ and p.conjuge is None


def test_cpf_cnpj_invalido():
    with pytest.raises(ValidationError):
        ProprietarioInput(**_prop("123", 100))


def test_arras_rejeitada():
    payload = _contrato([_prop(CPF_A, 100)])
    payload["arras"] = {"valor": 1000}
    with pytest.raises(ValidationError):
        ContratoExclusividadeCreate(**payload)


def test_signatarios_multiproprietarios():
    """3 condôminos, 2 casados (comunhão parcial) → 5 signatários, WhatsApp distinto."""
    from routes.contratos_exclusividade import _signatarios_de_proprietarios
    props = [
        _prop(CPF_A, 33.34, estado_civil="casado", regime_bens="comunhao_parcial",
              conjuge={"nome": "Cj A", "cpf": CPF_CONJ, "whatsapp": "5599000000001"}),
        _prop(CPF_B, 33.33, estado_civil="casado", regime_bens="comunhao_parcial",
              conjuge={"nome": "Cj B", "cpf": CPF_CONJ, "whatsapp": "5599000000002"}),
        _prop(CPF_C, 33.33),
    ]
    sigs = _signatarios_de_proprietarios(props)
    assert len(sigs) == 5
    assert sum(1 for s in sigs if s["papel"] == "proprietario") == 3
    assert sum(1 for s in sigs if s["papel"] == "conjuge") == 2


def test_signatarios_whatsapp_repetido_422():
    from fastapi import HTTPException
    from routes.contratos_exclusividade import _signatarios_de_proprietarios
    props = [_prop(CPF_A, 50), _prop(CPF_B, 50)]
    props[0]["whatsapp"] = props[1]["whatsapp"] = "5599888887777"
    with pytest.raises(HTTPException) as exc:
        _signatarios_de_proprietarios(props)
    assert exc.value.status_code == 422
