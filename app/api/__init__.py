from app.api.dashboard import router as dashboard_router
from app.api.rules import router as rules_router
from app.api.destination import router as destination_router
from app.api.whatsapp import router as whatsapp_router
from app.api.processing import router as processing_router

__all__ = [
    "dashboard_router",
    "rules_router",
    "destination_router",
    "whatsapp_router",
    "processing_router",
]
