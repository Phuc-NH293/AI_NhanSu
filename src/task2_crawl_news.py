"""
Task 2 — Crawl bài báo về nghệ sĩ liên quan tới ma tuý.

Hướng dẫn:
    1. Crawl tối thiểu 5 bài báo từ các trang tin tức Việt Nam.
    2. Ưu tiên Crawl4AI; nếu môi trường không có (vd Python 3.14 chưa hỗ trợ),
       tự động fallback sang requests + BeautifulSoup.
    3. Lưu output vào data/landing/news/
    4. Mỗi bài lưu 1 file JSON với metadata (url, title, date_crawled, content).

Cài đặt (tuỳ chọn):
    pip install crawl4ai
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Danh sách bài báo về nghệ sĩ Việt liên quan tới ma tuý (nguồn báo chính thống).
ARTICLE_URLS = [
    "https://ngoisao.vnexpress.net/nhung-nghe-si-viet-nga-ngua-vi-ma-tuy-4816068.html",
    "https://vietnamnet.vn/sao-viet-bi-bat-ngoi-tu-mat-danh-tieng-vi-chat-cam-2513746.html",
    "https://vietnamnet.vn/3-nu-nghe-si-viet-tu-huy-danh-tieng-vi-lien-quan-den-ma-tuy-2514737.html",
    "https://tienphong.vn/nghe-si-dinh-ma-tuy-khoang-trong-sau-nhung-cu-truot-nga-post1845503.tpo",
    "https://vov.vn/giai-tri/chua-day-1-thang-3-nghe-si-viet-bi-khoi-to-vi-lien-quan-ma-tuy-gay-chan-dong-post1293496.vov",
    "https://baochinhphu.vn/khoi-to-bat-tam-giam-ca-si-long-nhat-son-ngoc-minh-vi-to-chuc-su-dung-ma-tuy-102260520125739676.htm",
    "https://danviet.vn/nhuc-nhoi-loat-nghe-si-vuong-lao-ly-vi-ma-tuy-khong-chi-la-sa-nga-ma-con-la-su-ton-thuong-doi-voi-niem-tin-cong-chung-d1428424.html",
]


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _extract_with_bs4(url: str) -> dict:
    """Fallback crawler: requests + BeautifulSoup. Trích tiêu đề + nội dung <p>."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    # Tiêu đề: ưu tiên og:title, rồi <h1>, rồi <title>.
    title = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.h1:
        title = soup.h1.get_text(strip=True)
    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    # Loại bỏ phần thừa rồi gom toàn bộ đoạn văn.
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    content = "\n\n".join(p for p in paragraphs if len(p) > 40)

    return {
        "url": url,
        "title": title or "Unknown",
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content,
        "crawler": "requests+bs4",
    }


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài báo và trả về dict metadata + content.
    Dùng Crawl4AI nếu có, ngược lại fallback requests + BeautifulSoup.
    """
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return {
                "url": url,
                "title": (result.metadata or {}).get("title", "Unknown"),
                "date_crawled": datetime.now().isoformat(),
                "content_markdown": result.markdown or "",
                "crawler": "crawl4ai",
            }
    except ImportError:
        # Crawl4AI không khả dụng -> fallback đồng bộ qua thread.
        return await asyncio.to_thread(_extract_with_bs4, url)


async def crawl_all():
    """Crawl toàn bộ bài báo trong ARTICLE_URLS."""
    setup_directory()

    saved = 0
    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        try:
            article = await crawl_article(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Lỗi: {exc}")
            continue

        if len((article.get("content_markdown") or "")) < 200:
            print("  ✗ Nội dung quá ngắn, bỏ qua.")
            continue

        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1
        print(f"  ✓ Saved: {filename} ({filepath.stat().st_size // 1024} KB) — {article['title'][:60]}")

    print(f"\nHoàn tất: {saved}/{len(ARTICLE_URLS)} bài đã lưu vào {DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
