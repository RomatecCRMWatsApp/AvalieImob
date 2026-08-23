# @module services.inferencia.graficos — PNGs de diagnóstico do modelo (300 dpi).
#
# Quatro gráficos exigidos pelo MD §6, na paleta institucional:
#   1. resíduos padronizados × valores estimados (bandas ±2σ)
#   2. observado × estimado (reta de 45°)
#   3. histograma dos resíduos com a normal sobreposta
#   4. Q-Q plot dos resíduos
#
# ADAPTAÇÃO à infra do projeto: o MD pede GridFS; o AvalieImob não usa GridFS —
# arquivos binários vão para o R2 (services.r2_storage), com fallback em base64
# dentro do próprio documento quando o R2 não estiver configurado.
import base64
import io
import logging
import uuid

import matplotlib
matplotlib.use("Agg")            # backend headless — obrigatório no servidor
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
from scipy import stats          # noqa: E402

logger = logging.getLogger("romatec")

VERDE = "#0C3320"
DOURADO = "#C9A84C"
CINZA = "#8A8A8A"
DPI = 300

TITULOS = {
    "residuos": "Resíduos padronizados × valores estimados",
    "observado_estimado": "Valores observados × valores estimados",
    "histograma": "Distribuição dos resíduos",
    "qq": "Q-Q plot dos resíduos",
}


def _fig(titulo: str):
    fig, ax = plt.subplots(figsize=(6.2, 4.2), dpi=DPI)
    ax.set_title(titulo, color=VERDE, fontsize=11, fontweight="bold", pad=12)
    ax.grid(True, linewidth=0.4, color="#E3E3E3")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(CINZA)
    ax.tick_params(colors=CINZA, labelsize=8)
    return fig, ax


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def gerar(resultado: dict) -> dict:
    """Devolve {chave: bytes_png}. Puro — não persiste nada."""
    fitted = np.asarray(resultado["_fitted"], dtype=float)
    resid_pad = np.asarray(resultado["_resid_pad"], dtype=float)
    y = np.asarray(resultado["_y"], dtype=float)
    resid = np.asarray(resultado["_modelo"].resid, dtype=float)

    saida = {}

    # 1. Resíduos padronizados × estimados
    fig, ax = _fig(TITULOS["residuos"])
    ax.scatter(fitted, resid_pad, s=26, color=VERDE, alpha=0.75, edgecolors="white",
               linewidths=0.5)
    ax.axhline(0, color=CINZA, linewidth=0.8)
    for s in (2, -2):
        ax.axhline(s, color=DOURADO, linewidth=1.0, linestyle="--")
    ax.set_xlabel("Valor estimado (espaço transformado)", fontsize=8, color=CINZA)
    ax.set_ylabel("Resíduo padronizado (σ)", fontsize=8, color=CINZA)
    saida["residuos"] = _png(fig)

    # 2. Observado × estimado
    fig, ax = _fig(TITULOS["observado_estimado"])
    ax.scatter(fitted, y, s=26, color=VERDE, alpha=0.75, edgecolors="white", linewidths=0.5)
    lo, hi = float(min(y.min(), fitted.min())), float(max(y.max(), fitted.max()))
    ax.plot([lo, hi], [lo, hi], color=DOURADO, linewidth=1.2)
    ax.set_xlabel("Estimado", fontsize=8, color=CINZA)
    ax.set_ylabel("Observado", fontsize=8, color=CINZA)
    saida["observado_estimado"] = _png(fig)

    # 3. Histograma dos resíduos + normal
    fig, ax = _fig(TITULOS["histograma"])
    n_bins = max(6, min(14, int(np.sqrt(len(resid)) * 1.6)))
    ax.hist(resid, bins=n_bins, density=True, color=VERDE, alpha=0.72,
            edgecolor="white", linewidth=0.6)
    mu, sd = float(np.mean(resid)), float(np.std(resid, ddof=1))
    if sd > 0:
        xs = np.linspace(resid.min() - sd, resid.max() + sd, 200)
        ax.plot(xs, stats.norm.pdf(xs, mu, sd), color=DOURADO, linewidth=1.6)
    ax.set_xlabel("Resíduo", fontsize=8, color=CINZA)
    ax.set_ylabel("Densidade", fontsize=8, color=CINZA)
    saida["histograma"] = _png(fig)

    # 4. Q-Q plot
    fig, ax = _fig(TITULOS["qq"])
    (osm, osr), (slope, intercept, _) = stats.probplot(resid, dist="norm")
    ax.scatter(osm, osr, s=26, color=VERDE, alpha=0.75, edgecolors="white", linewidths=0.5)
    ax.plot(osm, slope * osm + intercept, color=DOURADO, linewidth=1.2)
    ax.set_xlabel("Quantis teóricos", fontsize=8, color=CINZA)
    ax.set_ylabel("Quantis dos resíduos", fontsize=8, color=CINZA)
    saida["qq"] = _png(fig)

    return saida


def persistir(pngs: dict, user_id: str, modelo_id: str) -> dict:
    """Sobe no R2 e devolve {chave: {url|b64}}. Sem R2, guarda base64 no doc."""
    saida = {}
    for chave, png in (pngs or {}).items():
        registro = {"titulo": TITULOS.get(chave, chave), "bytes": len(png)}
        try:
            from services import r2_storage
            key = f"inferencia/{user_id}/{modelo_id}/{chave}_{uuid.uuid4().hex[:8]}.png"
            registro["url"] = r2_storage.upload_bytes(png, key, "image/png")
            registro["key"] = key
        except Exception as e:  # noqa: BLE001 — sem R2 configurado, cai no inline
            logger.warning("Inferência: gráfico %s não foi ao R2 (%s); usando base64.",
                           chave, e)
            registro["b64"] = base64.b64encode(png).decode()
        saida[chave] = registro
    return saida


def carregar_bytes(registro: dict) -> bytes:
    """Recupera o PNG (R2 ou base64) — usado pelo gerador de PDF."""
    if not registro:
        return b""
    if registro.get("b64"):
        return base64.b64decode(registro["b64"])
    ref = registro.get("key") or registro.get("url")
    if not ref:
        return b""
    try:
        from services import r2_storage
        return r2_storage.download_bytes(ref)
    except Exception as e:  # noqa: BLE001
        logger.warning("Inferência: falha ao baixar gráfico (%s)", e)
        return b""
