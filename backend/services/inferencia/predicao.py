# @module services.inferencia.predicao — valor no ponto, IC da média e IP de nova observação.
#
# Regras que NÃO podem ser afrouxadas (MD §5.4):
#   - é o IP (não o IC) que define o Grau de Precisão;
#   - calcular no espaço transformado e destransformar os LIMITES pela inversa —
#     jamais aplicar a inversa sobre a amplitude;
#   - dependente em ln ⇒ a estimativa destransformada é a MEDIANA condicional.
from services.inferencia.transformacoes import inversa

NOTA_LOG = ("Estimativa destransformada corresponde à mediana da distribuição "
            "condicional, não à média aritmética.")


def predizer(modelo, Xp, esp, params: dict) -> dict:
    nivel = float(params.get("nivel_ip", 0.80))
    ca = float(params.get("campo_arbitrio", 0.15))
    alpha = 1 - nivel

    pred = modelo.get_prediction(Xp)
    sf = pred.summary_frame(alpha=alpha)
    centro_t = float(sf["mean"].iloc[0])
    ic_inf_t, ic_sup_t = float(sf["mean_ci_lower"].iloc[0]), float(sf["mean_ci_upper"].iloc[0])
    ip_inf_t, ip_sup_t = float(sf["obs_ci_lower"].iloc[0]), float(sf["obs_ci_upper"].iloc[0])

    inv = inversa(esp.transf_dependente)
    centro = float(inv(centro_t))
    ic_inf, ic_sup = float(inv(ic_inf_t)), float(inv(ic_sup_t))
    ip_inf, ip_sup = float(inv(ip_inf_t)), float(inv(ip_sup_t))

    # Transformações decrescentes (1/x) invertem a ordem dos limites.
    if ic_inf > ic_sup:
        ic_inf, ic_sup = ic_sup, ic_inf
    if ip_inf > ip_sup:
        ip_inf, ip_sup = ip_sup, ip_inf

    amplitude_ip = (ip_sup - ip_inf) / centro if centro else float("inf")

    return {
        "nivel": nivel,
        "valor_central": centro,
        "ic80": {"inferior": ic_inf, "superior": ic_sup},
        "ip80": {"inferior": ip_inf, "superior": ip_sup},
        "amplitude_ip80": float(amplitude_ip),
        "campo_arbitrio": {"inferior": centro * (1 - ca), "superior": centro * (1 + ca),
                           "percentual": ca},
        "espaco_transformado": {
            "centro": centro_t,
            "ic": {"inferior": ic_inf_t, "superior": ic_sup_t},
            "ip": {"inferior": ip_inf_t, "superior": ip_sup_t},
        },
        "dependente_transformada": esp.transf_dependente != "identidade",
        "observacao_destransformacao": NOTA_LOG if esp.transf_dependente == "ln" else None,
    }


def totalizar(predicao: dict, quantidade: float) -> dict:
    """Valor unitário → valor total (área do avaliando). Multiplica os LIMITES."""
    q = float(quantidade or 0)
    if q <= 0:
        return {}
    def m(v):
        return float(v) * q
    return {
        "quantidade": q,
        "valor_central": m(predicao["valor_central"]),
        "ip80": {"inferior": m(predicao["ip80"]["inferior"]),
                 "superior": m(predicao["ip80"]["superior"])},
        "ic80": {"inferior": m(predicao["ic80"]["inferior"]),
                 "superior": m(predicao["ic80"]["superior"])},
        "campo_arbitrio": {"inferior": m(predicao["campo_arbitrio"]["inferior"]),
                           "superior": m(predicao["campo_arbitrio"]["superior"])},
    }
