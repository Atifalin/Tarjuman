import re
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from backend.app.providers.base import (
    AIProvider,
    ProviderClass,
    PrivacyClass,
    TranslationResult,
    Tuple_Availability
)

logger = logging.getLogger(__name__)

# Configure local workspace directory for Argos packages to avoid macOS sandbox issues
ARGOS_DATA_DIR = (Path(__file__).resolve().parent.parent.parent.parent / "data" / "argos_data")
ARGOS_DATA_DIR.mkdir(parents=True, exist_ok=True)

try:
    import argostranslate.settings
    argostranslate.settings.data_dir = ARGOS_DATA_DIR
    argostranslate.settings.cache_dir = ARGOS_DATA_DIR
    argostranslate.settings.package_dirs = [ARGOS_DATA_DIR / "packages"]
    argostranslate.settings.local_package_index = ARGOS_DATA_DIR / "index.json"
except Exception:
    pass

class ArgosProvider(AIProvider):
    """
    Open-source Offline Neural Machine Translation Provider using OpenNMT / CTranslate2.
    Explicitly operates and reports pivot route: Arabic -> English -> Urdu.
    """

    def __init__(self):
        self._initialized = False
        self._sp_ar_en = None
        self._tr_ar_en = None
        self._sp_en_ur = None
        self._tr_en_ur = None

    def get_provider_name(self) -> str:
        return "argos"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.LOCAL_MT

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.OFFLINE

    def is_cloud(self) -> bool:
        return False

    def _packages_installed(self) -> bool:
        ar_en = ARGOS_DATA_DIR / "packages" / "ar_en" / "model"
        en_ur = ARGOS_DATA_DIR / "packages" / "en_ur" / "model"
        return ar_en.exists() and en_ur.exists()

    async def check_availability(self) -> Tuple_Availability:
        try:
            import ctranslate2
            import sentencepiece
        except ImportError:
            return Tuple_Availability(
                is_available=False,
                status_message="Argos Translate dependencies (ctranslate2/sentencepiece) not installed.",
                status_code="NOT_INSTALLED",
                details={"installed": False}
            )

        if not self._packages_installed():
            return Tuple_Availability(
                is_available=False,
                status_message="Argos offline models missing. Click 'Install Argos (~90 MB)' to download.",
                status_code="DOWNLOAD_REQUIRED",
                details={"installed": True, "packages_ready": False, "required": ["ar_en", "en_ur"]}
            )

        return Tuple_Availability(
            is_available=True,
            status_message="Argos Translate offline engine is ready (Pivot: ar -> en -> ur).",
            status_code="AVAILABLE",
            details={"route": "ar -> en -> ur", "pivot": ["en"], "engine": "CTranslate2 / OpenNMT"}
        )

    def _init_models(self):
        if self._initialized:
            return

        import ctranslate2
        import sentencepiece as spm

        pkg_dir = ARGOS_DATA_DIR / "packages"
        ar_en_dir = pkg_dir / "ar_en"
        en_ur_dir = pkg_dir / "en_ur"

        if not (ar_en_dir.exists() and en_ur_dir.exists()):
            raise RuntimeError("Argos packages ar_en or en_ur not found in local package store.")

        self._sp_ar_en = spm.SentencePieceProcessor(model_file=str(ar_en_dir / "sentencepiece.model"))
        self._tr_ar_en = ctranslate2.Translator(str(ar_en_dir / "model"), device="cpu")

        self._sp_en_ur = spm.SentencePieceProcessor(model_file=str(en_ur_dir / "sentencepiece.model"))
        self._tr_en_ur = ctranslate2.Translator(str(en_ur_dir / "model"), device="cpu")
        self._initialized = True

    async def test_arabic_urdu_model(self, model_id: str = "argos-translate") -> Dict[str, Any]:
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
            res = await self.translate_arabic_to_urdu(sample_arabic)
            lat = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "arabic": sample_arabic,
                "english_intermediate": res.english_intermediate,
                "urdu": res.translated_text,
                "output": res.translated_text,
                "latency_ms": lat,
                "route": res.route,
                "pivot": res.pivot_languages,
                "status_code": "VERIFIED"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": int((time.time() - start_time) * 1000),
                "status_code": "FAILED"
            }

    async def translate_arabic_to_urdu(self, source_text: str) -> TranslationResult:
        """
        Executes explicit two-stage CTranslate2 offline translation:
        1. Arabic -> English (intermediate)
        2. English -> Urdu (final)
        """
        if not self._packages_installed():
            raise RuntimeError(
                "Argos packages for Arabic -> English -> Urdu are not installed. "
                "Please click 'Install Argos (~90 MB)' in Setup Wizard."
            )

        self._init_models()
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

        # Stage 1: Batch Arabic -> English
        ar_token_batch = [self._sp_ar_en.encode(s, out_type=str) for s in all_sentences]
        ar_res = self._tr_ar_en.translate_batch(ar_token_batch, max_decoding_length=256)
        en_sentences = [
            self._sp_ar_en.decode(r.hypotheses[0]).replace("▁", " ").strip()
            for r in ar_res
        ]
        english_intermediate = "\n".join(en_sentences)

        # Stage 2: Batch English -> Urdu
        en_token_batch = [self._sp_en_ur.encode(s, out_type=str) for s in en_sentences]
        ur_res = self._tr_en_ur.translate_batch(en_token_batch, max_decoding_length=256)
        ur_sentences = [
            self._sp_en_ur.decode(r.hypotheses[0]).replace("▁", " ").strip()
            for r in ur_res
        ]
        final_urdu = "\n".join(ur_sentences)

        latency = int((time.time() - start_t) * 1000)

        return TranslationResult(
            source_text=source_text,
            translated_text=final_urdu,
            provider_name="argos",
            provider_class=ProviderClass.LOCAL_MT.value,
            privacy_class=PrivacyClass.OFFLINE.value,
            model_name="argos-translate",
            execution_backend="ctranslate2",
            route="ar -> en -> ur",
            is_pivot=True,
            pivot_languages=["en"],
            english_intermediate=english_intermediate,
            latency_ms=latency,
            peak_ram_mb=350.0,
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
        return await self.translate_arabic_to_urdu(source_text)

    async def translate_arabic_to_english(self, source_text: str) -> str:
        """Translates Arabic -> English directly using the ar_en CTranslate2 model."""
        if not self._packages_installed():
            raise RuntimeError(
                "Argos packages for Arabic -> English are not installed. "
                "Please click 'Install Argos (~90 MB)' in Setup Wizard."
            )
        if not source_text.strip():
            return ""

        self._init_models()
        lines = [line.strip() for line in source_text.split("\n") if line.strip()]
        sents = []
        for line in lines:
            sents.extend([s.strip() for s in re.split(r'([.؟!؛]+)', line) if s.strip()])
        if not sents:
            sents = [source_text.strip()]

        combined = []
        for i in range(0, len(sents) - 1, 2):
            combined.append(sents[i] + sents[i + 1])
        if len(sents) % 2 == 1:
            combined.append(sents[-1])

        ar_tokens = [self._sp_ar_en.encode(s, out_type=str) for s in combined]
        ar_res = self._tr_ar_en.translate_batch(ar_tokens, max_decoding_length=256)
        en_sentences = [
            self._sp_ar_en.decode(r.hypotheses[0]).replace("▁", " ").strip()
            for r in ar_res
        ]
        return " ".join(en_sentences)
