"""Tự khởi động cùng Windows, ghi vào Registry của người dùng (HKCU).

Khác bản cũ ở một điểm quan trọng: lệnh đăng ký chạy `mangalib app --hidden`, và
mọi đường dẫn do `paths.py` quyết định — nên cwd mà Windows đặt khi tự khởi động
(`C:\\Windows\\System32`) không còn ảnh hưởng gì. Bản cũ chết ngay lúc import ở
đúng tình huống này.
"""

from __future__ import annotations

import logging
import sys

__all__ = ["APP_NAME", "command", "disable", "enable", "is_enabled"]

logger = logging.getLogger(__name__)

APP_NAME = "MangaLocalLibrary"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def command() -> str:
    """Lệnh ghi vào Registry."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" app --hidden'
    return f'"{sys.executable}" -m mangalib.cli app --hidden'


def _open_key(write: bool):
    import winreg

    access = winreg.KEY_ALL_ACCESS if write else winreg.KEY_READ
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, access)


def enable() -> bool:
    if not sys.platform.startswith("win"):
        return False
    import winreg

    try:
        with _open_key(write=True) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command())
        return True
    except OSError as exc:
        logger.error("không ghi được Registry: %s", exc)
        return False


def disable() -> bool:
    if not sys.platform.startswith("win"):
        return False
    import winreg

    try:
        with _open_key(write=True) as key:
            winreg.DeleteValue(key, APP_NAME)
        return True
    except FileNotFoundError:
        return True  # chưa bật thì coi như đã tắt
    except OSError as exc:
        logger.error("không xoá được khoá Registry: %s", exc)
        return False


def is_enabled() -> bool:
    if not sys.platform.startswith("win"):
        return False
    import winreg

    try:
        with _open_key(write=False) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
    except OSError:
        return False
    return "mangalib" in value.lower() or sys.executable in value
