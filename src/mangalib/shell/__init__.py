"""Vỏ desktop: khay hệ thống, cửa sổ app, tự khởi động.

    window.py     mở web UI trong cửa sổ Edge --app (0 dependency mới)
    tray.py       icon khay hệ thống
    autostart.py  Registry HKCU, lệnh `mangalib app --hidden`
"""

from __future__ import annotations

from mangalib.shell import autostart, tray, window

__all__ = ["autostart", "tray", "window"]
