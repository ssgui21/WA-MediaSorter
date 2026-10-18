from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.repositories.rule_repository import RuleRepository
from app.services.image_downloader import ImageDownloader
from app.integrations.whatsapp.client import WhatsAppClient
from app.services.processing_service import ProcessingService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_rule_repo():
    return RuleRepository()


def get_whatsapp_client():
    return WhatsAppClient()


@router.get("", response_model=Dict[str, Any])
def get_dashboard_summary():
    """
    Retorna o resumo completo do painel inicial da aplicação:
    - Estado da aplicação
    - Estado da conexão com o WhatsApp
    - Grupos disponíveis e grupo selecionado
    - Pasta de destino e sua validade
    - Regras ativas
    - Estatísticas reais da sessão
    """
    rule_repo = RuleRepository()
    downloader = ImageDownloader()
    whatsapp = WhatsAppClient()
    
    # Da instância global ou singleton
    from app.main import processing_service

    dest_path = rule_repo.get_destination_path()
    is_valid_dest, dest_msg = downloader.validate_destination(dest_path)

    all_rules = rule_repo.list_rules()
    active_rules = [r for r in all_rules if r.is_active]

    wa_status = whatsapp.get_status()
    groups = whatsapp.list_groups()

    session_stats = processing_service.get_session_stats()
    job_progress = processing_service.get_current_progress()

    return {
        "app_status": "processando" if job_progress["status"] == "running" else "pronto",
        "whatsapp": {
            "state": wa_status["state"],
            "message": wa_status["message"],
            "driver_available": wa_status["driver_available"],
            "groups_count": len(groups),
            "selected_group_id": wa_status["selected_group_id"],
        },
        "destination": {
            "path": dest_path,
            "is_valid": is_valid_dest,
            "message": dest_msg,
        },
        "rules": {
            "total_count": len(all_rules),
            "active_count": len(active_rules),
            "active_rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "criteria_type": r.criteria_type.value,
                    "logical_operator": r.logical_operator.value,
                    "confidence_threshold": r.confidence_threshold,
                }
                for r in active_rules
            ]
        },
        "session_stats": session_stats,
        "current_job": job_progress
    }
