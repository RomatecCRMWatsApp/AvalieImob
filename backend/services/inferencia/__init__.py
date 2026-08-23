# @module services.inferencia — Motor de Inferência Estatística (MCDDM / tratamento científico).
#
# ABNT NBR 14653-2 (urbano) e 14653-3 (rural). Habilita Grau III de fundamentação,
# exigido em perícia judicial, desapropriação, servidão e imóvel rural de porte.
#
# Portado da implementação de referência aprovada em 21 verificações — a matemática
# não é reescrita; a suíte tests/test_inferencia.py é critério de merge.
from services.inferencia.design_matrix import Especificacao, Regressor
from services.inferencia.enquadramento import carregar_params, enquadrar
from services.inferencia.motor import estimar, serializavel
from services.inferencia.transformacoes import (ROTULO_HUMANO, TRANSFORMACOES,
                                                ErroInferencia)

__all__ = [
    "Especificacao", "Regressor", "estimar", "serializavel",
    "ErroInferencia", "TRANSFORMACOES", "ROTULO_HUMANO",
    "carregar_params", "enquadrar",
]
