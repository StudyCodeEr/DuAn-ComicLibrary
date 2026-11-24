"""Khởi tạo logging TƯỜNG MINH (quy tắc R2).

Bản cũ (`utils/logger.py`) gọi `os.makedirs("logs")` và mở `FileHandler` ngay ở
module scope với đường dẫn **tương đối**. Khi Windows tự khởi động app bằng
`--hidden` qua Registry, cwd là `C:\\Windows\\System32`, nên dòng đó ném
`PermissionError` **ngay lúc import** và app chết trước khi vẽ được UI.

Ở đây không có dòng I/O nào chạy khi import. `setup_logging()` được gọi tường minh
từ `cli.py`, và nó dùng `paths.logs_dir()` nên không phụ thuộc cwd.
"""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

from mangalib import paths

__all__ = ["log_crash", "setup_logging"]

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def setup_logging(
    *,
    level: int = logging.INFO,
    to_console: bool = True,
    logs_dir: Path | None = None,
) -> Path:
    """Cấu hình logger gốc. Trả về đường dẫn file log của hôm nay.

    Gọi nhiều lần là an toàn: handler cũ được thay, không cộng dồn (nguyên nhân
    bản cũ in mỗi dòng log hai lần).
    """
    directory = Path(logs_dir) if logs_dir is not None else paths.logs_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / f"log_{datetime.now():%Y-%m-%d}.txt"

    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if to_console:
        handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
        handlers=handlers,
        force=True,
    )
    return log_file


def log_crash(exc: BaseException, *, logs_dir: Path | None = None) -> Path:
    """Ghi traceback đầy đủ vào `crash.log`, dạng **ghi thêm**.

    Bản cũ mở `crash_log.txt` ở mode `"w"` nên mỗi lần sập lại xoá dấu vết lần
    trước, và hàm đó còn bị một stub trong `main.py:44` che nên chưa bao giờ chạy.
    """
    directory = Path(logs_dir) if logs_dir is not None else paths.logs_dir()
    directory.mkdir(parents=True, exist_ok=True)
    crash_file = directory / "crash.log"

    report = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    with crash_file.open("a", encoding="utf-8") as handle:
        handle.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{report}")

    logging.getLogger(__name__).critical("Ứng dụng gặp lỗi nghiêm trọng: %s", exc)
    return crash_file
