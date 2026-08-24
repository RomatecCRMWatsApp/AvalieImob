# @module routes.inferencia — Tratamento científico (MCDDM): modelos de regressão.
#
# ADAPTAÇÕES às convenções do AvalieImob (o MD assume outra base):
#   - isolamento por `user_id` do TOKEN (o repo não tem tenant_id); gravamos
#     `tenant_id` como espelho. Toda query filtra {id, user_id} — sempre.
#   - id = uuid str (não ObjectId), datas via _now, `serialize_doc` na saída.
#   - gráficos no R2 (o repo não usa GridFS).
#
# Estimação SÍNCRONA (MD §7): OLS de algumas centenas de linhas resolve em
# milissegundos — não criar fila. O trabalho pesado roda em asyncio.to_thread
# para não bloquear o event loop (padrão do projeto).
import asyncio
import logging
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.modelo_inferencia import (AmostraBody, CriarModeloBody, EspecificacaoBody,
                                      HomologarBody, ImportarAmostrasBody,
                                      ModeloInferencia, PredizerBody)
from services.inferencia import ErroInferencia, Especificacao, estimar, serializavel
from services.inferencia import graficos as GRAF
from services.inferencia.enquadramento import carregar_params
from services.inferencia.transformacoes import ROTULO_HUMANO

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/inferencia", tags=["Inferência Estatística"])

COL = "modelos_inferencia"
_NORMA_POR_TIPO = {"urbano": "14653-2", "rural": "14653-3"}


# ── Helpers ──────────────────────────────────────────────────────────────────
async def _obter(db, mid: str, uid: str) -> dict:
    """Sempre filtrando por dono — isolamento é regra dura deste módulo."""
    doc = await db[COL].find_one({"id": mid, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Modelo não encontrado")
    return doc


def _amostra_df(doc: dict) -> pd.DataFrame:
    linhas = []
    for item in (doc.get("amostra") or []):
        linha = dict(item.get("variaveis") or {})
        linha["dado_id"] = item.get("dado_id") or ""
        linha["utilizado"] = bool(item.get("utilizado", True))
        linhas.append(linha)
    if not linhas:
        raise HTTPException(422, "Modelo sem amostra. Importe ou informe os dados de mercado.")
    return pd.DataFrame(linhas)


def _bloquear_se_homologado(doc: dict) -> None:
    """Modelo homologado é IMUTÁVEL — o PTAM assinado referencia estes números."""
    if doc.get("status") == "homologado":
        raise HTTPException(
            409, "Modelo homologado é imutável. Crie uma nova versão para alterar "
                 "(POST /inferencia/modelos/{id}/nova-versao).")


async def _salvar(db, mid: str, uid: str, campos: dict) -> dict:
    """Escrita atômica — find_one_and_update, nunca ler-modificar-gravar."""
    campos["atualizado_em"] = datetime.utcnow()
    doc = await db[COL].find_one_and_update(
        {"id": mid, "user_id": uid}, {"$set": campos}, return_document=True)
    if not doc:
        raise HTTPException(404, "Modelo não encontrado")
    return doc


def _rodar(doc: dict) -> dict:
    """Executa o motor sobre o doc persistido. Levanta ErroInferencia."""
    esp = Especificacao.from_dict(doc.get("especificacao") or {})
    if not esp.regressores:
        raise ErroInferencia("Modelo sem regressores. Defina ao menos uma variável.")
    return estimar(
        _amostra_df(doc), esp, doc.get("avaliando") or {},
        norma=doc.get("norma") or _NORMA_POR_TIPO.get(doc.get("tipo_imovel"), "14653-2"),
        quantidade_total=doc.get("area_total_avaliando"),
    )


# ── Catálogo (para a tela montar os seletores) ───────────────────────────────
@router.get("/opcoes")
async def opcoes(uid: str = Depends(get_active_subscriber)):
    return {
        "transformacoes": [{"valor": k, "rotulo": v} for k, v in ROTULO_HUMANO.items()],
        "tipos_variavel": [
            {"valor": "quantitativa", "rotulo": "Quantitativa"},
            {"valor": "dicotomica", "rotulo": "Dicotômica (0/1)"},
            {"valor": "codigo_alocado", "rotulo": "Código alocado"},
        ],
        "normas": [
            {"valor": "14653-2", "rotulo": "NBR 14653-2 — urbano",
             "params": carregar_params("14653-2")},
            {"valor": "14653-3", "rotulo": "NBR 14653-3 — rural",
             "params": carregar_params("14653-3")},
        ],
    }


# ── CRUD ─────────────────────────────────────────────────────────────────────
@router.post("/modelos", status_code=201)
async def criar_modelo(body: CriarModeloBody, uid: str = Depends(get_active_subscriber),
                       db=Depends(get_db)):
    n = await db[COL].count_documents({"user_id": uid})
    modelo = ModeloInferencia(
        user_id=uid, tenant_id=uid,
        nome=body.nome or f"Modelo {n + 1:02d}",
        avaliacao_id=body.avaliacao_id, ptam_id=body.ptam_id,
        tipo_imovel=body.tipo_imovel,
        norma=body.norma or _NORMA_POR_TIPO.get(body.tipo_imovel, "14653-2"),
        amostra=body.amostra or [],
        especificacao=body.especificacao or None,
        avaliando=body.avaliando or {},
        area_total_avaliando=body.area_total_avaliando,
    )
    doc = modelo.model_dump(mode="json")
    await db[COL].insert_one(dict(doc))
    return serialize_doc(doc)


@router.get("/modelos")
async def listar_modelos(avaliacao_id: str = None, uid: str = Depends(get_active_subscriber),
                         db=Depends(get_db)):
    filtro = {"user_id": uid}
    if avaliacao_id:
        filtro["avaliacao_id"] = avaliacao_id
    docs = await db[COL].find(filtro, {"resultado": 0}).sort("criado_em", -1).to_list(300)
    return [serialize_doc(d) for d in docs]


@router.get("/modelos/{mid}")
async def obter_modelo(mid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _obter(db, mid, uid))


@router.delete("/modelos/{mid}")
async def excluir_modelo(mid: str, uid: str = Depends(get_active_subscriber),
                         db=Depends(get_db)):
    doc = await _obter(db, mid, uid)
    _bloquear_se_homologado(doc)
    await db[COL].delete_one({"id": mid, "user_id": uid})
    return {"ok": True}


@router.patch("/modelos/{mid}/especificacao")
async def atualizar_especificacao(mid: str, body: EspecificacaoBody,
                                  uid: str = Depends(get_active_subscriber),
                                  db=Depends(get_db)):
    doc = await _obter(db, mid, uid)
    _bloquear_se_homologado(doc)
    campos = {"especificacao": body.especificacao.model_dump(mode="json"),
              "status": "rascunho", "resultado": None, "enquadramento": None}
    if body.avaliando is not None:
        campos["avaliando"] = body.avaliando
    if body.area_total_avaliando is not None:
        campos["area_total_avaliando"] = body.area_total_avaliando
    if body.nome:
        campos["nome"] = body.nome
    return serialize_doc(await _salvar(db, mid, uid, campos))


@router.patch("/modelos/{mid}/amostra")
async def atualizar_amostra(mid: str, body: AmostraBody,
                            uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Marca utilizado/descartado (motivo OBRIGATÓRIO ao descartar) ou troca a amostra."""
    doc = await _obter(db, mid, uid)
    _bloquear_se_homologado(doc)

    if body.substituir is not None:
        amostra = [d.model_dump(mode="json") for d in body.substituir]
    else:
        amostra = [dict(a) for a in (doc.get("amostra") or [])]
        por_id = {a.get("dado_id"): a for a in amostra}
        for item in body.itens:
            alvo = por_id.get(item.dado_id)
            if not alvo:
                raise HTTPException(404, f"Dado não encontrado na amostra: {item.dado_id}")
            if not item.utilizado and not (item.motivo_descarte or "").strip():
                raise HTTPException(
                    422, f"Informe o motivo do descarte do dado {item.dado_id} — "
                         "o saneamento da amostra vai para o laudo.")
            alvo["utilizado"] = bool(item.utilizado)
            alvo["motivo_descarte"] = (item.motivo_descarte or "").strip() or None

    return serialize_doc(await _salvar(db, mid, uid, {
        "amostra": amostra, "status": "rascunho", "resultado": None, "enquadramento": None}))


# ── Estimação / predição ─────────────────────────────────────────────────────
@router.post("/modelos/{mid}/estimar")
async def estimar_modelo(mid: str, uid: str = Depends(get_active_subscriber),
                         db=Depends(get_db)):
    """OLS + diagnóstico + enquadramento + gráficos. Síncrono (milissegundos)."""
    doc = await _obter(db, mid, uid)
    _bloquear_se_homologado(doc)
    try:
        resultado = await asyncio.to_thread(_rodar, doc)
    except ErroInferencia as e:
        raise HTTPException(422, str(e))
    except (KeyError, ValueError, TypeError) as e:
        logger.exception("Inferência: falha ao estimar modelo %s", mid)
        raise HTTPException(422, f"Não foi possível estimar: {e}")

    try:
        pngs = await asyncio.to_thread(GRAF.gerar, resultado)
        graficos = await asyncio.to_thread(GRAF.persistir, pngs, uid, mid)
    except Exception as e:  # noqa: BLE001 — gráfico é acessório, não derruba a estimação
        logger.warning("Inferência: gráficos não gerados (%s)", e)
        graficos = {}

    limpo = serializavel(resultado)
    salvo = await _salvar(db, mid, uid, {
        "resultado": limpo, "enquadramento": limpo.get("enquadramento"),
        "graficos": graficos, "status": "estimado", "estimado_em": datetime.utcnow()})
    return serialize_doc(salvo)


@router.post("/modelos/{mid}/predizer")
async def predizer(mid: str, body: PredizerBody, uid: str = Depends(get_active_subscriber),
                   db=Depends(get_db)):
    """Valor no ponto para OUTRO avaliando, sem reescrever o modelo homologado."""
    doc = await _obter(db, mid, uid)
    alvo = dict(doc)
    if body.avaliando:
        alvo["avaliando"] = body.avaliando
    if body.area_total_avaliando is not None:
        alvo["area_total_avaliando"] = body.area_total_avaliando
    try:
        resultado = await asyncio.to_thread(_rodar, alvo)
    except ErroInferencia as e:
        raise HTTPException(422, str(e))
    limpo = serializavel(resultado)
    # Só persiste quando o modelo ainda é editável.
    if doc.get("status") != "homologado" and body.avaliando:
        await _salvar(db, mid, uid, {
            "avaliando": alvo["avaliando"],
            "area_total_avaliando": alvo.get("area_total_avaliando"),
            "resultado": limpo, "enquadramento": limpo.get("enquadramento")})
    return {"predicao": limpo["predicao"], "enquadramento": limpo["enquadramento"],
            "extrapolacoes": limpo["extrapolacoes"]}


@router.post("/modelos/{mid}/homologar")
async def homologar(mid: str, body: HomologarBody, uid: str = Depends(get_active_subscriber),
                    db=Depends(get_db)):
    """Congela o modelo e vincula ao PTAM. A partir daqui, é imutável."""
    doc = await _obter(db, mid, uid)
    if doc.get("status") == "homologado":
        raise HTTPException(409, "Modelo já homologado.")
    if not doc.get("resultado"):
        raise HTTPException(422, "Estime o modelo antes de homologar.")

    params = carregar_params(doc.get("norma") or "14653-2")
    pendentes = [item for item in params.get("checklist_manual", [])
                 if not body.checklist_manual.get(item)]
    if pendentes and not body.forcar:
        raise HTTPException(422, "Confirme o checklist manual antes de homologar: "
                                 + "; ".join(pendentes))

    campos = {
        "status": "homologado",
        "homologado_em": datetime.utcnow(),
        "checklist_manual": body.checklist_manual,
        "observacao_homologacao": (body.observacao or "").strip() or None,
    }
    if body.ptam_id:
        campos["ptam_id"] = body.ptam_id
    return serialize_doc(await _salvar(db, mid, uid, campos))


@router.post("/modelos/{mid}/nova-versao", status_code=201)
async def nova_versao(mid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Homologado não se edita: gera uma NOVA versão preservando a anterior."""
    doc = await _obter(db, mid, uid)
    novo = dict(doc)
    novo.pop("_id", None)
    modelo = ModeloInferencia(**{
        **{k: v for k, v in novo.items() if k in ModeloInferencia.model_fields},
        "id": ModeloInferencia().id,
        "status": "rascunho",
        "versao": int(doc.get("versao") or 1) + 1,
        "origem_versao_id": doc.get("id"),
        "nome": f"{doc.get('nome')} (v{int(doc.get('versao') or 1) + 1})",
        "homologado_em": None,
        "criado_em": datetime.utcnow(),
        "atualizado_em": datetime.utcnow(),
    })
    d = modelo.model_dump(mode="json")
    await db[COL].insert_one(dict(d))
    return serialize_doc(d)


# ── Relatório e importação ───────────────────────────────────────────────────
@router.get("/modelos/{mid}/relatorio")
async def relatorio(mid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Payload das 9 seções do PDF (MD §11) — mesma fonte que o gerador usa."""
    doc = await _obter(db, mid, uid)
    if not doc.get("resultado"):
        raise HTTPException(422, "Estime o modelo antes de gerar o relatório.")
    from services.inferencia.relatorio import montar_payload
    return montar_payload(doc)


@router.get("/modelos/{mid}/pdf")
async def pdf(mid: str, tema: str = "prime2", uid: str = Depends(get_active_subscriber),
              db=Depends(get_db)):
    """Laudo do tratamento científico, nas 9 seções da norma."""
    doc = await _obter(db, mid, uid)
    if not doc.get("resultado"):
        raise HTTPException(422, "Estime o modelo antes de gerar o PDF.")
    from services.inferencia.relatorio import gerar_pdf
    try:
        blob = await asyncio.to_thread(gerar_pdf, doc, tema)
    except Exception as e:  # noqa: BLE001
        logger.exception("Inferência: falha ao gerar PDF do modelo %s", mid)
        raise HTTPException(500, f"Falha ao gerar o PDF: {type(e).__name__}: {e}")
    nome = f"Inferencia_{(doc.get('nome') or 'modelo').replace(' ', '_')}.pdf"
    return Response(content=blob, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"',
                             "Cache-Control": "no-store"})


# ── Vínculo com o PTAM: o laudo passa a tirar o valor da regressão ──────────
@router.post("/modelos/{mid}/vincular-ptam/{ptam_id}")
async def vincular_ptam(mid: str, ptam_id: str, uid: str = Depends(get_active_subscriber),
                        db=Depends(get_db)):
    """Liga um modelo HOMOLOGADO ao laudo. O snapshot é congelado no vínculo."""
    from services.inferencia.vinculo_ptam import VinculoError, preparar

    modelo = await _obter(db, mid, uid)
    ptam = await db.ptam_documents.find_one({"id": ptam_id, "user_id": uid})
    if not ptam:
        raise HTTPException(404, "Laudo não encontrado")
    try:
        campos = preparar(modelo, ptam)
    except VinculoError as e:
        raise HTTPException(409, str(e))

    await db.ptam_documents.update_one({"id": ptam_id, "user_id": uid}, {"$set": campos})
    await _salvar(db, mid, uid, {"ptam_id": ptam_id})
    logger.info("Inferência: modelo %s vinculado ao PTAM %s (user %s)", mid, ptam_id, uid)
    return {"ok": True, "ptam_id": ptam_id,
            "valores": {k: v for k, v in campos.items() if not k.startswith("inferencia")}}


@router.delete("/ptam/{ptam_id}/vinculo")
async def desvincular_ptam(ptam_id: str, uid: str = Depends(get_active_subscriber),
                           db=Depends(get_db)):
    """Volta o laudo ao tratamento por fatores."""
    from services.inferencia.vinculo_ptam import desvincular_campos

    ptam = await db.ptam_documents.find_one({"id": ptam_id, "user_id": uid})
    if not ptam:
        raise HTTPException(404, "Laudo não encontrado")
    if ptam.get("icp_status") == "assinado":
        raise HTTPException(409, "Laudo assinado: não é possível trocar o método.")
    await db.ptam_documents.update_one({"id": ptam_id, "user_id": uid},
                                       {"$set": desvincular_campos()})
    return {"ok": True}


@router.get("/ptam/{ptam_id}/modelos-disponiveis")
async def modelos_para_o_laudo(ptam_id: str, uid: str = Depends(get_active_subscriber),
                               db=Depends(get_db)):
    """Modelos HOMOLOGADOS do avaliador — os únicos que podem alimentar um laudo."""
    docs = await db[COL].find({"user_id": uid, "status": "homologado"}, {"resultado": 0}) \
        .sort("homologado_em", -1).to_list(100)
    ptam = await db.ptam_documents.find_one({"id": ptam_id, "user_id": uid},
                                            {"inferencia_modelo_id": 1})
    return {"vinculado": (ptam or {}).get("inferencia_modelo_id"),
            "modelos": [serialize_doc(d) for d in docs]}


@router.post("/modelos/{mid}/importar-amostras")
async def importar_amostras(mid: str, body: ImportarAmostrasBody,
                            uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Puxa dados do banco `amostras_mercado` para dentro do modelo."""
    doc = await _obter(db, mid, uid)
    _bloquear_se_homologado(doc)

    filtro: dict = {"user_id": uid}
    if body.categoria:
        filtro["categoria"] = body.categoria
    if body.cidade:
        filtro["municipio"] = {"$regex": f"^{body.cidade}$", "$options": "i"}
    if body.uf:
        filtro["uf"] = body.uf.upper()
    docs = await db.amostras_mercado.find(filtro).sort("created_at", -1) \
        .to_list(max(1, min(int(body.limite or 200), 500)))

    amostra = []
    for d in docs:
        variaveis = _variaveis_da_amostra(d, body.campos)
        if not variaveis.get("vu"):
            continue          # sem valor unitário o dado não serve ao modelo
        amostra.append({
            "dado_id": d.get("referencia") or d.get("id") or "",
            "utilizado": True, "motivo_descarte": None, "variaveis": variaveis,
        })
    if not amostra:
        raise HTTPException(422, "Nenhuma amostra com valor unitário calculável no filtro.")

    salvo = await _salvar(db, mid, uid, {
        "amostra": amostra, "status": "rascunho", "resultado": None, "enquadramento": None})
    return {"importados": len(amostra), "modelo": serialize_doc(salvo)}


def _variaveis_da_amostra(d: dict, campos: list) -> dict:
    """Mapeia o doc de `amostras_mercado` para as variáveis do modelo."""
    area = (d.get("area_total_m2") or d.get("area_terreno_m2")
            or d.get("area_construida_m2") or d.get("area_m2") or 0)
    valor = float(d.get("valor_rs") or 0)
    vu = round(valor / float(area), 2) if area and valor else 0.0
    base = {
        "vu": vu, "valor_rs": valor, "area": float(area or 0),
        "area_construida": float(d.get("area_construida_m2") or 0),
        "area_terreno": float(d.get("area_terreno_m2") or 0),
        "idade": float(d.get("idade_anos") or 0),
        "quartos": float((d.get("quarto_social") or 0) + (d.get("suite_simples") or 0)
                         + (d.get("suite_master") or 0)),
        "banheiros": float((d.get("banheiro_social") or 0) + (d.get("lavabo") or 0)),
        "vagas": float(d.get("garagem_coberta") or d.get("vagas") or 0),
    }
    for c in (campos or []):
        v = d.get(c)
        if isinstance(v, (int, float)):
            base[c] = float(v)
    return base
