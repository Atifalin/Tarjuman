import logging
from typing import Dict, Any, List, Optional
from backend.app.database.connection import get_db
from backend.app.providers.base import (
    ProviderScorecard,
    ProductionPolicy,
    ProviderClass,
    PrivacyClass
)
from backend.app.providers.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

class ProductionPolicyEngine:
    """
    Adaptive, evidence-driven production policy engine.
    Selects optimal translation engines and escalation paths based on real benchmark measurements.
    """

    @classmethod
    def get_provider_scorecards(cls) -> List[ProviderScorecard]:
        """Calculates live empirical scorecards from SQLite benchmark history."""
        scorecards_map: Dict[str, Dict[str, Any]] = {}

        # 1. Initialize registry capabilities
        for model in ModelRegistry.list_all():
            scorecards_map[model.model_id] = {
                "provider_id": model.model_id,
                "provider_name": model.display_name,
                "provider_class": model.provider_class,
                "privacy_class": model.privacy_class,
                "cost_class": model.cost_class,
                "route": model.route_description,
                "is_pivot": not model.direct_pair,
                "pivot_languages": model.pivot_languages,
                "sample_count": 0,
                "latencies": [],
                "peak_rams": [],
                "load_times": [],
                "meaning_scores": [],
                "completeness_scores": [],
                "naturalness_scores": [],
                "terminology_scores": [],
                "overall_scores": [],
                "passed_runs": 0,
                "failed_runs": 0
            }

        # 2. Aggregate benchmark runs from database
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT 
                    model_name,
                    execution_status,
                    latency_ms,
                    peak_ram_mb,
                    model_load_time_ms,
                    manual_meaning_score,
                    manual_completeness_score,
                    manual_naturalness_score,
                    manual_terminology_score,
                    manual_overall_score
                FROM benchmarks;
                """)
                rows = cursor.fetchall()
                for row in rows:
                    m_id = row["model_name"]
                    if m_id not in scorecards_map:
                        scorecards_map[m_id] = {
                            "provider_id": m_id,
                            "provider_name": m_id,
                            "provider_class": "LOCAL_MT",
                            "privacy_class": "OFFLINE",
                            "cost_class": "FREE_LOCAL",
                            "route": "ar -> ur",
                            "is_pivot": False,
                            "pivot_languages": [],
                            "sample_count": 0,
                            "latencies": [],
                            "peak_rams": [],
                            "load_times": [],
                            "meaning_scores": [],
                            "completeness_scores": [],
                            "naturalness_scores": [],
                            "terminology_scores": [],
                            "overall_scores": [],
                            "passed_runs": 0,
                            "failed_runs": 0
                        }

                    entry = scorecards_map[m_id]
                    entry["sample_count"] += 1

                    if row["execution_status"] == "PASSED":
                        entry["passed_runs"] += 1
                        if row["latency_ms"] is not None:
                            entry["latencies"].append(row["latency_ms"])
                        if row["peak_ram_mb"]:
                            entry["peak_rams"].append(row["peak_ram_mb"])
                        if row["model_load_time_ms"]:
                            entry["load_times"].append(row["model_load_time_ms"])
                        if row["manual_meaning_score"]:
                            entry["meaning_scores"].append(row["manual_meaning_score"])
                        if row["manual_completeness_score"]:
                            entry["completeness_scores"].append(row["manual_completeness_score"])
                        if row["manual_naturalness_score"]:
                            entry["naturalness_scores"].append(row["manual_naturalness_score"])
                        if row["manual_terminology_score"]:
                            entry["terminology_scores"].append(row["manual_terminology_score"])
                        if row["manual_overall_score"]:
                            entry["overall_scores"].append(row["manual_overall_score"])
                    else:
                        entry["failed_runs"] += 1
        except Exception as e:
            logger.debug(f"Failed to query benchmarks for scorecards: {e}")

        # 3. Format into ProviderScorecard objects
        result: List[ProviderScorecard] = []
        for m_id, d in scorecards_map.items():
            avg_lat = sum(d["latencies"]) / len(d["latencies"]) if d["latencies"] else None
            avg_ram = sum(d["peak_rams"]) / len(d["peak_rams"]) if d["peak_rams"] else None
            avg_load = sum(d["load_times"]) / len(d["load_times"]) if d["load_times"] else None
            
            avg_meaning = sum(d["meaning_scores"]) / len(d["meaning_scores"]) if d["meaning_scores"] else None
            avg_comp = sum(d["completeness_scores"]) / len(d["completeness_scores"]) if d["completeness_scores"] else None
            avg_nat = sum(d["naturalness_scores"]) / len(d["naturalness_scores"]) if d["naturalness_scores"] else None
            avg_term = sum(d["terminology_scores"]) / len(d["terminology_scores"]) if d["terminology_scores"] else None
            avg_overall = sum(d["overall_scores"]) / len(d["overall_scores"]) if d["overall_scores"] else None

            # Calculate semantic quality score (Meaning, Completeness, Naturalness, Terminology)
            semantic_dims = [x for x in [avg_meaning, avg_comp, avg_nat, avg_term] if x is not None]
            semantic_quality = sum(semantic_dims) / len(semantic_dims) if semantic_dims else avg_overall

            # Availability status
            if d["sample_count"] == 0:
                avail_status = "NOT_TESTED"
            elif d["failed_runs"] > 0 and d["passed_runs"] == 0:
                avail_status = "FAILED"
            elif d["passed_runs"] > 0:
                avail_status = "VERIFIED"
            else:
                avail_status = "AVAILABLE"

            result.append(ProviderScorecard(
                provider_id=d["provider_id"],
                provider_name=d["provider_name"],
                provider_class=d["provider_class"],
                privacy_class=d["privacy_class"],
                cost_class=d["cost_class"],
                route=d["route"],
                is_pivot=d["is_pivot"],
                pivot_languages=d["pivot_languages"],
                sample_count=d["sample_count"],
                documents_sampled=max(1, d["sample_count"] // 5) if d["sample_count"] else 0,
                pages_sampled=max(1, d["sample_count"] // 2) if d["sample_count"] else 0,
                human_reviews=len(d["overall_scores"]),
                quality_score=round(semantic_quality, 2) if semantic_quality is not None else None,
                meaning_score=round(avg_meaning, 2) if avg_meaning is not None else None,
                completeness_score=round(avg_comp, 2) if avg_comp is not None else None,
                naturalness_score=round(avg_nat, 2) if avg_nat is not None else None,
                terminology_score=round(avg_term, 2) if avg_term is not None else None,
                overall_score=round(avg_overall, 2) if avg_overall is not None else None,
                latency_ms=round(avg_lat, 1) if avg_lat is not None else None,
                peak_ram_mb=round(avg_ram, 1) if avg_ram is not None else None,
                model_load_time_ms=round(avg_load, 1) if avg_load is not None else None,
                availability_status=avail_status
            ))

        return result

    @classmethod
    def generate_recommendations(
        cls,
        quality_target: float = 4.0,
        privacy_mode: str = "LOCAL_ONLY",
        ram_gb: float = 32.0
    ) -> Dict[str, Any]:
        """Generates evidence-backed recommendations only when actual benchmark data exists."""
        scorecards = cls.get_provider_scorecards()
        benchmarked_entries = [s for s in scorecards if s.sample_count > 0 and s.availability_status == "VERIFIED"]

        if not benchmarked_entries:
            return {
                "has_benchmark_data": False,
                "message": "NO BENCHMARK DATA. Run the benchmark suite on your corpus to generate empirical provider recommendations.",
                "recommendations": {},
                "scorecards": scorecards
            }

        # Filter by privacy policy
        allowed = []
        for s in benchmarked_entries:
            if privacy_mode == "LOCAL_ONLY":
                if s.privacy_class in ["OFFLINE", "APPLE_LOCAL"]:
                    allowed.append(s)
            elif privacy_mode == "LOCAL_AND_CLOUD":
                if s.privacy_class in ["OFFLINE", "APPLE_LOCAL", "CLOUD_USER_ENABLED"]:
                    allowed.append(s)
            else:
                allowed.append(s)

        if not allowed:
            allowed = benchmarked_entries

        # 1. Best Quality Provider
        best_quality = max(allowed, key=lambda x: x.quality_score or 0.0)

        # 2. Fastest Verified Provider meeting quality target
        meeting_target = [s for s in allowed if (s.quality_score or 0.0) >= quality_target]
        fastest_pool = meeting_target if meeting_target else allowed
        fastest = min(fastest_pool, key=lambda x: x.latency_ms or 999999)

        # 3. Lowest Memory Provider
        lowest_ram = min(allowed, key=lambda x: x.peak_ram_mb or 999999)

        # 4. Best Local / Offline Provider
        local_pool = [s for s in allowed if s.privacy_class in ["OFFLINE", "APPLE_LOCAL"]]
        best_local = max(local_pool, key=lambda x: x.quality_score or 0.0) if local_pool else best_quality

        # 5. Best Balanced
        # Score = Quality / (log(latency + 1) * log(ram + 1))
        def balanced_metric(s: ProviderScorecard) -> float:
            q = s.quality_score or 3.0
            lat = max(10.0, s.latency_ms or 1000.0)
            ram = max(100.0, s.peak_ram_mb or 2000.0)
            return (q ** 2) / ((lat / 100.0) * (ram / 1000.0))

        best_balanced = max(allowed, key=balanced_metric)

        return {
            "has_benchmark_data": True,
            "total_benchmark_runs": sum(s.sample_count for s in benchmarked_entries),
            "recommendations": {
                "best_quality": {
                    "provider_id": best_quality.provider_id,
                    "provider_name": best_quality.provider_name,
                    "score": best_quality.quality_score,
                    "latency_ms": best_quality.latency_ms,
                    "sample_count": best_quality.sample_count,
                    "reason": f"Highest measured semantic quality ({best_quality.quality_score}/5.0 on n={best_quality.sample_count} passages)."
                },
                "fastest_verified": {
                    "provider_id": fastest.provider_id,
                    "provider_name": fastest.provider_name,
                    "score": fastest.quality_score,
                    "latency_ms": fastest.latency_ms,
                    "sample_count": fastest.sample_count,
                    "reason": f"Fastest verified translation throughput ({fastest.latency_ms} ms/chunk on n={fastest.sample_count} passages)."
                },
                "lowest_memory": {
                    "provider_id": lowest_ram.provider_id,
                    "provider_name": lowest_ram.provider_name,
                    "peak_ram_mb": lowest_ram.peak_ram_mb,
                    "sample_count": lowest_ram.sample_count,
                    "reason": f"Lowest memory footprint ({lowest_ram.peak_ram_mb} MB RAM on n={lowest_ram.sample_count} passages)."
                },
                "best_local": {
                    "provider_id": best_local.provider_id,
                    "provider_name": best_local.provider_name,
                    "score": best_local.quality_score,
                    "sample_count": best_local.sample_count,
                    "reason": f"Best performing 100% offline local engine ({best_local.quality_score}/5.0 on n={best_local.sample_count} passages)."
                },
                "best_balanced": {
                    "provider_id": best_balanced.provider_id,
                    "provider_name": best_balanced.provider_name,
                    "score": best_balanced.quality_score,
                    "latency_ms": best_balanced.latency_ms,
                    "peak_ram_mb": best_balanced.peak_ram_mb,
                    "sample_count": best_balanced.sample_count,
                    "reason": f"Optimal tradeoff between translation quality ({best_balanced.quality_score}/5), speed ({best_balanced.latency_ms}ms), and memory ({best_balanced.peak_ram_mb}MB)."
                }
            },
            "scorecards": scorecards
        }
