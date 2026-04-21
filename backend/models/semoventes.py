# @module models.semoventes — Modelos Pydantic para Semoventes (Penhor Rural Bancário)
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.common import _id, _now


class CategoriaSemovente(BaseModel):
    categoria: str = ""
    quantidade: int = 0
    raca: str = ""
    faixa_etaria: str = ""
    peso_medio_kg: float = 0
    registro_genealogico: str = ""
    valor_unitario: float = 0
    valor_total: float = 0
    taxa_prenhez: Optional[float] = None
    producao_leite: Optional[float] = None
    arrobas_estimadas: Optional[float] = None
    estagio: Optional[str] = None
    aptidao: Optional[str] = None
    fase: Optional[str] = None


class SemoventeBase(BaseModel):
    # Identificacao
    numero_laudo: Optional[str] = ""
    tipo_semovente: str = "bovino"
    status: str = "rascunho"

    # Operacao bancaria
    instituicao_financeira: Optional[str] = ""
    modalidade_credito: Optional[str] = "credito_rural_livre"
    valor_credito: Optional[float] = 0
    devedor_nome: Optional[str] = ""
    devedor_cpf_cnpj: Optional[str] = ""

    # Propriedade
    propriedade_nome: Optional[str] = ""
    propriedade_municipio: Optional[str] = ""
    propriedade_uf: Optional[str] = ""
    matricula_imovel: Optional[str] = ""
    cri_cartorio: Optional[str] = ""

    # Rebanho
    categorias: List[CategoriaSemovente] = Field(default_factory=list)
    total_cabecas: Optional[int] = 0
    total_ua: Optional[float] = 0
    lotacao_ua_ha: Optional[float] = 0

    # Rastreabilidade
    brincos_sisbov: Optional[bool] = False
    brinco_inicio: Optional[str] = ""
    brinco_fim: Optional[str] = ""
    marcacao_ferro: Optional[bool] = False
    marcacao_descricao: Optional[str] = ""
    microchip: Optional[bool] = False
    situacao_esisbov: Optional[str] = ""

    # Situacao sanitaria
    vacina_aftosa_data: Optional[str] = ""
    vacina_aftosa_orgao: Optional[str] = ""
    vacina_brucelose_data: Optional[str] = ""
    teste_tuberculose: Optional[str] = "nao_realizado"
    teste_tuberculose_data: Optional[str] = ""
    vermifugacao_data: Optional[str] = ""
    vermifugacao_produto: Optional[str] = ""
    mortalidade_percentual: Optional[float] = 0
    area_livre_aftosa: Optional[bool] = False
    gta_em_dia: Optional[bool] = False

    # Infraestrutura
    capacidade_suporte_ua_ha: Optional[float] = 0
    disponibilidade_agua: Optional[str] = ""
    instalacoes: Optional[str] = ""
    estado_conservacao_instalacoes: Optional[str] = ""
    capacidade_confinamento: Optional[int] = 0

    # Avaliacao / cotacoes
    cotacao_arroba_data: Optional[str] = ""
    cotacao_arroba_valor: Optional[float] = 0
    cotacao_fonte: Optional[str] = ""
    cotacao_bezerro: Optional[float] = 0
    cotacao_vaca: Optional[float] = 0
    cotacao_touro_po: Optional[float] = 0
    valor_mercado_total: Optional[float] = 0
    fator_liquidez: Optional[float] = 0.65
    valor_garantia_aceito: Optional[float] = 0
    ltv_recomendado: Optional[float] = 65
    validade_laudo_meses: Optional[int] = 6
    seguro_recomendado_valor: Optional[float] = 0

    # Vistoria
    vistoria_data: Optional[str] = ""
    vistoria_horario: Optional[str] = ""
    contagem_fisica_presencial: Optional[bool] = False
    condicao_corporal_media: Optional[float] = 3.0
    fotos: List[str] = Field(default_factory=list)

    # Responsavel (CRMV obrigatorio para penhor rural)
    responsavel_nome: Optional[str] = ""
    crmv_numero: Optional[str] = ""
    crmv_uf: Optional[str] = ""
    especialidade: Optional[str] = ""
    art_crmv_numero: Optional[str] = ""
    art_data_registro: Optional[str] = ""

    # Declaracoes
    declaracao_contagem_presencial: Optional[bool] = False
    declaracao_sem_conflito: Optional[bool] = False
    declaracao_penhor_registrado: Optional[bool] = False
    restricoes_ressalvas: Optional[str] = ""


class Semovente(SemoventeBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
