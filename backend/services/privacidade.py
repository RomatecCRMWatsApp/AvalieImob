# @module services.privacidade — direitos do titular (LGPD art. 18) e exportação de dados.
"""Funções puras + operações no banco para:

1. Pedidos de titulares (confirmação/acesso, correção, informação sobre
   compartilhamento, revogação, eliminação/anonimização/bloqueio, portabilidade).
   Funciona também para quem NÃO tem conta (cliente de um avaliador, lead da
   calculadora, contato de prospecção). Nada é apagado automaticamente: o pedido
   gera um protocolo, e a decisão e a execução são do responsável, com trilha.

2. Exportação dos dados da própria conta (JSON), sempre escopada pelo `user_id`
   do token. Segredos (senha, tokens, certificados, credenciais de integração) e
   binários grandes ficam de fora.

Distinções que o código respeita (ver docs/privacidade/retencao-e-direitos.md):
- excluir a CONTA de login ≠ excluir um CLIENTE cadastrado ≠ atender pedido de
  TITULAR ≠ excluir a EMPRESA. "Excluir minha conta" aqui só abre pedido; nunca
  apaga a carteira de clientes nem documentos assinados.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

COL_PEDIDOS = "privacidade_solicitacoes"

TIPOS = {
    "confirmacao_acesso": "Confirmação de tratamento e acesso aos dados",
    "correcao": "Correção de dados incompletos, inexatos ou desatualizados",
    "compartilhamento": "Informação sobre com quem os dados são compartilhados",
    "revogacao": "Revogação de consentimento",
    "eliminacao": "Eliminação, anonimização ou bloqueio",
    "portabilidade": "Portabilidade",
    "exclusao_conta": "Encerramento da minha conta",
    "outro": "Outro assunto de privacidade",
}

STATUS = ("recebida", "verificando_identidade", "em_analise", "atendida", "indeferida")

# Prazo de referência em dias corridos por tipo. É CONFIGURÁVEL (sys_config
# "privacidade_prazos") e precisa ser validado pelo jurídico: a LGPD fixa 15 dias
# para a declaração completa de acesso (art. 19, II); os demais dependem de
# regulamentação e do caso. Não use como promessa pública.
PRAZOS_PADRAO = {
    "confirmacao_acesso": 15,
    "correcao": 15,
    "compartilhamento": 15,
    "revogacao": 15,
    "eliminacao": 15,
    "portabilidade": 15,
    "exclusao_conta": 15,
    "outro": 15,
}

# Coleções que NUNCA entram na exportação (segredos, controle interno ou dados de terceiros).
COLECOES_EXCLUIDAS = {
    "credenciais", "certificados", "integracoes", "sso_jti_usados", "sys_config",
    "sys_leases", "system_flags", "counters", "payment_events", "user_access_log",
    COL_PEDIDOS, "blog_eventos", "cub_cache", "zonas_planodiretor",
    "contrato_clause_templates", "geo_urbano_presets", "georef_verificacoes",
    "leads_avaliacao", "prospeccao", "prospeccao_campanha", "atendimento_conversas",
    "email_logs", "tenant_branding",
}
_CAMPO_SECRETO = re.compile(
    r"(password|senha|token|secret|segredo|pfx|encrypted|cifrad|api_?key|apikey|"
    r"chave_privada|private_key|reset_|webhook|security|credencia)", re.IGNORECASE)
_CAMPO_BINARIO = re.compile(r"(_b64|b64_|paginas_render|data_b64|imagem_b64|traco)$", re.IGNORECASE)
MAX_DOCS_POR_COLECAO = 5000


def gerar_protocolo(agora: Optional[datetime] = None) -> str:
    agora = agora or datetime.utcnow()
    return f"PRIV-{agora:%Y%m%d}-{secrets.token_hex(3).upper()}"


def prazo_para(tipo: str, recebida_em: datetime, prazos: Optional[dict] = None) -> datetime:
    dias = int((prazos or PRAZOS_PADRAO).get(tipo, PRAZOS_PADRAO["outro"]))
    return recebida_em + timedelta(days=dias)


def validar_pedido(dados: dict) -> Optional[str]:
    """Mensagem de erro, ou None. Coleta mínima: nome, e-mail, tipo e descrição."""
    if dados.get("tipo") not in TIPOS:
        return "Escolha o tipo de pedido."
    nome = (dados.get("nome") or "").strip()
    if len(nome) < 3:
        return "Informe seu nome completo."
    email = (dados.get("email") or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "Informe um e-mail válido para receber a resposta."
    if dados.get("relacao") not in ("titular", "representante"):
        return "Informe se você é o titular ou representante."
    if len((dados.get("descricao") or "").strip()) < 10:
        return "Descreva o pedido (ex.: quais dados, em qual documento ou cadastro)."
    return None


def montar_pedido(dados: dict, *, user_id: Optional[str] = None, agora: Optional[datetime] = None,
                  prazos: Optional[dict] = None) -> dict:
    agora = agora or datetime.utcnow()
    tipo = dados["tipo"]
    return {
        "protocolo": gerar_protocolo(agora),
        "tipo": tipo,
        "tipo_label": TIPOS[tipo],
        "nome": dados["nome"].strip()[:120],
        "email": dados["email"].strip().lower()[:160],
        "telefone": (dados.get("telefone") or "").strip()[:30],
        "relacao": dados["relacao"],
        "descricao": dados["descricao"].strip()[:2000],
        # Pedido de quem tem conta e está logado: identidade já verificada pelo login.
        # Pedido público: identidade a verificar pelo responsável antes de executar.
        "user_id": user_id,
        "origem": "conta" if user_id else "publico",
        "identidade": "verificada_login" if user_id else "pendente",
        "status": "recebida",
        "recebida_em": agora,
        "prazo_referencia": prazo_para(tipo, agora, prazos),
        "historico": [{"em": agora, "status": "recebida", "por": "sistema", "nota": "Pedido registrado."}],
        "responsavel": None,
    }


def aplicar_atualizacao(pedido: dict, status: Optional[str], nota: str, por: str,
                        responsavel: Optional[str] = None, agora: Optional[datetime] = None) -> dict:
    """Devolve o $set/$push para mudar status com trilha. Levanta ValueError se inválido."""
    if status is not None and status not in STATUS:
        raise ValueError("Status inválido.")
    agora = agora or datetime.utcnow()
    novo = status or pedido.get("status")
    s: dict = {"status": novo, "atualizado_em": agora}
    if responsavel is not None:
        s["responsavel"] = responsavel[:120]
    if novo in ("atendida", "indeferida"):
        s["concluida_em"] = agora
    return {"$set": s, "$push": {"historico": {"em": agora, "status": novo, "por": por, "nota": (nota or "")[:1000]}}}


# ── Exportação ───────────────────────────────────────────────────────────────

def _limpar(v: Any) -> Any:
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if k == "_id":
                continue
            if _CAMPO_SECRETO.search(str(k)):
                out[k] = "[omitido por segurança]"
            elif _CAMPO_BINARIO.search(str(k)) and isinstance(x, (str, bytes, list)):
                tam = len(x) if not isinstance(x, list) else sum(len(str(i)) for i in x)
                out[k] = f"[arquivo omitido: {tam} caracteres — baixe pelo próprio documento no painel]"
            else:
                out[k] = _limpar(x)
        return out
    if isinstance(v, list):
        return [_limpar(x) for x in v]
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, bytes):
        return f"[binário omitido: {len(v)} bytes]"
    return v


def limpar_documento(doc: dict) -> dict:
    """Remove segredos e binários de um documento antes de exportar. Função pura."""
    return _limpar(doc or {})


async def exportar_dados_usuario(db, uid: str, colecoes: Optional[Iterable[str]] = None,
                                 agora: Optional[datetime] = None) -> dict:
    """Junta os dados do usuário em todas as coleções com `user_id`. Escopo sempre pelo uid."""
    agora = agora or datetime.utcnow()
    if colecoes is None:
        colecoes = await db.list_collection_names()
    conta = await db.users.find_one({"id": uid}) or {}
    resultado: dict = {
        "gerado_em": agora.isoformat(),
        "aviso": ("Exportação dos dados vinculados à sua conta no AvalieImob. Segredos (senha, "
                  "tokens, certificados digitais e credenciais de integração) não são incluídos. "
                  "Documentos e imagens aparecem como referência; baixe os arquivos pelo painel. "
                  "Os cadastros de clientes são dados de terceiros sob sua responsabilidade."),
        "conta": limpar_documento(conta),
        "colecoes": {},
    }
    for nome in sorted(set(colecoes)):
        if nome in COLECOES_EXCLUIDAS or nome == "users" or nome.startswith("system."):
            continue
        docs = await db[nome].find({"user_id": uid}).to_list(MAX_DOCS_POR_COLECAO)
        if docs:
            resultado["colecoes"][nome] = [limpar_documento(d) for d in docs]
    return resultado
