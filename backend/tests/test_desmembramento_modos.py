# Testes da exposição do modo de precificação do Desmembramento (§6) via chaves flat:
# 'auto' não deve acionar modo_precificacao; por_imovel e personalizado por chaves planas.
from services.pricing.desmembramento import calcular_desmembramento


def _base(**extra):
    d = {"tipo": "desmembramento", "tipo_zona": "urbana", "area_total_m2": 1000,
         "valor_venal_total": 300000, "numero_lotes_resultantes": 3,
         "honorario_projeto_sm": 1, "iptu_em_dia": True}
    d.update(extra)
    return d


def test_modo_auto_nao_aciona_modo_precificacao():
    # 'auto' (ou vazio) deve cair no cálculo paramétrico padrão, sem levantar erro
    sem = calcular_desmembramento(_base())["custos"]
    auto = calcular_desmembramento(_base(modo_precificacao="auto"))["custos"]
    assert auto["secao_5_total"] == sem["secao_5_total"]
    vazio = calcular_desmembramento(_base(modo_precificacao=""))["custos"]
    assert vazio["secao_5_total"] == sem["secao_5_total"]


def test_modo_por_imovel_flat():
    c = calcular_desmembramento(_base(modo_precificacao="por_imovel", valor_por_imovel=1500))["custos"]
    assert c["secao_3_honorarios"][0]["valor"] == 4500.0   # 1500 × 3 lotes
    assert "3 im" in c["secao_3_honorarios"][0]["descricao"].lower()


def test_modo_personalizado_flat():
    c = calcular_desmembramento(_base(
        modo_precificacao="personalizado",
        honorarios_personalizados_valor=4800,
        honorarios_personalizados_descritivo="Pacote fechado combinado"))["custos"]
    linha = c["secao_3_honorarios"][0]
    assert linha["valor"] == 4800.0
    assert "Pacote fechado combinado" in (linha.get("observacao") or "")
