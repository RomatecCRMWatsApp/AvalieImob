# @module models.nfse — Modelos do módulo de EMISSÃO de NFS-e (Padrão Nacional 2026).
# Fluxo: DPS (declaração) → transmissão (gateway OU Sefin) → NFS-e autorizada (chave 50).
# PR1 = FUNDAÇÃO (modelos + cálculo); NÃO transmite nada. Adaptado às convenções do repo
# (Pydantic v2, ids uuid str, contador via db.counters).
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


def _uid() -> str:
    return str(uuid.uuid4())


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ────────────────────────────────────────────────────────────────────
class Provider(str, Enum):
    gateway = "gateway"
    sefin_nacional = "sefin_nacional"
    abrasf = "abrasf"                  # webservice municipal padrão ABRASF (ex.: SpeedGov/Açailândia)


class Ambiente(str, Enum):
    homologacao = "homologacao"
    producao = "producao"


class StatusNFSe(str, Enum):
    pendente = "pendente"
    processando = "processando"
    autorizada = "autorizada"
    rejeitada = "rejeitada"
    cancelada = "cancelada"
    erro = "erro"


class TipoDocumento(str, Enum):
    cpf = "cpf"
    cnpj = "cnpj"
    estrangeiro = "estrangeiro"


# ── Sub-modelos de configuração ──────────────────────────────────────────────
class Endereco(BaseModel):
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cep: str = ""
    codigo_ibge: str = ""


class Emitente(BaseModel):
    razao_social: str
    nome_fantasia: str = ""
    cnpj: str
    inscricao_municipal: str = ""
    inscricao_estadual: str = "0"
    regime_tributario: str = "lucro_presumido"
    optante_simples: bool = False
    telefone: str = ""
    endereco: Endereco = Field(default_factory=Endereco)


class GatewayConfig(BaseModel):
    nome: str = "focus_nfe"            # focus_nfe|plugnotas|nstecnologia|enotas
    base_url: str = ""
    token_ref: str = ""                # NOME da env var (nunca o token em claro)
    extras: dict = Field(default_factory=dict)


class SefinConfig(BaseModel):
    # Sefin Nacional (recepção da DPS, mTLS). Homologação = "Produção Restrita".
    #   Homologação: https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional
    #   Produção:    https://sefin.nfse.gov.br/SefinNacional
    base_url_sefin: str = ""
    # ADN (consulta/distribuição/DANFSe). Homolog: https://adn.producaorestrita.nfse.gov.br
    base_url_adn: str = ""
    certificado_id: str = ""           # id do cert em db.certificados (e-CNPJ já cadastrado); senão usa o PJ ativo
    certificado_ref: str = ""          # alternativa: caminho/ref do .pfx (secret/arquivo)
    certificado_senha_ref: str = ""    # env var da senha (quando via arquivo)
    serie_dps: str = "1"
    # TRAVA DE SEGURANÇA: só transmite de verdade quando True (habilitar SÓ após validar
    # XSD + testar em HOMOLOGAÇÃO). Default False → emitir() monta/assina/empacota mas NÃO envia.
    transmissao_habilitada: bool = False
    # Rotas REST oficiais (Manual Contribuintes Emissor Público v1.2, out/2025):
    rota_emissao: str = "/nfse"        # POST /nfse — geração síncrona da NFS-e (recebe a DPS)
    rota_consulta: str = "/nfse"       # GET /nfse/{chaveAcesso} — consulta por chave


class AbrasfConfig(BaseModel):
    """Webservice municipal padrão ABRASF (SOAP). Ex.: SpeedGov — ISS Eletrônico de Açailândia.
    O RPS é assinado com o e-CNPJ (XMLDSIG). Login/senha é só do PORTAL; a API usa o certificado.
    """
    # CONFIRMADO no WSDL http://speedgov.com.br/wsmod/Nfes?wsdl (SpeedGov Açailândia):
    url_ws: str = "http://speedgov.com.br/wsmod/Nfes"   # endpoint de TESTE/homologação
    url_ws_producao: str = ""
    versao_abrasf: str = "1.00"        # ABRASF 1.0 (confirmado)
    namespace: str = "http://www.abrasf.org.br/nfse.xsd"                      # ns do EnviarLoteRpsEnvio (RPS)
    namespace_ws: str = "http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd"   # ns do wrapper da operação SOAP
    operacao_envio: str = "RecepcionarLoteRps"   # wrapper: <RecepcionarLoteRps><header/><parameters/></...>
    operacao_consulta: str = "ConsultarLoteRps"
    operacao_consulta_rps: str = "ConsultarNfsePorRps"
    operacao_cancela: str = "CancelarNfse"
    soap_action: str = ""              # WSDL: soapAction VAZIO
    assinar_rps: bool = False          # modelo oficial do SpeedGov é SEM assinatura (homologação)
    serie_rps: str = "1"
    tipo_rps: str = "1"                # 1=RPS
    certificado_id: str = ""           # cert em db.certificados; senão o PJ ativo
    assinatura_sha: str = "sha1"       # ABRASF 1.0 usa RSA-SHA1; 2.x pode ser sha256
    # TRAVA DE SEGURANÇA: nada transmite até validar contra o WSDL + homologação.
    transmissao_habilitada: bool = False


class TributosFederaisCfg(BaseModel):
    aliquota_pis: float = 0.0
    aliquota_cofins: float = 0.0
    aliquota_csll: float = 0.0
    aliquota_irrf: float = 0.0
    aliquota_inss: float = 0.0
    reter_federais: bool = False


class IbsCbs(BaseModel):
    incluir: bool = True               # transição RTC 2026 — sempre presente (zerado)
    valor_ibs_municipal: float = 0.0
    valor_ibs_estadual: float = 0.0
    valor_cbs: float = 0.0


class FiscalDefaults(BaseModel):
    item_lista_servico: str = "17.01"
    codigo_tributacao_municipal: str = ""
    codigo_tributacao_nacional: str = ""          # cTribNac (6 díg.); senão derivado do item
    codigo_nbs: str = "114039000"                 # cNBS padrão (engenharia) — CONFIRMAR por serviço
    descricao_atividade: str = ""
    cnae: str = ""
    aliquota_iss: float = 0.02
    iss_retido: bool = False
    natureza_operacao: str = "tributada_municipio"
    regime_especial_tributacao: str = "0"
    exigibilidade_iss: str = "1"
    tributos_federais: TributosFederaisCfg = Field(default_factory=TributosFederaisCfg)
    ibscbs: IbsCbs = Field(default_factory=IbsCbs)


class NFSeConfig(BaseModel):
    id: str = Field(default_factory=_uid)
    municipio_nome: str
    municipio_uf: str
    codigo_ibge: str
    provider: Provider = Provider.gateway
    ambiente: Ambiente = Ambiente.homologacao
    ativo: bool = True
    emitente: Emitente
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    sefin: SefinConfig = Field(default_factory=SefinConfig)
    abrasf: AbrasfConfig = Field(default_factory=AbrasfConfig)
    fiscal_defaults: FiscalDefaults = Field(default_factory=FiscalDefaults)
    template_danfse: str = "prime1"
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora)


# ── Documento da NFS-e ───────────────────────────────────────────────────────
class Origem(BaseModel):
    tipo: str                          # recibo_honorarios|ptam|servico_avulso
    ref_id: Optional[str] = None
    descricao: str = ""


class Tomador(BaseModel):
    tipo_documento: TipoDocumento = TipoDocumento.cpf
    documento: str = ""
    razao_nome: str = ""
    email: str = ""
    endereco: Optional[Endereco] = None


class TributosFederaisDoc(BaseModel):
    pis: float = 0.0
    cofins: float = 0.0
    inss: float = 0.0
    csll: float = 0.0
    irrf: float = 0.0
    retencoes_federais: float = 0.0


class Servico(BaseModel):
    discriminacao: str = ""
    item_lista_servico: str = "17.01"
    codigo_tributacao_nacional: str = ""   # cTribNac (6 díg.); se vazio, derivado do item
    codigo_tributacao_municipal: str = ""
    cnbs: str = ""                         # cNBS (9 díg., obrigatório na DPS Nacional)
    local_prestacao_ibge: str = ""
    valor_servico: float = 0.0
    valor_deducoes: float = 0.0
    desconto_incondicionado: float = 0.0
    desconto_condicionado: float = 0.0
    base_calculo: float = 0.0          # calculado
    aliquota_iss: float = 0.02
    valor_iss: float = 0.0             # calculado
    iss_retido: bool = False
    tributos_federais: TributosFederaisDoc = Field(default_factory=TributosFederaisDoc)
    ibscbs: IbsCbs = Field(default_factory=IbsCbs)
    valor_liquido: float = 0.0         # calculado


class DPS(BaseModel):
    serie: str = "1"
    numero: Optional[int] = None
    id_dps: Optional[str] = None
    data_emissao: Optional[datetime] = None


class Rejeicao(BaseModel):
    codigo: str = ""
    mensagem: str = ""


class Evento(BaseModel):
    tipo: str                          # cancelamento|substituicao
    motivo: str = ""
    data: datetime = Field(default_factory=_agora)
    protocolo: str = ""
    status: str = "registrado"


class NFSeDocumento(BaseModel):
    id: str = Field(default_factory=_uid)
    config_id: str
    provider: Provider = Provider.gateway
    ambiente: Ambiente = Ambiente.homologacao
    origem: Origem
    tomador: Tomador
    servico: Servico
    dps: DPS = Field(default_factory=DPS)
    status: StatusNFSe = StatusNFSe.pendente
    chave_acesso: Optional[str] = None
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    xml_autorizado_path: Optional[str] = None
    danfse_pdf_path: Optional[str] = None
    url_consulta_publica: Optional[str] = None
    rejeicao: Optional[Rejeicao] = None
    eventos: List[Evento] = Field(default_factory=list)
    tentativas: int = 0
    idempotency_key: str = Field(default_factory=_uid)
    template_danfse: str = "prime1"
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora)


# ── Resultados dos providers ─────────────────────────────────────────────────
class ResultadoEmissao(BaseModel):
    status: StatusNFSe
    chave_acesso: Optional[str] = None
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    xml_autorizado: Optional[Any] = None     # str|bytes
    danfse_pdf: Optional[bytes] = None
    url_consulta_publica: Optional[str] = None
    rejeicao: Optional[Rejeicao] = None


class ResultadoEvento(BaseModel):
    status: str
    protocolo: str = ""
    mensagem: str = ""


# ── Cálculo fiscal (mesma regra do DANFSe; fonte única de verdade fiscal) ─────
def calcular_valores(servico: Servico | dict) -> dict:
    """Calcula base, valor_iss e valor_liquido a partir do serviço. Aceita Servico ou dict."""
    s = servico.model_dump() if isinstance(servico, Servico) else dict(servico or {})

    def f(k):
        try:
            return float(s.get(k) or 0)
        except (TypeError, ValueError):
            return 0.0

    valor = f("valor_servico")
    deducao = f("valor_deducoes")
    desc_inc = f("desconto_incondicionado")
    desc_cond = f("desconto_condicionado")
    aliq = f("aliquota_iss")
    pct = aliq * 100 if 0 < aliq <= 1 else aliq          # aceita 0.02 OU 2.0

    trib = s.get("tributos_federais") or {}
    ret_fed = float(trib.get("retencoes_federais") or 0)
    base = round(valor - deducao - desc_inc, 2)
    valor_iss = round(base * pct / 100, 2)
    iss_retido_v = valor_iss if s.get("iss_retido") else 0.0
    liquido = round(valor - desc_inc - desc_cond - ret_fed - iss_retido_v, 2)
    return {"base_calculo": base, "valor_iss": valor_iss, "valor_liquido": liquido}
