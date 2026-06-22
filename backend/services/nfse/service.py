# @module services.nfse.service — Orquestração da emissão de NFS-e.
# PR1 = FUNDAÇÃO: prepara a DPS (numeração + cálculo) e persiste o documento `pendente`.
# A TRANSMISSÃO real fica a cargo do provider (stubs no PR1 → levantam erro controlado:
# NADA é emitido de verdade até os adapters serem implementados em homologação).
from __future__ import annotations

from datetime import datetime, timezone

from models.nfse import (
    NFSeConfig, NFSeDocumento, Servico, Tomador, Origem, DPS,
    StatusNFSe, calcular_valores,
)
from services.nfse import repository as repo
from services.nfse.providers.factory import get_provider
from services.nfse.exceptions import NFSeError, NFSeConfigError, NFSeProviderError, NFSeRejeitada


async def preparar_documento(db, config: NFSeConfig, origem: Origem,
                             tomador: Tomador, servico: Servico) -> NFSeDocumento:
    """Reserva o número da DPS, aplica os cálculos fiscais e cria o documento `pendente`.
    NÃO transmite. Retorna o NFSeDocumento persistido."""
    # cálculo fiscal (fonte única: models.nfse.calcular_valores)
    calc = calcular_valores(servico)
    servico.base_calculo = calc["base_calculo"]
    servico.valor_iss = calc["valor_iss"]
    servico.valor_liquido = calc["valor_liquido"]

    serie = config.sefin.serie_dps or "1"
    numero = await repo.proximo_numero_dps(db, config.id, serie)

    doc = NFSeDocumento(
        config_id=config.id, provider=config.provider, ambiente=config.ambiente,
        origem=origem, tomador=tomador, servico=servico,
        dps=DPS(serie=serie, numero=numero, id_dps=f"{config.id}-{serie}-{numero}",
                data_emissao=datetime.now(timezone.utc)),
        status=StatusNFSe.pendente, template_danfse=config.template_danfse,
    )
    await repo.criar_documento(db, doc.model_dump(mode="json"))
    return doc


async def emitir(db, config: NFSeConfig, doc: NFSeDocumento, owner_uid: str = None) -> NFSeDocumento:
    """Transmite o documento via provider (transmissão travada por segurança).
    Injeta db+owner_uid no provider p/ carregar o e-CNPJ já cadastrado (db.certificados)."""
    provider = get_provider(config)
    try:
        provider.db = db
        provider.owner_uid = owner_uid
    except Exception:  # noqa: BLE001
        pass
    try:
        resultado = await provider.emitir(doc)
        patch = {
            "status": resultado.status.value if hasattr(resultado.status, "value") else resultado.status,
            "chave_acesso": resultado.chave_acesso, "numero_nfse": resultado.numero_nfse,
            "codigo_verificacao": resultado.codigo_verificacao,
            "url_consulta_publica": resultado.url_consulta_publica,
            "rejeicao": resultado.rejeicao.model_dump() if resultado.rejeicao else None,
        }
    except NFSeRejeitada as e:
        patch = {"status": StatusNFSe.rejeitada.value, "rejeicao": {"codigo": e.codigo, "mensagem": e.mensagem}}
    except (NFSeProviderError, NFSeConfigError, NFSeError) as e:
        patch = {"status": StatusNFSe.erro.value, "rejeicao": {"codigo": "PROVIDER", "mensagem": str(e)}}
    atualizado = await repo.atualizar_documento(db, doc.id, patch) or doc.model_dump(mode="json")
    return NFSeDocumento(**{k: v for k, v in atualizado.items() if k != "_id"})
