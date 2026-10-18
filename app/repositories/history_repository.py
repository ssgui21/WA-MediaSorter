import sqlite3
from pathlib import Path
from typing import List, Optional
from threading import Lock
from datetime import datetime

from app.config import HISTORY_DB_FILE
from app.models.history import ExecutionRecord


class HistoryRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or HISTORY_DB_FILE
        self._lock = Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        source_group TEXT NOT NULL,
                        analyzed_count INTEGER NOT NULL,
                        approved_count INTEGER NOT NULL,
                        rejected_count INTEGER NOT NULL,
                        saved_count INTEGER NOT NULL,
                        errors_count INTEGER NOT NULL,
                        details TEXT DEFAULT ''
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS saved_hashes (
                        content_hash TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        saved_path TEXT NOT NULL,
                        saved_at TEXT NOT NULL
                    )
                """)
                conn.commit()

    def add_execution(self, record: ExecutionRecord) -> int:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO executions (
                        created_at, source_group, analyzed_count, approved_count,
                        rejected_count, saved_count, errors_count, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.created_at,
                    record.source_group,
                    record.analyzed_count,
                    record.approved_count,
                    record.rejected_count,
                    record.saved_count,
                    record.errors_count,
                    record.details,
                ))
                conn.commit()
                return cursor.lastrowid

    def list_executions(self, limit: int = 50) -> List[ExecutionRecord]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, created_at, source_group, analyzed_count,
                           approved_count, rejected_count, saved_count,
                           errors_count, details
                    FROM executions
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [ExecutionRecord(**dict(row)) for row in rows]

    def is_hash_known(self, content_hash: str) -> bool:
        if not content_hash:
            return False
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM saved_hashes WHERE content_hash = ?", (content_hash,))
                return cursor.fetchone() is not None

    def record_saved_hash(self, content_hash: str, filename: str, saved_path: str) -> None:
        if not content_hash:
            return
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT OR REPLACE INTO saved_hashes (content_hash, filename, saved_path, saved_at)
                    VALUES (?, ?, ?, ?)
                """, (content_hash, filename, saved_path, now))
                conn.commit()
