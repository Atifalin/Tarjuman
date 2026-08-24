import re
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel

class LanguageSanityResult(BaseModel):
    classification: str  # STRONG_URDU, LIKELY_URDU, AMBIGUOUS, LIKELY_ARABIC
    urdu_char_ratio: float
    urdu_marker_ratio: float
    arabic_marker_ratio: float
    detected_urdu_markers: List[str]
    detected_arabic_markers: List[str]
    details: str

class QACheckResult(BaseModel):
    verdict: str  # PASS, WARNING, REVIEW_REQUIRED
    mechanical_pass: bool  # True if no obvious mechanical defects detected
    issues: List[str]
    word_count_source: int
    word_count_target: int
    char_ratio: float
    missing_numbers: List[str]
    language_check: LanguageSanityResult

# Common refusal patterns across models
REFUSAL_PATTERNS = [
    r"i cannot translate",
    r"as an ai",
    r"i am sorry",
    r"content policy",
    r"معذرت",
    r"میں اس کا ترجمہ نہیں کر سکتا",
]

# Conversational artifacts
FLUFF_PATTERNS = [
    r"^here is the urdu translation",
    r"^here is the translation",
    r"^sure, here",
    r"^translated text:",
    r"^ترجمہ درج ذیل ہے",
]

# Urdu-specific characters (absent in standard Modern Standard Arabic)
URDU_SPECIFIC_CHARS = set("ٹڈڑںےپچژگھۂۓ")

# Common Urdu grammatical particles and function words
URDU_GRAMMAR_MARKERS = {
    "ہے", "ہیں", "ہوں", "ہو", "کا", "کی", "کے", "کو", "سے", "میں",
    "پر", "تک", "نے", "تھا", "تھی", "تھے", "اور", "کہ", "یہ", "وہ",
    "کر", "کیا", "کیوں", "کون", "کب", "کہاں", "کیسے", "کرنے", "ہوا",
    "ہوئی", "ہوئے", "ہوتا", "ہوتی", "ہوتے", "گیا", "گئی", "گئے",
    "جاتا", "جاتی", "جاتے", "رہا", "رہی", "رہے", "والا", "والی", "والے",
    "چاہیے", "نہیں", "مت", "آپ", "ہم", "تم", "اس", "ان", "انہیں", "اسے"
}

# Distinctive Arabic grammatical particles and function words (which should not dominate in Urdu text)
ARABIC_GRAMMAR_MARKERS = {
    "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك",
    "الذي", "التي", "الذين", "اللاتي", "أن", "إن", "كان", "كانت", "يكون",
    "تكون", "قد", "لم", "لن", "لو", "إذا", "إذ", "ثم", "أو", "أم", "لكن",
    "غير", "بين", "قبل", "بعد", "عند", "لدى", "حيث", "هو", "هي", "هم",
    "هن", "أنت", "نحن", "أنا", "كل", "بعض", "أي", "ماذا", "كيف", "لماذا",
    "متى", "أين", "قال", "قالت", "يقول", "تقول", "التي", "الذي", "الذين"
}

# Digits pattern for Eastern and Western numerals
NUMERAL_PATTERN = re.compile(r"[\d٠-٩]+")

class QAEngine:
    """
    Deterministic QA & Heuristics Engine.
    Produces explicit verdict (PASS, WARNING, REVIEW_REQUIRED) with specific bulleted reasons.

    CRITICAL SEMANTIC BOUNDARY:
    - 'PASS' signifies ONLY that the output has PASSED MECHANICAL SANITY CHECKS:
      (non-empty, non-echo, non-refusal, numeral preservation, structural length bounds, and valid Urdu script signals).
    - 'PASS' DOES NOT CERTIFY SEMANTIC CORRECTNESS OR SCHOLARLY FIDELITY.
    - Semantic fidelity, nuanced theology, and phrasing polish must be verified by
      human reviewer or secondary LLM review.
    """

    @classmethod
    def analyze_language_sanity(cls, text: str) -> LanguageSanityResult:
        """
        Multi-signal scored language sanity check.
        Categorizes output as:
        - STRONG_URDU: High ratio of Urdu characters and grammatical particles, negligible Arabic function words.
        - LIKELY_URDU: Positive Urdu markers present without dominant untranslated Arabic.
        - AMBIGUOUS: Mixed Arabic/Urdu or insufficient vocabulary in short/isolated tokens.
        - LIKELY_ARABIC: Predominantly Arabic function words, lacking Urdu orthography (untranslated copy-through).
        """
        t = text.strip()
        if not t:
            return LanguageSanityResult(
                classification="LIKELY_ARABIC",
                urdu_char_ratio=0.0,
                urdu_marker_ratio=0.0,
                arabic_marker_ratio=0.0,
                detected_urdu_markers=[],
                detected_arabic_markers=[],
                details="Empty string"
            )

        # Character-level analysis
        arabic_script_chars = [c for c in t if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F']
        total_chars = len(arabic_script_chars)
        urdu_char_count = sum(1 for c in arabic_script_chars if c in URDU_SPECIFIC_CHARS)
        urdu_char_ratio = round(urdu_char_count / max(total_chars, 1), 3)

        # Word-level tokenization
        words = re.findall(r'[\u0600-\u06FF\u0750-\u077F]+', t)
        total_words = len(words)
        if total_words == 0:
            return LanguageSanityResult(
                classification="AMBIGUOUS",
                urdu_char_ratio=0.0,
                urdu_marker_ratio=0.0,
                arabic_marker_ratio=0.0,
                detected_urdu_markers=[],
                detected_arabic_markers=[],
                details="No Arabic-script words extracted"
            )

        detected_urdu = [w for w in words if w in URDU_GRAMMAR_MARKERS]
        detected_arabic = [w for w in words if w in ARABIC_GRAMMAR_MARKERS]

        urdu_marker_ratio = round(len(detected_urdu) / total_words, 3)
        arabic_marker_ratio = round(len(detected_arabic) / total_words, 3)

        # Decision Tree for Multi-Signal Classification
        # 1. Obvious untranslated Arabic copy-through
        if arabic_marker_ratio >= 0.18 and urdu_marker_ratio == 0 and urdu_char_count == 0:
            classification = "LIKELY_ARABIC"
            details = f"Text contains {len(detected_arabic)} Arabic function words with 0 Urdu markers (untranslated Arabic copy-through)."

        # 2. Strong Urdu
        elif (urdu_char_ratio >= 0.02 and urdu_marker_ratio >= 0.10) or (urdu_marker_ratio >= 0.18 and arabic_marker_ratio <= 0.04):
            classification = "STRONG_URDU"
            details = f"Strong Urdu orthography (Urdu char ratio: {urdu_char_ratio}, Urdu marker ratio: {urdu_marker_ratio})."

        # 3. Likely Urdu
        elif urdu_marker_ratio >= 0.06 or (urdu_char_count >= 1 and arabic_marker_ratio <= 0.06):
            classification = "LIKELY_URDU"
            details = f"Likely Urdu (Urdu markers: {len(detected_urdu)}, Urdu chars: {urdu_char_count})."

        # 4. Mixed Arabic / Urdu
        elif urdu_marker_ratio > 0.04 and arabic_marker_ratio > 0.08:
            classification = "AMBIGUOUS"
            details = f"Mixed Arabic/Urdu output detected ({len(detected_urdu)} Urdu vs {len(detected_arabic)} Arabic particles)."

        # 5. Fallback for short phrases or ambiguous text
        else:
            classification = "AMBIGUOUS"
            details = "Insufficient distinct Urdu grammatical particles or characters to confirm language."

        return LanguageSanityResult(
            classification=classification,
            urdu_char_ratio=urdu_char_ratio,
            urdu_marker_ratio=urdu_marker_ratio,
            arabic_marker_ratio=arabic_marker_ratio,
            detected_urdu_markers=list(set(detected_urdu)),
            detected_arabic_markers=list(set(detected_arabic)),
            details=details
        )

    @classmethod
    def evaluate(
        cls,
        source_arabic: str,
        target_urdu: str,
        glossary_terms: Optional[Dict[str, str]] = None
    ) -> QACheckResult:
        issues: List[str] = []
        verdict = "PASS"

        src = source_arabic.strip()
        tgt = target_urdu.strip() if target_urdu else ""

        # Initial language sanity assessment
        lang_res = cls.analyze_language_sanity(tgt)

        # 1. Empty Check
        if not tgt:
            return QACheckResult(
                verdict="REVIEW_REQUIRED",
                mechanical_pass=False,
                issues=["Mechanical Error: Urdu translation output is completely empty."],
                word_count_source=len(src.split()),
                word_count_target=0,
                char_ratio=0.0,
                missing_numbers=[],
                language_check=lang_res
            )

        src_words = len(src.split())
        tgt_words = len(tgt.split())
        char_ratio = round(len(tgt) / max(len(src), 1), 2)

        # 2. Identical text check (Echo)
        if src == tgt:
            issues.append("Mechanical Error: Output is identical to the Arabic source (echo copy-through).")
            verdict = "REVIEW_REQUIRED"

        # 3. Model refusal check
        tgt_lower = tgt.lower()
        for pat in REFUSAL_PATTERNS:
            if re.search(pat, tgt_lower):
                issues.append("Mechanical Error: Model produced a conversational refusal/disclaimer instead of translating.")
                verdict = "REVIEW_REQUIRED"
                break

        # 4. Conversational fluff check
        for pat in FLUFF_PATTERNS:
            if re.search(pat, tgt_lower):
                issues.append("Mechanical Warning: Translation contains introductory conversational fluff or English commentary.")
                if verdict != "REVIEW_REQUIRED":
                    verdict = "WARNING"
                break

        # 5. Language Sanity Check (Multi-Signal)
        if lang_res.classification == "LIKELY_ARABIC" and src_words >= 3:
            issues.append(f"Language Failure: Output appears to be untranslated Arabic ({lang_res.details}).")
            verdict = "REVIEW_REQUIRED"
        elif lang_res.classification == "AMBIGUOUS" and src_words >= 5:
            issues.append(f"Language Warning: {lang_res.details}")
            if verdict != "REVIEW_REQUIRED":
                verdict = "WARNING"

        # 6. Length ratio checks (Advisory bounds)
        if src_words >= 15:
            if tgt_words < src_words * 0.35:
                issues.append(f"Length Distortion: Output unusually short ({tgt_words} Urdu words vs {src_words} Arabic words). Possible dropped content.")
                if verdict != "REVIEW_REQUIRED":
                    verdict = "WARNING"
            elif tgt_words > src_words * 3.5:
                issues.append(f"Length Distortion: Output unusually lengthy ({tgt_words} Urdu words vs {src_words} Arabic words). Possible hallucinated filler.")
                if verdict != "REVIEW_REQUIRED":
                    verdict = "WARNING"

        # 7. Preserved numbers & dates check
        src_numbers = set(NUMERAL_PATTERN.findall(src))
        tgt_numbers = set(NUMERAL_PATTERN.findall(tgt))
        
        def normalize_digits(s: str) -> str:
            arabic_indic = "٠١٢٣٤٥٦٧٨٩"
            ascii_digits = "0123456789"
            trans = str.maketrans(arabic_indic, ascii_digits)
            return s.translate(trans)

        norm_src_nums = {normalize_digits(n) for n in src_numbers}
        norm_tgt_nums = {normalize_digits(n) for n in tgt_numbers}
        
        missing_nums = list(norm_src_nums - norm_tgt_nums)
        if missing_nums:
            issues.append(f"Numeral Check: Source numbers not preserved in translation: {', '.join(missing_nums)}")
            if verdict != "REVIEW_REQUIRED":
                verdict = "WARNING"

        # 8. Glossary compliance check
        if glossary_terms:
            for ar_term, preferred_ur in glossary_terms.items():
                if ar_term in src and preferred_ur not in tgt:
                    issues.append(f"Glossary Check: Term '{ar_term}' expected Urdu '{preferred_ur}' but was not matched.")
                    if verdict != "REVIEW_REQUIRED":
                        verdict = "WARNING"

        mechanical_pass = (verdict == "PASS")

        return QACheckResult(
            verdict=verdict,
            mechanical_pass=mechanical_pass,
            issues=issues,
            word_count_source=src_words,
            word_count_target=tgt_words,
            char_ratio=char_ratio,
            missing_numbers=missing_nums,
            language_check=lang_res
        )
