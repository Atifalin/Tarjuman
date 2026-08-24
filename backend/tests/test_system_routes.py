import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_dependencies_status_endpoint():
    res = client.get("/api/system/dependencies")
    assert res.status_code == 200
    data = res.json()
    assert "pytorch" in data
    assert "ollama" in data
    assert "gemini" in data
    assert "readiness_matrix" in data

def test_verify_pytorch_endpoint():
    res = client.post("/api/system/verify-pytorch")
    assert res.status_code == 200
    data = res.json()
    assert "installed" in data
    assert "mps_available" in data

def test_failed_benchmark_metrics_are_null():
    # Execute benchmark on unavailable model
    payload = {
        "custom_arabic_text": "العلم صيد والكتابة قيده",
        "models": ["madlad400-7b-mt"]  # currently torch is uninstalled in environment
    }
    res = client.post("/api/benchmarks/custom-run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["passages"]) == 1
    output = data["passages"][0]["outputs"][0]
    assert output["execution_status"] in ["NOT_INSTALLED", "FAILED"]
    assert output["latency_ms"] is None
    assert output["throughput_chunks_per_min"] is None
    assert output["estimated_tokens_per_min"] is None
    assert output["urdu_text"] is None
    assert output["output_length_words"] == 0
    assert "PyTorch" in output["error"] or "torch" in output["error"]
