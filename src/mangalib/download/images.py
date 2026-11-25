"""Nhận dạng ảnh bằng magic byte, và thumbnail. Pillow CHỈ được import ở đây."""

from __future__ import annotations

import logging
from pathlib import Path

__all__ = ["make_thumbnail", "sniff_ext"]

logger = logging.getLogger(__name__)


def sniff_ext(data: bytes) -> str | None:
    """Phần mở rộng thật theo nội dung. None nghĩa là dữ liệu không phải ảnh.

    Bản cũ tin vào đuôi trong URL nên lưu cả trang lỗi HTML thành `Trang_007.png`.
    """
    if len(data) < 12:
        return None
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return "avif"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    return None


def make_thumbnail(source: Path, dest: Path, *, width: int = 400) -> bool:
    """Tạo thumbnail cho lưới thư viện. Thất bại thì báo False, không nêu lỗi."""
    try:
        from PIL import Image

        with Image.open(source) as image:
            image.thumbnail((width, width * 3))
            dest.parent.mkdir(parents=True, exist_ok=True)
            image.convert("RGB").save(dest, format="WEBP", quality=82)
        return True
    except (OSError, ValueError) as exc:
        logger.warning("không tạo được thumbnail cho %s: %s", source.name, exc)
        return False
