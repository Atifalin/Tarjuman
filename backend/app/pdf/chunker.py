import re
from typing import List, Dict, Any

# Arabic sentence end markers
ARABIC_SENTENCE_DELIMITERS = re.compile(r'([.؟!؛\n\r]+)')

class ArabicChunker:
    """
    Intelligent paragraph and punctuation-aware Arabic document chunker.
    Splits long pages into cohesive chunks without cutting mid-sentence.
    """

    @classmethod
    def split_into_sentences(cls, text: str) -> List[str]:
        parts = ARABIC_SENTENCE_DELIMITERS.split(text)
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sent = (parts[i] + parts[i+1]).strip()
            if sent:
                sentences.append(sent)
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        return sentences if sentences else [text.strip()]

    @classmethod
    def chunk_page_text(
        cls,
        text: str,
        page_num: int,
        target_word_count: int = 60,
        max_word_count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Chunks text for a specific page into semantic paragraph/sentence blocks.
        """
        if not text.strip():
            return []

        # Split on double line breaks (paragraphs) first
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk_sentences = []
        current_words = 0

        for para in raw_paragraphs:
            para_sentences = cls.split_into_sentences(para)
            for sent in para_sentences:
                sent_words = len(sent.split())
                
                if current_words + sent_words > max_word_count and current_chunk_sentences:
                    # Flush current chunk
                    chunk_text = " ".join(current_chunk_sentences).strip()
                    chunks.append(chunk_text)
                    current_chunk_sentences = [sent]
                    current_words = sent_words
                else:
                    current_chunk_sentences.append(sent)
                    current_words += sent_words

        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences).strip()
            chunks.append(chunk_text)

        result = []
        for idx, c_text in enumerate(chunks):
            result.append({
                "page_number": page_num,
                "chunk_index": idx + 1,
                "text": c_text,
                "word_count": len(c_text.split())
            })

        return result
