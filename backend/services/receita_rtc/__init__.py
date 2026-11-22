# @module services.receita_rtc — integração com as calculadoras oficiais da Receita Federal (CBS/IBS/IS).
#
# Camada anti-corrupção: o resto do sistema só conhece os tipos deste pacote.
# A lógica tributária é SEMPRE a da calculadora oficial; aqui não se calcula imposto.
# Regras e decisões: docs/receita-rtc/PENDENCIAS.md (fonte única).
