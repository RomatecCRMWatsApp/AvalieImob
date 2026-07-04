# @module services.nfse.danfse_import — Importa uma NFS-e JÁ EXPEDIDA (PDF) → doc FLAT do DANFSe.
"""Lê o PDF de uma NFS-e emitida (layout SpeedGov/ABRASF — Açailândia/MA) e extrai TODOS
os dados para o documento FLAT usado pelo gerador de DANFSe (pdf.templates.danfse_base).

Objetivo: o usuário sobe a nota já emitida no portal, o sistema extrai o conteúdo idêntico
ao original e permite RE-TEMATIZAR (Prime I/II/Tradicional) para exportar/enviar/baixar —
até que a emissão direta pelo sistema esteja liberada.

O texto do PDF é lido com pdfplumber (SpeedGov emite com camada de texto). A extração é por
regex ancorada nos rótulos do template; os rótulos usam `.` no lugar de letras acentuadas
para tolerar variações de codificação. Valores monetários ficam como string pt-BR
("8.500,00") — o gerador recalcula base/ISS/líquido a partir deles.
"""
from __future__ import annotations

import io
import re

# Rótulos de seção que delimitam os blocos do PDF (âncoras de escopo).
_SEC_PRESTADOR = re.compile(r"DADOS DO PRESTADOR", re.I)
_SEC_TOMADOR = re.compile(r"DADOS DO TOMADOR", re.I)
_SEC_CODIGO = re.compile(r"C.DIGO DA ATIVIDADE", re.I)
_SEC_TRIBUTOS = re.compile(r"TRIBUTOS FEDERAIS", re.I)


class ImportacaoNFSeError(ValueError):
    """PDF ilegível ou fora do layout de NFS-e suportado."""


def extrair_texto_pdf(data: bytes) -> str:
    """Concatena o texto de todas as páginas do PDF (camada de texto)."""
    import pdfplumber

    partes: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pg in pdf.pages:
                t = pg.extract_text() or ""
                if t:
                    partes.append(t)
    except ImportacaoNFSeError:
        raise
    except Exception as e:  # noqa: BLE001  (PDF corrompido / não-PDF)
        raise ImportacaoNFSeError(
            "Arquivo inválido: envie o PDF da NFS-e emitida.") from e
    return "\n".join(partes)


def _g(pattern: str, texto: str, grupo: int = 1, flags: int = re.I) -> str:
    m = re.search(pattern, texto, flags)
    return (m.group(grupo) or "").strip() if m else ""


def _digitos(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def _bloco(texto: str, ini: re.Pattern, fim: re.Pattern | None) -> str:
    """Recorta o texto entre o rótulo `ini` e o rótulo `fim` (ou o fim do texto)."""
    m0 = ini.search(texto)
    if not m0:
        return ""
    resto = texto[m0.end():]
    if fim:
        m1 = fim.search(resto)
        if m1:
            return resto[: m1.start()]
    return resto


def _num_ou_zero(v: str) -> str:
    v = (v or "").strip()
    return v if v else "0,00"


def parse_nfse_pdf(data: bytes) -> dict:
    """PDF (bytes) → dict com {doc: FLAT, avisos: [str], texto: str}."""
    texto = extrair_texto_pdf(data)
    if len(texto.strip()) < 60:
        raise ImportacaoNFSeError(
            "Não foi possível ler o texto do PDF. Envie o PDF original da NFS-e "
            "(gerado pelo portal), não uma imagem/escaneado.")

    avisos: list[str] = []
    linhas = [ln for ln in texto.splitlines()]

    prestador = _bloco(texto, _SEC_PRESTADOR, _SEC_TOMADOR)
    tomador = _bloco(texto, _SEC_TOMADOR, None)
    # o bloco do tomador vai até a discriminação; recorto o excedente
    tomador_head = tomador
    m_disc = _SEC_CODIGO.search(tomador)
    if m_disc:
        tomador_head = tomador[: m_disc.start()]

    # ── Cabeçalho / identificação ────────────────────────────────────────────
    # numero: primeiro run de 6-12 dígitos ANTES da "Chave de Acesso"
    antes_chave = texto.split("Chave de Acesso")[0]
    numero = _g(r"\b(\d{6,12})\b", antes_chave)
    serie = _g(r"S.RIE\s*\n?\s*([A-Za-zÀ-ÿ]+)", texto) or "ELETRÔNICA"

    doc: dict = {
        "numero_nfse": numero or "0000000000",
        "serie": serie.upper() if serie else "ELETRÔNICA",
        "estado": _g(r"(ESTADO DO [A-ZÀ-ÿ ]+?)\s+Nota", texto) or "Estado do Maranhão",
        "prefeitura": "Prefeitura Municipal de Açailândia",
        "secretaria": "Secretaria de Economia e Finanças",
        "data_geracao": _g(r"Data de Gera..o\s+(\d{2}/\d{2}/\d{4})", texto),
        "competencia": _g(r"Compet.ncia\s+([A-Z]{3}/\d{4})", texto),
        "numero_rps": _g(r"N.\s*do RPS\s+(\d+)", texto) or "0",
        "dps_substituida": _g(r"DPS Substitu.da\s+(\d+)", texto) or "0",
        "local_prestacao": _g(r"Local da Presta..o\s+([^\n]+?)\s+Optante", texto)
        or _g(r"Local da Presta..o\s+(\S+)", texto),
        "optante_simples": _g(r"Optante do Simples\s+(\S+)", texto) or "NÃO",
        "regime_esp": _g(r"Regime Especial de Tributa..o\s+(\S[^\n]*)", texto) or "0-Nenhum",
        "chave_acesso": _g(r"Chave de Acesso\s+(\d{30,})", texto),

        # ── Prestador (escopo prestador) ─────────────────────────────────────
        "prest_razao": _g(r"Raz.o Social\s+([^\n]+)", prestador),
        "prest_fantasia": _g(r"Nome Fantasia\s*([^\n]+)", prestador),
        "prest_endereco": _g(r"Endere.o\s+([^\n]+)", prestador),
        "prest_cnpj": _digitos(_g(r"CPF/CNPJ\s+([\d./\-]+)", prestador)),
        "prest_im": _g(r"Insc\.?\s*Municipal\s+(\d+)", prestador),
        "prest_uf": _g(r"\bUF\s+([A-Z]{2})\b", prestador),
        "prest_ie": _g(r"Insc\.?\s*Estadual\s+(\d+)", prestador) or "0",
        "prest_cidade": _g(r"Cidade\s+([^\n]+?)\s+C\.?E\.?P", prestador),
        "prest_cep": _digitos(_g(r"C\.?E\.?P\s+(\d+)", prestador)),
        "prest_fone": _digitos(_g(r"Telefone\s*(\d[\d\s\-()]*)", prestador)),

        # ── Tomador (escopo tomador) ─────────────────────────────────────────
        "tom_razao": _g(r"Raz.o Social\s+([^\n]+?)\s+E-?mail", tomador_head)
        or _g(r"Raz.o Social\s+([^\n]+)", tomador_head),
        "tom_email": _g(r"E-?mail\s+(\S+@\S+)", tomador_head),
        "tom_endereco": _g(r"Endere.o\s+([^\n]+)", tomador_head),
        "tom_cnpj": _digitos(_g(r"CPF/CNPJ\s+([\d./\-]+)", tomador_head)),
        "tom_im": _g(r"Insc\.?\s*Municipal\s+(\d+)", tomador_head) or "0",
        "tom_fone": _digitos(_g(r"Telefone\s*(\d[\d\s\-()]*)", tomador_head)),
    }

    # complemento do prestador (Comp. QUADRA 104) → anexa ao endereço se ainda não estiver
    comp = _g(r"Comp\.\s+([^\n]+?)\s+Telefone", prestador)
    if comp and comp not in doc["prest_endereco"]:
        doc["prest_endereco"] = f"{doc['prest_endereco']} - {comp}".strip(" -")

    # ── Discriminação (entre o CPF do tomador e "CODIGO DA ATIVIDADE") ────────
    doc["discriminacao"] = _extrair_discriminacao(linhas)

    # ── Código da atividade/serviço (linha logo após o rótulo) ───────────────
    doc["cod_atividade"] = _linha_apos(linhas, _SEC_CODIGO)

    # ── Tributos federais (quase sempre zerados) ─────────────────────────────
    bl_trib = _bloco(texto, _SEC_TRIBUTOS, re.compile(r"VALORES DO PRESTADOR", re.I))
    doc.update({
        "tipo_ret": "Não Retido" if re.search(r"N.o Re", bl_trib) else
        (_g(r"Tipo Reten..o\s+([^\n]+?)\s+Aliq", bl_trib) or "Não Retido"),
        "aliq_pis": _num_ou_zero(_g(r"Aliq\.?\s*PIS\s+([\d.,]+)", bl_trib)),
        "pis": _num_ou_zero(_g(r"\bPIS\s+([\d.,]+)\s+Aliq", bl_trib) or _g(r"\bPIS\s+([\d.,]+)", bl_trib)),
        "aliq_cofins": _num_ou_zero(_g(r"Aliq\.?\s*COFINS\s+([\d.,]+)", bl_trib)),
        "cofins": _num_ou_zero(_g(r"COFINS\s+([\d.,]+)", bl_trib)),
        "inss": _num_ou_zero(_g(r"INSS\s+([\d.,]+)", bl_trib)),
        "csll": _num_ou_zero(_g(r"CSLL\s+([\d.,]+)", bl_trib)),
        "irrf": _num_ou_zero(_g(r"IRRF\s+([\d.,]+)", bl_trib)),
    })

    # ── Valores / operação / ISS (rótulos inline no texto) ───────────────────
    doc.update({
        "valor_servico": _num_ou_zero(_g(r"Valor dos Servi.os\s+([\d.,]+)", texto)),
        "deducao": _num_ou_zero(_g(r"Dedu..o permitida em lei\s+([\d.,]+)", texto)),
        "desc_incond": _num_ou_zero(_g(r"\(-\)\s*Desconto Incondicionado\s+([\d.,]+)", texto)),
        "desc_cond": _num_ou_zero(_g(r"\(-\)\s*Desconto condicionado\s+([\d.,]+)", texto)),
        "ret_fed": _num_ou_zero(_g(r"\(-\)\s*Reten..es Federais\s+([\d.,]+)", texto)),
        "outras_ret": _num_ou_zero(_g(r"Outras Reten..es\s+([\d.,]+)", texto)),
        "iss_retido_v": _num_ou_zero(_g(r"\(-\)\s*ISS Retido\s+([\d.,]+)", texto)),
        "aliquota_iss": _g(r"Aliquota do ISS\s+([\d.,]+)", texto) or "0",
        "natureza": _g(r"(Tributada[^\n(]*)", texto) or "Tributada no Município",
        # código alfanumérico do SpeedGov (contém letras) — o lookahead evita casar a chave (só dígitos)
        "cod_validacao": _g(r"\b((?=[a-z0-9]*[a-z])[a-z0-9]{20,})\b", texto),
        "link_consulta": _g(r"(https?://\S+)", texto),
        "iss_a_reter": "Sim" if re.search(r"\(X\)\s*Sim", texto) else "Não",
        "ibs_mun": _num_ou_zero(_g(r"IBS Municipal R\$\s+([\d.,]+)", texto)),
        "ibs_est": _num_ou_zero(_g(r"IBS Estadual R\$\s+([\d.,]+)", texto)),
        "cbs": _num_ou_zero(_g(r"CBS R\$\s+([\d.,]+)", texto)),
    })

    # ── Construção civil + rodapé ────────────────────────────────────────────
    doc.update({
        "cno": _g(r"C.DIGO CNO/CEI[^\n]*\n\s*([0-9./\-]+)\b", texto),
        "iptu": "",
        "end_obra": "",
        "outras_info": "",
        "impressa_em": _g(r"Impressa em:\s+([\d/]+\s+[\d:]+)", texto),
        "hora_emissao": _g(r"Hora da emiss.o:\s+([\d:]+)", texto),
    })

    # ── Sanidade + avisos p/ o usuário ───────────────────────────────────────
    if not doc["numero_nfse"] or doc["numero_nfse"] == "0000000000":
        avisos.append("Número da nota não localizado — confira o campo 'Nota Nº'.")
    if not doc["prest_razao"]:
        avisos.append("Razão social do prestador não localizada.")
    if not doc["valor_servico"] or doc["valor_servico"] == "0,00":
        avisos.append("Valor dos serviços não localizado — confira antes de gerar.")

    return {"doc": doc, "avisos": avisos, "texto": texto}


def _linha_apos(linhas: list[str], rotulo: re.Pattern) -> str:
    """Retorna a primeira linha NÃO vazia após a linha que casa `rotulo`."""
    for i, ln in enumerate(linhas):
        if rotulo.search(ln):
            for j in range(i + 1, len(linhas)):
                if linhas[j].strip():
                    return linhas[j].strip()
    return ""


def _extrair_discriminacao(linhas: list[str]) -> str:
    """Junta as linhas entre o CPF/CNPJ do tomador e 'CODIGO DA ATIVIDADE'."""
    # localiza a última linha do bloco do tomador (a que tem o CPF/CNPJ do tomador)
    i_tom = next((i for i, ln in enumerate(linhas) if _SEC_TOMADOR.search(ln)), None)
    if i_tom is None:
        return ""
    i_ini = None
    for j in range(i_tom + 1, len(linhas)):
        if re.search(r"CPF/CNPJ", linhas[j], re.I):
            i_ini = j + 1
            break
    if i_ini is None:
        return ""
    corpo: list[str] = []
    for k in range(i_ini, len(linhas)):
        if _SEC_CODIGO.search(linhas[k]):
            break
        if linhas[k].strip():
            corpo.append(linhas[k].strip())
    return " ".join(corpo).strip()
