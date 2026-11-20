# @module services.log_redaction — Redação de dados pessoais e segredos nos LOGS.
#
# Vários pontos do código registram telefone, e-mail ou CPF do destinatário em
# mensagens de log ("Falha ao enviar WhatsApp p/ 5599...", "enviado por email para
# fulano@..."). E o access log do uvicorn grava a URL completa, incluindo tokens de
# links públicos (/ptam/public/<token>, /aceite/<token>, ?token= do webhook).
#
# Em vez de editar dezenas de linhas, um `logging.Filter` aplicado aos HANDLERS
# reescreve a mensagem JÁ FORMATADA antes de ela sair. Regras (conservadoras):
#   - e-mail            → f***@dominio.com
#   - CPF (com/sem máscara, 11 dígitos isolados) → ***.***.***-NN
#   - telefone BR (10 a 13 dígitos isolados, com ou sem +55) → ******NNNN
#   - "Bearer <jwt>", JWT solto e parâmetros token/senha/secret/key na query → [REDACTED]
#   - segmento de URL com token urlsafe longo (>= 32 chars, não-UUID) → [TOKEN]
# CNPJ (14 dígitos) NÃO é mascarado: é dado empresarial público e útil em diagnóstico.
# UUIDs (ids internos) também ficam — são necessários para depurar.
#
# Falha na redação NUNCA derruba o log (o filtro sempre devolve True).
import logging
import re

_EMAIL = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_QS_SECRET = re.compile(
    r"(?i)([?&](?:token|access_token|senha|password|secret|key|api_key|codigo|code)=)[^&\s\"']+"
)
_CPF_FMT = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-(\d{2})\b")
# UUID primeiro (para não confundir seus blocos com telefone/token)
_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
# Sequência de dígitos isolada (sem letra/dígito colado). 11 = CPF ou celular; 10-13 = telefone.
_DIGITOS = re.compile(r"(?<![\w.])(\+?\d{10,13})(?![\w])")
_PATH_TOKEN = re.compile(r"(/)([A-Za-z0-9_-]{32,})(?=[/?\s\"']|$)")


def _mascara_digitos(m: "re.Match") -> str:
    bruto = m.group(1)
    dig = bruto.lstrip("+")
    if len(dig) == 14:          # CNPJ sem máscara — mantém
        return bruto
    return "*" * (len(dig) - 4) + dig[-4:]


def _mascara_path(m: "re.Match") -> str:
    seg = m.group(2)
    if _UUID.fullmatch(seg):
        return m.group(0)
    # só dígitos longos já são tratados como telefone/doc; aqui é token urlsafe
    if seg.isdigit():
        return m.group(0)
    return m.group(1) + "[TOKEN]"


def redigir(texto: str) -> str:
    """Aplica as regras de redação a um texto qualquer (função pura, testável)."""
    if not texto:
        return texto
    s = str(texto)
    s = _BEARER.sub(r"\1[REDACTED]", s)
    s = _JWT.sub("[JWT]", s)
    s = _QS_SECRET.sub(r"\1[REDACTED]", s)
    s = _EMAIL.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", s)
    s = _CPF_FMT.sub(lambda m: f"***.***.***-{m.group(1)}", s)
    # protege UUIDs trocando-os por marcadores durante a redação de dígitos/tokens
    uuids = []

    def _guarda(m):
        uuids.append(m.group(0))
        return f"\x00{len(uuids) - 1}\x00"

    s = _UUID.sub(_guarda, s)
    s = _PATH_TOKEN.sub(_mascara_path, s)
    s = _DIGITOS.sub(_mascara_digitos, s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: uuids[int(m.group(1))], s)
    return s


class RedactingFilter(logging.Filter):
    """Filtro de logging que redige a mensagem final (msg % args) do registro."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            msg = record.getMessage()
            novo = redigir(msg)
            if novo != msg:
                record.msg = novo
                record.args = ()
        except Exception:  # noqa: BLE001 — redação nunca derruba o log
            pass
        return True


_NOMES_LOGGERS = ("", "uvicorn", "uvicorn.error", "uvicorn.access", "romatec")


def instalar_filtro() -> int:
    """Instala o filtro em todos os handlers dos loggers relevantes. Idempotente.

    Retorna quantos handlers receberam o filtro (útil em teste/diagnóstico).
    """
    n = 0
    for nome in _NOMES_LOGGERS:
        for h in logging.getLogger(nome).handlers:
            if not any(isinstance(f, RedactingFilter) for f in h.filters):
                h.addFilter(RedactingFilter())
                n += 1
    return n
