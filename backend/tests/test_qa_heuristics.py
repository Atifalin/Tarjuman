import pytest
from backend.app.qa.heuristics import QAEngine

def test_qa_empty_target():
    res = QAEngine.evaluate("هذا نص عربي للاختبار", "")
    assert res.verdict == "REVIEW_REQUIRED"
    assert res.mechanical_pass is False
    assert any("empty" in issue.lower() for issue in res.issues)

def test_qa_identical_text():
    src = "هذا نص عربي للاختبار"
    res = QAEngine.evaluate(src, src)
    assert res.verdict == "REVIEW_REQUIRED"
    assert res.mechanical_pass is False
    assert any("identical" in issue.lower() for issue in res.issues)

def test_qa_refusal_detection():
    src = "نص عربي للاختبار"
    tgt = "I cannot translate this text as an AI model."
    res = QAEngine.evaluate(src, tgt)
    assert res.verdict == "REVIEW_REQUIRED"
    assert res.mechanical_pass is False
    assert any("refusal" in issue.lower() for issue in res.issues)

def test_qa_number_preservation():
    src = "ولد الإمام في عام 150 هجرية وتوفي عام 204 هجرية."
    tgt = "امام صاحب کی پیدائش ہوئی۔"  # Dropped numbers
    res = QAEngine.evaluate(src, tgt)
    assert res.verdict in ["WARNING", "REVIEW_REQUIRED"]
    assert any("numeral" in issue.lower() for issue in res.issues)

def test_qa_valid_mechanical_pass():
    src = "تعد تقنيات الذكاء الاصطناعي الحديثة نقلة نوعية في معالجة اللغات الطبيعية."
    tgt = "جدید مصنوعی ذہانت کی ٹیکنالوجیز قدرتی زبان کی پروسیسنگ میں ایک اہم پیش رفت ہیں۔"
    res = QAEngine.evaluate(src, tgt)
    assert res.verdict == "PASS"
    assert res.mechanical_pass is True
    assert res.language_check.classification in ["STRONG_URDU", "LIKELY_URDU"]
    assert len(res.issues) == 0

def test_qa_untranslated_arabic_detection():
    src = "قال الإمام الشافعي في كتابه الرسالة عن أصول الفقه."
    # Model simply copy-pasted Arabic text with Arabic function words (في, عن)
    tgt = "قال الإمام الشافعي في كتابه الرسالة عن أصول الفقه والبيان."
    res = QAEngine.evaluate(src, tgt)
    assert res.verdict == "REVIEW_REQUIRED"
    assert res.language_check.classification == "LIKELY_ARABIC"
    assert any("untranslated arabic" in issue.lower() for issue in res.issues)

def test_qa_mixed_or_ambiguous_language():
    src = "هذا البحث العلمي المفصل."
    # Mixed output or missing distinctive markers
    tgt = "هذا علمي بحث."
    res = QAEngine.evaluate(src, tgt)
    assert res.language_check.classification in ["AMBIGUOUS", "LIKELY_ARABIC"]

def test_qa_language_sanity_levels():
    strong_urdu = "یہ کتاب اسلامی تاریخ اور فقہ کے اہم اصولوں پر مشتمل ہے۔"
    res_strong = QAEngine.analyze_language_sanity(strong_urdu)
    assert res_strong.classification == "STRONG_URDU"
    assert res_strong.urdu_marker_ratio > 0.10

    pure_arabic = "هذا الكتاب يشتمل على أصول الفقه والشريعة الإسلامية في العصر العباسي."
    res_arabic = QAEngine.analyze_language_sanity(pure_arabic)
    assert res_arabic.classification == "LIKELY_ARABIC"
    assert res_arabic.arabic_marker_ratio > 0.10

def test_qa_glossary_enforcement():
    src = "حث الإسلام على الصلاة والزكاة."
    tgt = "اسلام نے عبادت کا حکم دیا۔"  # Missing 'نماز' and 'زکوٰۃ'
    glossary = {"الصلاة": "نماز", "الزكاة": "زکوٰۃ"}
    res = QAEngine.evaluate(src, tgt, glossary_terms=glossary)
    assert res.verdict == "WARNING"
    assert any("glossary" in issue.lower() for issue in res.issues)
