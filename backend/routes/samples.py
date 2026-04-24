# @module routes.samples — Alias para amostras de mercado (delega para scraper)
from fastapi import APIRouter, Depends
from routes.scraper import router as scraper_router

router = APIRouter(prefix="/samples", tags=["samples"])

# Importar handlers do scraper
from routes.scraper import (
    listar_amostras_salvas,
    salvar_amostra_manual,
    remover_amostra_salva,
)
from dependencies import get_active_subscriber

@router.get("")
async def list_samples(uid: str = Depends(get_active_subscriber)):
    """Lista amostras salvas do usuário."""
    return await listar_amostras_salvas(uid)

@router.post("")
async def create_sample(data: dict, uid: str = Depends(get_active_subscriber)):
    """Cria nova amostra manual."""
    return await salvar_amostra_manual(data, uid)

@router.delete("/{id}")
async def delete_sample(id: str, uid: str = Depends(get_active_subscriber)):
    """Remove amostra salva."""
    return await remover_amostra_salva(id, uid)
