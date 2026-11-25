"""Mở web UI trong một cửa sổ riêng, không thanh địa chỉ.

Dùng Edge đã cài với `--app=` nên **không thêm dependency nào**: không Chromium
riêng, không Electron, không webview. Nếu không tìm thấy Edge thì mở bằng trình
duyệt mặc định.
"""

from __future__ import annotations

import logging
import subprocess
import webbrowser
from pathlib import Path

__all__ = ["find_browser", "open_window"]

logger = logging.getLogger(__name__)

_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def find_browser() -> Path | None:
    for candidate in _CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def open_window(url: str, *, width: int = 1280, height: int = 900) -> str:
    """Mở cửa sổ app. Trả về cách đã dùng, để báo lại cho người dùng."""
    browser = find_browser()
    if browser is not None:
        try:
            subprocess.Popen(
                [
                    str(browser),
                    f"--app={url}",
                    f"--window-size={width},{height}",
                ]
            )
            return f"cửa sổ app ({browser.name})"
        except OSError as exc:
            logger.warning("không mở được %s: %s", browser.name, exc)

    webbrowser.open(url)
    return "trình duyệt mặc định"
