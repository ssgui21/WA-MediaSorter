from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ExecutionRecord(BaseModel):
    id: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    source_group: str
    analyzed_count: int
    approved_count: int
    rejected_count: int
    saved_count: int
    errors_count: int
    details: str = ""
