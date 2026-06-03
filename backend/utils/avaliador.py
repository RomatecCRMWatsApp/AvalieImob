# @module utils.avaliador — Fonte ÚNICA dos dados do avaliador para os laudos.
# BUG-04: assinatura e Currículo (Anexo IV) devem vir do perfil cadastrado,
#         nunca de valores hardcoded.
# BUG-05: normalização/formatação consistente de CPF/CNPJ (fonte única).
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ── CPF / CNPJ ─────────────────────────────────────────────────────────────
def so_digitos(doc: Any) -> str:
    return "".join(c for c in str(doc or "") if c.isdigit())


def formata_doc(doc: Any) -> str:
    """Aplica máscara de CPF (11 díg.) ou CNPJ (14 díg.). Caso contrário, retorna como veio."""
    d = so_digitos(doc)
    if len(d) == 11:
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    if len(d) == 14:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    return str(doc or "")


# ── Registros profissionais ────────────────────────────────────────────────
def _fmt_numero_registro(numero: Any, milhar: bool) -> str:
    """Formata número de registro. milhar=True insere separador de milhar (ex.: 4705 -> 4.705)."""
    s = str(numero or "").strip()
    if milhar and s.isdigit() and len(s) > 3:
        return f"{int(s):,}".replace(",", ".")
    return s


def _coletar_registros(perfil: Dict[str, Any]) -> Dict[str, str]:
    """
    Lê perfil['registros'] (lista de {tipo, numero, uf, ...}) e devolve strings
    prontas por tipo. Chaves: cnai, creci, crea, cau, cft, incra, outros(list).
    """
    out: Dict[str, Any] = {"cnai": "", "creci": "", "crea": "", "cau": "",
                           "cft": "", "incra": "", "outros": []}
    for r in (perfil.get("registros") or []):
        if not isinstance(r, dict):
            continue
        tipo = str(r.get("tipo") or "").strip().upper()
        numero = str(r.get("numero") or "").strip()
        uf = str(r.get("uf") or "").strip().upper()
        if not numero:
            continue
        if "CNAI" in tipo:
            out["cnai"] = f"CNAI {numero}"
        elif "CRECI" in tipo:
            out["creci"] = f"CRECI/{uf} {_fmt_numero_registro(numero, True)}" if uf \
                else f"CRECI {_fmt_numero_registro(numero, True)}"
        elif "CREA" in tipo:
            out["crea"] = f"CREA/{uf} {numero}" if uf else f"CREA {numero}"
        elif "CAU" in tipo:
            out["cau"] = f"CAU/{uf} {numero}" if uf else f"CAU {numero}"
        elif "CFT" in tipo or "AGRIMENS" in tipo:
            out["cft"] = f"CFT/{uf} {numero}" if uf else f"CFT {numero}"
        elif "INCRA" in tipo:
            out["incra"] = f"INCRA {numero}"
        else:
            label = tipo.title() if tipo else "Registro"
            out["outros"].append(f"{label}/{uf} {numero}" if uf else f"{label} {numero}")
    return out


# ── Resolução principal ────────────────────────────────────────────────────
def resolver_dados_avaliador(
    perfil: Optional[Dict[str, Any]] = None,
    user: Optional[Dict[str, Any]] = None,
    ptam: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fonte única dos dados do avaliador para assinatura + Currículo.
    Prioridade: perfil cadastrado > campos do laudo (ptam) > usuário logado.
    Nunca usa valores hardcoded.
    """
    perfil = perfil or {}
    user = user or {}
    ptam = ptam or {}

    reg = _coletar_registros(perfil)

    nome = (perfil.get("nome_completo") or ptam.get("responsavel_nome")
            or user.get("name") or "").strip()

    # Registros: perfil é fonte primária; cai para campos do laudo se perfil vazio.
    cnai = reg["cnai"] or (f"CNAI {ptam['responsavel_cnai']}" if ptam.get("responsavel_cnai") else "")
    creci = reg["creci"] or (ptam.get("responsavel_creci") or user.get("crea") or "")
    art_trt = (ptam.get("art_rrt_numero") or ptam.get("art_trt_numero") or "").strip()

    # Lista pronta de registros para a assinatura (sem vazios, sem duplicar).
    linha_registros: List[str] = []
    for v in [creci, cnai, reg["crea"], reg["cau"], reg["cft"], reg["incra"], *reg["outros"]]:
        if v and v not in linha_registros:
            linha_registros.append(v)

    site = perfil.get("site") or ""
    endereco = perfil.get("endereco_escritorio") or ""
    cidade_uf = ", ".join([p for p in [perfil.get("cidade"), perfil.get("uf")] if p])
    if perfil.get("cep"):
        endereco = ", ".join([p for p in [endereco, cidade_uf, f"CEP {perfil['cep']}"] if p])
    elif cidade_uf:
        endereco = ", ".join([p for p in [endereco, cidade_uf] if p])

    # perfil_completo reflete o CADASTRO do perfil (não o fallback do laudo),
    # para acionar o aviso "Complete seu perfil" no dashboard.
    perfil_completo = bool(perfil.get("nome_completo") and (perfil.get("registros") or []))

    return {
        "nome": nome,
        "cargo": (perfil.get("bio_resumo") or "").strip(),
        "cnai": cnai,
        "creci": creci,
        "crea": reg["crea"],
        "cau": reg["cau"],
        "cft": reg["cft"],
        "incra": reg["incra"],
        "art_trt": art_trt,
        "registros_linhas": linha_registros,
        "telefone": perfil.get("telefone") or "",
        "email": perfil.get("email_profissional") or "",
        "site": site,
        "endereco": endereco,
        "cpf": formata_doc(perfil.get("cpf")) if perfil.get("cpf") else "",
        # Blocos do Currículo (Anexo IV)
        "formacoes": perfil.get("formacoes") or [],
        "experiencias": perfil.get("experiencias") or [],
        "especializacoes": perfil.get("especializacoes") or [],
        "habilitacoes": perfil.get("habilitacoes") or [],
        "tribunais": perfil.get("tribunais_cadastrado") or [],
        "bancos": perfil.get("bancos_habilitado") or [],
        "areas_atuacao": perfil.get("areas_atuacao") or [],
        "associacoes": perfil.get("membro_associacoes") or [],
        "bio_resumo": perfil.get("bio_resumo") or "",
        "perfil_completo": perfil_completo,
    }


def cpf_solicitante(ptam: Dict[str, Any]) -> str:
    """BUG-05: CPF do solicitante de FONTE ÚNICA (solicitante_cpf_cnpj), formatado."""
    ptam = ptam or {}
    return formata_doc(ptam.get("solicitante_cpf_cnpj") or ptam.get("solicitante_cpf") or "")
