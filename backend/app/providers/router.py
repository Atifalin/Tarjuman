import logging
import json
import time
from typing import Dict, Any, Optional, Tuple, List
from backend.app.providers.base import (
    TranslationResult,
    ReviewResult,
    ProviderClass,
    PrivacyClass
)
from backend.app.providers.ollama_provider import OllamaProvider
from backend.app.providers.lmstudio_provider import LMStudioProvider
from backend.app.providers.gemini_provider import GeminiProvider
from backend.app.providers.transformers_provider import TransformersProvider
from backend.app.providers.nllb_provider import NLLBProvider
from backend.app.providers.argos_provider import ArgosProvider
from backend.app.providers.apple_provider import AppleTranslationProvider
from backend.app.providers.free_web_provider import FreeWebTranslator
from backend.app.providers.model_registry import ModelRegistry
from backend.app.qa.heuristics import QAEngine, QACheckResult
from backend.app.terminology.manager import TerminologyManager
from backend.app.terminology.translation_memory import TranslationMemory

logger = logging.getLogger(__name__)

class TranslationRouter:
    """
    Intelligent Adaptive Translation Router.
    Routes document chunks through verified local engines with 100% offline fallback:
    NLLB-200 (Direct ar -> ur) -> Argos Translate (Pivot ar -> en -> ur)
    """

    def __init__(self):
        self.ollama = OllamaProvider()
        self.lmstudio = LMStudioProvider()
        self.gemini = GeminiProvider()
        self.transformers = TransformersProvider()
        self.nllb = NLLBProvider()
        self.argos = ArgosProvider()
        self.apple = AppleTranslationProvider()
        self.free_web = FreeWebTranslator()

    def get_provider_for_model(self, model_id: str):
        meta = ModelRegistry.get_capability(model_id)
        if not meta:
            if "nllb" in model_id.lower():
                return self.nllb
            elif "gemini" in model_id.lower():
                return self.gemini
            elif "argos" in model_id.lower():
                return self.argos
            elif "apple" in model_id.lower():
                return self.apple
            elif "web" in model_id.lower() or "lingva" in model_id.lower() or "mymemory" in model_id.lower():
                return self.free_web
            return self.ollama
        
        pname = meta.provider_name.lower()
        if "nllb" in model_id.lower() or pname == "nllb":
            return self.nllb
        elif pname == "argos":
            return self.argos
        elif pname == "apple_translation":
            return self.apple
        elif pname == "public_web":
            return self.free_web
        elif pname == "transformers":
            return self.transformers
        elif pname == "gemini":
            return self.gemini
        elif pname == "lmstudio":
            return self.lmstudio
        return self.ollama

    async def route_translation(
        self,
        source_arabic: str,
        routing_strategy: str = "local_only",
        production_policy: str = "BALANCED",
        privacy_mode: str = "LOCAL_ONLY",
        primary_model_id: str = "nllb-200-distilled-1.3b",
        secondary_model_id: Optional[str] = None,
        reviewer_model_id: Optional[str] = "qwen3:8b",
        gemini_model_id: str = "gemini-3.6-flash",
        project_id: Optional[str] = None,
        bypass_tm: bool = False
    ) -> Dict[str, Any]:
        """
        Executes end-to-end chunk translation, checking TM, Glossary, QA, and adaptive escalation.
        Returns comprehensive result dictionary with unbroken provenance.
        Set bypass_tm=True to force a fresh translation (e.g. explicit "Regenerate") even if an
        identical source text was previously approved and cached in Translation Memory.
        """
        # 1. Check Translation Memory for identical approved text
        tm_match = None if bypass_tm else TranslationMemory.lookup_exact_match(source_arabic)
        glossary_terms = TerminologyManager.match_terms_in_text(source_arabic, project_id=project_id)

        if tm_match:
            qa_res = QAEngine.evaluate(source_arabic, tm_match.approved_urdu, glossary_terms)
            original_model = tm_match.source_model or "unknown (pre-provenance-tracking)"
            return {
                "source_text": source_arabic,
                "target_urdu": tm_match.approved_urdu,
                "secondary_urdu": None,
                "reviewer_urdu": None,
                "final_urdu": tm_match.approved_urdu,
                "qa_status": qa_res.verdict,
                "qa_issues": qa_res.issues,
                "primary_provider": "TranslationMemory",
                "primary_provider_class": "LOCAL_MT",
                "primary_model": f"TM-ExactMatch (originally: {original_model})",
                "execution_backend": "sqlite_exact_match",
                "route": "Translation Memory (Exact Match)",
                "is_pivot": False,
                "pivot_languages": [],
                "secondary_provider": None,
                "secondary_model": None,
                "review_provider": None,
                "review_model": None,
                "latency_ms": 1,
                "peak_ram_mb": 0.0,
                "memory_pressure": "GREEN",
                "is_cloud": False,
                "is_tm_match": True,
                "english_intermediate": None
            }

        # 2. Privacy Policy Enforcement
        if privacy_mode == "LOCAL_ONLY":
            if "gemini" in primary_model_id.lower() or routing_strategy == "gemini_primary":
                raise RuntimeError("Privacy Lock: Google Gemini blocked under LOCAL_ONLY project mode.")
            if "web" in primary_model_id.lower() or "lingva" in primary_model_id.lower() or "mymemory" in primary_model_id.lower():
                raise RuntimeError("Privacy Lock: Public Web Translation blocked under LOCAL_ONLY project mode.")

        # 3. Execute Primary Translation
        primary_prov = self.get_provider_for_model(primary_model_id)
        is_cloud_used = primary_prov.is_cloud()
        
        # Primary inference execution with automatic offline fallback
        try:
            if isinstance(primary_prov, ArgosProvider):
                t_res = await primary_prov.translate_arabic_to_urdu(source_arabic)
            elif isinstance(primary_prov, NLLBProvider):
                t_res = await primary_prov.translate_arabic_to_urdu(source_arabic)
            elif isinstance(primary_prov, AppleTranslationProvider):
                t_res = await primary_prov.translate(source_arabic, source_lang="ar", target_lang="ur")
            elif isinstance(primary_prov, FreeWebTranslator):
                t_res = await primary_prov.translate_arabic_to_urdu(
                    source_arabic,
                    privacy_mode=privacy_mode,
                    preferred_endpoint=primary_model_id
                )
            elif isinstance(primary_prov, GeminiProvider):
                t_res = await primary_prov.translate_direct(source_arabic, model=primary_model_id)
            elif isinstance(primary_prov, OllamaProvider):
                t_res = await primary_prov.translate_via_chat(source_arabic, model=primary_model_id)
            elif isinstance(primary_prov, LMStudioProvider):
                t_res = await primary_prov.translate_via_chat(source_arabic, model=primary_model_id)
            else:
                t_res = await primary_prov.translate(source_arabic, model=primary_model_id)
        except Exception as e:
            logger.warning(f"Primary model {primary_model_id} execution failed: {e}. Triggering automatic local fallback.")
            if isinstance(primary_prov, ArgosProvider):
                raise e
            elif not isinstance(primary_prov, NLLBProvider):
                # Prefer direct NLLB-200 (ar -> ur) over Argos's lossy ar -> en -> ur pivot
                nllb_avail = await self.nllb.check_availability()
                if nllb_avail.is_available:
                    logger.info(f"Falling back to NLLB-200 (direct ar -> ur) after {primary_model_id} failure.")
                    t_res = await self.nllb.translate_arabic_to_urdu(source_arabic)
                else:
                    t_res = await self.argos.translate_arabic_to_urdu(source_arabic)
            else:
                t_res = await self.argos.translate_arabic_to_urdu(source_arabic)

        target_urdu = t_res.translated_text
        latency_total_ms = t_res.latency_ms
        primary_provider_class = t_res.provider_class
        execution_backend = t_res.execution_backend
        route_str = t_res.route
        is_pivot = t_res.is_pivot
        pivot_langs = t_res.pivot_languages
        english_intermediate = t_res.english_intermediate
        peak_ram_mb = t_res.peak_ram_mb
        memory_pressure = t_res.memory_pressure

        # 4. Mechanical QA Evaluation
        qa_res = QAEngine.evaluate(source_arabic, target_urdu, glossary_terms)

        secondary_urdu = None
        reviewer_urdu = None
        secondary_provider_name = None
        secondary_model_name = None
        review_provider_name = None
        review_model_name = None
        final_urdu = target_urdu

        # 5. Adaptive Escalation on QA Warning or Explicit Strategy
        needs_escalation = (
            production_policy == "ADAPTIVE_ESCALATION" and qa_res.verdict in ["WARNING", "REVIEW_REQUIRED"]
        ) or (routing_strategy == "local_gemini_review" and qa_res.verdict in ["WARNING", "REVIEW_REQUIRED"])

        if needs_escalation:
            # Stage A: Secondary Translation if configured
            if secondary_model_id and secondary_model_id != primary_model_id:
                try:
                    sec_prov = self.get_provider_for_model(secondary_model_id)
                    if isinstance(sec_prov, TransformersProvider):
                        sec_res = await sec_prov.translate(source_arabic, model=secondary_model_id)
                        secondary_urdu = sec_res.translated_text
                        secondary_provider_name = sec_prov.get_provider_name()
                        secondary_model_name = secondary_model_id
                        latency_total_ms += sec_res.latency_ms
                except Exception as e:
                    logger.warning(f"Secondary model escalation failed: {e}")

            # Stage B: Semantic Reviewer (Qwen3 or Gemini)
            if reviewer_model_id:
                try:
                    rev_prov = self.get_provider_for_model(reviewer_model_id)
                    if isinstance(rev_prov, GeminiProvider) and privacy_mode != "LOCAL_ONLY":
                        rev_res = await rev_prov.review_translation(
                            source_arabic=source_arabic,
                            candidate_urdu=target_urdu,
                            glossary_terms=glossary_terms,
                            model=reviewer_model_id
                        )
                        reviewer_urdu = rev_res.revised_urdu
                        review_provider_name = "gemini"
                        review_model_name = reviewer_model_id
                        if rev_res.revised_urdu:
                            final_urdu = rev_res.revised_urdu
                        latency_total_ms += rev_res.latency_ms
                    elif isinstance(rev_prov, (OllamaProvider, LMStudioProvider)):
                        rev_res = await rev_prov.review_translation(
                            source_arabic=source_arabic,
                            candidate_urdu=target_urdu,
                            glossary_terms=glossary_terms,
                            model=reviewer_model_id
                        )
                        reviewer_urdu = rev_res.revised_urdu
                        review_provider_name = rev_prov.get_provider_name()
                        review_model_name = reviewer_model_id
                        if rev_res.revised_urdu:
                            final_urdu = rev_res.revised_urdu
                        latency_total_ms += rev_res.latency_ms
                except Exception as e:
                    logger.warning(f"Reviewer escalation failed: {e}")

        return {
            "source_text": source_arabic,
            "target_urdu": target_urdu,
            "secondary_urdu": secondary_urdu,
            "reviewer_urdu": reviewer_urdu,
            "final_urdu": final_urdu,
            "qa_status": qa_res.verdict,
            "qa_issues": qa_res.issues,
            "primary_provider": primary_prov.get_provider_name(),
            "primary_provider_class": primary_provider_class,
            "primary_model": primary_model_id,
            "execution_backend": execution_backend,
            "route": route_str,
            "is_pivot": is_pivot,
            "pivot_languages": pivot_langs,
            "english_intermediate": english_intermediate,
            "secondary_provider": secondary_provider_name,
            "secondary_model": secondary_model_name,
            "review_provider": review_provider_name,
            "review_model": review_model_name,
            "latency_ms": latency_total_ms,
            "peak_ram_mb": peak_ram_mb,
            "memory_pressure": memory_pressure,
            "is_cloud": is_cloud_used,
            "is_tm_match": False
        }

    async def generate_english_reference(
        self,
        source_arabic: str,
        provider_model_id: str = "qwen3:8b",
        privacy_mode: str = "LOCAL_ONLY"
    ) -> Dict[str, Any]:
        """Generates English literal reference bridge for human review workstation."""
        start_t = time.time()
        english_text = ""
        route = f"Direct English Ref ({provider_model_id})"

        if "gemini" in provider_model_id.lower():
            if privacy_mode == "LOCAL_ONLY":
                raise RuntimeError("Gemini English reference blocked in LOCAL_ONLY mode.")
            english_text = await self.gemini.generate(
                f"Translate this classical Arabic passage into clear, accurate English reference for scholarly review:\n\n{source_arabic}",
                model=provider_model_id
            )
            route = "Gemini Cloud API (ar -> en)"
        elif "argos" in provider_model_id.lower():
            english_text = await self.argos.translate_arabic_to_english(source_arabic)
            route = "Argos CTranslate2 (ar -> en)"
        elif "web" in provider_model_id.lower() or "google" in provider_model_id.lower():
            english_text = await self.free_web.translate_arabic_to_english(source_arabic, privacy_mode=privacy_mode)
            route = "Google Web Unofficial (ar -> en)"
        elif "ollama" in provider_model_id.lower() or "qwen" in provider_model_id.lower():
            english_text = await self.ollama.generate(
                f"Provide a faithful English reference translation of this Arabic text:\n\n{source_arabic}",
                model=provider_model_id
            )
            route = "Qwen3 Ollama (ar -> en)"
        else:
            # Default to Qwen3 or FreeWeb if available
            try:
                english_text = await self.ollama.generate(
                    f"Translate to English for reference: {source_arabic}",
                    model="qwen3:8b"
                )
                route = "Qwen3 Ollama (ar -> en)"
            except Exception:
                english_text = f"[English reference generation unavailable for {provider_model_id}]"

        lat = max(10, int((time.time() - start_t) * 1000))
        return {
            "english_reference": english_text.strip(),
            "provider": provider_model_id,
            "model": provider_model_id,
            "route": route,
            "latency_ms": lat
        }
