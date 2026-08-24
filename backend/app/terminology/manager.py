import csv
import io
import uuid
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from backend.app.database.connection import get_db
from backend.app.database.models import GlossaryItem

logger = logging.getLogger(__name__)

class TerminologyManager:
    """Manages persistent translation glossary with CSV import/export and term matching."""

    @classmethod
    def get_terms_for_project(cls, project_id: Optional[str] = None) -> List[GlossaryItem]:
        with get_db() as conn:
            cursor = conn.cursor()
            if project_id:
                cursor.execute(
                    "SELECT * FROM glossary WHERE project_id = ? OR project_id IS NULL ORDER BY source_arabic ASC;",
                    (project_id,)
                )
            else:
                cursor.execute("SELECT * FROM glossary ORDER BY source_arabic ASC;")
            
            rows = cursor.fetchall()
            return [
                GlossaryItem(
                    id=row["id"],
                    project_id=row["project_id"],
                    source_arabic=row["source_arabic"],
                    target_urdu=row["target_urdu"],
                    category=row["category"],
                    notes=row["notes"],
                    is_approved=bool(row["is_approved"]),
                    created_at=row["created_at"]
                )
                for row in rows
            ]

    @classmethod
    def add_term(cls, item: GlossaryItem) -> GlossaryItem:
        term_id = item.id or str(uuid.uuid4())
        created_at = item.created_at or datetime.now().isoformat()
        with get_db() as conn:
            conn.execute("""
            INSERT INTO glossary (id, project_id, source_arabic, target_urdu, category, notes, is_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, source_arabic) DO UPDATE SET
                target_urdu = excluded.target_urdu,
                category = excluded.category,
                notes = excluded.notes,
                is_approved = excluded.is_approved;
            """, (
                term_id,
                item.project_id,
                item.source_arabic.strip(),
                item.target_urdu.strip(),
                item.category or "General",
                item.notes or "",
                1 if item.is_approved else 0,
                created_at
            ))
        item.id = term_id
        item.created_at = created_at
        return item

    @classmethod
    def delete_term(cls, term_id: str) -> bool:
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM glossary WHERE id = ?;", (term_id,))
            return cursor.rowcount > 0

    @classmethod
    def match_terms_in_text(cls, text: str, project_id: Optional[str] = None) -> Dict[str, str]:
        """Finds any glossary terms that occur within the given Arabic source text."""
        terms = cls.get_terms_for_project(project_id)
        matched = {}
        for item in terms:
            if item.is_approved and item.source_arabic in text:
                matched[item.source_arabic] = item.target_urdu
        return matched

    @classmethod
    def export_csv(cls, project_id: Optional[str] = None) -> str:
        terms = cls.get_terms_for_project(project_id)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Arabic", "Urdu", "Category", "Notes"])
        for t in terms:
            writer.writerow([t.source_arabic, t.target_urdu, t.category, t.notes])
        return output.getvalue()

    @classmethod
    def import_csv(cls, csv_content: str, project_id: Optional[str] = None) -> int:
        reader = csv.reader(io.StringIO(csv_content.strip()))
        header = next(reader, None)
        count = 0
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                arabic = row[0].strip()
                urdu = row[1].strip()
                category = row[2].strip() if len(row) > 2 else "General"
                notes = row[3].strip() if len(row) > 3 else ""
                cls.add_term(GlossaryItem(
                    project_id=project_id,
                    source_arabic=arabic,
                    target_urdu=urdu,
                    category=category,
                    notes=notes,
                    is_approved=True
                ))
                count += 1
        return count
