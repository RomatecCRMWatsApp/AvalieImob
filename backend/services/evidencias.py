# @module services.evidencias — linha do tempo de evidências (somente leitura).
#
# Reúne, numa sequência por data, o que já existe espalhado em várias coleções:
#   PTAM: criação, versões (automáticas e lacradas, com SHA-256), assinatura ICP,
#         vistoria importada e eventos do link público (gerado/enviado/visualizado).
#   TVI:  registro (inclusive se veio da fila do aparelho), fotos (data/hora + GPS),
#         assinaturas (com SHA-256 da imagem) e compartilhamentos.
# Não grava nada, não cria coleção nova e não expõe IP/navegador de quem abriu o link.
# Funções PURAS: recebem os documentos já carregados (a rota faz as consultas
# escopadas por user_id) e devolvem a lista de eventos.
import hashlib
from datetime import datetime
from typing import Iterable, Optional


def _iso(v) -> Optional[str]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _evento(tipo: str, quando, titulo: str, detalhe: str = "", **extra) -> dict:
    ev = {"tipo": tipo, "quando": _iso(quando), "titulo": titulo, "detalhe": detalhe}
    ev.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    return ev


def _ordenar(eventos: list) -> list:
    return sorted(eventos, key=lambda e: e.get("quando") or "")


def _sha256(texto: str) -> str:
    return hashlib.sha256((texto or "").encode()).hexdigest()


_LINK = {
    "gerado": "Link público gerado",
    "reativado": "Link público reativado",
    "desativado": "Link público desativado",
    "enviado": "Link enviado ao cliente",
    "visualizado": "Cliente abriu o link",
}


def eventos_ptam(ptam: dict, versoes: Iterable[dict] = (), link_eventos: Iterable[dict] = (),
                 vistoria_origem: Optional[dict] = None) -> list:
    ev = [_evento("criado", ptam.get("created_at"), "Laudo criado",
                  f"PTAM nº {ptam.get('numero_ptam') or '—'}")]

    for v in versoes:
        if v.get("tipo") == "lacrado":
            ev.append(_evento(
                "lacre", v.get("created_at"), f"Versão {v.get('numero_versao')} lacrada",
                v.get("observacao") or "", referencia=v.get("numero_lacre"),
                hash_sha256=v.get("hash_sha256"), versao_id=v.get("id")))
        else:
            n = len(v.get("diffs") or [])
            ev.append(_evento(
                "versao", v.get("created_at"), f"Versão {v.get('numero_versao')} salva",
                f"{n} campo(s) alterado(s)" if n else "", hash_sha256=v.get("hash_sha256"),
                versao_id=v.get("id")))

    if vistoria_origem:
        ev.append(_evento(
            "vistoria", ptam.get("vistoria_importada_em") or vistoria_origem.get("updated_at"),
            "Vistoria importada", vistoria_origem.get("numero_tvi") or "",
            referencia=vistoria_origem.get("id")))

    if ptam.get("icp_status") == "assinado" or ptam.get("icp_signed_at"):
        ev.append(_evento(
            "assinatura", ptam.get("icp_signed_at"), "Assinado com certificado ICP-Brasil",
            ptam.get("icp_titular") or "", hash_sha256=ptam.get("icp_hash")))
    if ptam.get("assinatura_invalidada_em"):
        ev.append(_evento(
            "assinatura_invalidada", ptam.get("assinatura_invalidada_em"),
            "Assinatura invalidada por edição", "O conteúdo mudou depois da assinatura."))

    for e in link_eventos:
        tipo = e.get("tipo") or "link"
        detalhe = " · ".join(x for x in (e.get("canal"), e.get("destinatario")) if x)
        ev.append(_evento(f"link_{tipo}", e.get("created_at"),
                          _LINK.get(tipo, f"Link: {tipo}"), detalhe))
    return _ordenar(ev)


def eventos_tvi(vist: dict, fotos: Iterable[dict] = (), assinaturas: Iterable[dict] = (),
                compartilhamentos: Iterable[dict] = ()) -> list:
    origem = "registrada no aparelho e enviada pela fila" if vist.get("client_id") else ""
    ev = [_evento("criado", vist.get("created_at"), "Vistoria registrada",
                  " · ".join(x for x in (vist.get("numero_tvi"), origem) if x))]

    for f in fotos:
        gps = f.get("gps") or {}
        local = (f"GPS {gps['lat']:.6f}, {gps['lng']:.6f}"
                 if isinstance(gps, dict) and gps.get("lat") is not None
                 and gps.get("lng") is not None else "sem GPS")
        ev.append(_evento(
            "foto", f.get("timestamp") or f.get("created_at"),
            f"Foto — {f.get('ambiente') or 'Geral'}",
            " · ".join(x for x in (f.get("legenda"), local) if x),
            url=f.get("url"), foto_id=f.get("id")))

    for a in assinaturas:
        ev.append(_evento(
            "assinatura", a.get("created_at"), f"Assinatura de {a.get('signatario') or '—'}",
            a.get("cargo") or "", hash_sha256=_sha256(a.get("data_b64") or "")))

    for s in compartilhamentos:
        ev.append(_evento("compartilhado", s.get("enviado_em") or s.get("created_at"),
                          "Vistoria compartilhada",
                          " · ".join(x for x in (s.get("canal"), s.get("destinatario")) if x)))
    return _ordenar(ev)
