from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str
    folder_path: str
    mode: str = "review"  # review, automatic, hybrid, compare
    routing_strategy: str = "local_only"
    production_policy: str = "BALANCED"  # FAST_LOCAL, BEST_LOCAL_QUALITY, BALANCED, 16GB_SAFE, 32GB_QUALITY, ADAPTIVE_ESCALATION
    privacy_mode: str = "LOCAL_ONLY"  # LOCAL_ONLY, LOCAL_AND_CLOUD, ALLOW_PUBLIC_WEB
    quality_target: float = 4.0
    min_meaning_floor: float = 3.5
    min_completeness_floor: float = 3.5
    min_naturalness_floor: float = 3.5
    min_terminology_floor: float = 3.5
    primary_model_id: str = "nllb-200-distilled-1.3b"
    secondary_model_id: Optional[str] = None
    reviewer_model_id: Optional[str] = "qwen3:8b"
    gemini_model_id: Optional[str] = "gemini-3.6-flash"
    preferred_english_provider: Optional[str] = "qwen3:8b"

class ProjectRecord(BaseModel):
    id: str
    name: str
    folder_path: str
    mode: str
    routing_strategy: str
    production_policy: str = "BALANCED"
    privacy_mode: str = "LOCAL_ONLY"
    quality_target: float = 4.0
    min_meaning_floor: float = 3.5
    min_completeness_floor: float = 3.5
    min_naturalness_floor: float = 3.5
    min_terminology_floor: float = 3.5
    primary_model_id: str
    secondary_model_id: Optional[str] = None
    reviewer_model_id: Optional[str] = None
    gemini_model_id: Optional[str] = None
    preferred_english_provider: Optional[str] = "qwen3:8b"
    status: str = "active"  # active, paused, completed
    created_at: str
    updated_at: str

class DocumentRecord(BaseModel):
    id: str
    project_id: str
    filename: str
    filepath: str
    total_pages: int = 0
    processed_pages: int = 0
    total_chunks: int = 0
    completed_chunks: int = 0
    is_scanned: bool = False
    status: str = "pending"  # pending, extracting, translating, completed, failed
    error_message: Optional[str] = None

class ChunkRecord(BaseModel):
    id: str
    document_id: str
    project_id: str
    page_number: int
    chunk_index: int
    source_text: str
    target_urdu: Optional[str] = None
    secondary_urdu: Optional[str] = None
    reviewer_urdu: Optional[str] = None
    final_urdu: Optional[str] = None
    status: str = "pending"  # pending, extracting, ocr, translating, qa, awaiting_review, approved, rejected, failed
    qa_status: Optional[str] = None  # PASS, WARNING, REVIEW_REQUIRED, FAILED
    qa_issues: List[str] = Field(default_factory=list)
    primary_provider: Optional[str] = None
    primary_provider_class: Optional[str] = None
    primary_model: Optional[str] = None
    execution_backend: Optional[str] = None
    route: Optional[str] = None
    is_pivot: bool = False
    pivot_languages: List[str] = Field(default_factory=list)
    secondary_provider: Optional[str] = None
    secondary_model: Optional[str] = None
    review_provider: Optional[str] = None
    review_model: Optional[str] = None
    approved_by: Optional[str] = None  # human, auto
    approved_at: Optional[str] = None
    latency_ms: Optional[int] = None
    peak_ram_mb: Optional[float] = 0.0
    memory_pressure: Optional[str] = "GREEN"
    english_reference: Optional[str] = None
    english_reference_provider: Optional[str] = None
    english_reference_model: Optional[str] = None
    english_reference_route: Optional[str] = None
    english_reference_timestamp: Optional[str] = None
    ocr_provider: Optional[str] = None
    ocr_engine: Optional[str] = None
    ocr_language: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_timestamp: Optional[str] = None
    created_at: str
    updated_at: str

class GlossaryItem(BaseModel):
    id: Optional[str] = None
    project_id: Optional[str] = None
    source_arabic: str
    target_urdu: str
    category: Optional[str] = "General"
    notes: Optional[str] = ""
    is_approved: bool = True
    created_at: Optional[str] = None

class TranslationMemoryItem(BaseModel):
    id: Optional[str] = None
    source_hash: str
    source_arabic: str
    approved_urdu: str
    usage_count: int = 1
    source_provider: Optional[str] = None
    source_model: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class BenchmarkRun(BaseModel):
    id: str
    run_name: str
    test_case_id: str
    category: str
    source_arabic: str
    provider_name: str
    provider_class: Optional[str] = None
    model_name: str
    target_urdu: Optional[str] = None
    route: Optional[str] = None
    is_pivot: bool = False
    pivot_languages: List[str] = Field(default_factory=list)
    english_intermediate: Optional[str] = None
    latency_ms: Optional[int] = None
    execution_status: str = "PASSED"
    error: Optional[str] = None
    output_length_chars: int = 0
    output_length_words: int = 0
    peak_ram_mb: float = 0.0
    memory_pressure: str = "GREEN"
    model_load_time_ms: int = 0
    qa_status: str
    manual_meaning_score: Optional[int] = None
    manual_completeness_score: Optional[int] = None
    manual_naturalness_score: Optional[int] = None
    manual_terminology_score: Optional[int] = None
    manual_overall_score: Optional[int] = None
    sample_count: int = 1
    created_at: str
