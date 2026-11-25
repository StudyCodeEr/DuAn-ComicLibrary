"""Nhận dạng ảnh bằng magic byte, và thumbnail. Pillow CHỈ được import ở đây."""

from __future__ import annotations

import logging
from pathlib import Path

__all__ = ["convert", "make_thumbnail", "sniff_ext"]

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


def convert(data: bytes, fmt: str) -> tuple[bytes, str] | None:
    """Đổi ảnh sang `fmt`, trả `(bytes, đuôi)`. None = giữ nguyên bản gốc.

    Mặc định là "original" vì re-encode làm file phình 3-5 lần - đúng lỗi của bản
    cũ. Hàm này chỉ chạy khi người dùng tự chọn định dạng khác trong Cài đặt.
    Đổi hỏng thì trả None để bên gọi vẫn lưu được bytes gốc, không mất ảnh.
    """
    if fmt == "original":
        return None
    try:
        import io

        from PIL import Image

        pillow_name = {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[fmt]
        buffer = io.BytesIO()
        with Image.open(io.BytesIO(data)) as image:
            # JPEG khong co kenh alpha: anh PNG trong suot phai phang ve RGB truoc.
            source = image.convert("RGB") if pillow_name == "JPEG" else image
            source.save(buffer, format=pillow_name, quality=88)
        return buffer.getvalue(), {"jpeg": "jpg", "png": "png", "webp": "webp"}[fmt]
    except (OSError, ValueError, KeyError) as exc:
        logger.warning("không đổi được ảnh sang %s, giữ bản gốc: %s", fmt, exc)
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
