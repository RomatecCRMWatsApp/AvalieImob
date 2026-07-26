# @module models.onr_sigri — Arquivo ONR (SIG-RI) STANDALONE.
#
# Módulo SEPARADO dos procedimentos do Geo Urbano. O RT sobe o MAPA + MEMORIAL +
# ART/TRT + CERTIDÃO já prontos; o sistema extrai a poligonal do memorial e gera
# o pacote shapefile SIG-RI. Coleção própria: onr_sigri_jobs.
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


def _uid() -> str:
    return str(uuid.uuid4())


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class OnrJob(BaseModel):
    id: str = Field(default_factory=_uid)
    user_id: str = ""
    numero: Optional[str] = None                # ONR-AAAA-NNNN
    nome: str = ""                              # denominação/identificação livre
    status: str = "rascunho"                    # rascunho|extraido|validado|gerado
    # Natureza do ato → vira NAT_ATO no DBF (schema_onr faz upper())
    natureza: str = "georreferenciamento"
    # Identificação do imóvel (extraída do memorial / editável)
    denominacao_imovel: Optional[str] = None
    municipio: Optional[str] = "Açailândia"
    uf: Optional[str] = "MA"
    bairro: Optional[str] = None
    loteamento: Optional[str] = None
    quadra: Optional[str] = None
    lote_resultante: Optional[str] = None
    endereco: Optional[str] = None
    numero_imovel: Optional[str] = None
    cep: Optional[str] = None
    unidade: Optional[str] = None
    codigo_ibge: Optional[str] = "2100055"      # Açailândia/MA
    cib: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    zoneamento: Optional[str] = None
    precisao_posicional_m: Optional[float] = 0.10
    data_levantamento: Optional[str] = None
    area_declarada_m2: Optional[float] = None
    perimetro_m: Optional[float] = None
    fuso: Optional[int] = None
    hemisferio: Optional[str] = None
    trt_numero: Optional[str] = None
    obs_onr: Optional[str] = None
    # Coleções extraídas / editáveis
    vertices: List[dict] = Field(default_factory=list)
    matriculas: List[dict] = Field(default_factory=list)
    partes: List[dict] = Field(default_factory=list)       # proprietários
    confrontantes: List[dict] = Field(default_factory=list)
    cartorio: dict = Field(default_factory=dict)           # {nome, cns, comarca}
    responsavel_tecnico: dict = Field(default_factory=lambda: {
        "nome": "José Romário Pinto Bezerra",
        "formacao": "Técnico em Agrimensura",
        "conselho": "CFT/MA 01209185369",
        "credenciamento_incra": "FQNS",
    })
    # Uploads (R2) + validação
    uploads: dict = Field(default_factory=dict)            # {mapa|memorial|art_trt|certidao: [{...}]}
    onr_justificativas: List[dict] = Field(default_factory=list)
    onr_validacao: dict = Field(default_factory=dict)
    # Auditoria
    extracao_em: Optional[str] = None
    extracao_por: Optional[str] = None
    extracao_confianca: Optional[float] = None
    extracao_avisos: List[str] = Field(default_factory=list)
    campos_editados: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora)


class CriarOnrBody(BaseModel):
    nome: str
    natureza: str = "georreferenciamento"
    municipio: Optional[str] = "Açailândia"
    uf: Optional[str] = "MA"


class AtualizarOnrBody(BaseModel):
    """Atualização parcial — só campos enviados são gravados (exclude_unset)."""
    nome: Optional[str] = None
    status: Optional[str] = None
    natureza: Optional[str] = None
    denominacao_imovel: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    bairro: Optional[str] = None
    loteamento: Optional[str] = None
    quadra: Optional[str] = None
    lote_resultante: Optional[str] = None
    endereco: Optional[str] = None
    numero_imovel: Optional[str] = None
    cep: Optional[str] = None
    unidade: Optional[str] = None
    codigo_ibge: Optional[str] = None
    cib: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    zoneamento: Optional[str] = None
    precisao_posicional_m: Optional[float] = None
    data_levantamento: Optional[str] = None
    area_declarada_m2: Optional[float] = None
    perimetro_m: Optional[float] = None
    fuso: Optional[int] = None
    hemisferio: Optional[str] = None
    trt_numero: Optional[str] = None
    obs_onr: Optional[str] = None
    vertices: Optional[List[dict]] = None
    matriculas: Optional[List[dict]] = None
    partes: Optional[List[dict]] = None
    confrontantes: Optional[List[dict]] = None
    cartorio: Optional[dict] = None
    responsavel_tecnico: Optional[dict] = None


class JustificarOnrBody(BaseModel):
    codigo: str
    texto: str
