"""
Task 4 — Chunking & Indexing vào Vector Store.

Pipeline: load markdown -> chunk -> embed -> index (ChromaDB).
Ngoài ra lưu chunks.json để Task 6 (BM25) tái sử dụng cùng tập chunk.

Cài đặt:
    pip install langchain-text-splitters sentence-transformers chromadb
"""

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

try:
    from .enterprise_rag import enrich_policy_metadata
except ImportError:
    from enterprise_rag import enrich_policy_metadata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"
INDEX_DIR = ROOT / "data" / "index"
CHROMA_DIR = INDEX_DIR / "chroma"
CHUNKS_JSON = INDEX_DIR / "chunks.json"
COLLECTION_NAME = "DrugLawDocs"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn
# =============================================================================

# Atomic chunks work better for policy lookup: usually one clause, bullet group, or
# short paragraph. Heading context is repeated so small chunks remain understandable.
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "420"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "60"))
CHUNKING_METHOD = "markdown_atomic"

# Embedding: paraphrase-multilingual-MiniLM-L12-v2.
# - Multilingual (hỗ trợ tiếng Việt tốt), 384 chiều, nhẹ (~470MB), nhanh trên CPU.
# - Cân bằng chất lượng/tốc độ; thay cho bge-m3 (2.2GB, chậm trên CPU) trong môi trường local.
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

# Vector store: ChromaDB — local persistent, không cần Docker, hỗ trợ cosine.
VECTOR_STORE = "chromadb"


# =============================================================================
# SHARED HELPERS (dùng lại ở Task 5, 6, 9)
# =============================================================================

@lru_cache(maxsize=1)
def get_embedding_model():
    """Load sentence-transformers model 1 lần (singleton)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text -> list vector (normalize để dùng cosine)."""
    model = get_embedding_model()
    embs = model.encode(
        texts, normalize_embeddings=True, show_progress_bar=len(texts) > 50
    )
    return [e.tolist() for e in embs]


def get_chroma_client():
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_chroma_collection(create: bool = False):
    """Lấy (hoặc tạo) collection Chroma với cosine space."""
    client = get_chroma_client()
    if create:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:  # noqa: BLE001
            pass
        return client.create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return client.get_collection(COLLECTION_NAME)


def _markdown_frontmatter_value(content: str, field: str) -> str | None:
    match = re.search(rf"(?im)^\*\*{re.escape(field)}:\*\*\s*(.+?)\s*$", content)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def markdown_document_metadata(md_file: Path, content: str) -> dict:
    """Build stable retrieval metadata from markdown sidecar fields."""
    default_type = "legal" if "legal" in md_file.parts else "news"
    doc_type = _markdown_frontmatter_value(content, "Type") or default_type
    metadata = {"source": md_file.name, "type": doc_type}

    declared_source = _markdown_frontmatter_value(content, "Source")
    if declared_source:
        metadata["declared_source"] = declared_source
    overrides = {
        "version": _markdown_frontmatter_value(content, "Version"),
        "status": _markdown_frontmatter_value(content, "Status"),
        "effective_from": _markdown_frontmatter_value(content, "Effective-From"),
        "effective_to": _markdown_frontmatter_value(content, "Effective-To"),
        "allowed_roles": _markdown_frontmatter_value(content, "Allowed-Roles"),
        "departments": _markdown_frontmatter_value(content, "Departments"),
        "confidentiality": _markdown_frontmatter_value(content, "Confidentiality"),
    }
    return enrich_policy_metadata(metadata, {key: value for key, value in overrides.items() if value is not None})


# =============================================================================
# PIPELINE
# =============================================================================

def load_documents() -> list[dict]:
    """Đọc toàn bộ markdown files từ data/standardized/."""
    documents = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        documents.append({"content": content, "metadata": markdown_document_metadata(md_file, content)})
    return documents


def _markdown_sections(text: str) -> list[tuple[str, str]]:
    """Return (heading path, body) sections while preserving heading hierarchy."""
    sections = []
    headings: list[str] = []
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if content:
            sections.append((" > ".join(headings), content))
        body.clear()

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            body.append(line)
            continue
        flush()
        level = len(match.group(1))
        title = match.group(2).strip()
        headings[:] = headings[: level - 1]
        headings.append(title)

    flush()
    return sections or [("", text.strip())]


def _fallback_split(text: str, size: int, overlap: int) -> list[str]:
    """Boundary-aware splitter used when langchain-text-splitters is unavailable."""
    pieces = []
    remaining = text.strip()
    while len(remaining) > size:
        window = remaining[: size + 1]
        boundaries = [window.rfind(mark) for mark in ("\n\n", "\n- ", "\n", ". ", "; ", ", ", " ")]
        cut = max(boundaries)
        if cut < max(40, size // 2):
            cut = size
        piece = remaining[:cut].strip()
        if piece:
            pieces.append(piece)
        restart = max(0, cut - overlap)
        remaining = remaining[restart:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _split_atomic(text: str, size: int, overlap: int) -> list[str]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=size,
            chunk_overlap=min(overlap, max(0, size // 4)),
            separators=["\n\n", "\n- ", "\n* ", "\n", ". ", "; ", ", ", " ", ""],
        )
        return splitter.split_text(text)
    except ImportError:
        return _fallback_split(text, size, overlap)


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Create small policy chunks with inherited Markdown heading context."""

    chunks = []
    for doc in documents:
        document_chunk_index = 0
        for section_index, (heading_path, body) in enumerate(_markdown_sections(doc["content"])):
            # Keep the nearest headings, capped so they do not dominate the embedding.
            heading_context = heading_path[-120:].strip()
            prefix = f"Chủ đề: {heading_context}\n" if heading_context else ""
            body_budget = max(180, CHUNK_SIZE - len(prefix))
            pieces = _split_atomic(body, body_budget, CHUNK_OVERLAP)
            for section_chunk_index, piece in enumerate(pieces):
                content = f"{prefix}{piece.strip()}".strip()
                if len(content) < 20:
                    continue
                chunks.append(
                    {
                        "content": content,
                        "metadata": {
                            **doc["metadata"],
                            "chunk_index": document_chunk_index,
                            "section_index": section_index,
                            "section_chunk_index": section_chunk_index,
                            "section_path": heading_context or "document",
                        },
                    }
                )
                document_chunk_index += 1
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed toàn bộ chunks; thêm key 'embedding'."""
    vectors = embed_texts([c["content"] for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        chunk["embedding"] = vec
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """Lưu chunks (kèm embedding) vào ChromaDB + dump chunks.json cho BM25."""
    collection = get_chroma_collection(create=True)

    ids, docs, metas, embs = [], [], [], []
    for i, c in enumerate(chunks):
        ids.append(f"chunk_{i}")
        docs.append(c["content"])
        metas.append(c["metadata"])
        embs.append(c["embedding"])

    # Chroma batch giới hạn kích thước -> chèn theo lô.
    BATCH = 1000
    for s in range(0, len(ids), BATCH):
        e = s + BATCH
        collection.add(
            ids=ids[s:e], documents=docs[s:e], metadatas=metas[s:e], embeddings=embs[s:e]
        )

    # Lưu chunks (không kèm embedding) cho Task 6 BM25.
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    slim = [{"content": c["content"], "metadata": c["metadata"]} for c in chunks]
    CHUNKS_JSON.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")


def run_pipeline():
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks (dim={len(chunks[0]['embedding'])})")

    index_to_vectorstore(chunks)
    print(f"✓ Indexed {len(chunks)} chunks → ChromaDB ({CHROMA_DIR})")
    print(f"✓ Saved chunks → {CHUNKS_JSON}")


if __name__ == "__main__":
    run_pipeline()
