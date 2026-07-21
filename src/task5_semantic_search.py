"""
Task 5 — Semantic Search Module (dense retrieval).

Embed query bằng cùng model ở Task 4 -> truy vấn ChromaDB (cosine) -> top_k.
"""

try:
    from .task4_chunking_indexing import embed_texts, get_chroma_collection
except ImportError:  # hỗ trợ chạy trực tiếp: python src/task5_semantic_search.py
    from task4_chunking_indexing import embed_texts, get_chroma_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa bằng vector similarity (cosine).

    Returns:
        List of {'content', 'score', 'metadata'} sorted by score descending.
    """
    try:
        collection = get_chroma_collection(create=False)
    except Exception:  # noqa: BLE001 — chưa index (chạy Task 4 trước)
        return []

    query_emb = embed_texts([query])[0]
    res = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    results = []
    for doc, meta, dist in zip(docs, metas, dists):
        results.append(
            {
                "content": doc,
                "score": float(1.0 - dist),  # cosine distance -> similarity
                "metadata": meta or {},
            }
        )
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for r in semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5):
        print(f"[{r['score']:.3f}] ({r['metadata'].get('source')}) {r['content'][:90]}...")
