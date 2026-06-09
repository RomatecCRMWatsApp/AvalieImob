# @module services.link_tracking — Auditoria do link público do laudo (Feature de controle).
# Registra eventos (gerado / enviado / visualizado) por PTAM e mantém contadores-resumo
# no próprio documento (ptam_documents) para o badge do card, além do log detalhado em
# `ptam_link_eventos` para o modal de histórico.
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger("romatec")

# tipos válidos: "gerado" | "enviado" | "visualizado" | "desativado"


async def registrar_evento(
    db,
    ptam: dict,
    tipo: str,
    *,
    canal: Optional[str] = None,        # whatsapp | telegram | email | link
    destinatario: Optional[str] = None,  # número/e-mail/nome
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Insere um evento de link e atualiza os contadores-resumo no PTAM.
    Nunca propaga exceção — tracking não pode quebrar o fluxo principal."""
    try:
        pid = ptam.get("id")
        uid = ptam.get("user_id")
        if not pid:
            return
        agora = datetime.utcnow()

        evento = {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "ptam_id": pid,
            "tipo": tipo,
            "canal": canal,
            "destinatario": destinatario,
            "ip": ip,
            "user_agent": (user_agent or "")[:300] or None,
            "created_at": agora,
        }
        await db.ptam_link_eventos.insert_one(evento)

        set_fields = {}
        inc_fields = {}
        if tipo == "visualizado":
            inc_fields["link_views"] = 1
            set_fields["link_views_last"] = agora
            # primeira visualização: só grava se ainda não existir
            await db.ptam_documents.update_one(
                {"id": pid, "link_views_first": {"$exists": False}},
                {"$set": {"link_views_first": agora}},
            )
        elif tipo == "enviado":
            inc_fields["link_sends"] = 1
            set_fields["link_last_sent"] = agora
            set_fields["link_last_canal"] = canal
            if destinatario:
                set_fields["link_last_destinatario"] = destinatario
        elif tipo == "gerado":
            set_fields["link_gerado_em"] = agora

        if set_fields or inc_fields:
            update = {}
            if set_fields:
                update["$set"] = set_fields
            if inc_fields:
                update["$inc"] = inc_fields
            await db.ptam_documents.update_one({"id": pid}, update)
    except Exception as e:  # noqa: BLE001
        logger.warning("Falha ao registrar evento de link (%s): %s", tipo, e)


def client_ip(request) -> Optional[str]:
    """Extrai o IP real respeitando proxies (X-Forwarded-For)."""
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


async def listar_eventos(db, pid: str, uid: str, limit: int = 200) -> dict:
    """Histórico de eventos + resumo, escopado ao dono do PTAM."""
    ptam = await db.ptam_documents.find_one(
        {"id": pid, "user_id": uid},
        {
            "_id": 0, "link_views": 1, "link_views_first": 1, "link_views_last": 1,
            "link_sends": 1, "link_last_sent": 1, "link_last_canal": 1,
            "link_last_destinatario": 1, "link_gerado_em": 1,
            "link_publico_ativo": 1, "link_publico_token": 1,
        },
    )
    if ptam is None:
        return {"encontrado": False}
    eventos = await db.ptam_link_eventos.find(
        {"ptam_id": pid, "user_id": uid}, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    return {
        "encontrado": True,
        "resumo": {
            "views": ptam.get("link_views", 0),
            "views_first": ptam.get("link_views_first"),
            "views_last": ptam.get("link_views_last"),
            "sends": ptam.get("link_sends", 0),
            "last_sent": ptam.get("link_last_sent"),
            "last_canal": ptam.get("link_last_canal"),
            "last_destinatario": ptam.get("link_last_destinatario"),
            "gerado_em": ptam.get("link_gerado_em"),
            "ativo": ptam.get("link_publico_ativo", False),
        },
        "eventos": eventos,
    }
