import io
import time
import pytest
from pathlib import Path
from PIL import Image

from app.models.item import MediaItem
from app.models.rule import RuleCreate, CriteriaType, LogicalOperator
from app.repositories.rule_repository import RuleRepository
from app.repositories.history_repository import HistoryRepository
from app.services.rule_engine import RuleEngine
from app.services.image_downloader import ImageDownloader
from app.services.processing_service import ProcessingService
from app.integrations.whatsapp.client import LocalSampleSource


@pytest.fixture
def service_env(tmp_path):
    settings_file = tmp_path / "settings.json"
    db_file = tmp_path / "history.db"
    dest_dir = tmp_path / "downloads"
    sample_dir = tmp_path / "sample_images"
    dest_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    rule_repo = RuleRepository(settings_file)
    rule_repo.set_destination_path(str(dest_dir))
    history_repo = HistoryRepository(db_file)
    rule_engine = RuleEngine()
    downloader = ImageDownloader(history_repo)
    sample_source = LocalSampleSource(sample_dir)

    # Criar uma imagem de teste na pasta de amostras
    img = Image.new("RGB", (60, 60), color="blue")
    img_path = sample_dir / "comprovante_banco.png"
    img.save(img_path, format="PNG")
    txt_path = sample_dir / "comprovante_banco.txt"
    txt_path.write_text("Segue comprovante de transferência bancária.", encoding="utf-8")

    # Criar uma regra ativa que deve aprovar
    rule_repo.create_rule(
        RuleCreate(
            name="Comprovantes",
            criteria_type=CriteriaType.TEXT,
            specific_config={"keywords": ["comprovante"], "match_mode": "any"},
            is_active=True,
            logical_operator=LogicalOperator.OR,
            confidence_threshold=0.5
        )
    )

    proc_service = ProcessingService(
        rule_repo=rule_repo,
        history_repo=history_repo,
        rule_engine=rule_engine,
        image_downloader=downloader,
        sample_source=sample_source
    )

    return {
        "service": proc_service,
        "dest_dir": dest_dir,
        "sample_dir": sample_dir,
        "history_repo": history_repo
    }


def test_preview_does_not_save_files(service_env):
    """Testa se a geração de prévia avalia a imagem sem gravá-la no disco."""
    service = service_env["service"]
    dest_dir = service_env["dest_dir"]

    results = service.generate_preview(source_mode="sample")

    assert len(results) == 1
    assert results[0].evaluation.approved is True
    assert results[0].saved is False

    # A pasta de destino deve continuar vazia
    saved_files = list(dest_dir.iterdir())
    assert len(saved_files) == 0


def test_processing_execution_saves_approved_images(service_env):
    """Testa a execução síncrona/direta do processamento salvando as imagens aprovadas."""
    service = service_env["service"]
    dest_dir = service_env["dest_dir"]

    # Executa o processamento
    service._process_worker(source_mode="sample", group_id=None)

    progress = service.get_current_progress()
    assert progress["status"] == "completed"
    assert progress["processed"] == 1
    assert progress["approved"] == 1
    assert progress["saved"] == 1

    # O arquivo deve ter sido salvo no destino
    saved_files = [f for f in dest_dir.iterdir() if f.is_file()]
    assert len(saved_files) == 1
    assert saved_files[0].name == "comprovante_banco.png"


def test_processing_cancellation(service_env):
    """Testa a capacidade de cancelar um processamento."""
    service = service_env["service"]
    service._is_processing = True

    cancelled = service.cancel_processing()
    assert cancelled is True
    assert service._cancel_requested is True

    progress = service.get_current_progress()
    assert "cancelamento solicitado" in progress["message"].lower()
