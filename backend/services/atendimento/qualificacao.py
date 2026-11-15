# @module services.atendimento.qualificacao — Qualificação de leads (funções PURAS).
"""Lê a conversa e decide em que ponto do funil o visitante está.

Duas fontes se combinam: (1) o bloco <<META {...}>> que a IA escreve no fim da
resposta e (2) heurísticas por palavra-chave (rede de segurança quando a IA não
devolve o META ou nenhum provedor responde). O estágio só SOBE, nunca desce.
"""
import json
import re
import unicodedata
from typing import Optional

from services.atendimento.conhecimento import SITE, TRIAL_DIAS, WHATSAPP_ROMATEC, PLANOS

ESTAGIOS = ["curioso", "interessado", "qualificado", "convertido"]
PERFIS = {"profissional", "cliente_servico", "indefinido"}
ASSUNTOS = {
    "plataforma", "planos", "teste", "ptam", "laudo", "pericia", "inferencia", "rural",
    "garantia", "locacao", "vistoria", "contratos", "assinatura", "propostas", "georref",
    "geo_urbano", "usucapiao", "reurb", "onr", "inss_obra", "topografia", "servico", "outro",
}

ROTULO_ASSUNTO = {
    "plataforma": "Plataforma", "planos": "Planos/preço", "teste": "Teste grátis",
    "ptam": "PTAM", "laudo": "Laudo técnico", "pericia": "Perícia", "inferencia": "Inferência estatística",
    "rural": "Avaliação rural", "garantia": "Garantias", "locacao": "Locação", "vistoria": "Vistoria",
    "contratos": "Contratos", "assinatura": "Assinatura digital", "propostas": "Propostas",
    "georref": "Georreferenciamento", "geo_urbano": "Geo Urbano", "usucapiao": "Usucapião",
    "reurb": "REURB", "onr": "Arquivo ONR", "inss_obra": "INSS de obra", "topografia": "Topografia",
    "servico": "Serviço técnico", "outro": "Outro",
}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


# palavra-chave (já sem acento) → assunto
_PALAVRAS = [
    (r"\bptam\b|parecer tecnico|avaliacao mercadolog|quanto vale|valor (do|de) (meu )?imovel", "ptam"),
    (r"\blaudo", "laudo"),
    (r"perici|perito|judicial|desapropria|servidao|indeniza", "pericia"),
    (r"inferencia|regressao|grau iii|grau 3|estatistic|tratamento cientifico", "inferencia"),
    (r"rural|fazenda|sitio|chacara|gleba|terra nua", "rural"),
    (r"garantia|safra|rebanho|bovino|maquina", "garantia"),
    (r"aluguel|locacao|locar", "locacao"),
    (r"vistoria|averbac|habite", "vistoria"),
    (r"contrato|exclusividade|procuracao|compra e venda|promessa", "contratos"),
    (r"assinatura|assinar|icp|certificado digital|e-cpf|e-cnpj", "assinatura"),
    (r"proposta|orcamento", "propostas"),
    (r"\bgel\b|\bgeo\b|georref|georeferenc|sigef|incra|ccir|memorial", "georref"),
    (r"desmembra|remembra|desdobro|retifica|lote urbano|geo urbano|bci|iptu", "geo_urbano"),
    (r"usucapi", "usucapiao"),
    (r"reurb|regulariza", "reurb"),
    (r"\bonr\b|sig-?ri|shapefile|provimento 195|mapa\.onr", "onr"),
    (r"\binss\b|sero|cno\b", "inss_obra"),
    (r"topograf|levantamento|planialtimetr|demarca", "topografia"),
    (r"preco|valor do plano|quanto custa|mensalidade|planos?\b|assinar o sistema|pagamento|pix|boleto", "planos"),
    (r"teste|gratis|gratuito|trial|experimentar", "teste"),
]

# intenção de FECHAR (sobe para qualificado)
_COMPRA = re.compile(
    r"quero (assinar|contratar|fechar|comprar|o plano|fazer|um laudo|um orcamento|orcamento)"
    r"|vou assinar|como (eu )?(assino|contrato|pago|compro)|pode (me )?(fazer|mandar) (o )?orcamento"
    r"|preciso (de um|do|de) (laudo|ptam|georref|levantamento|servico|usucapiao|orcamento)"
    r"|fechar negocio|tenho interesse em contratar|quanto (fica|sai|cobra) (o|um|pra|para)"
)
_HUMANO = re.compile(r"falar com (um |uma )?(pessoa|humano|atendente|alguem|jose|o dono|voce)|me liga|me chama|atendente humano")
_PRECO = re.compile(r"preco|quanto custa|valor|mensalidade|plano|pagamento|desconto")
_PERFIL_PROF = re.compile(r"sou (corretor|avaliador|perito|engenheir|arquitet|agrimensor|topograf|tecnico)|minha imobiliaria|meus clientes|emito laudo|faco laudo|trabalho com")
_PERFIL_CLI = re.compile(r"meu (imovel|terreno|lote|casa|fazenda|sitio)|minha (casa|fazenda|terra|propriedade)|preciso (de um|do) (laudo|servico|georref|levantamento)|quero regularizar|fazer usucapiao")

_RE_FONE = re.compile(r"(?:\+?55\s*)?\(?\d{2}\)?\s*9?\s*\d{4}[-\s]?\d{4}")
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_RE_NOME = re.compile(r"(?:meu nome (?:e|eh)|me chamo|sou o|sou a|aqui (?:e|eh) o|aqui (?:e|eh) a)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,3})", re.I)
_RE_META = re.compile(r"<<\s*META\s*(\{.*?\})\s*>>", re.S)


def detectar_assuntos(texto: str) -> list:
    t = _norm(texto)
    return [a for padrao, a in _PALAVRAS if re.search(padrao, t)]


def detectar_sinais(texto: str) -> dict:
    t = _norm(texto)
    perfil = None
    if _PERFIL_PROF.search(t):
        perfil = "profissional"
    elif _PERFIL_CLI.search(t):
        perfil = "cliente_servico"
    return {
        "compra": bool(_COMPRA.search(t)),
        "humano": bool(_HUMANO.search(t)),
        "preco": bool(_PRECO.search(t)),
        "perfil": perfil,
    }


def normalizar_fone(numero: str) -> str:
    d = re.sub(r"\D", "", numero or "")
    if len(d) in (10, 11):
        d = "55" + d
    return d if len(d) in (12, 13) else ""


def extrair_contato(texto: str) -> dict:
    """WhatsApp, e-mail e nome escritos livremente na mensagem."""
    out = {}
    m = _RE_EMAIL.search(texto or "")
    if m:
        out["email"] = m.group(0).strip(".").lower()
    sem_email = _RE_EMAIL.sub(" ", texto or "")
    m = _RE_FONE.search(sem_email)
    if m:
        f = normalizar_fone(m.group(0))
        if f:
            out["whatsapp"] = f
    m = _RE_NOME.search(texto or "")
    if m:
        nome = m.group(1).strip()
        if len(nome) >= 2:
            out["nome"] = nome.title()
    return out


def separar_meta(resposta: str) -> tuple:
    """Remove o bloco <<META {...}>> da resposta e devolve (texto, meta)."""
    meta = {}
    m = _RE_META.search(resposta or "")
    if m:
        try:
            meta = json.loads(m.group(1))
        except (ValueError, TypeError):
            meta = {}
    texto = _RE_META.sub("", resposta or "")
    texto = re.sub(r"<<\s*META.*$", "", texto, flags=re.S)  # META truncado
    texto = texto.replace("**", "").strip()
    return texto, meta if isinstance(meta, dict) else {}


def subir_estagio(atual: Optional[str], novo: Optional[str]) -> str:
    """O estágio só avança no funil."""
    a = ESTAGIOS.index(atual) if atual in ESTAGIOS else 0
    n = ESTAGIOS.index(novo) if novo in ESTAGIOS else 0
    return ESTAGIOS[max(a, n)]


def avaliar(conversa: dict, texto_cliente: str, meta: dict) -> dict:
    """Combina META da IA + heurísticas. Devolve os campos a gravar na conversa."""
    sinais = detectar_sinais(texto_cliente)
    assuntos = set(conversa.get("assuntos") or [])
    assuntos.update(detectar_assuntos(texto_cliente))
    assuntos.update(a for a in (meta.get("assuntos") or []) if a in ASSUNTOS)

    estagio = conversa.get("estagio") or "curioso"
    if sinais["preco"] or "teste" in assuntos or "planos" in assuntos:
        estagio = subir_estagio(estagio, "interessado")
    if (conversa.get("n_msgs_cliente") or 0) >= 4:
        estagio = subir_estagio(estagio, "interessado")
    if sinais["compra"] or sinais["humano"]:
        estagio = subir_estagio(estagio, "qualificado")
    if meta.get("estagio") in ("curioso", "interessado", "qualificado"):
        estagio = subir_estagio(estagio, meta["estagio"])

    perfil = conversa.get("perfil") or "indefinido"
    novo_perfil = sinais["perfil"] or (meta.get("perfil") if meta.get("perfil") in PERFIS else None)
    if novo_perfil and novo_perfil != "indefinido":
        perfil = novo_perfil

    contato = extrair_contato(texto_cliente)
    for k in ("nome", "whatsapp", "email"):
        v = meta.get(k)
        if v and k not in contato:
            if k == "whatsapp":
                v = normalizar_fone(str(v))
            if v:
                contato[k] = str(v).strip()[:120]

    pediu_humano = bool(conversa.get("pediu_humano")) or sinais["humano"]
    tem_contato = bool(contato.get("whatsapp") or conversa.get("whatsapp")
                       or contato.get("email") or conversa.get("email"))
    pedir_contato = (estagio == "qualificado" and not tem_contato) or bool(meta.get("pedir_contato") and not tem_contato)
    return {
        "estagio": estagio,
        "perfil": perfil,
        "assuntos": sorted(assuntos),
        "contato": contato,
        "pediu_humano": pediu_humano,
        "pedir_contato": pedir_contato,
    }


def deve_encaminhar(conversa: dict) -> bool:
    """Avisar o dono: qualificado (ou pediu pessoa) E deixou como ser contatado,
    uma única vez por conversa."""
    if conversa.get("notificado_em"):
        return False
    quente = conversa.get("estagio") in ("qualificado", "convertido") or conversa.get("pediu_humano")
    return bool(quente and (conversa.get("whatsapp") or conversa.get("email")))


def link_cadastro(sessao_id: str = "") -> str:
    return f"{SITE}/cadastro?utm_source=site&utm_medium=robo&utm_campaign=atendimento"


def acoes(conversa: dict) -> list:
    """Botões mostrados abaixo da resposta."""
    estagio = conversa.get("estagio") or "curioso"
    perfil = conversa.get("perfil") or "indefinido"
    assuntos = set(conversa.get("assuntos") or [])
    out = []
    if perfil != "cliente_servico" and (estagio != "curioso" or assuntos & {"planos", "teste", "plataforma"}):
        out.append({"tipo": "cadastro", "label": f"Testar {TRIAL_DIAS} dias grátis", "url": "/cadastro?utm_source=site&utm_medium=robo&utm_campaign=atendimento"})
    if "planos" in assuntos:
        out.append({"tipo": "planos", "label": "Ver planos", "url": "/planos"})
    if estagio == "qualificado" or conversa.get("pediu_humano") or perfil == "cliente_servico":
        out.append({"tipo": "whatsapp", "label": "Falar com o José no WhatsApp",
                    "url": f"https://wa.me/{WHATSAPP_ROMATEC}?text=" + "Ol%C3%A1%2C%20vim%20pelo%20site%20do%20AvalieImob"})
    return out


# ── Respostas sem IA (nenhum provedor disponível) ────────────────────────────
_OFFLINE = {
    "planos": "Os planos do AvalieImob:\n" + "\n".join(f"• {n}: {p}" for n, p, _ in PLANOS)
              + f"\nE dá para testar {TRIAL_DIAS} dias grátis, sem cartão. Você é corretor/avaliador?",
    "teste": f"O teste é grátis por {TRIAL_DIAS} dias: cria a conta em {SITE}/cadastro e entra na hora, "
             "sem cartão e sem cobrança automática. Quer o link?",
    "ptam": "O PTAM (Parecer Técnico de Avaliação Mercadológica) sai em etapas guiadas, conforme a "
            "NBR 14653: dados do imóvel com mapa, vistoria com fotos GPS, amostras de mercado, "
            "homogeneização, cálculo e conclusão — em PDF/Word, com assinatura ICP-Brasil e link "
            "para o cliente. Você emite laudos ou precisa de um laudo pronto?",
    "laudo": "Fazemos laudos e o sistema emite laudos técnicos com tratamento por fatores ou "
             "inferência estatística (até Grau III, NBR 14653). Você é avaliador ou precisa do laudo?",
    "pericia": "Para perícia judicial, desapropriação e servidão o AvalieImob tem o Tratamento "
               "Científico (regressão, testes estatísticos e enquadramento até Grau III). "
               "Precisa do serviço ou quer usar a ferramenta?",
    "inferencia": "A inferência estatística faz regressão sobre a amostra, testa os pressupostos "
                  "(normalidade, homocedasticidade, Durbin-Watson, VIF) e gera os gráficos e o "
                  "grau de fundamentação/precisão automaticamente. Quer testar?",
    "georref": "No georreferenciamento rural (SIGEF/INCRA) o sistema lê o memorial, o CCIR e a "
               "matrícula e gera requerimento ao cartório, laudo, memorial, DRL dos confrontantes, "
               "shapefile e o dossiê completo. Você faz georreferenciamento ou precisa do serviço?",
    "geo_urbano": "No Geo Urbano saem remembramento, desdobro, retificação de área, usucapião "
                  "extrajudicial e REURB: requerimentos, memoriais, croqui e dossiê, com o proprietário "
                  "assinando pelo WhatsApp. É para o seu escritório ou para um imóvel seu?",
    "usucapiao": "A usucapião extrajudicial (art. 216-A da Lei 6.015/73) sai completa: requerimento, "
                 "ata notarial, edital, anuência dos confrontantes, planta e memorial. Quer que o José "
                 "veja o seu caso? Me passa seu nome e WhatsApp.",
    "onr": "O Arquivo ONR (Provimento CNJ 195/2025): você sobe mapa, memorial, ART e certidão; o "
           "sistema extrai os vértices, valida e gera o shapefile pronto para o mapa.onr.org.br, "
           "além da descrição do polígono. Quer testar?",
    "contratos": "São 15 tipos de contrato com cláusulas geradas pela IA. O cliente assina pelo "
                 "WhatsApp (nome + CPF ou desenho) e você sela com ICP-Brasil. Quer testar?",
}


def resposta_offline(assuntos: list, estagio: str) -> str:
    if estagio == "qualificado":
        return ("Perfeito! Para o José te atender pessoalmente, me passa seu nome e WhatsApp? "
                f"Se for usar a plataforma, já pode criar a conta grátis em {SITE}/cadastro.")
    for a in assuntos:
        if a in _OFFLINE:
            return _OFFLINE[a]
    return ("Sou a Roma_IA, atendente do AvalieImob. A plataforma emite PTAM e laudos (NBR 14653), "
            "contratos com assinatura pelo WhatsApp, georreferenciamento, usucapião e o arquivo ONR. "
            "Você é profissional da área ou precisa de um serviço?")
