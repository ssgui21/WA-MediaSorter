import base64
import io
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image

from app.models.item import MediaItem, ProcessedItemResult
from app.models.rule import OverallEvaluationResult
from app.models.history import ExecutionRecord
from app.repositories.rule_repository import RuleRepository
from app.repositories.history_repository import HistoryRepository
from app.services.rule_engine import RuleEngine
from app.services.image_downloader import ImageDownloader
from app.integrations.whatsapp.client import WhatsAppClient, LocalSampleSource


class ProcessingService:
    """
    Orquestrador de prévia e processamento em lote de imagens.
    Executa de forma não-bloqueante e oferece suporte a cancelamento imediato.
    """

    def __init__(
        self,
        rule_repo: Optional[RuleRepository] = None,
        history_repo: Optional[HistoryRepository] = None,
        rule_engine: Optional[RuleEngine] = None,
        image_downloader: Optional[ImageDownloader] = None,
        whatsapp_client: Optional[WhatsAppClient] = None,
        sample_source: Optional[LocalSampleSource] = None,
    ):
        self.rule_repo = rule_repo or RuleRepository()
        self.history_repo = history_repo or HistoryRepository()
        self.rule_engine = rule_engine or RuleEngine()
        self.downloader = image_downloader or ImageDownloader(self.history_repo)
        self.whatsapp_client = whatsapp_client or WhatsAppClient()
        self.sample_source = sample_source or LocalSampleSource()

        self._lock = threading.Lock()
        self._is_processing = False
        self._cancel_requested = False
        self._current_progress: Dict[str, Any] = {
            "status": "idle", # 'idle', 'running', 'completed', 'cancelled', 'error'
            "source": "none",
            "total": 0,
            "processed": 0,
            "approved": 0,
            "rejected": 0,
            "saved": 0,
            "errors": 0,
            "current_file": "",
            "message": "Nenhum processamento em andamento."
        }
        self._last_results: List[ProcessedItemResult] = []

        # Estatísticas acumuladas da sessão
        self._session_stats = {
            "processed": 0,
            "approved": 0,
            "rejected": 0,
            "saved": 0,
            "errors": 0
        }

    def get_session_stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._session_stats)

    def get_current_progress(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._current_progress)

    def get_last_results(self) -> List[ProcessedItemResult]:
        with self._lock:
            return list(self._last_results)

    def cancel_processing(self) -> bool:
        """Solicita o cancelamento da execução em andamento."""
        with self._lock:
            if self._is_processing:
                self._cancel_requested = True
                self._current_progress["message"] = "Cancelamento solicitado pelo usuário. Finalizando etapa atual..."
                return True
            return False

    @staticmethod
    def generate_thumbnail_base64(image_bytes: bytes, max_size: Tuple[int, int] = (150, 150)) -> Optional[str]:
        """Gera uma miniatura leve em base64 para exibição na interface web."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("RGB")
                img.thumbnail(max_size)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=75)
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return f"data:image/jpeg;base64,{b64}"
        except Exception:
            return None

    def _get_items_from_source(self, source_mode: str, group_id: Optional[str] = None) -> List[Tuple[MediaItem, bytes]]:
        """Obtém os itens conforme a origem selecionada."""
        if source_mode == "whatsapp":
            if not group_id:
                return []
            return self.whatsapp_client.fetch_group_images(group_id)
        elif source_mode == "sample":
            return self.sample_source.list_sample_items()
        return []

    def generate_preview(self, source_mode: str = "sample", group_id: Optional[str] = None) -> List[ProcessedItemResult]:
        """
        Gera a prévia das imagens e da avaliação das regras SEM salvar nada no disco.
        """
        rules = self.rule_repo.list_rules()
        raw_items = self._get_items_from_source(source_mode, group_id)
        results: List[ProcessedItemResult] = []

        for item, content in raw_items:
            # Gerar miniatura para visualização
            item.thumbnail_url = self.generate_thumbnail_base64(content)
            item.content_hash = self.downloader.analyzer.calculate_sha256(content)

            # Avaliar regras
            evaluation = self.rule_engine.evaluate_all_rules(rules, item, content)

            results.append(
                ProcessedItemResult(
                    item=item,
                    evaluation=evaluation,
                    saved=False,
                    saved_path=None,
                    error_message=None,
                    is_duplicate=self.history_repo.is_hash_known(item.content_hash)
                )
            )

        with self._lock:
            self._last_results = results
        return results

    def start_processing(self, source_mode: str = "sample", group_id: Optional[str] = None) -> bool:
        """
        Inicia a execução do processamento em uma thread em segundo plano,
        mantendo a interface do servidor responsiva e sem congelar.
        """
        with self._lock:
            if self._is_processing:
                return False
            self._is_processing = True
            self._cancel_requested = False
            self._current_progress = {
                "status": "running",
                "source": source_mode,
                "total": 0,
                "processed": 0,
                "approved": 0,
                "rejected": 0,
                "saved": 0,
                "errors": 0,
                "current_file": "",
                "message": "Iniciando processamento de imagens..."
            }

        thread = threading.Thread(
            target=self._process_worker,
            args=(source_mode, group_id),
            daemon=True
        )
        thread.start()
        return True

    def _process_worker(self, source_mode: str, group_id: Optional[str]) -> None:
        destination_path = self.rule_repo.get_destination_path()
        rules = self.rule_repo.list_rules()
        raw_items = self._get_items_from_source(source_mode, group_id)

        # 1. Validação prévia da pasta de destino
        valid_dest, dest_err = self.downloader.validate_destination(destination_path)
        if not valid_dest:
            with self._lock:
                self._is_processing = False
                self._current_progress["status"] = "error"
                self._current_progress["message"] = f"Destino inválido: {dest_err}"
                self._session_stats["errors"] += 1
            return

        total = len(raw_items)
        with self._lock:
            self._current_progress["total"] = total
            self._last_results = []

        processed = 0
        approved = 0
        rejected = 0
        saved = 0
        errors = 0
        results_collector: List[ProcessedItemResult] = []

        source_name = "WhatsApp (" + str(group_id) + ")" if source_mode == "whatsapp" else "Amostra Local"

        for item, content in raw_items:
            # Verificação de solicitação de cancelamento
            with self._lock:
                if self._cancel_requested:
                    self._is_processing = False
                    self._current_progress["status"] = "cancelled"
                    self._current_progress["message"] = "Processamento cancelado pelo usuário."
                    break

            with self._lock:
                self._current_progress["current_file"] = item.filename
                self._current_progress["processed"] = processed

            item.thumbnail_url = self.generate_thumbnail_base64(content)
            item.content_hash = self.downloader.analyzer.calculate_sha256(content)

            # Avaliar regras
            evaluation = self.rule_engine.evaluate_all_rules(rules, item, content)
            processed += 1

            saved_flag = False
            saved_path = None
            err_msg = None
            is_dup = False

            if evaluation.approved:
                approved += 1
                # Salvar no destino
                success, path, msg, is_dup = self.downloader.save_image(
                    image_bytes=content,
                    original_filename=item.filename,
                    destination_dir_str=destination_path,
                    check_existing_hashes=True
                )
                if success:
                    saved += 1
                    saved_flag = True
                    saved_path = path
                else:
                    if is_dup:
                        err_msg = msg
                    else:
                        errors += 1
                        err_msg = msg
            else:
                rejected += 1

            res_item = ProcessedItemResult(
                item=item,
                evaluation=evaluation,
                saved=saved_flag,
                saved_path=saved_path,
                error_message=err_msg,
                is_duplicate=is_dup
            )
            results_collector.append(res_item)

            # Atualizar progresso
            with self._lock:
                self._current_progress["processed"] = processed
                self._current_progress["approved"] = approved
                self._current_progress["rejected"] = rejected
                self._current_progress["saved"] = saved
                self._current_progress["errors"] = errors

        # Finalização da execução
        with self._lock:
            self._is_processing = False
            self._last_results = results_collector

            if self._current_progress["status"] != "cancelled":
                self._current_progress["status"] = "completed"
                self._current_progress["message"] = (
                    f"Processamento concluído. {processed} imagens analisadas, "
                    f"{approved} aprovadas, {saved} salvas no destino."
                )

            # Atualizar estatísticas de sessão
            self._session_stats["processed"] += processed
            self._session_stats["approved"] += approved
            self._session_stats["rejected"] += rejected
            self._session_stats["saved"] += saved
            self._session_stats["errors"] += errors

        # Registrar histórico no SQLite
        try:
            record = ExecutionRecord(
                created_at=datetime.now().isoformat(),
                source_group=source_name,
                analyzed_count=processed,
                approved_count=approved,
                rejected_count=rejected,
                saved_count=saved,
                errors_count=errors,
                details=self._current_progress.get("message", "")
            )
            self.history_repo.add_execution(record)
        except Exception:
            pass
