"""
Task 7 — Reranking Module.

Cung cấp 3 phương pháp (đều implement đầy đủ):
    - cross_encoder: CrossEncoder neural rerank (bật bằng env ENABLE_CROSS_ENCODER=1).
                     Mặc định fallback sang token-overlap để test nhanh/không tải model.
    - mmr (Maximal Marginal Relevance): cân bằng relevance & diversity.
    - rrf (Reciprocal Rank Fusion): gộp nhiều ranked list.
"""

import math
import os
import re
import unicodedata

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _ascii_fold(text: str) -> str:
    folded = "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )
    return folded.replace("đ", "d")


def _tok(text: str) -> set:
    return set(_TOKEN_RE.findall(_ascii_fold(text)))


def _overlap_score(query: str, content: str) -> float:
    """Điểm liên quan từ vựng (Jaccard-weighted) — fallback nhanh, không cần model."""
    q, d = _tok(query), _tok(content)
    if not q or not d:
        return 0.0
    inter = len(q & d)
    return inter / (len(q) + math.log1p(len(d)))


# =============================================================================
# Cross-encoder
# =============================================================================

_CE_MODEL = None


def _get_cross_encoder():
    global _CE_MODEL
    if _CE_MODEL is None:
        from sentence_transformers import CrossEncoder

        model_name = os.getenv("RERANK_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        _CE_MODEL = CrossEncoder(model_name)
    return _CE_MODEL


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank bằng cross-encoder. Bật model thật bằng ENABLE_CROSS_ENCODER=1
    (nếu không sẽ dùng fallback token-overlap để giữ test nhanh & offline-safe).
    """
    if not candidates:
        return []

    scores = None
    if os.getenv("ENABLE_CROSS_ENCODER", "0").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            ce = _get_cross_encoder()
            scores = ce.predict([(query, c["content"]) for c in candidates])
            scores = [float(s) for s in scores]
        except Exception:  # noqa: BLE001 — offline / model lỗi -> fallback
            scores = None

    if scores is None:
        scores = [_overlap_score(query, c["content"]) for c in candidates]

    reranked = []
    for c, s in zip(candidates, scores):
        item = dict(c)
        item["score"] = float(s)
        reranked.append(item)
    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked[:top_k]


# =============================================================================
# MMR
# =============================================================================

def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance: MMR = λ*sim(q,d) - (1-λ)*max sim(d, selected).
    Yêu cầu mỗi candidate có 'embedding'.
    """
    if not candidates:
        return []

    selected, remaining = [], list(range(len(candidates)))
    while remaining and len(selected) < top_k:
        best_idx, best = None, float("-inf")
        for idx in remaining:
            emb = candidates[idx].get("embedding")
            if emb is None:
                relevance = candidates[idx].get("score", 0.0)
                max_sim = 0.0
            else:
                relevance = _cosine(query_embedding, emb)
                max_sim = max(
                    (_cosine(emb, candidates[s]["embedding"]) for s in selected),
                    default=0.0,
                )
            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
            if mmr > best:
                best, best_idx = mmr, idx
        selected.append(best_idx)
        remaining.remove(best_idx)

    out = []
    for rank, idx in enumerate(selected):
        item = dict(candidates[idx])
        item["score"] = float(len(selected) - rank)  # giữ thứ tự MMR
        out.append(item)
    return out


# =============================================================================
# RRF
# =============================================================================

def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """Reciprocal Rank Fusion: RRF(d) = Σ 1/(k + rank_r(d))."""
    rrf_scores: dict = {}
    content_map: dict = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            content_map[key] = item

    ordered = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for content, score in ordered[:top_k]:
        item = dict(content_map[content])
        item["score"] = float(score)
        results.append(item)
    return results


# =============================================================================
# Unified interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",
) -> list[dict]:
    """Giao diện rerank thống nhất (mặc định cross_encoder)."""
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        if not candidates:
            return []
        q_emb = candidates[0].get("query_embedding")
        return rerank_mmr(q_emb or [], candidates, top_k)
    elif method == "rrf":
        return rerank_rrf([candidates], top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    dummy = [
        {"content": "Điều 248: Tội tàng trữ trái phép chất ma tuý", "score": 0.8, "metadata": {}},
        {"content": "Nghệ sĩ X bị bắt vì sử dụng ma tuý", "score": 0.7, "metadata": {}},
        {"content": "Hình phạt tù từ 2-7 năm cho tội tàng trữ ma tuý", "score": 0.6, "metadata": {}},
    ]
    for r in rerank("hình phạt tàng trữ ma tuý", dummy, top_k=2):
        print(f"[{r['score']:.3f}] {r['content']}")
