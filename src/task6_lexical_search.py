"""Task 6 - Lexical search module (BM25)."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

try:
    from .task4_chunking_indexing import CHUNKS_JSON
except ImportError:
    from task4_chunking_indexing import CHUNKS_JSON

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _ascii_fold(text: str) -> str:
    folded = "".join(
        char
        for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )
    return folded.replace("đ", "d")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(_ascii_fold(text))


@lru_cache(maxsize=1)
def _load_corpus() -> tuple[list[dict], object | None]:
    """Read chunks.json and build a cached BM25 index when the dependency is available."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return [], None

    if not CHUNKS_JSON.exists():
        return [], None

    corpus = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
    tokenized = [tokenize(doc["content"]) for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    return corpus, bm25


def build_bm25_index(corpus: list[dict]):
    """Build a BM25 index from a provided corpus."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None
    return BM25Okapi([tokenize(doc["content"]) for doc in corpus])


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return BM25 matches sorted by score descending."""
    corpus, bm25 = _load_corpus()
    if not corpus or bm25 is None:
        return []

    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results = []
    for idx in ranked[:top_k]:
        if scores[idx] <= 0:
            continue
        results.append(
            {
                "content": corpus[idx]["content"],
                "score": float(scores[idx]),
                "metadata": corpus[idx].get("metadata", {}),
            }
        )
    return results


if __name__ == "__main__":
    for result in lexical_search("Điều 248 tàng trữ trái phép chất ma túy", top_k=5):
        print(f"[{result['score']:.3f}] ({result['metadata'].get('source')}) {result['content'][:90]}...")
