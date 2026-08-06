# @module services.assinatura.origem_pdf — Resolve o PDF do documento de origem p/ o envio.
# Reutiliza os geradores ReportLab/R2 já existentes de cada módulo (NÃO duplica lógica de PDF).
# Padrão: imports LAZY dentro de cada ramo (evita importação circular com as rotas) +
# asyncio.to_thread para os geradores síncronos.
from __future__ import annotations

import asyncio


class OrigemNaoSuportada(Exception):
    """Origem não encontrada ou ainda não conectada ao envio de assinatura."""


def _safe(nome) -> str:
    return str(nome or "sem-numero").replace("/", "-").replace("\\", "-").strip() or "documento"


async def resolver(db, user_id: str, origem_tipo: str, origem_id: str):
    """Retorna (pdf_bytes, nome_documento) do documento de origem, isolado por user_id."""

    # ── PTAM (laudo de avaliação) ───────────────────────────────────────────
    if origem_tipo == "ptam":
        doc = await db.ptam_documents.find_one({"id": origem_id, "user_id": user_id})
        if not doc:
            raise OrigemNaoSuportada("PTAM não encontrado")
        from services.ptam_pdf_v2 import generate_ptam_pdf_v2
        perfil = await db.perfil_avaliador.find_one({"user_id": user_id})
        pdf = await asyncio.to_thread(generate_ptam_pdf_v2, doc, perfil)
        return pdf, f"PTAM_{_safe(doc.get('number'))}.pdf"

    # ── Recibo de honorários ────────────────────────────────────────────────
    if origem_tipo == "recibo":
        doc = await db.recibos.find_one({"id": origem_id, "user_id": user_id})
        if not doc:
            raise OrigemNaoSuportada("Recibo não encontrado")
        from pdf.recibo_pdf import gerar_recibo_pdf
        from services.recibo_anexos import anexar_anexos_ao_pdf
        user = await db.users.find_one({"id": user_id}) or {}
        perfil = await db.perfis_avaliador.find_one({"user_id": user_id}) or {}
        logo_bytes = None
        try:
            from routes.recibos import _carregar_logo_bytes
            logo_bytes = await _carregar_logo_bytes(
                db, doc.get("emitente_logo_id") or user.get("company_logo"))
        except Exception:
            pass
        pdf = await asyncio.to_thread(
            gerar_recibo_pdf, recibo=doc, user=user, perfil=perfil, logo_bytes=logo_bytes)
        pdf = await anexar_anexos_ao_pdf(db, doc, pdf)  # embute anexos (PDF/imagens)
        return pdf, f"Recibo_{_safe(doc.get('numero'))}.pdf"

    # ── Contrato de exclusividade ───────────────────────────────────────────
    if origem_tipo == "contrato_exclusividade":
        doc = await db.contratos_exclusividade.find_one({"id": origem_id, "user_id": user_id})
        if not doc:
            raise OrigemNaoSuportada("Contrato de exclusividade não encontrado")
        # Documento LIMPO (rascunho, sem o selo do aceite interno) p/ o provedor coletar as firmas.
        from services.contrato_exclusividade_pdf import gerar_pdf_rascunho
        try:
            from routes.contratos_exclusividade import _carregar_fotos_bytes
            await _carregar_fotos_bytes(db, doc)  # popula os bytes das fotos in-place
        except Exception:
            pass
        pdf = await asyncio.to_thread(gerar_pdf_rascunho, doc)
        return pdf, f"Contrato_Exclusividade_{_safe(doc.get('numero') or origem_id)}.pdf"

    # ── Documento externo (PDF avulso enviado pelo usuário, já no R2) ────────
    if origem_tipo == "documento_externo":
        from services.documento_externo_service import COL
        doc = await db[COL].find_one({"id": origem_id, "user_id": user_id})
        if not doc:
            raise OrigemNaoSuportada("Documento externo não encontrado")
        key = doc.get("pdf_key")
        if not key:
            raise OrigemNaoSuportada("Documento externo sem PDF armazenado")
        from services import r2_storage
        pdf = await asyncio.to_thread(r2_storage.download_bytes, key)
        return pdf, f"{_safe(doc.get('nome') or 'documento')}.pdf"

    # ── Laudo de agrimensura (Topografia & Geo) ─────────────────────────────
    if origem_tipo == "laudo_agrimensura":
        doc = await db.georef_projetos.find_one({"id": origem_id, "user_id": user_id})
        if not doc:
            raise OrigemNaoSuportada("Projeto de agrimensura não encontrado")
        from services.georef.generators import pdf as PDF
        try:
            from routes.georef import _injetar_logo, _plantas_laudo
            await _injetar_logo(db, user_id, doc)                # white-label
            doc["_plantas_laudo"] = await asyncio.to_thread(_plantas_laudo, doc)
        except Exception:
            pass
        tema = doc.get("tema_pdf") or "prime_i"
        pdf = await asyncio.to_thread(PDF.gerar_pdf, "laudo_tecnico", doc, tema)
        return pdf, f"Laudo_Agrimensura_{_safe(doc.get('numero') or origem_id)}.pdf"

    # "outro" e não mapeados: não há documento de origem no sistema.
    raise OrigemNaoSuportada(
        f"origem '{origem_tipo}' não possui documento de origem gerável no sistema")
