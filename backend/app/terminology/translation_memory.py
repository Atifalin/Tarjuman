import hashlib
import uuid
import logging
from typing import Optional, List, Dict
from datetime import datetime
from backend.app.database.connection import get_db
from backend.app.database.models import TranslationMemoryItem

logger = logging.getLogger(__name__)

def hash_arabic_text(text: str) -> str:
    # Normalize whitespace before hashing
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class TranslationMemory:
    """Manages translation memory storage and exact/fuzzy recall."""

    @classmethod
    def save_approved_translation(
        cls,
        source_arabic: str,
        approved_urdu: str,
        source_provider: Optional[str] = None,
        source_model: Optional[str] = None
    ) -> str:
        s_hash = hash_arabic_text(source_arabic)
        now = datetime.now().isoformat()
        tm_id = str(uuid.uuid4())

        with get_db() as conn:
            conn.execute("""
            INSERT INTO translation_memory (id, source_hash, source_arabic, approved_urdu, usage_count, source_provider, source_model, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(source_hash) DO UPDATE SET
                approved_urdu = excluded.approved_urdu,
                usage_count = usage_count + 1,
                source_provider = excluded.source_provider,
                source_model = excluded.source_model,
                updated_at = excluded.updated_at;
            """, (tm_id, s_hash, source_arabic.strip(), approved_urdu.strip(), source_provider, source_model, now, now))
        return s_hash

    @classmethod
    def lookup_exact_match(cls, source_arabic: str) -> Optional[TranslationMemoryItem]:
        s_hash = hash_arabic_text(source_arabic)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM translation_memory WHERE source_hash = ?;", (s_hash,))
            row = cursor.fetchone()
            if row:
                keys = row.keys()
                return TranslationMemoryItem(
                    id=row["id"],
                    source_hash=row["source_hash"],
                    source_arabic=row["source_arabic"],
                    approved_urdu=row["approved_urdu"],
                    usage_count=row["usage_count"],
                    source_provider=row["source_provider"] if "source_provider" in keys else None,
                    source_model=row["source_model"] if "source_model" in keys else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
        return None

    @classmethod
    def clear_all(cls) -> int:
        """Wipes the entire translation memory cache. Returns number of rows deleted."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM translation_memory;")
            count = cursor.fetchone()[0]
            conn.execute("DELETE FROM translation_memory;")
            return count
