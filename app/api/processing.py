from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.models.item import ProcessedItemResult
from app.models.history import ExecutionRecord
from app.config import SAMPLE_IMAGES_DIR

router = APIRouter(prefix="/api/processing", tags=["Processamento"])


class PreviewRequest(BaseModel):
    source_mode: str = "sample" # 'sample' ou 'whatsapp'
    group_id: Optional[str] = None


class StartProcessingRequest(BaseModel):
    source_mode: str = "sample" # 'sample' ou 'whatsapp'
    group_id: Optional[str] = None


@router.post("/preview", response_model=List[ProcessedItemResult])
def preview_processing(req: PreviewRequest):
    """
    Gera a prévia das imagens avaliadas com base nas regras ativas,
    SEM salvar nenhum arquivo no destino.
    """
    from app.main import processing_service
    return processing_service.generate_preview(
        source_mode=req.source_mode,
        group_id=req.group_id
    )


@router.post("/start", response_model=Dict[str, Any])
def start_processing(req: StartProcessingRequest):
    """
    Inicia o processamento em segundo plano sem congelar o servidor.
    """
    from app.main import processing_service
    started = processing_service.start_processing(
        source_mode=req.source_mode,
        group_id=req.group_id
    )
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um processamento em andamento."
        )
    return {
        "success": True,
        "message": "Processamento iniciado com sucesso em segundo plano."
    }


@router.post("/cancel", response_model=Dict[str, Any])
def cancel_processing():
    """Cancela a execução em andamento."""
    from app.main import processing_service
    cancelled = processing_service.cancel_processing()
    return {
        "success": cancelled,
        "message": "Solicitação de cancelamento enviada." if cancelled else "Nenhum processamento ativo para cancelar."
    }


@router.get("/status", response_model=Dict[str, Any])
def get_processing_status():
    """Retorna o progresso atual do processamento."""
    from app.main import processing_service
    return processing_service.get_current_progress()


@router.get("/results", response_model=List[ProcessedItemResult])
def get_processing_results():
    """Retorna a lista de itens avaliados no último processamento ou prévia."""
    from app.main import processing_service
    return processing_service.get_last_results()


@router.get("/history", response_model=List[ExecutionRecord])
def get_execution_history(limit: int = 50):
    """Retorna o histórico de execuções persistido no banco SQLite local."""
    from app.main import history_repo
    return history_repo.list_executions(limit=limit)


@router.post("/samples/upload", response_model=Dict[str, Any])
async def upload_sample_image(
    file: UploadFile = File(...),
    caption: str = Form("")
):
    """
    Permite enviar uma imagem para a pasta de demonstração local,
    facilitando o teste imediato do motor de regras.
    """
    from app.services.image_analyzer import ImageAnalyzer
    SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    analyzer = ImageAnalyzer()
    is_valid, mime, msg = analyzer.validate_image_content(content, file.filename)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo rejeitado: {msg}"
        )

    clean_filename = Path(file.filename).name
    target_path = SAMPLE_IMAGES_DIR / clean_filename
    with open(target_path, "wb") as f:
        f.write(content)

    if caption:
        txt_path = target_path.with_suffix(".txt")
        txt_path.write_text(caption, encoding="utf-8")

    return {
        "success": True,
        "filename": clean_filename,
        "message": f"Imagem '{clean_filename}' adicionada às amostras de teste."
    }
