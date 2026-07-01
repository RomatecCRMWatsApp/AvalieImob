# @module utils.extenso — Valor monetário por extenso (pt-BR), suporte até 999 bilhões.
# BUG-01: garante que o valor por extenso NUNCA saia vazio no laudo.
#
# Usa num2words quando disponível; caso contrário, recorre a um conversor puro
# em Python (sem dependências) — assim o laudo sempre tem o valor escrito.
from __future__ import annotations

from typing import Optional

# ── Conversor puro (fallback) ──────────────────────────────────────────────
_UNIDADES = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
_DEZ_A_DEZENOVE = ["dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis",
                   "dezessete", "dezoito", "dezenove"]
_DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta",
            "oitenta", "noventa"]
_CENTENAS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
             "seiscentos", "setecentos", "oitocentos", "novecentos"]
# (singular, plural) por escala de milhar
_ESCALAS = [("", ""), ("mil", "mil"), ("milhão", "milhões"),
            ("bilhão", "bilhões"), ("trilhão", "trilhões")]


def _centena_extenso(n: int) -> str:
    """Converte 0..999 em texto."""
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    partes = []
    centena = n // 100
    resto = n % 100
    if centena:
        partes.append(_CENTENAS[centena])
    if resto:
        if resto < 10:
            partes.append(_UNIDADES[resto])
        elif resto < 20:
            partes.append(_DEZ_A_DEZENOVE[resto - 10])
        else:
            dez = resto // 10
            uni = resto % 10
            if uni:
                partes.append(f"{_DEZENAS[dez]} e {_UNIDADES[uni]}")
            else:
                partes.append(_DEZENAS[dez])
    return " e ".join(partes)


def _inteiro_extenso(n: int) -> str:
    """Converte inteiro >= 0 em texto pt-BR (até trilhões)."""
    if n == 0:
        return "zero"
    if n < 0:
        return "menos " + _inteiro_extenso(-n)

    grupos = []  # do menos significativo para o mais significativo
    while n > 0:
        grupos.append(n % 1000)
        n //= 1000

    if len(grupos) > len(_ESCALAS):
        # acima de trilhões não é suportado pelo fallback
        raise ValueError("valor fora do intervalo suportado")

    partes = []
    for i in range(len(grupos) - 1, -1, -1):
        g = grupos[i]
        if g == 0:
            continue
        singular, plural = _ESCALAS[i]
        if i == 1:  # milhar
            texto = "mil" if g == 1 else f"{_centena_extenso(g)} mil"
            partes.append(texto)
        elif i >= 2:  # milhão+
            escala = singular if g == 1 else plural
            partes.append(f"{_centena_extenso(g)} {escala}")
        else:  # centena final
            partes.append(_centena_extenso(g))

    # Junção pt-BR: "e" antes do último grupo quando ele é < 100 ou múltiplo de 100
    if len(partes) == 1:
        return partes[0]
    ultimo = grupos[0]
    if 0 < ultimo < 100 or (ultimo % 100 == 0 and ultimo != 0):
        return " e ".join([", ".join(partes[:-1]), partes[-1]]) if len(partes) > 2 \
            else f"{partes[0]} e {partes[1]}"
    return ", ".join(partes[:-1]) + ", " + partes[-1] if len(partes) > 2 \
        else f"{partes[0]} {partes[1]}"


def _fallback_extenso(valor: float) -> str:
    reais = int(valor)
    centavos = int(round((round(valor, 2) - reais) * 100))
    if centavos >= 100:  # arredondamento de borda
        reais += 1
        centavos -= 100
    moeda = "real" if reais == 1 else "reais"
    texto = f"{_inteiro_extenso(reais)} {moeda}"
    if centavos:
        cent_lbl = "centavo" if centavos == 1 else "centavos"
        texto += f" e {_inteiro_extenso(centavos)} {cent_lbl}"
    return texto


def valor_por_extenso(valor: Optional[float]) -> str:
    """
    Retorna o valor monetário por extenso em pt-BR.
    Ex.: 7188476.13 -> "sete milhões, cento e oitenta e oito mil,
                        quatrocentos e setenta e seis reais e treze centavos"
    Nunca retorna string vazia para valores válidos (> 0).
    """
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""

    # Caminho preferencial: num2words (cobre até centenas de bilhões nativamente)
    try:
        from num2words import num2words
        reais = int(v)
        centavos = int(round((round(v, 2) - reais) * 100))
        if centavos >= 100:
            reais += 1
            centavos -= 100
        moeda = "real" if reais == 1 else "reais"
        texto = f"{num2words(reais, lang='pt_BR')} {moeda}"
        if centavos:
            cent_lbl = "centavo" if centavos == 1 else "centavos"
            texto += f" e {num2words(centavos, lang='pt_BR')} {cent_lbl}"
        return texto
    except Exception:
        pass

    # Fallback puro
    try:
        return _fallback_extenso(v)
    except Exception:
        return ""


# ── Métricas por extenso (área / distância) — usado no Memorial urbano ─────────
def area_extenso(area_m2: Optional[float]) -> str:
    """Área em m² por extenso. Ex.: 1106.00 -> 'mil cento e seis metros quadrados';
    fração não nula vira '… e N centésimos'. Retorna '' para valor inválido/<=0."""
    try:
        v = float(area_m2 or 0)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    inteiro = int(v)
    centesimos = int(round((round(v, 2) - inteiro) * 100))
    if centesimos >= 100:                       # arredondamento de borda
        inteiro += 1
        centesimos -= 100
    if inteiro == 1 and centesimos == 0:
        return "um metro quadrado"
    try:
        base = f"{_inteiro_extenso(inteiro)} metros quadrados" if inteiro else ""
        if centesimos:
            cent = f"{_inteiro_extenso(centesimos)} centésimos"
            return f"{base} e {cent}" if base else cent
        return base
    except Exception:
        return ""


def distancia_extenso(d_m: Optional[float]) -> str:
    """Distância em metros por extenso: parte inteira = metros, 2 casas = centímetros.
    Ex.: 22.89 -> 'vinte e dois metros e oitenta e nove centímetros'."""
    try:
        v = float(d_m or 0)
    except (TypeError, ValueError):
        return ""
    if v < 0:
        return ""
    total_cm = int(round(v * 100))
    metros_i, centimetros = divmod(total_cm, 100)
    partes = []
    try:
        if metros_i:
            partes.append(f"{_inteiro_extenso(metros_i)} " + ("metro" if metros_i == 1 else "metros"))
        if centimetros:
            partes.append(f"{_inteiro_extenso(centimetros)} " + ("centímetro" if centimetros == 1 else "centímetros"))
    except Exception:
        return ""
    if not partes:
        return "zero metro"
    return " e ".join(partes)
