import time
import logging
from typing import Dict, Any, Optional
from backend.app.providers.base import (
    AIProvider,
    TranslationModelAdapter,
    TranslationResult,
    Tuple_Availability,
    ProviderClass,
    PrivacyClass
)

logger = logging.getLogger(__name__)

class TransformersProvider(AIProvider, TranslationModelAdapter):
    """
    Direct Local Transformers / PyTorch Seq2Seq Provider.
    Specifically tuned for Seq2Seq Machine Translation models:
    - Google MADLAD-400 7B MT (target prefix: `<2ur> `)
    Executes true Seq2Seq encoder-decoder inference on Apple Silicon MPS / CPU.
    Never routes translation models through chat APIs.

    NOTE: `check_availability()` only reports whether the PyTorch/Transformers *runtime*
    is installed — it deliberately does NOT imply model weights are downloaded. MADLAD-400
    7B is a ~14GB download that only happens when a user explicitly runs `translate()`/
    `test_arabic_urdu_model()` for it; use `has_local_weights_cached()` to check first
    before wiring this provider into any automated/batch flow (e.g. "Run All Benchmarks").
    """

    HF_REPO_MAP = {
        "madlad400-7b-mt": "google/madlad400-7b-mt",
    }

    def __init__(self):
        self._loaded_models = {}
        self._loaded_tokenizers = {}

    def get_provider_name(self) -> str:
        return "transformers"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.LOCAL_MT

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.OFFLINE

    def is_cloud(self) -> bool:
        return False

    def has_local_weights_cached(self, model_id: str) -> bool:
        """Checks the local HuggingFace cache for already-downloaded weights, without downloading anything."""
        repo_id = self.HF_REPO_MAP.get(model_id.lower())
        if not repo_id:
            return False
        try:
            from huggingface_hub import scan_cache_dir
            cache_info = scan_cache_dir()
            return any(repo.repo_id == repo_id for repo in cache_info.repos)
        except Exception:
            return False

    async def check_availability(self) -> Tuple_Availability:
        try:
            import torch
            import transformers
            has_mps = torch.backends.mps.is_available()
            return Tuple_Availability(
                is_available=True,
                status_message=f"Local PyTorch Seq2Seq runtime ready (Apple Silicon MPS: {'Enabled' if has_mps else 'CPU mode'}). Model weights are downloaded separately on first use.",
                details={
                    "mps_available": has_mps,
                    "torch_version": torch.__version__,
                    "transformers_version": transformers.__version__,
                    "supported_models": ["madlad400-7b-mt"]
                }
            )
        except ImportError as e:
            return Tuple_Availability(
                is_available=False,
                status_message=f"PyTorch / Transformers not installed: {e}",
                details={"installed": False}
            )

    async def translate(
        self,
        source_text: str,
        source_lang: str = "ar",
        target_lang: str = "ur",
        model: str = "madlad400-7b-mt",
        **kwargs
    ) -> TranslationResult:
        """
        Executes genuine Seq2Seq translation pipeline according to model architecture.
        """
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        t0 = time.perf_counter()
        device = "mps" if torch.backends.mps.is_available() else "cpu"

        # 1. Google MADLAD-400 Seq2Seq Inference
        if "madlad" in model.lower():
            # MADLAD requires target prefix `<2ur> `
            prepared_text = f"<2ur> {source_text.strip()}"
            
            # Check if weights loaded or in cache
            if model not in self._loaded_models:
                try:
                    tok = AutoTokenizer.from_pretrained("google/madlad400-7b-mt")
                    mdl = AutoModelForSeq2SeqLM.from_pretrained(
                        "google/madlad400-7b-mt",
                        torch_dtype=torch.float16 if device == "mps" else torch.float32,
                        low_cpu_mem_usage=True
                    ).to(device)
                    self._loaded_tokenizers[model] = tok
                    self._loaded_models[model] = mdl
                except Exception as e:
                    raise RuntimeError(f"MADLAD-400 7B MT model weights not available locally in cache: {e}")

            tok = self._loaded_tokenizers[model]
            mdl = self._loaded_models[model]

            inputs = tok(prepared_text, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = mdl.generate(
                    **inputs,
                    max_new_tokens=kwargs.get("max_tokens", 512),
                    temperature=0.0
                )
            translated = tok.decode(outputs[0], skip_special_tokens=True).strip()

        else:
            raise ValueError(f"Unknown Seq2Seq translation model identifier: {model}. Use NLLBProvider for NLLB-200 models.")

        latency = int((time.perf_counter() - t0) * 1000)
        return TranslationResult(
            source_text=source_text,
            translated_text=translated,
            provider_name="transformers",
            model_name=model,
            latency_ms=latency,
            is_cloud=False
        )

    async def test_arabic_urdu_model(self, model_id: str) -> Dict[str, Any]:
        """Validates real Arabic -> Urdu translation using Seq2Seq pipeline."""
        test_source = "كيف حالك؟"
        try:
            res = await self.translate(test_source, model=model_id)
            urdu = res.translated_text
            if not urdu or urdu == test_source:
                return {"success": False, "error": "Empty or identical output from Seq2Seq model."}
            return {
                "success": True,
                "model": model_id,
                "source": test_source,
                "output": urdu,
                "latency_ms": res.latency_ms,
                "verified": True,
                "architecture": "seq2seq_encoder_decoder"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Seq2Seq model {model_id} verification check: {str(e)}"
            }
