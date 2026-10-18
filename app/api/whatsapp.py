from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.integrations.whatsapp.base import WhatsAppGroup
from app.integrations.whatsapp.client import WhatsAppClient

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

# Cliente mantido em memória
whatsapp_client = WhatsAppClient()


class SelectGroupRequest(BaseModel):
    group_id: str


@router.get("/status", response_model=Dict[str, Any])
def get_whatsapp_status():
    """Consulta o estado atual da conexão com o WhatsApp."""
    return whatsapp_client.get_status()


@router.post("/connect", response_model=Dict[str, Any])
def connect_whatsapp():
    """Inicia a tentativa de conexão com o WhatsApp Web."""
    return whatsapp_client.connect()


@router.post("/disconnect", response_model=Dict[str, Any])
def disconnect_whatsapp():
    """Encerra a sessão com o WhatsApp com segurança."""
    success = whatsapp_client.disconnect()
    return {
        "success": success,
        "message": "Sessão desconectada com segurança."
    }


@router.get("/qr", response_model=Dict[str, Any])
def get_qr_code():
    """Retorna dados do QR Code quando aguardando autenticação."""
    qr_data = whatsapp_client.get_auth_qr()
    return {
        "has_qr": qr_data is not None,
        "qr_data": qr_data
    }


@router.get("/groups", response_model=List[WhatsAppGroup])
def list_groups():
    """Lista os grupos acessíveis na conta conectada."""
    return whatsapp_client.list_groups()


@router.post("/select-group", response_model=Dict[str, Any])
def select_group(req: SelectGroupRequest):
    """Seleciona um grupo para leitura de imagens."""
    success = whatsapp_client.select_group(req.group_id)
    return {
        "success": success,
        "selected_group_id": req.group_id
    }
