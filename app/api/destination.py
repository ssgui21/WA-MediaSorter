from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Dict, Any

from app.repositories.rule_repository import RuleRepository
from app.services.image_downloader import ImageDownloader

router = APIRouter(prefix="/api/destination", tags=["Destino"])
rule_repo = RuleRepository()
downloader = ImageDownloader()


class DestinationUpdateRequest(BaseModel):
    path: str = Field(..., min_length=1)


class DestinationValidateRequest(BaseModel):
    path: str = Field(..., min_length=1)


@router.get("", response_model=Dict[str, Any])
def get_destination():
    """Retorna a pasta de destino atual e o status de validação."""
    current_path = rule_repo.get_destination_path()
    is_valid, msg = downloader.validate_destination(current_path)
    return {
        "path": current_path,
        "is_valid": is_valid,
        "message": msg
    }


@router.post("", response_model=Dict[str, Any])
def update_destination(req: DestinationUpdateRequest):
    """Atualiza a pasta local de destino após validação."""
    is_valid, msg = downloader.validate_destination(req.path)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível definir o destino. {msg}"
        )
    resolved_path = str(Path(req.path).resolve())
    saved_path = rule_repo.set_destination_path(resolved_path)
    return {
        "path": saved_path,
        "is_valid": True,
        "message": "Destino atualizado e validado com sucesso."
    }


@router.post("/validate", response_model=Dict[str, Any])
def validate_destination_path(req: DestinationValidateRequest):
    """Valida a existência e a permissão de escrita de um caminho sem salvá-lo."""
    is_valid, msg = downloader.validate_destination(req.path)
    return {
        "path": req.path,
        "is_valid": is_valid,
        "message": msg
    }
