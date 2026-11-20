# @module services.processos — processo de trabalho que liga os documentos existentes.
#
# Um processo NÃO duplica laudo, vistoria, contrato ou foto: guarda só REFERÊNCIAS
# {tipo, id} aos documentos que já existem em suas coleções, mais as etapas, a agenda
# (vistorias, reuniões, entregas) e o histórico. Funções puras; as rotas fazem o I/O.
import uuid
from datetime import datetime, timedelta
from typing import Optional

STATUS = ("aberto", "em_andamento", "aguardando_cliente", "concluido", "cancelado")
STATUS_ROTULO = {
    "aberto": "Aberto", "em_andamento": "Em andamento",
    "aguardando_cliente": "Aguardando cliente", "concluido": "Concluído", "cancelado": "Cancelado",
}

TIPOS_SERVICO = {
    "avaliacao": "Avaliação (PTAM / laudo)",
    "vistoria": "Vistoria",
    "contrato": "Contrato / intermediação",
    "topografia": "Topografia / georreferenciamento",
    "outro": "Outro",
}

ETAPAS_PADRAO = {
    "avaliacao": ["Vistoria agendada", "Vistoria realizada", "Documentos recebidos",
                  "Pesquisa de mercado", "Laudo em revisão", "Laudo entregue"],
    "vistoria": ["Vistoria agendada", "Vistoria realizada", "Termo assinado", "Relatório entregue"],
    "contrato": ["Documentos recebidos", "Minuta enviada", "Assinaturas", "Registro/entrega"],
    "topografia": ["Levantamento de campo", "Processamento", "Peças técnicas",
                   "Assinaturas", "Protocolo"],
    "outro": ["Início", "Entrega"],
}

# tipo de referência → (coleção, rota no painel, campos usados no rótulo)
REFERENCIAS = {
    "ptam": ("ptam_documents", "/dashboard/ptam/{id}", ("numero_ptam", "property_label", "property_address")),
    "tvi": ("vistorias", "/dashboard/tvi/{id}", ("numero_tvi", "titulo", "imovel_endereco")),
    "contrato": ("contratos", "/dashboard/contratos/{id}", ("numero_contrato", "tipo_contrato")),
    "garantia": ("garantias", "/dashboard/garantias/{id}", ("numero", "titulo", "endereco")),
    "georref": ("georef_projetos", "/dashboard/topografia/georef/{id}", ("numero", "nome")),
    "geo_urbano": ("geo_urbano_projetos", "/dashboard/topografia/geo-urbano/{id}", ("numero", "denominacao")),
    "recibo": ("recibos", "/dashboard/recibos/{id}", ("numero", "descricao")),
    "proposta": ("propostas", "/dashboard/propostas/{id}", ("numero", "cliente_nome")),
}
REF_ROTULO_TIPO = {
    "ptam": "PTAM", "tvi": "Vistoria", "contrato": "Contrato", "garantia": "Garantia",
    "georref": "Georreferenciamento", "geo_urbano": "Geo Urbano", "recibo": "Recibo",
    "proposta": "Proposta",
}

AGENDA_TIPOS = {"vistoria": "Vistoria", "reuniao": "Reunião", "entrega": "Entrega", "outro": "Outro"}
AGENDA_STATUS = ("agendado", "confirmado", "realizado", "cancelado")


def agora() -> datetime:
    return datetime.utcnow()


def _id() -> str:
    return str(uuid.uuid4())


def rotulo_documento(tipo: str, doc: dict) -> str:
    campos = REFERENCIAS[tipo][2]
    partes = [str(doc.get(c)).strip() for c in campos if doc.get(c)]
    return " — ".join(partes[:2]) or REF_ROTULO_TIPO[tipo]


def link_documento(tipo: str, doc_id: str) -> str:
    return REFERENCIAS[tipo][1].format(id=doc_id)


def etapas_iniciais(tipo_servico: str) -> list:
    return [{"id": _id(), "titulo": t, "concluida": False, "concluida_em": None}
            for t in ETAPAS_PADRAO.get(tipo_servico, ETAPAS_PADRAO["outro"])]


def evento(texto: str, **extra) -> dict:
    ev = {"quando": agora(), "evento": texto}
    ev.update({k: v for k, v in extra.items() if v is not None})
    return ev


def validar_status(status: str) -> str:
    if status not in STATUS:
        raise ValueError("Situação inválida.")
    return status


def parse_inicio(valor) -> datetime:
    """Aceita ISO com ou sem fuso; guarda em UTC sem fuso (padrão do banco)."""
    if isinstance(valor, datetime):
        dt = valor
    else:
        s = str(valor or "").strip()
        if not s:
            raise ValueError("Informe a data e a hora.")
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Data/hora inválida.")
    if dt.tzinfo is not None:
        dt = (dt - dt.utcoffset()).replace(tzinfo=None)
    return dt


def novo_compromisso(tipo: str, inicio, duracao_min: int = 60, local: str = "",
                     contato: str = "", observacao: str = "") -> dict:
    if tipo not in AGENDA_TIPOS:
        raise ValueError("Tipo de compromisso inválido.")
    duracao = int(duracao_min or 60)
    if not 5 <= duracao <= 24 * 60:
        raise ValueError("Duração deve ficar entre 5 minutos e 24 horas.")
    ini = parse_inicio(inicio)
    return {
        "id": _id(), "tipo": tipo, "inicio": ini, "duracao_min": duracao,
        "local": (local or "").strip()[:300], "contato": (contato or "").strip()[:200],
        "observacao": (observacao or "").strip()[:1000], "status": "agendado",
        "historico": [evento("Agendado", para=ini)],
    }


def fim(c: dict) -> datetime:
    return c["inicio"] + timedelta(minutes=int(c.get("duracao_min") or 60))


def conflitos(compromisso: dict, outros: list, ignorar_id: Optional[str] = None) -> list:
    """Compromissos ativos que se sobrepõem no horário (apenas aviso, não bloqueia)."""
    ini, f = compromisso["inicio"], fim(compromisso)
    out = []
    for o in outros:
        if o.get("id") == ignorar_id or o.get("status") in ("cancelado", "realizado"):
            continue
        oi = o.get("inicio")
        if not isinstance(oi, datetime):
            try:
                oi = parse_inicio(oi)
            except ValueError:
                continue
        if oi < f and ini < oi + timedelta(minutes=int(o.get("duracao_min") or 60)):
            out.append(o)
    return out


def aplicar_acao_agenda(c: dict, acao: str, novo_inicio=None, motivo: str = "") -> dict:
    """confirmar | realizado | cancelar | reagendar — devolve o compromisso atualizado
    e mantém o histórico (o horário anterior fica registrado ao reagendar)."""
    c = dict(c)
    hist = list(c.get("historico") or [])
    if c.get("status") in ("cancelado", "realizado") and acao != "reagendar":
        raise ValueError("Compromisso já encerrado.")
    if acao == "confirmar":
        c["status"] = "confirmado"
        hist.append(evento("Confirmado"))
    elif acao == "realizado":
        c["status"] = "realizado"
        hist.append(evento("Realizado"))
    elif acao == "cancelar":
        c["status"] = "cancelado"
        hist.append(evento("Cancelado" + (f": {motivo.strip()[:300]}" if motivo else "")))
    elif acao == "reagendar":
        anterior = c["inicio"] if isinstance(c.get("inicio"), datetime) else parse_inicio(c.get("inicio"))
        novo = parse_inicio(novo_inicio)
        c["inicio"] = novo
        c["status"] = "agendado"
        hist.append(evento("Reagendado" + (f": {motivo.strip()[:300]}" if motivo else ""),
                           de=anterior, para=novo))
    else:
        raise ValueError("Ação inválida.")
    c["historico"] = hist
    return c


def progresso(processo: dict) -> int:
    etapas = processo.get("etapas") or []
    if not etapas:
        return 0
    return round(100 * sum(1 for e in etapas if e.get("concluida")) / len(etapas))
