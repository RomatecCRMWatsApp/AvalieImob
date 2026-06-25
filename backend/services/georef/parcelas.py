# @module services.georef.parcelas — Visão unificada das parcelas de um projeto.
#
# A "Parte I" é o topo do projeto (imovel/vertices/confrontantes); `projeto.parcelas`
# guarda as parcelas ADICIONAIS (Parte II+) do desmembramento/remembramento. Estes
# helpers dão uma lista única (principal + extras) p/ os geradores iterarem, e montam
# um "sub-projeto" por parcela p/ reusar os geradores existentes (Memorial etc.).
_ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def _romano(n: int) -> str:
    return _ROMANOS[n - 1] if 1 <= n <= len(_ROMANOS) else str(n)


def _view(projeto, parcela, principal, indice) -> dict:
    im = projeto.get("imovel") or {}
    fonte = im if principal else parcela
    return {
        "id": None if principal else parcela.get("id"),
        "rotulo": (parcela.get("rotulo") if not principal else None)
        or f"Parte {_romano(indice)}",
        "denominacao": fonte.get("denominacao"),
        "natureza_area": fonte.get("natureza_area"),
        "area_ha": fonte.get("area_ha"),
        "perimetro_m": fonte.get("perimetro_m"),
        "sistema_geodesico": fonte.get("sistema_geodesico") or "SIRGAS 2000",
        "certificacao_sigef": fonte.get("certificacao_sigef"),
        "vertices": (projeto.get("vertices") if principal else parcela.get("vertices")) or [],
        "confrontantes": (projeto.get("confrontantes") if principal
                          else parcela.get("confrontantes")) or [],
        "uploads": ({} if principal else (parcela.get("uploads") or {})),
        "principal": principal,
        "indice": indice,
    }


def parcelas_do_projeto(projeto) -> list:
    """Lista [principal, extra1, extra2, ...] normalizada para os geradores."""
    extras = projeto.get("parcelas") or []
    out = [_view(projeto, None, True, 1)]
    for i, p in enumerate(extras):
        out.append(_view(projeto, p, False, i + 2))
    return out


def tem_multiparcela(projeto) -> bool:
    return bool(projeto.get("parcelas"))


def projeto_da_parcela(projeto, parcela_view) -> dict:
    """Monta um 'sub-projeto' com os dados da parcela, p/ reusar os geradores.

    Sobrepõe denominação/área/perímetro/certificação/vértices/confrontantes do
    imóvel pelos da parcela, preservando os dados compartilhados (proprietário,
    matrícula de origem, cartório, RT, CCIR...).
    """
    imovel = dict(projeto.get("imovel") or {})
    for k in ("denominacao", "natureza_area", "area_ha", "perimetro_m",
              "sistema_geodesico", "certificacao_sigef"):
        if parcela_view.get(k) is not None:
            imovel[k] = parcela_view.get(k)
    return {
        **projeto,
        "imovel": imovel,
        "vertices": parcela_view.get("vertices") or [],
        "confrontantes": parcela_view.get("confrontantes") or [],
    }
