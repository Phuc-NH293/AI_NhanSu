"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Ưu tiên MarkItDown của Microsoft (https://github.com/microsoft/markitdown).
Nếu MarkItDown không khả dụng (vd Python 3.14 chưa hỗ trợ), tự fallback sang
pypdf cho file PDF. File JSON (news) được đọc trực tiếp, không cần MarkItDown.

Cài đặt (tuỳ chọn):
    pip install "markitdown[pdf]"

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục (legal/, news/)
"""

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Một số PDF pháp luật là bản scan (signed) không có text layer -> không trích được.
# Map theo tên file (stem) sang trang HTML chứa toàn văn để lấy text thay thế.
SCANNED_PDF_HTML_FALLBACK = {
    "nghi-dinh-105-2021-huong-dan-luat-ma-tuy": (
        "https://thuvienphapluat.vn/van-ban/Van-hoa-Xa-hoi/"
        "Nghi-dinh-105-2021-ND-CP-huong-dan-Luat-Phong-chong-ma-tuy-496664.aspx"
    ),
}


def _get_markitdown():
    """Trả về instance MarkItDown nếu import được, ngược lại None."""
    try:
        from markitdown import MarkItDown  # type: ignore

        return MarkItDown()
    except Exception:  # noqa: BLE001
        return None


def _pdf_to_markdown_pypdf(filepath: Path) -> str:
    """Fallback: trích text từ PDF bằng pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(filepath))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def _html_fulltext_fallback(url: str) -> str:
    """Lấy toàn văn pháp luật từ trang HTML (cho PDF scan không có text)."""
    resp = requests.get(url, headers=HEADERS, timeout=40)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    node = soup.find(id="divContentDoc") or soup.find("div", class_="content1")
    if node is None:
        return ""
    for tag in node(["script", "style"]):
        tag.decompose()
    return node.get_text("\n", strip=True)


def convert_legal_docs(md_converter) -> int:
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for filepath in legal_dir.iterdir():
        if filepath.suffix.lower() not in (".pdf", ".docx", ".doc"):
            continue
        print(f"Converting: {filepath.name}")

        text = ""
        engine = "markitdown"
        if md_converter is not None:
            try:
                text = md_converter.convert(str(filepath)).text_content or ""
            except Exception as exc:  # noqa: BLE001
                print(f"  ! MarkItDown lỗi ({exc}); thử pypdf...")
                text = ""
        if not text.strip() and filepath.suffix.lower() == ".pdf":
            text = _pdf_to_markdown_pypdf(filepath)
            engine = "pypdf"

        if not text.strip() and filepath.stem in SCANNED_PDF_HTML_FALLBACK:
            print("  ! PDF dạng scan (không có text); lấy toàn văn từ HTML...")
            text = _html_fulltext_fallback(SCANNED_PDF_HTML_FALLBACK[filepath.stem])
            engine = "html-fulltext"

        if not text.strip():
            print(f"  ✗ Không trích được nội dung: {filepath.name}")
            continue

        header = f"# {filepath.stem}\n\n**Nguồn file:** {filepath.name}\n\n---\n\n"
        output_path = output_dir / f"{filepath.stem}.md"
        output_path.write_text(header + text, encoding="utf-8")
        count += 1
        print(f"  ✓ Saved ({engine}): {output_path.name} ({len(text):,} chars)")
    return count


def convert_news_articles() -> int:
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for filepath in news_dir.iterdir():
        if filepath.suffix.lower() != ".json":
            continue
        print(f"Converting: {filepath.name}")
        data = json.loads(filepath.read_text(encoding="utf-8"))

        header = f"# {data.get('title', 'Unknown')}\n\n"
        header += f"**Source:** {data.get('url', 'N/A')}\n"
        header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"
        content = header + (data.get("content_markdown", "") or "")

        output_path = output_dir / f"{filepath.stem}.md"
        output_path.write_text(content, encoding="utf-8")
        count += 1
        print(f"  ✓ Saved: {output_path.name} ({len(content):,} chars)")
    return count


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown")
    print("=" * 50)

    md_converter = _get_markitdown()
    print("Engine PDF:", "MarkItDown" if md_converter else "pypdf (fallback)")

    print("\n--- Legal Documents ---")
    n_legal = convert_legal_docs(md_converter)

    print("\n--- News Articles ---")
    n_news = convert_news_articles()

    print(f"\n✓ Done! {n_legal} legal + {n_news} news → {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
