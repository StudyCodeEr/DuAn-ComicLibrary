"""mangalib - thu vien truyen tranh cuc bo.

QUY TAC R2: module khong duoc lam I/O luc import (khong mkdir, khong mo file,
khong doc config). Logging duoc khoi tao TUONG MINH tu cli.py.
Ly do: app cu chet ngay luc import khi autostart voi cwd = C:\\Windows\\System32,
vi utils/logger.py goi os.makedirs("logs") o module scope.
"""

__version__ = "3.0.0.dev0"
__all__ = ["__version__"]
