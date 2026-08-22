# @module routes.trials — Acesso de Teste (trial gratuito por N dias) — somente admin.
#
# Fluxo: o admin cria um login (ou libera para quem já é cadastrado) com prazo em
# dias e manda as credenciais por WhatsApp (Z-API do próprio admin) e/ou e-mail.
# O acesso expira SOZINHO — ver services/trial_service.py.
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from dependencies import get_admin_user
from services import trial_service as TS

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/admin/trials", tags=["Acesso de Teste"])


def _fmt_data(dt) -> str:
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", ""))
        except ValueError:
            return dt
    return dt.strftime("%d/%m/%Y") if isinstance(dt, datetime) else "—"


async def _enviar_whatsapp(db, admin_uid: str, *, telefone: str, mensagem: str) -> dict:
    """Dispara pela Z-API configurada pelo admin. Devolve {ok, erro?}."""
    from services.integracoes_util import carregar_integracoes
    from services import zapi_service

    cfg = await carregar_integracoes(db, admin_uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        return {"ok": False, "erro": "Z-API não configurada (Configurações → Integrações)."}
    try:
        await zapi_service.send_text(
            instance_id=cfg["zapi_instance_id"],
            token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=telefone,
            message=mensagem,
        )
        return {"ok": True}
    except Exception as e:  # noqa: BLE001 — envio é best-effort; o trial já foi liberado
        logger.error("Trial: falha no envio Z-API para %s: %s", telefone, e)
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


async def _enviar_email(email: str, nome: str, senha, dias: int, expira_em) -> dict:
    try:
        from email_service import send_trial_email
        await send_trial_email(email, nome or "", senha, dias, _fmt_data(expira_em))
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        logger.error("Trial: falha no e-mail para %s: %s", email, e)
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


@router.get("")
@router.get("/")
async def listar(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Todos os acessos de teste já concedidos, com dias restantes e situação."""
    trials = await TS.listar_trials(db)
    resumo = {"total": len(trials), "ativos": 0, "expirados": 0, "convertidos": 0, "encerrados": 0}
    for t in trials:
        chave = {"ativo": "ativos", "expirado": "expirados",
                 "convertido": "convertidos", "encerrado": "encerrados"}.get(t["situacao"])
        if chave:
            resumo[chave] += 1
    return {"resumo": resumo, "trials": trials}


@router.post("", status_code=201)
@router.post("/", status_code=201)
async def criar(payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Cria o login de teste (ou libera para quem já é cadastrado) e envia as credenciais.

    Body: {nome, email, telefone?, dias, senha?, observacao?,
           enviar_whatsapp?: bool, enviar_email?: bool}
    """
    p = payload or {}
    try:
        res = await TS.criar_ou_liberar_trial(
            db, uid,
            nome=str(p.get("nome") or ""),
            email=str(p.get("email") or ""),
            dias=p.get("dias"),
            telefone=str(p.get("telefone") or "") or None,
            senha=str(p.get("senha") or "") or None,
            observacao=str(p.get("observacao") or "") or None,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except TS.TrialError as e:
        raise HTTPException(409, str(e))

    user = res["user"]
    dias = int(user.get("trial_dias") or 0)
    expira = user.get("plan_expires")
    mensagem = TS.montar_mensagem_trial(
        nome=user.get("name") or "", email=user.get("email") or "",
        senha=res["senha_temporaria"], dias=dias,
        expira_em=datetime.fromisoformat(str(expira).replace("Z", "")) if expira else datetime.utcnow(),
    )

    envios = {}
    telefone = str(p.get("telefone") or user.get("phone") or "").strip()
    if p.get("enviar_whatsapp") and telefone:
        envios["whatsapp"] = await _enviar_whatsapp(db, uid, telefone=telefone, mensagem=mensagem)
    elif p.get("enviar_whatsapp"):
        envios["whatsapp"] = {"ok": False, "erro": "Telefone não informado."}
    if p.get("enviar_email"):
        envios["email"] = await _enviar_email(user.get("email"), user.get("name") or "",
                                              res["senha_temporaria"], dias, expira)

    logger.info("Admin %s liberou trial de %s dias para %s (criado=%s)",
                uid, dias, user.get("email"), res["criado"])
    return {"ok": True, "criado": res["criado"], "user": user,
            "senha_temporaria": res["senha_temporaria"], "mensagem": mensagem, "envios": envios}


@router.post("/{user_id}/estender")
async def estender(user_id: str, payload: dict = None,
                   uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Soma dias ao teste (se já venceu, conta a partir de agora)."""
    try:
        user = await TS.estender_trial(db, user_id, (payload or {}).get("dias"), admin_uid=uid)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except TS.TrialError as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "user": user}


@router.post("/{user_id}/encerrar")
async def encerrar(user_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Corta o acesso na hora (bloqueia na próxima requisição do cliente)."""
    try:
        user = await TS.encerrar_trial(db, user_id, admin_uid=uid)
    except TS.TrialError as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "user": user}


@router.post("/{user_id}/reenviar")
async def reenviar(user_id: str, payload: dict = None,
                   uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Reenvia as credenciais. Com `nova_senha: true`, gera uma senha nova antes.

    Body: {nova_senha?: bool, senha?, telefone?, enviar_whatsapp?: bool, enviar_email?: bool}
    """
    p = payload or {}
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(404, "Usuário não encontrado")

    senha = None
    if p.get("nova_senha") or p.get("senha"):
        try:
            senha = await TS.redefinir_senha(db, user_id, str(p.get("senha") or "") or None)
        except ValueError as e:
            raise HTTPException(422, str(e))

    st = TS.status_trial(u)
    dias = int(u.get("trial_dias") or 0)
    expira = st["expira_em"] or datetime.utcnow()
    mensagem = TS.montar_mensagem_trial(nome=u.get("name") or "", email=u.get("email") or "",
                                        senha=senha, dias=dias, expira_em=expira)
    envios = {}
    telefone = str(p.get("telefone") or u.get("phone") or "").strip()
    enviar_wa = p.get("enviar_whatsapp", True)
    if enviar_wa and telefone:
        envios["whatsapp"] = await _enviar_whatsapp(db, uid, telefone=telefone, mensagem=mensagem)
        if envios["whatsapp"]["ok"] and telefone != (u.get("phone") or ""):
            await db.users.update_one({"id": user_id}, {"$set": {"phone": telefone}})
    elif enviar_wa:
        envios["whatsapp"] = {"ok": False, "erro": "Telefone não informado."}
    if p.get("enviar_email"):
        envios["email"] = await _enviar_email(u.get("email"), u.get("name") or "",
                                              senha, dias, expira)
    return {"ok": True, "senha_temporaria": senha, "mensagem": mensagem, "envios": envios}
