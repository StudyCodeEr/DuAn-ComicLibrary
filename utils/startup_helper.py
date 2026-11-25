"""Shim tương thích: bản cài đặt thật nằm ở `mangalib.shell.autostart`.

File này còn tồn tại chỉ để UI Flet cũ còn import được cho tới khi nó bị xoá.
"""

from __future__ import annotations

from mangalib.shell.autostart import disable, enable, is_enabled


def is_windows() -> bool:
    import sys

    return sys.platform.startswith("win")


def toggle_startup(enable_flag: bool, app_name: str = "MangaLocalLibrary") -> bool:
    return enable() if enable_flag else disable()


def is_startup_enabled(app_name: str = "MangaLocalLibrary") -> bool:
    return is_enabled()
