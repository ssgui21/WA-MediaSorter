from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.rule import OverallEvaluationResult


class MediaItem(BaseModel):
    id: str
    filename: str
    source_group: str
    message_date: Optional[str] = None
    caption: str = ""
    file_path: Optional[str] = None
    content_hash: Optional[str] = None
    file_size_bytes: int = 0
    mime_type: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ProcessedItemResult(BaseModel):
    item: MediaItem
    evaluation: OverallEvaluationResult
    saved: bool = False
    saved_path: Optional[str] = None
    error_message: Optional[str] = None
    is_duplicate: bool = False
