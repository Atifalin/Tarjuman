import os
import uuid
import pytest
from datetime import datetime
from backend.app.database.connection import init_db, get_db
from backend.app.terminology.translation_memory import TranslationMemory

def test_database_init_and_tables():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        assert "projects" in tables
        assert "documents" in tables
        assert "chunks" in tables
        assert "glossary" in tables
        assert "translation_memory" in tables
        assert "benchmarks" in tables

def test_translation_memory_persistence():
    src = "الحمد لله رب العالمين"
    urdu = "تمام تعریفیں اللہ ہی کے لیے ہیں جو تمام جہانوں کا پالنے والا ہے۔"
    h1 = TranslationMemory.save_approved_translation(src, urdu)
    
    match = TranslationMemory.lookup_exact_match(src)
    assert match is not None
    assert match.approved_urdu == urdu
    assert match.source_hash == h1
