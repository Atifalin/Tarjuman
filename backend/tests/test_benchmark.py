import pytest
from backend.app.benchmark.arabic_test_suite import BenchmarkSuite

@pytest.mark.asyncio
async def test_custom_benchmark_comparison_execution():
    from backend.app.database.connection import init_db
    init_db()
    test_arabic = (
        "1. عن أبي هريرة رضي الله عنه قال: قال رسول الله صلى الله عليه وسلم: كلمتان خفيفتان على اللسان.\n\n"
        "2. قال الإمام الشافعي رحمه الله: ما ناظرت أحداً قط إلا أحببت أن يوفق ويسدد."
    )
    # Test with mock/offline capability checking
    res = await BenchmarkSuite.run_custom_comparison(test_arabic, ["gemini-3.6-flash"])
    assert res["total_passages"] == 2
    assert len(res["passages"]) == 2
    assert res["passages"][0]["passage_index"] == 1
    assert len(res["passages"][0]["outputs"]) == 1
    output_entry = res["passages"][0]["outputs"][0]
    assert "latency_ms" in output_entry
    assert "memory_metrics" in output_entry
    assert "process_ram_mb" in output_entry["memory_metrics"]
