import time
import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.database.connection import get_db
from backend.app.hardware.monitor import HardwareMonitor
from backend.app.providers.router import TranslationRouter
from backend.app.qa.heuristics import QAEngine

logger = logging.getLogger(__name__)

ARABIC_BENCHMARK_SAMPLES = [
    {
        "id": "tc_01",
        "category": "Modern Standard Arabic",
        "title": "News & Technology",
        "source": "تعد تقنيات الذكاء الاصطناعي الحديثة نقلة نوعية في معالجة اللغات الطبيعية والترجمة الآلية."
    },
    {
        "id": "tc_02",
        "category": "Long Paragraph",
        "title": "Academic Discourse",
        "source": "إن دراسة التاريخ الإسلامي تتطلب فهمًا عميقًا للظروف الاجتماعية والسياسية التي أحاطت بتلك الحقبة، ولا يمكن الاكتفاء بالقراءة السطحية للنصوص دون تمحيص الأسانيد وتحقيق الروايات التاريخية المتعددة."
    },
    {
        "id": "tc_03",
        "category": "Classical Arabic",
        "title": "Classical Literature & Balagha",
        "source": "لسان الفتى نصف ونصف فؤاده، فلم يبق إلا صورة اللحم والدم. وما المرء إلا حيث يجعل نفسه، فكن في أعلى المراتب ترتقي."
    },
    {
        "id": "tc_04",
        "category": "Religious Terminology",
        "title": "Fiqh & Quranic Terms",
        "source": "فرض الله الصلاة والزكاة على المسلمين، ودعا إلى إيتاء ذي القربى والنهي عن الفحشاء والمنكر والبغي، وحث على التقوى والإحسان."
    },
    {
        "id": "tc_05",
        "category": "Names & Lineage",
        "title": "Historical Figures",
        "source": "ولد الإمام محمد بن إدريس الشافعي في غزة عام ١٥٠ هـ، وتوفي في مصر عام ٢٠٤ هـ بعد أن أسس مذهبه الفقهي الشهير."
    },
    {
        "id": "tc_06",
        "category": "Numbers & Dates",
        "title": "Numerical Accuracy",
        "source": "بلغ عدد المخطوطات المحفوظة في المكتبة 14,500 مخطوطة، يعود تاريخ أقدمها إلى عام 452 هجرية الموافق 1060 ميلادية."
    },
    {
        "id": "tc_07",
        "category": "Quotations & Dialogue",
        "title": "Dialogue & Direct Speech",
        "source": "قال المعلم لطلابه: «من جد وجد ومن زرع حصد»، فأجابه الطالب قائلاً: «سنبذل قصارى جهدنا لتحقيق النجاح بإذن الله»."
    },
    {
        "id": "tc_08",
        "category": "Arabic Punctuation",
        "title": "Punctuation Sensitivity",
        "source": "هل قرأت هذا الكتاب المفيد؟ إنه يحتوي على: فوائد لغوية، ودروس تاريخية؛ فلا تفوت قراءته!"
    },
    {
        "id": "tc_09",
        "category": "Difficult Idioms",
        "title": "Metaphor & Context",
        "source": "بلغ السيل الزبى، ولم يعد في قوس الصبر منزع، فلزم على الجميع تدارك الأمر قبل فوات الأوان."
    },
    {
        "id": "tc_10",
        "category": "Headings & Lists",
        "title": "Structured Text",
        "source": "الباب الأول: في آداب طلب العلم.\nأولاً: إخلاص النية لله تعالى.\nثانياً: العمل بالعلم.\nثالثاً: توقير المعلمين والمشايخ."
    }
]

class BenchmarkSuite:
    """Built-in multi-model benchmark evaluation runner."""

    @classmethod
    def get_sample_test_cases(cls) -> List[Dict[str, Any]]:
        return ARABIC_BENCHMARK_SAMPLES

    @classmethod
    async def run_benchmark(cls, model_id: str, run_name: Optional[str] = None) -> List[Dict[str, Any]]:
        router = TranslationRouter()
        r_name = run_name or f"Run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        results = []

        for sample in ARABIC_BENCHMARK_SAMPLES:
            t0 = time.perf_counter()
            hw_before = HardwareMonitor.get_hardware_status()
            prov = router.get_provider_for_model(model_id)
            pname = prov.get_provider_name()
            
            try:
                # Pre-flight availability check
                avail = await prov.check_availability()
                if not avail.is_available:
                    raise RuntimeError(avail.status_message)

                if pname == "gemini":
                    t_res = await prov.translate_direct(sample["source"], model=model_id)
                elif pname in ["ollama", "lmstudio"]:
                    t_res = await prov.translate_via_chat(sample["source"], model=model_id)
                else:
                    t_res = await prov.translate(sample["source"], model=model_id)

                urdu_text = t_res.translated_text
                latency = t_res.latency_ms
                qa_res = QAEngine.evaluate(sample["source"], urdu_text)
                qa_status = qa_res.verdict
                execution_status = "PASSED"
                error_msg = None
            except Exception as e:
                urdu_text = None
                latency = None
                qa_status = "FAILED"
                execution_status = "FAILED"
                error_msg = str(e)

            hw_after = HardwareMonitor.get_hardware_status()
            bench_id = str(uuid.uuid4())
            now_str = datetime.now().isoformat()

            with get_db() as conn:
                conn.execute("""
                INSERT INTO benchmarks (
                    id, run_name, test_case_id, category, source_arabic,
                    provider_name, model_name, target_urdu, latency_ms,
                    qa_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    bench_id, r_name, sample["id"], sample["category"], sample["source"],
                    pname, model_id, urdu_text or "", latency, qa_status, now_str
                ))

            results.append({
                "id": bench_id,
                "run_name": r_name,
                "test_case_id": sample["id"],
                "category": sample["category"],
                "title": sample["title"],
                "source_arabic": sample["source"],
                "provider_name": pname,
                "model_name": model_id,
                "target_urdu": urdu_text,
                "latency_ms": latency,
                "execution_status": execution_status,
                "qa_status": qa_status,
                "error": error_msg,
                "peak_ram_mb": hw_after["process_memory_mb"],
                "memory_pressure": hw_after["memory_pressure"],
                "swap_mb": hw_after["swap_used_mb"]
            })

        return results

    @classmethod
    async def run_custom_comparison(cls, custom_text: str, models: List[str], run_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs real side-by-side comparison on custom user-provided Arabic text (single passage or 20-50 passages)
        across multiple models (MADLAD, NLLB, Qwen3, Gemini).
        Correctly distinguishes between real inference metrics vs. failed model execution.
        """
        router = TranslationRouter()
        r_name = run_name or f"CustomBench-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Split text into separate passages if multiple are pasted (delimited by double newline or numbered items)
        passages = [p.strip() for p in re.split(r'\n\s*\n', custom_text) if p.strip()]
        if not passages:
            passages = [custom_text.strip()]

        passage_results = []

        for p_idx, passage in enumerate(passages):
            model_outputs = []
            words_in_source = len(passage.split())

            for model_id in models:
                t0 = time.perf_counter()
                hw_before = HardwareMonitor.get_hardware_status()
                prov = router.get_provider_for_model(model_id)
                pname = prov.get_provider_name()

                try:
                    # 1. Pre-flight check
                    avail = await prov.check_availability()
                    if not avail.is_available:
                        if "not installed" in avail.status_message.lower():
                            raise ModuleNotFoundError(avail.status_message)
                        elif "not running" in avail.status_message.lower():
                            raise ConnectionError(avail.status_message)
                        else:
                            raise RuntimeError(avail.status_message)

                    # 2. Real inference execution
                    if pname == "gemini":
                        t_res = await prov.translate_direct(passage, model=model_id)
                    elif pname in ["ollama", "lmstudio"]:
                        t_res = await prov.translate_via_chat(passage, model=model_id)
                    else:
                        t_res = await prov.translate(passage, model=model_id)

                    urdu_text = t_res.translated_text
                    latency = t_res.latency_ms
                    qa_res = QAEngine.evaluate(passage, urdu_text)
                    qa_verdict = qa_res.verdict
                    qa_issues = qa_res.issues
                    error_msg = None
                    execution_status = "PASSED"
                    
                    out_chars = len(urdu_text)
                    out_words = len(urdu_text.split()) if urdu_text else 0
                    chunks_per_min = round(60000.0 / max(latency, 1), 1) if latency and latency > 0 else None
                    tokens_per_min = round((out_words * 1.3) * (60000.0 / max(latency, 1)), 0) if latency and latency > 0 else None

                except ModuleNotFoundError as e:
                    urdu_text = None
                    latency = None
                    qa_verdict = "FAILED"
                    qa_issues = [f"Missing dependency: {str(e)}"]
                    error_msg = str(e)
                    execution_status = "NOT_INSTALLED"
                    out_chars = 0
                    out_words = 0
                    chunks_per_min = None
                    tokens_per_min = None

                except ConnectionError as e:
                    urdu_text = None
                    latency = None
                    qa_verdict = "FAILED"
                    qa_issues = [f"Connection error: {str(e)}"]
                    error_msg = str(e)
                    execution_status = "NOT_CONNECTED"
                    out_chars = 0
                    out_words = 0
                    chunks_per_min = None
                    tokens_per_min = None

                except Exception as e:
                    urdu_text = None
                    latency = None
                    qa_verdict = "FAILED"
                    qa_issues = [f"Provider execution error: {str(e)}"]
                    error_msg = str(e)
                    execution_status = "FAILED"
                    out_chars = 0
                    out_words = 0
                    chunks_per_min = None
                    tokens_per_min = None

                hw_after = HardwareMonitor.get_hardware_status()
                bench_id = str(uuid.uuid4())
                now_str = datetime.now().isoformat()

                with get_db() as conn:
                    conn.execute("""
                    INSERT INTO benchmarks (
                        id, run_name, test_case_id, category, source_arabic,
                        provider_name, model_name, target_urdu, latency_ms,
                        output_length_chars, output_length_words, peak_ram_mb, memory_pressure,
                        qa_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        bench_id, r_name, f"passage_{p_idx + 1}", "Custom Passage", passage,
                        pname, model_id, urdu_text or "", latency,
                        out_chars, out_words, hw_after["process_memory_mb"], hw_after["memory_pressure"],
                        qa_verdict, now_str
                    ))

                model_outputs.append({
                    "bench_id": bench_id,
                    "model_id": model_id,
                    "provider_name": pname,
                    "execution_status": execution_status,
                    "urdu_text": urdu_text,
                    "latency_ms": latency,
                    "output_length_chars": out_chars,
                    "output_length_words": out_words,
                    "throughput_chunks_per_min": chunks_per_min,
                    "estimated_tokens_per_min": tokens_per_min,
                    "qa_status": qa_verdict,
                    "qa_issues": qa_issues,
                    "error": error_msg,
                    "memory_metrics": {
                        "process_ram_mb": hw_after["process_memory_mb"],
                        "ram_percent": hw_after["ram_percent"],
                        "memory_pressure": hw_after["memory_pressure"],
                        "swap_used_mb": hw_after["swap_used_mb"]
                    }
                })

            passage_results.append({
                "passage_index": p_idx + 1,
                "source_arabic": passage,
                "word_count": words_in_source,
                "outputs": model_outputs
            })

        return {
            "run_name": r_name,
            "total_passages": len(passages),
            "models_tested": len(models),
            "passages": passage_results
        }

    @classmethod
    def get_benchmark_history(cls, run_name: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            if run_name:
                cursor.execute("SELECT * FROM benchmarks WHERE run_name = ? ORDER BY test_case_id ASC;", (run_name,))
            else:
                cursor.execute("SELECT * FROM benchmarks ORDER BY created_at DESC LIMIT 300;")
            return [dict(row) for row in cursor.fetchall()]

    @classmethod
    async def run_all_available_benchmarks(cls, run_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Runs the 10-category benchmark suite across all models that are currently available/ready."""
        router = TranslationRouter()
        r_name = run_name or f"Suite-All-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        all_models = [m.model_id for m in router.list_supported_models()]
        
        available_models = []
        for mid in all_models:
            try:
                prov = router.get_provider_for_model(mid)
                avail = await prov.check_availability()
                if not avail.is_available:
                    continue
                # Guard against silently triggering multi-GB downloads for uninstalled
                # Transformers-backed models (e.g. MADLAD-400) during an automated batch run.
                if hasattr(prov, "has_local_weights_cached") and not prov.has_local_weights_cached(mid):
                    continue
                available_models.append(mid)
            except Exception:
                pass

        if not available_models:
            raise RuntimeError("No translation models are currently ready. Please verify models in Setup Wizard.")

        combined_results = []
        for mid in available_models:
            try:
                res = await cls.run_benchmark(mid, run_name=r_name)
                combined_results.extend(res)
            except Exception as e:
                logger.error(f"Error running benchmark on {mid}: {e}")

        return combined_results

    @classmethod
    def clear_history(cls):
        with get_db() as conn:
            conn.execute("DELETE FROM benchmarks;")
        return {"success": True, "message": "All benchmark evaluations and scorecards cleared."}

    @classmethod
    def update_manual_scores(
        cls,
        bench_id: str,
        meaning: int,
        completeness: int,
        naturalness: int,
        terminology: int,
        overall: int
    ):
        with get_db() as conn:
            conn.execute("""
            UPDATE benchmarks SET
                manual_meaning_score = ?,
                manual_completeness_score = ?,
                manual_naturalness_score = ?,
                manual_terminology_score = ?,
                manual_overall_score = ?
            WHERE id = ?;
            """, (meaning, completeness, naturalness, terminology, overall, bench_id))
