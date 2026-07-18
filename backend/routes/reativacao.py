# @module routes.reativacao — campanha de reativação de cadastros que não ativaram.
# Admin controla; o descadastro é público (LGPD).
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from db import get_db
from dependencies import get_admin_user
from services import reativacao as R

logger = logging.getLogger("romatec")

router = APIRouter(tags=["reativacao"])
router_publico = APIRouter(tags=["reativacao-publico"])

_CFG_ID = "reativacao"


async def carregar_config(db) -> dict:
    doc = await db.sys_config.find_one({"_id": _CFG_ID}) or {}
    return {
        "ativo": bool(doc.get("ativo", False)),
        "hora": int(doc.get("hora", 9)),          # hora local (Brasília) do disparo
        "limite_dia": int(doc.get("limite_dia", 50)),
        "ultimo_dia": doc.get("ultimo_dia"),
    }


@router.get("/reativacao/status")
async def status(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Config + quem está na fila agora, por etapa."""
    cfg = await carregar_config(db)
    fila = await R.candidatos(db)
    por_etapa = {}
    for item in fila:
        n = item["etapa"] + 1
        por_etapa[f"etapa_{n}"] = por_etapa.get(f"etapa_{n}", 0) + 1

    inativos = await db.users.count_documents({"plan_status": {"$ne": "active"}})
    optouts = await db.users.count_documents({"reativacao_opt_out": True})

    # Situação de CADA pessoa: quantos e-mails já recebeu e por que está (ou não)
    # na fila. Sem isto o painel só mostra quem vai receber e esconde o histórico.
    na_fila_ids = {i["user"].get("id") for i in fila}
    pessoas = []
    total_enviados = 0
    async for u in db.users.find({"plan_status": {"$ne": "active"}}).sort("created_at", -1):
        enviadas = list(u.get("reativacao_enviadas") or [])
        total_enviados += len(enviadas)
        if u.get("reativacao_opt_out"):
            situacao = "descadastrado"
        elif len(enviadas) >= len(R.ETAPAS_DIAS):
            situacao = "concluida"
        elif u.get("id") in na_fila_ids:
            situacao = "na_fila"
        else:
            situacao = "aguardando"
        pessoas.append({
            "nome": u.get("name") or "",
            "email": u.get("email") or "",
            "enviados": len(enviadas),
            "etapas": sorted(e + 1 for e in enviadas),
            "ultimo_envio": u.get("reativacao_ultimo_envio"),
            "situacao": situacao,
            "total_etapas": len(R.ETAPAS_DIAS),
        })

    return {
        "config": cfg,
        "etapas_dias": R.ETAPAS_DIAS,
        "na_fila_agora": len(fila),
        "por_etapa": por_etapa,
        "total_inativos": inativos,
        "descadastrados": optouts,
        "total_enviados": total_enviados,
        "pessoas": pessoas,
        "destinatarios": [
            {"nome": i["user"].get("name"), "email": i["user"].get("email"),
             "etapa": i["etapa"] + 1}
            for i in fila[:50]
        ],
    }


@router.post("/reativacao/config")
async def salvar_config(payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    campos = {}
    if "ativo" in payload:
        campos["ativo"] = bool(payload["ativo"])
    if "hora" in payload:
        campos["hora"] = max(0, min(int(payload["hora"]), 23))
    if "limite_dia" in payload:
        campos["limite_dia"] = max(1, min(int(payload["limite_dia"]), 200))
    if not campos:
        raise HTTPException(status_code=400, detail="Nada a salvar")
    await db.sys_config.update_one({"_id": _CFG_ID}, {"$set": campos}, upsert=True)
    logger.info("Reativação: config alterada por %s: %s", uid, campos)
    return {"ok": True, **(await carregar_config(db))}


@router.post("/reativacao/enviar-teste")
async def enviar_teste(payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Envia uma etapa para um e-mail de teste, sem marcar ninguém."""
    email = str(payload.get("email") or "").strip()
    etapa = max(0, min(int(payload.get("etapa", 0)), len(R.ETAPAS_DIAS) - 1))
    perfil = str(payload.get("perfil") or "nunca")   # nunca | checkout
    if "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail inválido")

    from email_service import _send_email_sync
    import asyncio

    fake = {
        "id": "teste", "name": payload.get("nome") or "Fulano de Tal", "email": email,
        "status_funil": "checkout_started" if perfil == "checkout" else "never_started",
        "checkout_started_at": datetime.utcnow() if perfil == "checkout" else None,
    }
    assunto, html = R.assunto_e_corpo(
        etapa, fake, f"{R.APP_URL}/dashboard", f"{R.APP_URL}/api/reativacao/descadastrar/teste"
    )
    try:
        await asyncio.to_thread(_send_email_sync, email, assunto, html)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Falha ao enviar: {e}")
    return {"ok": True, "assunto": assunto, "etapa": etapa + 1}


@router.post("/reativacao/rodar-agora")
async def rodar_agora(payload: dict = None, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Dispara as etapas vencidas imediatamente (não espera o horário)."""
    cfg = await carregar_config(db)
    limite = int((payload or {}).get("limite") or cfg["limite_dia"])
    enviados = await R.rodar(db, limite=limite, intervalo=int((payload or {}).get("intervalo", 20)))
    return {"ok": True, "enviados": enviados}


@router.post("/reativacao/reenviar")
async def reenviar(payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Reenvio MANUAL para pessoas escolhidas na tela.

    Ignora de propósito a trava de 2 dias e o vencimento da etapa: aqui quem
    decide é o admin, que está olhando a lista. As travas automáticas continuam
    valendo para o disparo diário.

    `etapa` nulo = próxima etapa não enviada (ou a última, se a sequência acabou).
    """
    emails = [str(e).strip().lower() for e in (payload.get("emails") or []) if str(e).strip()]
    if not emails:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma pessoa")
    etapa_fixa = payload.get("etapa")

    enviados, falhas = 0, []
    for email in emails:
        u = await db.users.find_one({"email": email})
        if not u:
            falhas.append(f"{email}: não encontrado")
            continue
        if u.get("reativacao_opt_out"):
            falhas.append(f"{email}: descadastrou (não reenviado)")
            continue

        if etapa_fixa is None:
            enviadas = set(u.get("reativacao_enviadas") or [])
            proxima = next((i for i in range(len(R.ETAPAS_DIAS)) if i not in enviadas), None)
            etapa = proxima if proxima is not None else len(R.ETAPAS_DIAS) - 1
        else:
            etapa = max(0, min(int(etapa_fixa), len(R.ETAPAS_DIAS) - 1))

        if await R.enviar_etapa(db, u, etapa):
            enviados += 1
        else:
            falhas.append(f"{email}: falha no envio")

    logger.info("Reativação: reenvio manual por %s — %s enviado(s)", uid, enviados)
    return {"ok": True, "enviados": enviados, "falhas": falhas}


@router_publico.get("/reativacao/descadastrar/{token}", response_class=HTMLResponse)
async def descadastrar(token: str, db=Depends(get_db)):
    """Opt-out (LGPD). Público, sem autenticação."""
    r = await db.users.update_one(
        {"reativacao_opt_out_token": token},
        {"$set": {"reativacao_opt_out": True, "reativacao_opt_out_em": datetime.utcnow()}},
    )
    ok = r.matched_count > 0
    msg = ("Pronto — você não receberá mais estes e-mails."
           if ok else "Link inválido ou já utilizado.")
    return HTMLResponse(f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Descadastro — AvalieImob</title></head>
<body style="margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
background:#0C3320;color:#f3f1e6;display:flex;align-items:center;justify-content:center;
min-height:100vh;padding:24px">
  <div style="max-width:460px;text-align:center">
    <div style="font-size:34px;color:#C9A84C;margin-bottom:8px">AvalieImob</div>
    <p style="font-size:17px;line-height:1.5">{msg}</p>
    <p style="font-size:13px;color:rgba(243,241,230,.6);margin-top:20px">
      Sua conta continua ativa — apenas os e-mails de acompanhamento foram interrompidos.
    </p>
  </div>
</body></html>""")
