# @module models — Re-exporta todos os modelos Pydantic para compatibilidade com imports legados
from models.common import _id, _now
from models.user import (
    UserRegister, UserLogin, User, UserPublic, AuthResponse, UserUpdate,
    CreateTestUserRequest, AdminUserOut,
)
from models.ptam import (
    PtamSample, PtamImpactArea, PtamMarketSample, PtamBase, Ptam,
    PtamVersion, PtamVersionDiff,
    AIMessage, AIMessageResponse, AIHistoryItem,
    Transaction, CreatePreferenceRequest,
    PerfilAvaliadorBase, PerfilAvaliador,
    RegistroProfissional, Formacao, Experiencia,
)
from models.locacao import LocacaoAmostra, LocacaoBase, Locacao
from models.garantias import (
    GarantiaSolicitante, GarantiaResponsavel, GarantiaBase, Garantia,
)
from models.semoventes import CategoriaSemovente, SemoventeBase, Semovente
from models.clients import ClientBase, Client, PropertyBase, Property, SampleBase, Sample, EvaluationBase, Evaluation
from models.tvi import (
    VistoriaModelBase, VistoriaModel,
    VistoriaBase, Vistoria,
    VistoriaPhoto, VistoriaSignature, VistoriaShare,
    PhotoUploadRequest, SignatureRequest,
)
from models.contrato import (
    PessoaFisica, PessoaJuridica, Parte, Corretor,
    ObjetoContrato, ParcelaPagamento, CondicoesPagamento,
    Testemunha, Clausula, AlertaJuridico,
    ContratoVersionDiff, ContratoVersion,
    ContratoBase, Contrato,
    TIPOS_CONTRATO,
)

__all__ = [
    "_id", "_now",
    "UserRegister", "UserLogin", "User", "UserPublic", "AuthResponse", "UserUpdate",
    "CreateTestUserRequest", "AdminUserOut",
    "PtamSample", "PtamImpactArea", "PtamMarketSample", "PtamBase", "Ptam",
    "PtamVersion", "PtamVersionDiff",
    "AIMessage", "AIMessageResponse", "AIHistoryItem",
    "Transaction", "CreatePreferenceRequest",
    "PerfilAvaliadorBase", "PerfilAvaliador",
    "RegistroProfissional", "Formacao", "Experiencia",
    "LocacaoAmostra", "LocacaoBase", "Locacao",
    "GarantiaSolicitante", "GarantiaResponsavel", "GarantiaBase", "Garantia",
    "CategoriaSemovente", "SemoventeBase", "Semovente",
    "ClientBase", "Client", "PropertyBase", "Property", "SampleBase", "Sample",
    "EvaluationBase", "Evaluation",
    "VistoriaModelBase", "VistoriaModel",
    "VistoriaBase", "Vistoria",
    "VistoriaPhoto", "VistoriaSignature", "VistoriaShare",
    "PhotoUploadRequest", "SignatureRequest",
    # Contratos
    "PessoaFisica", "PessoaJuridica", "Parte", "Corretor",
    "ObjetoContrato", "ParcelaPagamento", "CondicoesPagamento",
    "Testemunha", "Clausula", "AlertaJuridico",
    "ContratoVersionDiff", "ContratoVersion",
    "ContratoBase", "Contrato",
    "TIPOS_CONTRATO",
]
