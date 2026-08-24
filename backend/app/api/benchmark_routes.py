from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from backend.app.benchmark.arabic_test_suite import BenchmarkSuite
from backend.app.providers.policy_engine import ProductionPolicyEngine

router = APIRouter(prefix="/api/benchmarks", tags=["Benchmarks"])

class RunBenchmarkRequest(BaseModel):
    model_id: str
    run_name: Optional[str] = None

class ScoreRequest(BaseModel):
    benchmark_id: str
    meaning: int
    completeness: int = 5
    naturalness: int = 5
    terminology: int = 5
    overall: int = 5

@router.get("/samples")
def get_sample_test_cases():
    return BenchmarkSuite.get_sample_test_cases()

@router.get("/history")
def get_benchmark_history(run_name: Optional[str] = None):
    return BenchmarkSuite.get_benchmark_history(run_name)

@router.get("/scorecard")
def get_provider_scorecards():
    """Returns live empirical scorecard across all 5 provider categories."""
    return ProductionPolicyEngine.get_provider_scorecards()

@router.get("/recommendations")
def get_policy_recommendations(
    quality_target: float = Query(4.0, ge=1.0, le=5.0),
    privacy_mode: str = Query("LOCAL_ONLY")
):
    """Returns 5 evidence-based system recommendations from actual benchmark data."""
    return ProductionPolicyEngine.generate_recommendations(
        quality_target=quality_target,
        privacy_mode=privacy_mode
    )

@router.post("/run")
async def run_model_benchmark(req: RunBenchmarkRequest):
    return await BenchmarkSuite.run_benchmark(req.model_id, req.run_name)

@router.post("/run-all")
async def run_all_available_benchmarks():
    """Runs the full 10-category standard benchmark suite across all ready/available models."""
    return await BenchmarkSuite.run_all_available_benchmarks()

@router.delete("/history")
@router.post("/clear-history")
def clear_benchmark_history():
    """Deletes all recorded benchmark runs and performance evaluations."""
    return BenchmarkSuite.clear_history()

class CustomBenchmarkRequest(BaseModel):
    custom_arabic_text: str
    models: List[str]
    run_name: Optional[str] = None

@router.post("/custom-run")
async def run_custom_benchmark_comparison(req: CustomBenchmarkRequest):
    """Executes live side-by-side comparison on user-provided Arabic text with hardware metrics."""
    return await BenchmarkSuite.run_custom_comparison(req.custom_arabic_text, req.models, req.run_name)

@router.post("/score")
def submit_manual_evaluation(req: ScoreRequest):
    BenchmarkSuite.update_manual_scores(
        req.benchmark_id,
        req.meaning,
        req.completeness,
        req.naturalness,
        req.terminology,
        req.overall
    )
    return {"success": True}
