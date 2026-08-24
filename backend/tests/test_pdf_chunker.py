import pytest
from backend.app.pdf.chunker import ArabicChunker

def test_sentence_split():
    text = "قال المعلم للطلاب: من جد وجد ومن زرع حصد. فأجابه الطالب قائلاً: سنبذل قصارى جهدنا! هل توافق على ذلك؟"
    sentences = ArabicChunker.split_into_sentences(text)
    assert len(sentences) >= 3

def test_chunking_with_target_size():
    long_para = " ".join(["هذا نص عربي طويل يحتوي على جمل مفيدة لتعليم الترجمة الآلية."] * 20)
    chunks = ArabicChunker.chunk_page_text(long_para, page_num=1, target_word_count=50, max_word_count=100)
    assert len(chunks) >= 2
    for c in chunks:
        assert c["page_number"] == 1
        assert c["chunk_index"] >= 1
        assert len(c["text"]) > 0
