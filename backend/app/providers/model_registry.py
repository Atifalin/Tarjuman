from typing import List, Dict, Optional
from backend.app.providers.base import ModelCapability

# Verified Model Capability Catalog across all 5 Provider Categories
MODEL_REGISTRY: Dict[str, ModelCapability] = {
    # -------------------------------------------------------------
    # Category A: LOCAL_MT (Dedicated Local Machine Translation)
    # -------------------------------------------------------------
    "madlad400-7b-mt": ModelCapability(
        model_id="madlad400-7b-mt",
        display_name="Google MADLAD-400 7B MT",
        provider_name="transformers",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="seq2seq",
        execution_backends=["transformers", "mlx"],
        source_languages=["ar", "ara", "arb_Arab"],
        target_languages=["ur", "urd", "urd_Arab"],
        translation_capable=True,
        review_capable=False,
        parameter_count="7.2B",
        precision="float16 / 4-bit quantized",
        quantization="4-bit recommended on 16GB; fp16 on 32GB+",
        estimated_runtime_ram_gb=11.2,
        minimum_recommended_ram_gb=16.0,
        recommended_ram_gb=32.0,
        verified=True,
        official_source_url="https://huggingface.co/google/madlad400-7b-mt",
        role="PRIMARY_OR_ESCALATION",
        direct_pair=True,
        route_description="Direct (ar -> ur)",
        target_prefix_token="<2ur>"
    ),

    "nllb-200-distilled-1.3b": ModelCapability(
        model_id="nllb-200-distilled-1.3b",
        display_name="Meta NLLB-200 1.3B Distilled (MLX-class accuracy, CTranslate2 native)",
        provider_name="nllb",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="seq2seq",
        execution_backends=["ctranslate2", "transformers"],
        source_languages=["arb_Arab", "ar"],
        target_languages=["urd_Arab", "ur"],
        translation_capable=True,
        review_capable=False,
        parameter_count="1.3B",
        precision="int8 (CTranslate2)",
        quantization="int8",
        estimated_runtime_ram_gb=2.6,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://huggingface.co/facebook/nllb-200-distilled-1.3B",
        role="PRIMARY_OR_FAST_LOCAL",
        direct_pair=True,
        route_description="Direct (arb_Arab -> urd_Arab), native CTranslate2 int8 on Apple Silicon CPU (no MLX seq2seq runtime exists)"
    ),

    "madlad400-10b-mt": ModelCapability(
        model_id="madlad400-10b-mt",
        display_name="Google MADLAD-400 10.7B MT (Higher Quality — 32GB+ RAM Recommended)",
        provider_name="transformers",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="seq2seq",
        execution_backends=["transformers"],
        source_languages=["ar", "ara", "arb_Arab"],
        target_languages=["ur", "urd", "urd_Arab"],
        translation_capable=True,
        review_capable=False,
        parameter_count="10.7B",
        precision="float16",
        quantization="fp16 (32GB+ RAM); use madlad400-7b-mt on 16-24GB Macs instead",
        estimated_runtime_ram_gb=21.0,
        minimum_recommended_ram_gb=32.0,
        recommended_ram_gb=32.0,
        verified=True,
        official_source_url="https://huggingface.co/google/madlad400-10b-mt",
        role="PRIMARY_HIGH_QUALITY",
        direct_pair=True,
        route_description="Direct (ar -> ur). Google's largest MADLAD-400 checkpoint (trained on 250B tokens across 450+ languages, explicitly including Urdu) — reported by Google to be competitive with significantly larger models. Requires a separate ~21GB fp16 download; only offered on 32GB+ RAM Macs.",
        target_prefix_token="<2ur>"
    ),

    "nllb-200-3.3b": ModelCapability(
        model_id="nllb-200-3.3b",
        display_name="Meta NLLB-200 3.3B (Higher Quality — 32GB+ RAM Recommended)",
        provider_name="nllb",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="seq2seq",
        execution_backends=["ctranslate2", "transformers"],
        source_languages=["arb_Arab", "ar"],
        target_languages=["urd_Arab", "ur"],
        translation_capable=True,
        review_capable=False,
        parameter_count="3.3B",
        precision="int8 (CTranslate2)",
        quantization="int8",
        estimated_runtime_ram_gb=6.5,
        minimum_recommended_ram_gb=32.0,
        recommended_ram_gb=32.0,
        verified=True,
        official_source_url="https://huggingface.co/facebook/nllb-200-3.3B",
        role="PRIMARY_HIGH_QUALITY",
        direct_pair=True,
        route_description="Direct (arb_Arab -> urd_Arab), native CTranslate2 int8 — noticeably better translation quality than the 1.3B distilled default, at the cost of ~2.5x the RAM and disk. Only offered on Macs with 32GB+ RAM; requires a separate ~6.6GB download."
    ),

    "nllb-200-distilled-600m": ModelCapability(
        model_id="nllb-200-distilled-600m",
        display_name="Meta NLLB-200 600M Distilled (Lightweight)",
        provider_name="transformers",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="seq2seq",
        execution_backends=["transformers"],
        source_languages=["arb_Arab", "ar"],
        target_languages=["urd_Arab", "ur"],
        translation_capable=True,
        review_capable=False,
        parameter_count="600M",
        precision="float16 / int8",
        quantization="Lightweight",
        estimated_runtime_ram_gb=1.8,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://huggingface.co/facebook/nllb-200-distilled-600M",
        role="PRIMARY_OR_FAST_LOCAL",
        direct_pair=True,
        route_description="Direct (arb_Arab -> urd_Arab)"
    ),

    "argos-translate": ModelCapability(
        model_id="argos-translate",
        display_name="Argos Translate (CTranslate2 Offline)",
        provider_name="argos",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="opennmt_ctranslate2",
        execution_backends=["ctranslate2", "argostranslate"],
        source_languages=["ar"],
        target_languages=["ur", "en"],
        translation_capable=True,
        review_capable=False,
        parameter_count="Offline Seq2Seq",
        precision="int8",
        quantization="CTranslate2 int8",
        estimated_runtime_ram_gb=1.5,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://www.argosopentech.com/",
        role="PRIMARY_OR_FAST_LOCAL",
        direct_pair=False,
        pivot_languages=["en"],
        route_description="Pivot: Arabic -> English -> Urdu"
    ),

    "libretranslate-local": ModelCapability(
        model_id="libretranslate-local",
        display_name="LibreTranslate Local (Self-Hosted)",
        provider_name="libretranslate",
        provider_class="LOCAL_MT",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="libretranslate_api",
        execution_backends=["local_http"],
        source_languages=["ar"],
        target_languages=["ur", "en"],
        translation_capable=True,
        review_capable=False,
        parameter_count="Local Service",
        precision="int8",
        quantization="Local",
        estimated_runtime_ram_gb=2.0,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://libretranslate.com/",
        role="PRIMARY_OR_FAST_LOCAL",
        direct_pair=False,
        pivot_languages=["en"],
        route_description="Local Server (ar -> en -> ur)"
    ),

    # -------------------------------------------------------------
    # Category B: LOCAL_AI (Local General AI / LLMs)
    # -------------------------------------------------------------
    "qwen3:8b": ModelCapability(
        model_id="qwen3:8b",
        display_name="Qwen3 8B Instruct",
        provider_name="ollama",
        provider_class="LOCAL_AI",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="decoder_only",
        execution_backends=["ollama", "lmstudio", "mlx"],
        source_languages=["ar", "ur", "en"],
        target_languages=["ar", "ur", "en"],
        translation_capable=True,
        review_capable=True,
        parameter_count="8.2B",
        precision="q4_k_m",
        quantization="q4_k_m",
        estimated_runtime_ram_gb=5.6,
        minimum_recommended_ram_gb=14.0,
        recommended_ram_gb=32.0,
        verified=True,
        official_source_url="https://ollama.com/library/qwen3:8b",
        role="REVIEWER_OR_PRIMARY",
        direct_pair=True,
        route_description="Direct LLM Prompting"
    ),

    "qari-ocr-0.4.0-vl-4b": ModelCapability(
        model_id="qari-ocr-0.4.0-vl-4b",
        display_name="Qari-OCR-0.4.0 VL 4B (Arabic Manuscript OCR, MLX Native)",
        provider_name="mlx_vlm",
        provider_class="LOCAL_AI",
        privacy_class="OFFLINE",
        cost_class="FREE_LOCAL",
        architecture="vision_decoder_only",
        execution_backends=["mlx", "mlx_vlm"],
        source_languages=["ar"],
        target_languages=["ar"],
        translation_capable=False,
        review_capable=False,
        parameter_count="4B",
        precision="4-bit (MLX)",
        quantization="4-bit",
        estimated_runtime_ram_gb=3.5,
        minimum_recommended_ram_gb=16.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://huggingface.co/NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct",
        role="OCR_PRIMARY",
        direct_pair=True,
        route_description="Scanned page image -> transcribed Arabic text (native MLX / Apple Silicon GPU)"
    ),

    "apple-foundation-models": ModelCapability(
        model_id="apple-foundation-models",
        display_name="Apple Foundation Models (On-Device Intelligence)",
        provider_name="apple_intelligence",
        provider_class="LOCAL_AI",
        privacy_class="APPLE_LOCAL",
        cost_class="FREE_APPLE",
        architecture="apple_foundation",
        execution_backends=["apple_intelligence"],
        source_languages=["ar", "ur", "en"],
        target_languages=["ar", "ur", "en"],
        translation_capable=True,
        review_capable=True,
        parameter_count="3B On-Device",
        precision="Apple Silicon Optimized",
        quantization="CoreML",
        estimated_runtime_ram_gb=2.5,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=False,
        official_source_url="https://developer.apple.com/apple-intelligence/",
        role="REVIEWER_OR_PRIMARY",
        direct_pair=True,
        route_description="Apple Neural Engine"
    ),

    # -------------------------------------------------------------
    # Category C: APPLE_LOCAL (Apple Native Translation Framework)
    # -------------------------------------------------------------
    "apple-native-translation": ModelCapability(
        model_id="apple-native-translation",
        display_name="Apple Translation Framework (macOS 15+)",
        provider_name="apple_translation",
        provider_class="APPLE_LOCAL",
        privacy_class="APPLE_LOCAL",
        cost_class="FREE_APPLE",
        architecture="apple_translation",
        execution_backends=["apple_framework"],
        source_languages=["ar", "en"],
        target_languages=["ur", "en"],
        translation_capable=True,
        review_capable=False,
        parameter_count="On-Device CoreML",
        precision="Neural Engine",
        quantization="Apple Silicon ANE",
        estimated_runtime_ram_gb=1.2,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=False,
        official_source_url="https://developer.apple.com/documentation/translation",
        role="PRIMARY_OR_FAST_LOCAL",
        direct_pair=True,
        route_description="Apple On-Device TranslationSession"
    ),

    # -------------------------------------------------------------
    # Category D: CLOUD_AI (Cloud LLM Services - Opt-In Only)
    # -------------------------------------------------------------
    "gemini-3.6-flash": ModelCapability(
        model_id="gemini-3.6-flash",
        display_name="Google Gemini 3.6 Flash (Cloud)",
        provider_name="gemini",
        provider_class="CLOUD_AI",
        privacy_class="CLOUD_USER_ENABLED",
        cost_class="CLOUD_FREE_TIER",
        architecture="cloud_multimodal",
        execution_backends=["gemini_api"],
        source_languages=["ar", "ara", "all"],
        target_languages=["ur", "urd", "all"],
        translation_capable=True,
        review_capable=True,
        parameter_count="Cloud",
        precision="N/A",
        quantization="Cloud Hosted",
        estimated_runtime_ram_gb=0.1,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://ai.google.dev/",
        role="CLOUD_ALL",
        direct_pair=True,
        route_description="Google Generative AI API"
    ),

    "gemini-3.6-pro": ModelCapability(
        model_id="gemini-3.6-pro",
        display_name="Google Gemini 3.6 Pro (Cloud - Deep Reasoning)",
        provider_name="gemini",
        provider_class="CLOUD_AI",
        privacy_class="CLOUD_USER_ENABLED",
        cost_class="CLOUD_FREE_TIER",
        architecture="cloud_multimodal",
        execution_backends=["gemini_api"],
        source_languages=["ar", "ara", "all"],
        target_languages=["ur", "urd", "all"],
        translation_capable=True,
        review_capable=True,
        parameter_count="Cloud",
        precision="N/A",
        quantization="Cloud Hosted",
        estimated_runtime_ram_gb=0.1,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://ai.google.dev/",
        role="CLOUD_ALL",
        direct_pair=True,
        route_description="Google Generative AI API"
    ),

    # -------------------------------------------------------------
    # Category E: PUBLIC_WEB (Public Web Services - Opt-In Only)
    # -------------------------------------------------------------
    "google-web-unofficial": ModelCapability(
        model_id="google-web-unofficial",
        display_name="Google Translate Web (Unofficial)",
        provider_name="public_web",
        provider_class="PUBLIC_WEB",
        privacy_class="PUBLIC_WEB_USER_ENABLED",
        cost_class="PUBLIC_WEB",
        architecture="web_endpoint",
        execution_backends=["web_gtx"],
        source_languages=["ar"],
        target_languages=["ur", "en"],
        translation_capable=True,
        review_capable=False,
        parameter_count="Web Endpoint",
        precision="N/A",
        quantization="Public Endpoint",
        estimated_runtime_ram_gb=0.1,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://translate.google.com",
        role="REFERENCE_OR_FALLBACK",
        direct_pair=True,
        route_description="Google Web Endpoint (gtx)"
    ),

    "lingva-public": ModelCapability(
        model_id="lingva-public",
        display_name="Lingva Translate (Public Instance)",
        provider_name="public_web",
        provider_class="PUBLIC_WEB",
        privacy_class="PUBLIC_WEB_USER_ENABLED",
        cost_class="PUBLIC_WEB",
        architecture="web_endpoint",
        execution_backends=["web_lingva"],
        source_languages=["ar"],
        target_languages=["ur", "en"],
        translation_capable=True,
        review_capable=False,
        parameter_count="Web Endpoint",
        precision="N/A",
        quantization="Public Endpoint",
        estimated_runtime_ram_gb=0.1,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://lingva.ml",
        role="REFERENCE_OR_FALLBACK",
        direct_pair=True,
        route_description="Lingva Public Instance"
    ),

    "mymemory-public": ModelCapability(
        model_id="mymemory-public",
        display_name="MyMemory Translation API (Public)",
        provider_name="public_web",
        provider_class="PUBLIC_WEB",
        privacy_class="PUBLIC_WEB_USER_ENABLED",
        cost_class="PUBLIC_WEB",
        architecture="web_endpoint",
        execution_backends=["web_mymemory"],
        source_languages=["ar"],
        target_languages=["ur", "en"],
        translation_capable=True,
        review_capable=False,
        parameter_count="Web Endpoint",
        precision="N/A",
        quantization="Public Endpoint",
        estimated_runtime_ram_gb=0.1,
        minimum_recommended_ram_gb=8.0,
        recommended_ram_gb=16.0,
        verified=True,
        official_source_url="https://mymemory.translated.net",
        role="REFERENCE_OR_FALLBACK",
        direct_pair=True,
        route_description="MyMemory Free API"
    ),
}

class ModelRegistry:
    """Registry query and validation helper."""

    @classmethod
    def get_capability(cls, model_id: str) -> Optional[ModelCapability]:
        return MODEL_REGISTRY.get(model_id)

    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelCapability]:
        return cls.get_capability(model_id)

    @classmethod
    def list_all(cls) -> List[ModelCapability]:
        return list(MODEL_REGISTRY.values())

    @classmethod
    def list_all_models(cls) -> List[ModelCapability]:
        return cls.list_all()

    @classmethod
    def list_by_provider_class(cls, provider_class: str) -> List[ModelCapability]:
        return [m for m in MODEL_REGISTRY.values() if m.provider_class == provider_class]

    @classmethod
    def list_translation_models(cls) -> List[ModelCapability]:
        return [m for m in MODEL_REGISTRY.values() if m.translation_capable]

    @classmethod
    def list_review_models(cls) -> List[ModelCapability]:
        return [m for m in MODEL_REGISTRY.values() if m.review_capable]

    @classmethod
    def list_reviewer_models(cls) -> List[ModelCapability]:
        return cls.list_review_models()

    @classmethod
    def list_safe_for_ram(cls, ram_gb: float) -> List[ModelCapability]:
        return [m for m in MODEL_REGISTRY.values() if m.minimum_recommended_ram_gb <= ram_gb]

    @classmethod
    def is_arabic_to_urdu_verified(cls, model_id: str) -> bool:
        model = cls.get_capability(model_id)
        if not model:
            return False
        has_ar = any(l in ["ar", "ara", "arb_Arab", "all"] for l in model.source_languages)
        has_ur = any(l in ["ur", "urd", "urd_Arab", "all"] for l in model.target_languages)
        return has_ar and has_ur and model.translation_capable and model.verified
