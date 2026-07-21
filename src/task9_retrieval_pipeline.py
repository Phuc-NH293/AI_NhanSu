"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh.

Query
  ├→ Semantic Search (dense)  ─┐
  │                             ├→ Merge (RRF) → Rerank → Results (source='hybrid')
  ├→ Lexical Search (BM25)   ─┘
  └→ Nếu độ tin cậy hybrid < threshold → Fallback PageIndex (source='pageindex')
"""

try:
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search
    from .task7_reranking import rerank, rerank_rrf
    from .task8_pageindex_vectorless import pageindex_search
except ImportError:
    from task5_semantic_search import semantic_search
    from task6_lexical_search import lexical_search
    from task7_reranking import rerank, rerank_rrf
    from task8_pageindex_vectorless import pageindex_search


SCORE_THRESHOLD = 0.3          # độ tin cậy hybrid (theo cosine dense) tối thiểu
DEFAULT_TOP_K = 5
RERANK_METHOD = "cross_encoder"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """
    Retrieval pipeline hoàn chỉnh với fallback.

    Returns:
        List of {'content', 'score', 'metadata', 'source' in {'hybrid','pageindex'}}.
    """
    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)

    # Độ tin cậy hybrid = cosine similarity cao nhất từ dense (thang 0..1, dễ ngưỡng hoá).
    confidence = dense[0]["score"] if dense else 0.0

    # Merge dense + sparse bằng RRF.
    merged = rerank_rrf([dense, sparse], top_k=top_k * 2) if (dense or sparse) else []
    for item in merged:
        item["source"] = "hybrid"

    if use_reranking and merged:
        final = rerank(query, merged, top_k=top_k, method=RERANK_METHOD)
        for item in final:
            item.setdefault("source", "hybrid")
    else:
        final = merged[:top_k]

    # Fallback: hybrid yếu (confidence thấp) hoặc không có kết quả.
    if not final or confidence < score_threshold:
        fallback = pageindex_search(query, top_k=top_k)
        if fallback:
            return fallback[:top_k]

    return final[:top_k]


if __name__ == "__main__":
    queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý",
        "Nghệ sĩ nào bị bắt vì sử dụng ma tuý",
        "Luật phòng chống ma tuý 2021 quy định gì về cai nghiện",
    ]
    for q in queries:
        print(f"\nQuery: {q}\n" + "-" * 60)
        for i, r in enumerate(retrieve(q, top_k=3), 1):
            print(f"  {i}. [{r['score']:.3f}] [{r['source']}] ({r['metadata'].get('source')}) "
                  f"{r['content'][:70]}...")
