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


def open_window(
    url: str, *, width: int = 1280, height: int = 900
) -> tuple[str, subprocess.Popen | None]:
    """Mở cửa sổ app.

    Trả `(mô tả cách đã mở, tiến trình)`. Cần tiến trình để biết lúc người dùng
    đóng cửa sổ — ta không sở hữu nút X của cửa sổ Edge nên chỉ theo dõi được
    bằng cách chờ tiến trình kết thúc.
    """
    browser = find_browser()
    if browser is not None:
        try:
            proc = subprocess.Popen(
                [
                    str(browser),
                    f"--app={url}",
                    f"--window-size={width},{height}",
                ]
            )
            return f"cửa sổ app ({browser.name})", proc
        except OSError as exc:
            logger.warning("không mở được %s: %s", browser.name, exc)

    webbrowser.open(url)
    return "trình duyệt mặc định", None
