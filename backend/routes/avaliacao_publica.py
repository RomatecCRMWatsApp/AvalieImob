# @module routes.avaliacao_publica — Calculadora pública "Quanto vale meu imóvel?" + captura de lead.
"""Topo de funil PÚBLICO (sem auth): o visitante faz uma estimativa preliminar de
mercado por ACM simplificado → vê uma faixa de valor → deixa contato. O lead cai
em `leads_avaliacao` e dispara um WhatsApp ao avaliador (José) via Z-API.

IMPORTANTE (regra técnica): a estimativa NÃO é PTAM nem Laudo — é estimativa
preliminar de mercado (distinção ABNT NBR 14.653 / COFECI 1.066/2007). A tabela de
R$/m² é SEMENTE; calibrar com dados reais (amostras de PTAM).

Adaptado às convenções do AvalieImob (vs. o spec original que assumia env-var Z-API):
  - router montado sob /api (prefix local "/avaliacao-publica"); registrado em routes/__init__.
  - DB via `from db import get_db` + Depends(get_db).
  - Z-API reusa services.zapi_service + carregar_integracoes do OWNER (não env próprio):
    a notificação ao José sai pela integração já configurada do dono da conta.
  - rate-limit local (mesmo padrão de routes.assinatura_cliente).

NOTA (NÃO reintroduzir `from __future__ import annotations`): com PEP 563 as anotações
viram strings e o wrapper do slowapi (@limiter.limit + functools.wraps) faz o FastAPI
resolver os type hints no namespace do slowapi — onde `EstimativaInput` não existe —
então o body Pydantic é tratado como query param e o /estimar responde 422 "Field required".
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import get_admin_user

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/avaliacao-publica", tags=["Avaliação Pública"])

OWNER_EMAIL = "admin@romatecavalieimob.com.br"

# ===========================================================================
# CONFIGURAÇÃO DE MERCADO — CALIBRAR COM DADOS REAIS (semente).
# Chaves: "UF" (fallback do estado) ou "UF:CIDADE" (normalizada, sem acento,
# maiúscula). "_default" cobre regiões não mapeadas.
# ===========================================================================
BASE_M2_POR_REGIAO: dict[str, float] = {
    "_default": 3200.0,
    "MA": 2600.0,
    "MA:ACAILANDIA": 2400.0,
    "MA:IMPERATRIZ": 2900.0,
    "MA:SAO LUIS": 4200.0,
    "PA": 3000.0,
    "TO": 3100.0,
    "GO": 3800.0,
    "DF": 6000.0,
    "SP": 7200.0,
    "RJ": 6400.0,
    "MG": 4500.0,
    "BA": 3900.0,
}

FATOR_TIPO: dict[str, float] = {
    "apartamento": 1.00,
    "casa": 0.95,
    "comercial": 1.15,
    "terreno": 0.45,
    "rural": 0.30,
}
FATOR_PADRAO: dict[str, float] = {
    "popular": 0.80,
    "medio": 1.00,
    "alto": 1.30,
    "luxo": 1.70,
}
FATOR_CONSERVACAO: dict[str, float] = {
    "novo": 1.10,
    "bom": 1.00,
    "regular": 0.90,
    "reformar": 0.78,
}
# Banda da faixa (NBR 14653 trabalha intervalos); 12% gera uma faixa honesta.
BANDA = 0.12

# ===========================================================================
# Schemas (Pydantic v2)
# ===========================================================================
TipoImovel = Literal["apartamento", "casa", "comercial", "terreno", "rural"]
Padrao = Literal["popular", "medio", "alto", "luxo"]
Conservacao = Literal["novo", "bom", "regular", "reformar"]

_ACENTOS = str.maketrans("ÁÀÂÃÉÊÍÓÔÕÚÇ", "AAAAEEIOOOUC")


def _norm(texto: str) -> str:
    return (texto or "").strip().upper().translate(_ACENTOS)


class EstimativaInput(BaseModel):
    uf: str = Field(min_length=2, max_length=2)
    cidade: str = Field(min_length=2, max_length=80)
    tipo: TipoImovel
    area: float = Field(gt=0, le=1_000_000)
    quartos: int = Field(ge=0, le=30, default=0)
    vagas: int = Field(ge=0, le=30, default=0)
    padrao: Padrao = "medio"
    conservacao: Conservacao = "bom"

    @field_validator("uf")
    @classmethod
    def _uf_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("cidade")
    @classmethod
    def _cidade_clean(cls, v: str) -> str:
        return v.strip()


class EstimativaOutput(BaseModel):
    valor_m2: float
    valor_medio: float
    valor_min: float
    valor_max: float
    faixa_texto: str
    aviso: str
    base_m2: float            # R$/m² de referência da região (antes dos ajustes)
    regiao_base: str          # rótulo da base usada (cidade / UF / nacional)
    metodologia: str          # como o número foi obtido (transparência)
    fatores: list             # [{label, fator}] dos ajustes aplicados


class LeadInput(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    whatsapp: str = Field(min_length=8, max_length=20)
    email: Optional[str] = Field(default=None, max_length=120)
    imovel: EstimativaInput
    origem: str = Field(default="calculadora_publica", max_length=60)
    consentimento: bool = False          # LGPD — obrigatório True p/ gravar
    website: Optional[str] = Field(default=None, max_length=200)  # honeypot anti-bot (deve vir vazio)

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v.strip()):
            raise ValueError("E-mail inválido.")
        return v.strip().lower()


# ===========================================================================
# Núcleo do cálculo (ACM simplificado)
# ===========================================================================
_TIPO_LABEL = {"apartamento": "Apartamento", "casa": "Casa", "comercial": "Comercial", "terreno": "Terreno", "rural": "Rural"}
_PADRAO_LABEL = {"popular": "Popular", "medio": "Médio", "alto": "Alto", "luxo": "Luxo"}
_CONSERV_LABEL = {"novo": "Novo", "bom": "Bom", "regular": "Regular", "reformar": "A reformar"}


def _base_m2_info(uf: str, cidade: str):
    """Retorna (base_R$/m², rótulo, calibrado?). PRIORIZA a base REAL calibrada dos
    PTAMs emitidos (services.calibracao_base_m2); só cai na SEMENTE se não houver."""
    try:
        from services.calibracao_base_m2 import base_calibrada
        cal = base_calibrada(uf, cidade)
        if cal:
            media, n, label = cal
            return media, f"{label} · {n} avaliações reais", True
    except Exception:  # noqa: BLE001 — calibração indisponível → semente
        pass
    chave_cidade = f"{uf}:{_norm(cidade)}"
    if chave_cidade in BASE_M2_POR_REGIAO:
        return BASE_M2_POR_REGIAO[chave_cidade], f"{(cidade or '').strip().title()}/{uf}", False
    if uf in BASE_M2_POR_REGIAO:
        return BASE_M2_POR_REGIAO[uf], f"{uf} — base estadual", False
    return BASE_M2_POR_REGIAO["_default"], "Base nacional média", False


def calcular_estimativa(dados: EstimativaInput) -> EstimativaOutput:
    base, regiao_base, calibrado = _base_m2_info(dados.uf, dados.cidade)
    fator_vagas = 1.0 + min(dados.vagas, 4) * 0.025

    f_tipo = FATOR_TIPO[dados.tipo]
    f_padrao = FATOR_PADRAO[dados.padrao]
    f_conserv = FATOR_CONSERVACAO[dados.conservacao]
    valor_m2 = base * f_tipo * f_padrao * f_conserv * fator_vagas
    valor_medio = round(valor_m2 * dados.area, 2)
    valor_min = round(valor_medio * (1 - BANDA), 2)
    valor_max = round(valor_medio * (1 + BANDA), 2)

    def fmt(x: float) -> str:
        return f"R$ {x:,.0f}".replace(",", ".")

    faixa = f"{fmt(valor_min)} a {fmt(valor_max)}"
    aviso = (
        "Estimativa preliminar de mercado por análise comparativa simplificada. "
        "NÃO substitui Parecer Técnico de Avaliação Mercadológica (PTAM) nem Laudo "
        "de Avaliação conforme ABNT NBR 14.653 / Resolução COFECI 1.066/2007. Para "
        "fins judiciais, garantia bancária, inventário ou desapropriação é "
        "obrigatório documento técnico assinado por profissional habilitado."
    )
    origem_base = (
        "valor de referência por m² calibrado com avaliações (PTAM) reais da região"
        if calibrado else
        "valor de referência por m² da região"
    )
    metodologia = (
        "Cálculo por Análise Comparativa de Mercado (ACM) simplificada, inspirada na "
        f"ABNT NBR 14.653-2: parte-se de um {origem_base} e aplicam-se fatores de "
        "homogeneização por tipo de imóvel, padrão construtivo, estado de conservação "
        "e nº de vagas; a faixa reflete ±12% de dispersão de mercado."
    )
    fatores = [
        {"label": _TIPO_LABEL.get(dados.tipo, dados.tipo), "fator": round(f_tipo, 3)},
        {"label": f"Padrão {_PADRAO_LABEL.get(dados.padrao, dados.padrao).lower()}", "fator": round(f_padrao, 3)},
        {"label": f"Conservação {_CONSERV_LABEL.get(dados.conservacao, dados.conservacao).lower()}", "fator": round(f_conserv, 3)},
        {"label": f"{int(dados.vagas)} vaga(s)", "fator": round(fator_vagas, 3)},
    ]
    return EstimativaOutput(
        valor_m2=round(valor_m2, 2),
        valor_medio=valor_medio,
        valor_min=valor_min,
        valor_max=valor_max,
        faixa_texto=faixa,
        aviso=aviso,
        base_m2=round(base, 2),
        regiao_base=regiao_base,
        metodologia=metodologia,
        fatores=fatores,
    )


# ===========================================================================
# Notificação WhatsApp ao avaliador (reusa a integração Z-API do OWNER)
# ===========================================================================
def _norm_phone(numero: str) -> str:
    digitos = re.sub(r"\D", "", numero or "")
    if digitos and not digitos.startswith("55") and len(digitos) in (10, 11):
        digitos = "55" + digitos
    return digitos


async def _deve_notificar(db, whatsapp: str) -> bool:
    """Anti-spam da notificação Z-API: teto global por hora + dedupe por telefone.
    O lead É sempre gravado; só a notificação ao José é contida."""
    agora = datetime.now(timezone.utc)
    try:
        recentes = await db["leads_avaliacao"].count_documents({"criado_em": {"$gte": agora - timedelta(hours=1)}})
        if recentes > 30:  # flood improvável de leads legítimos numa hora → corta a notificação
            logger.warning("avaliacao_publica: teto de notificações/hora atingido (%s) — silenciando.", recentes)
            return False
        # mesmo telefone nos últimos 30 min (inclui o atual recém-inserido) → não renotifica
        mesmos = await db["leads_avaliacao"].count_documents(
            {"whatsapp": whatsapp, "criado_em": {"$gte": agora - timedelta(minutes=30)}})
        return mesmos <= 1
    except Exception:  # noqa: BLE001 — em erro, não bloqueia a notificação
        return True


async def _notificar_avaliador(db, mensagem: str) -> None:
    """Envia a notificação de lead pelo WhatsApp do dono da conta (José).
    Best-effort: nunca derruba o registro do lead se a Z-API falhar."""
    try:
        owner = await db.users.find_one({"email": OWNER_EMAIL})
        if not owner:
            logger.warning("avaliacao_publica: owner %s não encontrado — sem notificação.", OWNER_EMAIL)
            return
        owner_uid = owner.get("id") or owner.get("user_id") or str(owner.get("_id"))

        from services.integracoes_util import carregar_integracoes
        cfg = await carregar_integracoes(db, owner_uid)
        if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
            logger.warning("avaliacao_publica: Z-API do owner não configurada — sem notificação.")
            return

        destino = _norm_phone(
            os.environ.get("AVALIACAO_NOTIFY_PHONE")
            or owner.get("whatsapp") or owner.get("phone") or owner.get("telefone") or ""
        )
        if not destino:
            logger.warning("avaliacao_publica: sem telefone de destino p/ notificação.")
            return

        from services import zapi_service
        await zapi_service.send_text(
            instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"), phone=destino, message=mensagem,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("avaliacao_publica: falha ao notificar avaliador: %s", e)


# ===========================================================================
# Endpoints (públicos, rate-limited)
# ===========================================================================
@router.post("/estimar", response_model=EstimativaOutput)
@limiter.limit("30/minute")
async def estimar(dados: EstimativaInput, request: Request) -> EstimativaOutput:
    try:
        return calcular_estimativa(dados)
    except KeyError as e:
        raise HTTPException(422, f"Parâmetro inválido: {e}")
    except Exception as e:  # noqa: BLE001
        logger.exception("avaliacao_publica: erro ao estimar")
        raise HTTPException(500, "Falha ao calcular a estimativa.") from e


@router.post("/lead")
@limiter.limit("10/minute")
async def registrar_lead(lead: LeadInput, request: Request, db=Depends(get_db)) -> dict:
    # Honeypot: campo oculto preenchido = bot → descarta em SILÊNCIO (200 falso, sem gravar/notificar).
    if (lead.website or "").strip():
        logger.info("avaliacao_publica: lead descartado pelo honeypot.")
        return {"ok": True, "id": "ignored"}
    # LGPD: exige consentimento explícito.
    if not lead.consentimento:
        raise HTTPException(422, "É necessário autorizar o tratamento dos seus dados (LGPD).")

    estimativa = calcular_estimativa(lead.imovel)

    doc = {
        "nome": lead.nome.strip(),
        "whatsapp": _norm_phone(lead.whatsapp),
        "email": lead.email,
        "origem": lead.origem,
        "imovel": lead.imovel.model_dump(),
        "estimativa": estimativa.model_dump(),
        "status": "novo",
        "consentimento": True,
        "consentimento_em": datetime.now(timezone.utc),
        "criado_em": datetime.now(timezone.utc),
    }

    try:
        result = await db["leads_avaliacao"].insert_one(doc)
    except Exception as e:  # noqa: BLE001
        logger.exception("avaliacao_publica: erro ao salvar lead")
        raise HTTPException(500, "Falha ao registrar o lead.") from e

    imv = lead.imovel
    msg = (
        "🟢 *Novo lead — Calculadora AvalieImob*\n\n"
        f"👤 {doc['nome']}\n"
        f"📱 {doc['whatsapp']}\n"
        f"✉️ {doc['email'] or '—'}\n\n"
        f"🏠 {imv.tipo.capitalize()} • {imv.area:g} m² • {imv.cidade}/{imv.uf}\n"
        f"Padrão: {imv.padrao} | Conservação: {imv.conservacao} | Vagas: {imv.vagas}\n\n"
        f"💰 Estimativa: {estimativa.faixa_texto}"
    )
    # Anti-spam: o lead já está salvo; só notifica se passar no teto/dedupe.
    if await _deve_notificar(db, doc["whatsapp"]):
        await _notificar_avaliador(db, msg)
        # E-mail imediato ao dono (complementa o WhatsApp; best-effort, não bloqueia).
        try:
            from services.notificacao_lead import enviar_email_lead
            asyncio.create_task(enviar_email_lead(db, doc))
        except Exception as e:  # noqa: BLE001
            logger.error("avaliacao_publica: falha ao enfileirar e-mail de lead: %s", e)

    return {"ok": True, "id": str(result.inserted_id)}


# ===========================================================================
# Admin — recalibrar a base R$/m² a partir dos PTAMs reais (gated por get_admin_user)
# ===========================================================================
async def _owner_uid(db) -> Optional[str]:
    owner = await db.users.find_one({"email": OWNER_EMAIL})
    if not owner:
        return None
    return owner.get("id") or owner.get("user_id") or str(owner.get("_id"))


@router.post("/recalibrar-base")
async def recalibrar_base(db=Depends(get_db), _admin: str = Depends(get_admin_user)) -> dict:
    """Reagrega os PTAMs concluídos/assinados do dono → base R$/m² real por cidade/UF."""
    from services.calibracao_base_m2 import recalibrar
    uid = await _owner_uid(db)
    if not uid:
        raise HTTPException(404, "Conta dona (owner) não encontrada.")
    return await recalibrar(db, uid)


@router.get("/base-stats")
async def base_stats(db=Depends(get_db), _admin: str = Depends(get_admin_user)) -> dict:
    """Lista as regiões calibradas (base real) p/ o painel admin."""
    itens = []
    async for d in db["avaliacao_base_m2"].find({}).sort("n", -1):
        itens.append({
            "regiao": d.get("regiao_key"), "escopo": d.get("escopo"),
            "media_m2": d.get("media_m2"), "n": d.get("n"),
            "atualizado_em": d["atualizado_em"].isoformat() if d.get("atualizado_em") else None,
        })
    return {"regioes": itens, "total": len(itens)}
