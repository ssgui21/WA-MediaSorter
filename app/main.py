import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    BASE_DIR,
    FRONTEND_DIR,
    SERVER_HOST,
    SERVER_PORT,
    SETTINGS_FILE,
    HISTORY_DB_FILE,
)
from app.repositories.rule_repository import RuleRepository
from app.repositories.history_repository import HistoryRepository
from app.services.processing_service import ProcessingService
from app.api.dashboard import router as dashboard_router
from app.api.rules import router as rules_router
from app.api.destination import router as destination_router
from app.api.whatsapp import router as whatsapp_router
from app.api.processing import router as processing_router

# Inicialização de repositórios e serviços centrais
rule_repo = RuleRepository(SETTINGS_FILE)
history_repo = HistoryRepository(HISTORY_DB_FILE)
processing_service = ProcessingService(
    rule_repo=rule_repo,
    history_repo=history_repo
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização da aplicação
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Encerramento limpo
    try:
        processing_service.cancel_processing()
        processing_service.whatsapp_client.disconnect()
    except Exception:
        pass


app = FastAPI(
    title="WA-MediaSorter API",
    description="Backend local do organizador de imagens do WhatsApp",
    version="0.1.0",
    lifespan=lifespan
)

# CORS restrito ao ambiente local (127.0.0.1 / localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores da API
app.include_router(dashboard_router)
app.include_router(rules_router)
app.include_router(destination_router)
app.include_router(whatsapp_router)
app.include_router(processing_router)

# Servir arquivos estáticos do frontend (CSS, JS, imagens)
if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.get("/", include_in_schema=False)
def serve_index():
    """Entrega a página principal da interface."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(
        status_code=404,
        content={"detail": "Arquivo frontend/index.html não encontrado."}
    )


if __name__ == "__main__":
    import uvicorn
    # Executa escutando apenas em 127.0.0.1 por segurança
    uvicorn.run(
        "app.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False
    )
