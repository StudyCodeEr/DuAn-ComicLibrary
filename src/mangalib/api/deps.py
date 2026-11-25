"""Phụ thuộc dùng chung của API: xác thực LAN và giải đường dẫn file an toàn."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request

from mangalib import config, paths
from mangalib.errors import UnsafePathError

__all__ = ["is_local", "require_lan_token", "require_local", "resolve_page_file"]

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_local(request: Request) -> bool:
    return bool(request.client) and request.client.host in _LOCAL_HOSTS


def require_lan_token(request: Request) -> None:
    """Máy này miễn token; thiết bị khác trong LAN phải có token."""
    if is_local(request):
        return
    expected = config.load().lan_token
    if not expected:
        raise HTTPException(503, "Chưa có token LAN. Mở Cài đặt trên máy chủ để tạo.")
    supplied = request.headers.get("X-API-Token") or request.cookies.get("mlib_token")
    if supplied != expected:
        raise HTTPException(401, "Thiếu hoặc sai token. Quét lại mã QR trong Cài đặt.")


def require_local(request: Request) -> None:
    """Chỉ cho localhost: mở thư mục, chọn thư mục, nhận payload từ userscript."""
    if not is_local(request):
        raise HTTPException(403, "Chỉ dùng được trên chính máy chạy mangalib.")


def resolve_page_file(slug: str, chapter_dir: str, file_name: str) -> Path:
    """Giải đường dẫn ảnh, từ chối mọi thứ thoát ra ngoài thư viện.

    Lỗ hổng của bản cũ: `server_pc.py` ghép thẳng tên lấy từ URL vào đường dẫn,
    nên `GET /manga/..%2F..%2FUsers` liệt kê được thư mục ngoài thư viện.
    """
    try:
        target = paths.safe_join(paths.library_dir(), slug, chapter_dir, file_name)
    except UnsafePathError as exc:
        raise HTTPException(400, "Đường dẫn không hợp lệ") from exc
    if not target.is_file():
        raise HTTPException(404, "Không tìm thấy ảnh")
    return target
