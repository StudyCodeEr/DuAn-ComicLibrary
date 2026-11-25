"""Khay hệ thống. Chạy ở luồng chính và chặn cho tới khi người dùng chọn Thoát."""

from __future__ import annotations

import logging
from collections.abc import Callable

from mangalib import paths

__all__ = ["run_tray"]

logger = logging.getLogger(__name__)


def _load_icon():
    from PIL import Image

    for candidate in (
        paths.app_dir() / "app_icon.ico",
        paths.repo_root() / "app_icon.ico",
        paths.assets_dir() / "icon.png",
    ):
        if candidate.is_file():
            return Image.open(candidate)

    # Không có icon thì vẽ một ô vuông màu nhấn, hơn là để app không có khay.
    return Image.new("RGB", (64, 64), "#06b6d4")


def run_tray(url: str, *, on_open: Callable[[], None], on_quit: Callable[[], None]) -> None:
    """Hiện icon khay. Trả về khi người dùng chọn Thoát.

    Nếu pystray không dùng được (thiếu thư viện, môi trường không có khay), hàm
    này nói rõ và trả về ngay thay vì làm app chết.
    """
    try:
        import pystray
    except ImportError:
        logger.warning("pystray không khả dụng: app vẫn chạy, chỉ không có icon khay")
        return

    menu = pystray.Menu(
        pystray.MenuItem("Mở thư viện", lambda *_: on_open(), default=True),
        pystray.MenuItem(url, lambda *_: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Thoát", lambda icon, *_: (icon.stop(), on_quit())),
    )
    icon = pystray.Icon("mangalib", _load_icon(), "Manga Local Library", menu)
    icon.run()
