from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ProviderClass(str, Enum):
    LOCAL_MT = "LOCAL_MT"
    LOCAL_AI = "LOCAL_AI"
    APPLE_LOCAL = "APPLE_LOCAL"
    CLOUD_AI = "CLOUD_AI"
    PUBLIC_WEB = "PUBLIC_WEB"
    TEST = "TEST"

class PrivacyClass(str, Enum):
    OFFLINE = "OFFLINE"
    APPLE_LOCAL = "APPLE_LOCAL"
    CLOUD_USER_ENABLED = "CLOUD_USER_ENABLED"
    PUBLIC_WEB_USER_ENABLED = "PUBLIC_WEB_USER_ENABLED"

class CostClass(str, Enum):
    FREE_LOCAL = "FREE_LOCAL"
    FREE_APPLE = "FREE_APPLE"
    PUBLIC_WEB = "PUBLIC_WEB"
    CLOUD_FREE_TIER = "CLOUD_FREE_TIER"
    CLOUD_PAID = "CLOUD_PAID"

class ProductionPolicy(str, Enum):
    FAST_LOCAL = "FAST_LOCAL"
    BEST_LOCAL_QUALITY = "BEST_LOCAL_QUALITY"
    BALANCED = "BALANCED"
    SAFE_16GB = "16GB_SAFE"
    QUALITY_32GB = "32GB_QUALITY"
    ADAPTIVE_ESCALATION = "ADAPTIVE_ESCALATION"

class ModelCapability(BaseModel):
    model_id: str
    display_name: str
    provider_name: str
    provider_class: str = "LOCAL_MT"  # LOCAL_MT, LOCAL_AI, APPLE_LOCAL, CLOUD_AI, PUBLIC_WEB, TEST
    privacy_class: str = "OFFLINE"     # OFFLINE, APPLE_LOCAL, CLOUD_USER_ENABLED, PUBLIC_WEB_USER_ENABLED
    cost_class: str = "FREE_LOCAL"
    architecture: str                  # seq2seq, decoder_only, cloud_multimodal, apple_translation, web_endpoint
    execution_backends: List[str]
    source_languages: List[str]
    target_languages: List[str]
    translation_capable: bool
    review_capable: bool
    parameter_count: str
    precision: str
    quantization: str
    estimated_runtime_ram_gb: float
    minimum_recommended_ram_gb: float
    recommended_ram_gb: float
    verified: bool
    official_source_url: str
    role: str                          # PRIMARY_TRANSLATION, SECONDARY_TRANSLATION, REVIEWER_QA, CLOUD_ALL, REFERENCE_ONLY
    direct_pair: bool = True
    pivot_languages: List[str] = Field(default_factory=list)
    route_description: str = "Direct (ar -> ur)"
    target_prefix_token: Optional[str] = None  # Model-specific token (e.g. <2ur> for MADLAD)

class TranslationResult(BaseModel):
    source_text: str
    translated_text: str
    provider_name: str
    provider_class: str = "LOCAL_MT"
    privacy_class: str = "OFFLINE"
    model_name: str
    execution_backend: str = "native"
    route: str = "ar -> ur"
    is_pivot: bool = False
    pivot_languages: List[str] = Field(default_factory=list)
    english_intermediate: Optional[str] = None
    latency_ms: int
    peak_ram_mb: float = 0.0
    memory_pressure: str = "GREEN"
    raw_response: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    is_cloud: bool = False

class ReviewResult(BaseModel):
    source_text: str
    candidate_urdu: str
    revised_urdu: str
    qa_verdict: str  # PASS, WARNING, REVIEW_REQUIRED
    comments: List[str] = Field(default_factory=list)
    provider_name: str
    model_name: str
    latency_ms: int
    is_cloud: bool = False

class ProviderScorecard(BaseModel):
    provider_id: str
    provider_name: str
    provider_class: str
    privacy_class: str
    cost_class: str
    route: str
    is_pivot: bool = False
    pivot_languages: List[str] = Field(default_factory=list)
    sample_count: int = 0
    documents_sampled: int = 0
    pages_sampled: int = 0
    human_reviews: int = 0
    quality_score: Optional[float] = None
    meaning_score: Optional[float] = None
    completeness_score: Optional[float] = None
    naturalness_score: Optional[float] = None
    terminology_score: Optional[float] = None
    overall_score: Optional[float] = None
    latency_ms: Optional[float] = None
    peak_ram_mb: Optional[float] = None
    model_load_time_ms: Optional[float] = None
    availability_status: str = "NOT_TESTED"  # NOT_SUPPORTED, NOT_INSTALLED, DOWNLOAD_REQUIRED, AVAILABLE, TESTING, VERIFIED, FAILED

class Tuple_Availability(BaseModel):
    is_available: bool
    status_message: str
    status_code: str = "AVAILABLE"  # NOT_SUPPORTED, NOT_INSTALLED, DOWNLOAD_REQUIRED, AVAILABLE, VERIFIED, FAILED
    details: Dict[str, Any] = Field(default_factory=dict)

class AIProvider(ABC):
    """Base provider abstraction for all Tarjuman translation and review engines."""
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def get_provider_class(self) -> ProviderClass:
        pass

    @abstractmethod
    def get_privacy_class(self) -> PrivacyClass:
        pass

    @abstractmethod
    def is_cloud(self) -> bool:
        pass

    @abstractmethod
    async def check_availability(self) -> Tuple_Availability:
        pass

    @abstractmethod
    async def test_arabic_urdu_model(self, model_id: str) -> Dict[str, Any]:
        """Runs a real live test: كيف حالك؟ -> verifies Urdu output."""
        pass

class TranslationModelAdapter(ABC):
    """Adapter for specialized sequence-to-sequence translation models."""
    @abstractmethod
    async def translate(self, source_text: str, source_lang: str = "ar", target_lang: str = "ur", **kwargs) -> TranslationResult:
        pass

class ChatModelAdapter(ABC):
    """Adapter for instruction-tuned LLMs used for translation and semantic QA."""
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def translate_via_chat(self, source_text: str, model: str) -> TranslationResult:
        pass

    @abstractmethod
    async def review_translation(
        self,
        source_arabic: str,
        candidate_urdu: str,
        glossary_terms: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None
    ) -> ReviewResult:
        pass


