# @module services.assinatura.origem_pdf — Resolve o PDF do documento de origem p/ o envio.
# Reutiliza os geradores ReportLab existentes (NÃO duplica lógica de PDF).
from __future__ import annotations

import asyncio


class OrigemNaoSuportada(Exception):
    """Origem não encontrada ou ainda não conectada ao envio de assinatura."""


async def resolver(db, user_id: str, origem_tipo: str, origem_id: str):
    """Retorna (pdf_bytes, nome_documento) do documento de origem."""
    if origem_tipo == "ptam":
        doc = await db.ptam_documents.find_one({"id": origem_id, "user_id": user_id})
        if not doc:
            raise OrigemNaoSuportada("PTAM não encontrado")
        from services.ptam_pdf_v2 import generate_ptam_pdf_v2
        perfil = await db.perfil_avaliador.find_one({"user_id": user_id})
        pdf = await asyncio.to_thread(generate_ptam_pdf_v2, doc, perfil)
        num = str(doc.get("number") or "sem-numero").replace("/", "-")
        return pdf, f"PTAM_{num}.pdf"

    # Demais origens (contratos/recibos/doc-ext/laudos) usam os geradores já existentes —
    # conectar cada uma é um passo pequeno; por ora a rota devolve 422 com esta mensagem.
    raise OrigemNaoSuportada(
        f"origem '{origem_tipo}' ainda não conectada ao envio de assinatura "
        "(PTAM já conecta; contratos/recibos/doc-ext/laudos em seguida)"
    )
