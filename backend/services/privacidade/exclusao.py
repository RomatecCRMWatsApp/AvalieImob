# @module services.privacidade.exclusao — Exclusão/anonimização SEPARADA por alvo.
#
# Quatro operações DIFERENTES (nunca uma implica a outra):
#   1. CONTA DE LOGIN  (planejar_conta / anonimizar_conta)
#      Anonimiza os dados pessoais do usuário e encerra o login. NÃO apaga a carteira
#      (clientes, imóveis, laudos, contratos) — isso é a operação 4.
#   2. CONTATO/CLIENTE de um assinante (planejar_contato)
#      Já existe `DELETE /clients/{id}` (escopado ao dono). Aqui só o RELATÓRIO de
#      impacto: o contato pode estar COPIADO dentro de laudos/contratos emitidos, que
#      não são reescritos (registro do ato praticado).
#   3. PEDIDO DE TITULAR sem conta (localizar_titular)
#      Localiza onde o identificador aparece e em QUAL conta (assinante). Quem decide
#      o atendimento é o controlador daquele dado — frequentemente o assinante.
#   4. EMPRESA/TENANT inteiro — NÃO implementado (decisão de negócio/jurídica:
#      prazo de retenção, contrato, devolução da carteira). Só listado no plano.
#
# Registros PRESERVADOS (retenção justificável — prazos a validar pelo jurídico):
#   transactions / payment_events  → obrigação fiscal-contábil e defesa (CDC, CTN)
#   laudos/contratos/recibos assinados, assinaturas_pdf, nfse → prova do ato praticado,
#     responsabilidade técnica do avaliador, eventual litígio
#   privacidade_exclusoes          → prova do atendimento e reaplicação após restore
#
# Tudo é IDEMPOTENTE e tem DRY-RUN. A execução real exige a flag
# PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA (default desligada) — decisão do dono.
import hashlib
import re
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

# Campos do documento `users` substituídos na anonimização.
_USER_CAMPOS_PII = (
    "name", "email", "phone", "telefone", "cpf", "crea", "creci", "company",
    "referrer", "page_origin", "utm_source", "utm_medium", "utm_campaign",
    "avatar", "foto", "endereco",
)
# Campos do perfil profissional removidos (documentos e imagens pessoais).
_PERFIL_CAMPOS_PII = (
    "nome_completo", "foto_perfil", "cpf", "rg", "rg_orgao", "telefone", "email_profissional",
    "endereco_escritorio", "cep", "bio_resumo", "assinatura_visual_b64", "assinatura_tecnico_b64",
    "cartao_regularidade_b64", "cartao_regularidade_paginas_b64",
    "certidao_regularidade_b64", "certidao_regularidade_paginas_b64",
    "certificado_cnai_b64", "certificado_cnai_paginas_b64",
)
# Apagados integralmente: só servem à própria conta e não têm retenção justificável.
_APAGAR_POR_USER = ("ai_messages", "privacidade_exportacoes", "user_access_log")
# Preservados (com motivo) — só contados no plano.
_PRESERVAR = {
    "transactions": "pagamento — obrigação fiscal/contábil e defesa (prazo a validar)",
    "payment_events": "auditoria de pagamento — defesa e conciliação (prazo a validar)",
    "assinaturas_pdf": "documento assinado — prova do ato praticado",
    "nfse_documentos": "documento fiscal — obrigação legal",
}
# Dados de negócio (carteira) — NÃO tocados pela exclusão da conta.
_CARTEIRA = (
    "ptam_documents", "clients", "properties", "contratos", "recibos", "propostas",
    "vistorias", "garantias", "georef_projetos", "geo_urbano_projetos",
    "amostras_mercado", "documentos_externos", "evaluations", "locacoes",
)


def _pseudonimo(uid: str) -> str:
    return hashlib.sha256(("avalieimob-anon:" + uid).encode()).hexdigest()[:16]


async def _contar(db, nome: str, filtro: Dict[str, Any]) -> Optional[int]:
    try:
        return await getattr(db, nome).count_documents(filtro)
    except Exception:  # noqa: BLE001
        return None


async def planejar_conta(db, uid: str) -> Dict[str, Any]:
    """DRY-RUN: o que a anonimização da conta faria. Sem efeito colateral."""
    user = await db.users.find_one({"id": uid})
    if not user:
        raise LookupError("Usuário não encontrado.")
    role = str(user.get("role") or "").lower()
    plano: Dict[str, Any] = {
        "user_id": uid,
        "ja_anonimizado": bool(user.get("anonimizado_em")),
        "bloqueios": [],
        "anonimizar": {
            "users": [c for c in _USER_CAMPOS_PII if user.get(c)],
            "perfil_avaliador": [],
        },
        "apagar": {},
        "preservar": {},
        "carteira_nao_tocada": {},
        "observacoes": [
            "A carteira (clientes, laudos, contratos) NÃO é apagada pela exclusão da conta.",
            "Destino da carteira depende de decisão de negócio/jurídica (exclusão do tenant).",
            "Backups: a anonimização é reaplicada após restore (registro em privacidade_exclusoes).",
        ],
    }
    if role in ("admin", "owner", "ceo"):
        plano["bloqueios"].append("Conta administrativa: não pode ser anonimizada por este fluxo.")
    perfil = await db.perfil_avaliador.find_one({"user_id": uid})
    if perfil:
        plano["anonimizar"]["perfil_avaliador"] = [c for c in _PERFIL_CAMPOS_PII if perfil.get(c)]
    for nome in _APAGAR_POR_USER:
        plano["apagar"][nome] = await _contar(db, nome, {"user_id": uid})
    for nome, motivo in _PRESERVAR.items():
        plano["preservar"][nome] = {"quantidade": await _contar(db, nome, {"user_id": uid}), "motivo": motivo}
    for nome in _CARTEIRA:
        plano["carteira_nao_tocada"][nome] = await _contar(db, nome, {"user_id": uid})
    return plano


async def anonimizar_conta(db, uid: str, executado_por: str,
                           agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Executa a anonimização da conta. Idempotente. Levanta PermissionError se bloqueado."""
    agora = agora or datetime.utcnow()
    plano = await planejar_conta(db, uid)
    if plano["bloqueios"]:
        raise PermissionError("; ".join(plano["bloqueios"]))
    pseudo = _pseudonimo(uid)
    sets: Dict[str, Any] = {c: None for c in _USER_CAMPOS_PII}
    sets.update({
        "name": "Usuário removido",
        # e-mail único e INVÁLIDO (domínio .invalid, RFC 2606) — mantém índice único
        "email": f"removido+{pseudo}@anonimizado.invalid",
        "password_hash": "!" + secrets.token_hex(32),   # hash impossível: login bloqueado
        "plan_status": "encerrado",
        "conta_encerrada": True,
        "anonimizado_em": agora,
    })
    await db.users.update_one({"id": uid}, {"$set": sets})
    perfil_sets = {c: None for c in _PERFIL_CAMPOS_PII}
    await db.perfil_avaliador.update_one({"user_id": uid}, {"$set": perfil_sets})
    apagados = {}
    for nome in _APAGAR_POR_USER:
        try:
            r = await getattr(db, nome).delete_many({"user_id": uid})
            apagados[nome] = getattr(r, "deleted_count", None)
        except Exception:  # noqa: BLE001
            apagados[nome] = None
    # Registro de atendimento: SEM dados pessoais (só id interno e data).
    if not await db.privacidade_exclusoes.find_one({"user_id": uid, "tipo": "conta"}):
        await db.privacidade_exclusoes.insert_one({
            "id": secrets.token_hex(12), "user_id": uid, "tipo": "conta",
            "executado_em": agora, "executado_por": executado_por,
        })
    return {"user_id": uid, "anonimizado_em": agora, "apagados": apagados}


async def reaplicar_exclusoes(db, executado_por: str = "sistema:restore") -> List[str]:
    """Depois de restaurar um backup: reaplica toda anonimização já registrada.

    Idempotente — conta já anonimizada é reprocessada sem efeito adicional.
    """
    reaplicados: List[str] = []
    for reg in await db.privacidade_exclusoes.find({"tipo": "conta"}).to_list(100000):
        uid = reg.get("user_id")
        user = await db.users.find_one({"id": uid})
        if user and not str(user.get("email", "")).endswith("@anonimizado.invalid"):
            try:
                await anonimizar_conta(db, uid, executado_por)
                reaplicados.append(uid)
            except PermissionError:
                continue
    return reaplicados


async def planejar_contato(db, uid: str, client_id: str) -> Dict[str, Any]:
    """Relatório de impacto da exclusão de UM contato da carteira (escopado ao dono)."""
    cli = await db.clients.find_one({"id": client_id, "user_id": uid})
    if not cli:
        raise LookupError("Cliente não encontrado.")
    return {
        "client_id": client_id,
        "acao_disponivel": "DELETE /api/clients/{id} (remove o cadastro do contato)",
        "nao_alterados": [
            "Laudos, contratos e recibos já emitidos mantêm a cópia dos dados do contato "
            "(registro do ato; alteração exigiria nova versão do documento).",
        ],
        "outras_contas": "Não verificado — o mesmo contato em outra conta pertence a outro controlador.",
    }


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


async def localizar_titular(db, *, email: str = "", documento: str = "",
                            telefone: str = "") -> Dict[str, Any]:
    """Admin: onde o identificador aparece, agrupado por conta. Não devolve os dados."""
    email = (email or "").strip().lower()
    doc = _digitos(documento)
    tel = _digitos(telefone)
    if not (email or doc or tel):
        raise ValueError("Informe e-mail, CPF/CNPJ ou telefone.")
    alvos = []
    if email:
        alvos += [("users", "email", email), ("clients", "email", email),
                  ("leads_avaliacao", "email", email), ("prospeccao", "email", email)]
    if tel:
        alvos += [("users", "phone", tel), ("clients", "phone", tel),
                  ("leads_avaliacao", "whatsapp", tel), ("prospeccao", "telefone", tel)]
    if doc:
        alvos += [("clients", "doc", doc), ("clients", "doc", _formatar_doc(doc))]
    achados: List[Dict[str, Any]] = []
    for col, campo, valor in alvos:
        if not valor:
            continue
        try:
            docs = await getattr(db, col).find({campo: valor}).to_list(200)
        except Exception:  # noqa: BLE001
            continue
        for d in docs:
            achados.append({
                "colecao": col, "campo": campo, "registro_id": d.get("id") or str(d.get("_id")),
                "conta_responsavel": d.get("user_id") if col != "users" else d.get("id"),
            })
    # dedup
    vistos, unicos = set(), []
    for a in achados:
        k = (a["colecao"], a["registro_id"])
        if k not in vistos:
            vistos.add(k)
            unicos.append(a)
    return {"ocorrencias": unicos, "total": len(unicos)}


def _formatar_doc(d: str) -> str:
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return d
