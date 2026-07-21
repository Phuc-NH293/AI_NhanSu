"""
Task 8 — PageIndex Vectorless RAG.

Nếu có PAGEINDEX_API_KEY + SDK pageindex -> dùng dịch vụ PageIndex thật.
Nếu không -> fallback "vectorless" cục bộ: hiểu cấu trúc tài liệu (tách theo
heading / "Điều N") rồi xếp hạng section bằng độ trùng từ khoá — KHÔNG dùng embedding.
Cả hai đều trả kết quả gắn nhãn source='pageindex' để Task 9 dùng làm fallback.

Đăng ký: https://pageindex.ai/  ·  SDK: https://github.com/VectifyAI/PageIndex
"""

import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

try:
    from .task4_chunking_indexing import markdown_document_metadata
except ImportError:
    from task4_chunking_indexing import markdown_document_metadata

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
# Ranh giới section: heading markdown (#...) hoặc "Điều 12." trong văn bản luật.
_SECTION_RE = re.compile(r"(?m)^(?:#{1,6}\s+.*|Điều\s+\d+\..*)$")


def _tok(text: str) -> list[str]:
    folded = "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )
    return _TOKEN_RE.findall(folded)


# =============================================================================
# Local vectorless index (structural sections)
# =============================================================================

def _build_sections() -> list[dict]:
    """Tách toàn bộ markdown thành các section theo cấu trúc (heading/Điều)."""
    sections = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        metadata = markdown_document_metadata(md_file, text)

        # Vị trí các ranh giới section.
        bounds = [m.start() for m in _SECTION_RE.finditer(text)]
        if not bounds:
            bounds = [0]
        bounds.append(len(text))
        for i in range(len(bounds) - 1):
            chunk = text[bounds[i]:bounds[i + 1]].strip()
            if len(chunk) < 40:
                continue
            sections.append(
                {"content": chunk, "metadata": dict(metadata)}
            )
    return sections


_SECTIONS_CACHE = None


def _get_sections() -> list[dict]:
    global _SECTIONS_CACHE
    if _SECTIONS_CACHE is None:
        _SECTIONS_CACHE = _build_sections()
    return _SECTIONS_CACHE


def _vectorless_search(query: str, top_k: int) -> list[dict]:
    """Xếp hạng section bằng độ trùng từ khoá (vectorless)."""
    q = _tok(query)
    if not q:
        return []
    q_set = set(q)

    scored = []
    for sec in _get_sections():
        toks = _tok(sec["content"])
        if not toks:
            continue
        counts = sum(1 for t in toks if t in q_set)
        if counts == 0:
            continue
        # tf chuẩn hoá theo độ dài (ưu tiên section ngắn, đậm đặc từ khoá).
        score = counts / (len(toks) ** 0.5)
        scored.append((score, sec))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "content": sec["content"],
            "score": float(score),
            "metadata": sec["metadata"],
            "source": "pageindex",
        }
        for score, sec in scored[:top_k]
    ]


# =============================================================================
# Public API
# =============================================================================

def upload_documents():
    """Upload markdown lên PageIndex (chỉ khi có API key + SDK)."""
    if not PAGEINDEX_API_KEY:
        print("⚠ Chưa có PAGEINDEX_API_KEY — dùng vectorless cục bộ, không cần upload.")
        return
    from pageindex import PageIndex  # type: ignore

    pi = PageIndex(api_key=PAGEINDEX_API_KEY)
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        pi.upload(
            content=text,
            metadata=markdown_document_metadata(md_file, text),
        )
        print(f"  ✓ Uploaded: {md_file.name}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval. Dùng PageIndex API nếu có key, ngược lại fallback cục bộ.

    Returns:
        List of {'content', 'score', 'metadata', 'source': 'pageindex'}
    """
    if PAGEINDEX_API_KEY:
        try:
            from pageindex import PageIndex  # type: ignore

            pi = PageIndex(api_key=PAGEINDEX_API_KEY)
            results = pi.query(query=query, top_k=top_k)
            return [
                {
                    "content": r.text,
                    "score": float(getattr(r, "score", 0.0)),
                    "metadata": getattr(r, "metadata", {}) or {},
                    "source": "pageindex",
                }
                for r in results
            ]
        except Exception as exc:  # noqa: BLE001
            print(f"  ! PageIndex API lỗi ({exc}); fallback vectorless cục bộ.")

    return _vectorless_search(query, top_k)


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("ℹ Không có PAGEINDEX_API_KEY → dùng vectorless cục bộ (structural keyword).")
    for r in pageindex_search("hình phạt sử dụng ma tuý", top_k=3):
        print(f"[{r['score']:.3f}] ({r['metadata'].get('source')}) {r['content'][:90]}...")
