"""
Task 1 — Thu thập văn bản pháp luật về ma tuý và các chất cấm.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản pháp luật (PDF/DOCX) từ các nguồn chính thống.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, có năm ban hành.

Gợi ý nguồn:
    - https://thuvienphapluat.vn
    - https://vanban.chinhphu.vn
    - https://luatvietnam.vn

Gợi ý văn bản:
    - Luật Phòng, chống ma tuý 2021 (73/2021/QH15)
    - Nghị định 105/2021/NĐ-CP
    - Bộ luật Hình sự 2015 (sửa đổi 2017) - Chương XX
    - Nghị định 57/2022/NĐ-CP về danh mục chất ma tuý
"""

import sys
from pathlib import Path

import requests

# Đảm bảo in được tiếng Việt / ký tự unicode trên console Windows (cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# User-Agent giả lập trình duyệt — nhiều cổng thông tin .gov.vn chặn request không có UA.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Danh sách văn bản pháp luật về ma tuý + link tải trực tiếp (PDF) từ cổng .gov.vn.
DOCUMENTS = [
    {
        "filename": "luat-phong-chong-ma-tuy-2021.pdf",
        "title": "Luật Phòng, chống ma tuý 2021 (Luật số 73/2021/QH14)",
        "url": "https://datafiles.nghean.gov.vn/nan-ubnd/2930/quantritintuc20246/"
               "73_Lu%E1%BA%ADt%20ph%C3%B2ng-%20ch%E1%BB%91ng%20%20ma%20t%C3%BAy"
               "638532221004524725.pdf",
    },
    {
        "filename": "nghi-dinh-105-2021-huong-dan-luat-ma-tuy.pdf",
        "title": "Nghị định 105/2021/NĐ-CP hướng dẫn thi hành Luật Phòng, chống ma tuý",
        "url": "https://datafiles.nghean.gov.vn/nan-ubnd/2930/quantritintuc20246/"
               "105.signed_02638532227014354408.pdf",
    },
    {
        "filename": "bo-luat-hinh-su-2015-sua-doi-2017.pdf",
        "title": "Bộ luật Hình sự 2015 (sửa đổi 2017) — Chương XX: Các tội phạm về ma tuý",
        "url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/9/135-vbhn-vpqh.pdf",
    },
]


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def download_file(url: str, filename: str) -> Path:
    """Tải 1 file về DATA_DIR. Bỏ qua nếu file đã tồn tại và hợp lệ (>1KB)."""
    filepath = DATA_DIR / filename
    if filepath.exists() and filepath.stat().st_size > 1024:
        print(f"⏭  Đã có sẵn, bỏ qua: {filename}")
        return filepath

    resp = requests.get(url, headers=HEADERS, timeout=90)
    resp.raise_for_status()
    filepath.write_bytes(resp.content)
    size_kb = filepath.stat().st_size / 1024
    print(f"✓ Đã tải: {filename} ({size_kb:.1f} KB)")
    return filepath


def collect_all():
    """Tải toàn bộ văn bản pháp luật trong DOCUMENTS."""
    setup_directory()
    for doc in DOCUMENTS:
        try:
            download_file(doc["url"], doc["filename"])
        except Exception as exc:  # noqa: BLE001
            print(f"✗ Lỗi tải '{doc['title']}': {exc}")


if __name__ == "__main__":
    collect_all()
