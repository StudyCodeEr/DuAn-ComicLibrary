"""Tải và lưu.

    images.py    magic byte + thumbnail (Pillow chỉ ở đây)
    fetcher.py   tải song song, ghi nguyên tử, bỏ qua trang đã có
    pipeline.py  điều phối: metadata -> URL ảnh -> tải -> DB -> metadata.json
"""

from __future__ import annotations

from mangalib.download import fetcher, images, pipeline
from mangalib.download.pipeline import DownloadReport, download_manga

__all__ = ["DownloadReport", "download_manga", "fetcher", "images", "pipeline"]
