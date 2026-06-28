# @module services.geo_urbano.lotes — sub-projeto de um lote resultante (Desdobro).
#
# Reusa os geradores (Memorial) sobrepondo os dados do lote ao projeto, do mesmo
# jeito que o Georref faz com parcelas (projeto_da_parcela).
from __future__ import annotations


def projeto_do_lote(projeto: dict, lote: dict) -> dict:
    sub = {**projeto}
    sub["denominacao_imovel"] = lote.get("denominacao") or projeto.get("denominacao_imovel")
    sub["area_declarada_m2"] = lote.get("area_declarada_m2")
    sub["perimetro_m"] = lote.get("perimetro_m")
    sub["vertices"] = lote.get("vertices") or []
    sub["lote_resultante"] = lote.get("denominacao")
    sub["cmi_resultante"] = lote.get("cmi_resultante") or projeto.get("cmi_resultante")
    sub["_confrontacoes_lote"] = lote.get("confrontacoes") or []
    return sub
