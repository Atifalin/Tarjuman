import os
import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional
from datetime import datetime
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

def get_db_path() -> Path:
    return settings.DATABASE_PATH

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional scope around a series of operations with WAL mode."""
    conn = sqlite3.connect(str(get_db_path()), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database tables with indexes."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Projects table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'review',
            routing_strategy TEXT NOT NULL DEFAULT 'local_only',
            primary_model_id TEXT NOT NULL,
            secondary_model_id TEXT,
            reviewer_model_id TEXT,
            gemini_model_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        
        # Documents table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            total_pages INTEGER DEFAULT 0,
            processed_pages INTEGER DEFAULT 0,
            total_chunks INTEGER DEFAULT 0,
            completed_chunks INTEGER DEFAULT 0,
            is_scanned INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );
        """)
        
        # Chunks table (the atomic unit of translation)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            source_text TEXT NOT NULL,
            target_urdu TEXT,
            secondary_urdu TEXT,
            reviewer_urdu TEXT,
            final_urdu TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            qa_status TEXT,
            qa_issues TEXT DEFAULT '[]',
            primary_provider TEXT,
            primary_model TEXT,
            secondary_provider TEXT,
            secondary_model TEXT,
            review_provider TEXT,
            review_model TEXT,
            approved_by TEXT,
            approved_at TEXT,
            latency_ms INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );
        """)
        
        # Indexes for rapid navigation and filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_project_status ON chunks(project_id, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks(document_id, page_number);")

        # Glossary table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS glossary (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            source_arabic TEXT NOT NULL,
            target_urdu TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            notes TEXT DEFAULT '',
            is_approved INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, source_arabic)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_glossary_arabic ON glossary(source_arabic);")

        # Translation Memory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id TEXT PRIMARY KEY,
            source_hash TEXT UNIQUE NOT NULL,
            source_arabic TEXT NOT NULL,
            approved_urdu TEXT NOT NULL,
            usage_count INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tm_hash ON translation_memory(source_hash);")

        # Migration columns for translation_memory (provenance: which model/provider actually produced it)
        for col_name, col_type in [
            ("source_provider", "TEXT"),
            ("source_model", "TEXT")
        ]:
            try:
                cursor.execute(f"ALTER TABLE translation_memory ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass

        # Benchmarks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            id TEXT PRIMARY KEY,
            run_name TEXT NOT NULL,
            test_case_id TEXT NOT NULL,
            category TEXT NOT NULL,
            source_arabic TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            target_urdu TEXT,
            latency_ms INTEGER,
            execution_status TEXT DEFAULT 'PASSED',
            error TEXT,
            output_length_chars INTEGER DEFAULT 0,
            output_length_words INTEGER DEFAULT 0,
            peak_ram_mb REAL DEFAULT 0.0,
            memory_pressure TEXT DEFAULT 'GREEN',
            qa_status TEXT NOT NULL,
            manual_meaning_score INTEGER,
            manual_completeness_score INTEGER,
            manual_naturalness_score INTEGER,
            manual_terminology_score INTEGER,
            manual_overall_score INTEGER,
            created_at TEXT NOT NULL
        );
        """)

        # Safely ensure newly added columns exist in existing database
        for col_name, col_type in [
            ("manual_completeness_score", "INTEGER"),
            ("manual_naturalness_score", "INTEGER"),
            ("output_length_chars", "INTEGER DEFAULT 0"),
            ("output_length_words", "INTEGER DEFAULT 0"),
            ("peak_ram_mb", "REAL DEFAULT 0.0"),
            ("memory_pressure", "TEXT DEFAULT 'GREEN'"),
            ("execution_status", "TEXT DEFAULT 'PASSED'"),
            ("error", "TEXT")
        ]:
            try:
                cursor.execute(f"ALTER TABLE benchmarks ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass

        # Check if latency_ms has NOT NULL constraint and migrate if needed
        cursor.execute("PRAGMA table_info(benchmarks);")
        columns_info = cursor.fetchall()
        latency_col = next((c for c in columns_info if c["name"] == "latency_ms"), None)
        if latency_col and latency_col["notnull"] == 1:
            try:
                cursor.execute("CREATE TABLE benchmarks_backup AS SELECT * FROM benchmarks;")
                cursor.execute("DROP TABLE benchmarks;")
                cursor.execute("""
                CREATE TABLE benchmarks (
                    id TEXT PRIMARY KEY,
                    run_name TEXT NOT NULL,
                    test_case_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source_arabic TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    target_urdu TEXT,
                    latency_ms INTEGER,
                    execution_status TEXT DEFAULT 'PASSED',
                    error TEXT,
                    output_length_chars INTEGER DEFAULT 0,
                    output_length_words INTEGER DEFAULT 0,
                    peak_ram_mb REAL DEFAULT 0.0,
                    memory_pressure TEXT DEFAULT 'GREEN',
                    qa_status TEXT NOT NULL,
                    manual_meaning_score INTEGER,
                    manual_completeness_score INTEGER,
                    manual_naturalness_score INTEGER,
                    manual_terminology_score INTEGER,
                    manual_overall_score INTEGER,
                    created_at TEXT NOT NULL
                );
                """)
            except Exception:
                pass
        # System / Quota usage stats table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_stats (
            stat_date TEXT PRIMARY KEY,
            cloud_requests_count INTEGER DEFAULT 0,
            cloud_estimated_input_tokens INTEGER DEFAULT 0,
            cloud_estimated_output_tokens INTEGER DEFAULT 0
        );
        """)

        # Migration columns for projects
        for col_name, col_type in [
            ("privacy_mode", "TEXT DEFAULT 'LOCAL_ONLY'"),
            ("production_policy", "TEXT DEFAULT 'BALANCED'"),
            ("quality_target", "REAL DEFAULT 4.0"),
            ("min_meaning_floor", "REAL DEFAULT 3.5"),
            ("min_completeness_floor", "REAL DEFAULT 3.5"),
            ("min_naturalness_floor", "REAL DEFAULT 3.5"),
            ("min_terminology_floor", "REAL DEFAULT 3.5"),
            ("preferred_english_provider", "TEXT DEFAULT 'qwen3:8b'")
        ]:
            try:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass

        # Migration columns for chunks (full provenance & English reference)
        for col_name, col_type in [
            ("primary_provider_class", "TEXT"),
            ("execution_backend", "TEXT"),
            ("route", "TEXT"),
            ("is_pivot", "INTEGER DEFAULT 0"),
            ("pivot_languages", "TEXT DEFAULT '[]'"),
            ("peak_ram_mb", "REAL DEFAULT 0.0"),
            ("memory_pressure", "TEXT DEFAULT 'GREEN'"),
            ("english_reference", "TEXT"),
            ("english_reference_provider", "TEXT"),
            ("english_reference_model", "TEXT"),
            ("english_reference_route", "TEXT"),
            ("english_reference_timestamp", "TEXT"),
            ("ocr_provider", "TEXT"),
            ("ocr_engine", "TEXT"),
            ("ocr_language", "TEXT"),
            ("ocr_confidence", "REAL"),
            ("ocr_timestamp", "TEXT")
        ]:
            try:
                cursor.execute(f"ALTER TABLE chunks ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass

        # Migration columns for benchmarks (route, pivot, sample size, load time)
        for col_name, col_type in [
            ("provider_class", "TEXT"),
            ("privacy_class", "TEXT"),
            ("route", "TEXT"),
            ("is_pivot", "INTEGER DEFAULT 0"),
            ("pivot_languages", "TEXT DEFAULT '[]'"),
            ("english_intermediate", "TEXT"),
            ("sample_count", "INTEGER DEFAULT 1"),
            ("documents_sampled", "INTEGER DEFAULT 1"),
            ("pages_sampled", "INTEGER DEFAULT 1"),
            ("human_reviews", "INTEGER DEFAULT 0"),
            ("model_load_time_ms", "INTEGER DEFAULT 0")
        ]:
            try:
                cursor.execute(f"ALTER TABLE benchmarks ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass
        
        # Gemini per-tier usage log table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gemini_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_date TEXT NOT NULL,
            model_id TEXT NOT NULL,
            model_tier TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)

        # Clean up any dummy project paths to point to data/sample_books
        sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "sample_books"))
        os.makedirs(sample_dir, exist_ok=True)
        cursor.execute("UPDATE projects SET folder_path = ?, name = 'Sample Arabic Books' WHERE folder_path = '/dummy/path' OR folder_path = '';", (sample_dir,))
        cursor.execute("DELETE FROM documents WHERE filepath LIKE '/dummy/%';")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gemini_usage_date_tier ON gemini_usage_log(stat_date, model_tier);")

        # System event logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            module TEXT NOT NULL,
            message TEXT NOT NULL,
            extra_data TEXT,
            created_at TEXT NOT NULL
        );
        """)
        
    logger.info("Database initialized successfully with WAL mode.")
