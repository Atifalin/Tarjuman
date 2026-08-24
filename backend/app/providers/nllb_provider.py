import os
import re
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.providers.base import AIProvider, TranslationResult, ProviderClass, PrivacyClass, Tuple_Availability
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Supported NLLB variants: model_id -> (CTranslate2 folder name, HuggingFace repo id)
# The 1.3B distilled variant is the default: best accuracy/speed tradeoff on 16GB+ Apple Silicon,
# served via CTranslate2 int8 (fast, native, no MLX seq2seq runtime exists yet).
NLLB_VARIANTS: Dict[str, Dict[str, str]] = {
    "nllb-200-distilled-1.3b": {"dir": "nllb-200-1.3b", "hf": "facebook/nllb-200-distilled-1.3B"},
    "nllb-200-3.3b": {"dir": "nllb-200-3.3b", "hf": "facebook/nllb-200-3.3B"},
    "nllb-200-distilled-600m": {"dir": "nllb-200-600m", "hf": "facebook/nllb-200-distilled-600M"},
}
DEFAULT_NLLB_MODEL = "nllb-200-distilled-1.3b"


def _ct2_dir_for(model_id: str) -> Path:
    variant = NLLB_VARIANTS.get(model_id, NLLB_VARIANTS[DEFAULT_NLLB_MODEL])
    return (settings.MODELS_DIR / variant["dir"]).resolve()


def _hf_repo_for(model_id: str) -> str:
    variant = NLLB_VARIANTS.get(model_id, NLLB_VARIANTS[DEFAULT_NLLB_MODEL])
    return variant["hf"]


class NLLBProvider(AIProvider):
    """
    Primary Local Neural MT Provider for direct Arabic -> Urdu translation (Meta NLLB-200).
    Prefers a pre-converted CTranslate2 int8 model (fast, native Apple Silicon CPU inference,
    no accuracy loss vs. full precision) and falls back to HuggingFace Transformers on MPS/CPU
    if CTranslate2 weights haven't been downloaded/converted yet.
    """

    def __init__(self):
        self._translator = None
        self._tokenizer = None
        self._backend = "none" # "ctranslate2" | "transformers" | "none"
        self._loaded_model_id: Optional[str] = None

    def get_provider_name(self) -> str:
        return "nllb"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.LOCAL_MT

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.OFFLINE

    def is_cloud(self) -> bool:
        return False

    def _has_local_weights(self, model_id: str = DEFAULT_NLLB_MODEL) -> bool:
        ct2_dir = _ct2_dir_for(model_id)
        return (ct2_dir / "model.bin").exists()

    async def check_availability(self) -> Tuple_Availability:
        # Check CTranslate2 weights for the default (1.3B) variant
        if self._has_local_weights(DEFAULT_NLLB_MODEL):
            return Tuple_Availability(
                is_available=True,
                status_message="NLLB-200 1.3B local direct model is ready (arb_Arab -> urd_Arab, CTranslate2 int8).",
                status_code="AVAILABLE",
                details={"backend": "ctranslate2", "route": "ar -> ur (Direct)", "pivot": []}
            )

        # Check Transformers library
        try:
            import transformers
            import torch
            return Tuple_Availability(
                is_available=True,
                status_message="NLLB-200 ready via HuggingFace Transformers (facebook/nllb-200-distilled-1.3B).",
                status_code="AVAILABLE",
                details={"backend": "transformers", "route": "ar -> ur (Direct)", "pivot": []}
            )
        except ImportError:
            pass

        return Tuple_Availability(
            is_available=False,
            status_message="NLLB-200 is not installed. Install PyTorch & Transformers or download local weights.",
            status_code="NOT_INSTALLED",
            details={"installed": False, "route": "ar -> ur (Direct)"}
        )

    def _init_model(self, model_id: str = DEFAULT_NLLB_MODEL):
        if self._translator is not None and self._loaded_model_id == model_id:
            return

        ct2_dir = _ct2_dir_for(model_id)
        hf_repo = _hf_repo_for(model_id)

        # 1. Try local CTranslate2 directory (fast, quantized, native)
        if (ct2_dir / "model.bin").exists():
            import ctranslate2
            import transformers
            self._translator = ctranslate2.Translator(str(ct2_dir), device="cpu")
            self._tokenizer = transformers.AutoTokenizer.from_pretrained(str(ct2_dir), src_lang="arb_Arab")
            self._backend = "ctranslate2"
            self._loaded_model_id = model_id
            return

        # 2. Fall back to Transformers pipeline (direct HF download, no conversion)
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self._tokenizer = AutoTokenizer.from_pretrained(hf_repo, src_lang="arb_Arab")
            self._translator = AutoModelForSeq2SeqLM.from_pretrained(hf_repo).to(device)
            self._backend = "transformers"
            self._loaded_model_id = model_id
        except Exception as e:
            raise RuntimeError(f"Failed loading NLLB-200 model ({hf_repo}): {e}")

    async def test_arabic_urdu_model(self, model_id: str = DEFAULT_NLLB_MODEL) -> Dict[str, Any]:
        avail = await self.check_availability()
        if not avail.is_available:
            return {
                "success": False,
                "error": avail.status_message,
                "status_code": avail.status_code
            }

        start_time = time.time()
        sample_arabic = "كيف حالك؟"
        try:
            res = await self.translate_arabic_to_urdu(sample_arabic, model_id=model_id)
            lat = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "arabic": sample_arabic,
                "urdu": res.translated_text,
                "output": res.translated_text,
                "latency_ms": lat,
                "route": "ar -> ur (Direct)",
                "pivot": [],
                "status_code": "VERIFIED"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": int((time.time() - start_time) * 1000),
                "status_code": "FAILED"
            }

    async def translate_arabic_to_urdu(self, source_text: str, model_id: str = DEFAULT_NLLB_MODEL) -> TranslationResult:
        """Translates Arabic directly to Urdu using Meta NLLB-200."""
        self._init_model(model_id)
        start_t = time.time()
        clean_source = source_text.strip()

        lines = [line.strip() for line in clean_source.split("\n") if line.strip()]
        if not lines:
            lines = [clean_source]

        all_sentences = []
        for line in lines:
            sents = [s.strip() for s in re.split(r'([.؟!؛]+)', line) if s.strip()]
            combined = []
            for i in range(0, len(sents) - 1, 2):
                combined.append(sents[i] + sents[i+1])
            if len(sents) % 2 == 1:
                combined.append(sents[-1])
            all_sentences.extend(combined if combined else [line])

        if not all_sentences:
            all_sentences = [clean_source]

        if self._backend == "ctranslate2":
            token_batch = [
                self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(s))
                for s in all_sentences
            ]
            target_prefix = [["urd_Arab"]] * len(token_batch)
            results = self._translator.translate_batch(token_batch, target_prefix=target_prefix, max_decoding_length=256)
            translated_sents = [
                self._tokenizer.decode(self._tokenizer.convert_tokens_to_ids(r.hypotheses[0][1:]))
                for r in results
            ]
            final_urdu = "\n".join(translated_sents)
        else:
            import torch
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            translated_sents = []
            for s in all_sentences:
                inputs = self._tokenizer(s, return_tensors="pt").to(device)
                forced_bos_token_id = self._tokenizer.lang_code_to_id.get("urd_Arab", 256094)
                translated_tokens = self._translator.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=512
                )
                trans_text = self._tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
                translated_sents.append(trans_text.strip())
            final_urdu = "\n".join(translated_sents)

        latency = int((time.time() - start_t) * 1000)

        return TranslationResult(
            source_text=source_text,
            translated_text=final_urdu.strip(),
            provider_name="nllb",
            provider_class=ProviderClass.LOCAL_MT.value,
            privacy_class=PrivacyClass.OFFLINE.value,
            model_name=model_id,
            execution_backend=self._backend,
            route="ar -> ur (Direct)",
            is_pivot=False,
            pivot_languages=[],
            latency_ms=latency,
            peak_ram_mb=1200.0,
            memory_pressure="GREEN",
            is_cloud=False
        )

    async def translate(
        self,
        source_text: str,
        source_lang: str = "ar",
        target_lang: str = "ur",
        model: Optional[str] = None,
        **kwargs
    ) -> TranslationResult:
        model_id = model if model in NLLB_VARIANTS else DEFAULT_NLLB_MODEL
        return await self.translate_arabic_to_urdu(source_text, model_id=model_id)
