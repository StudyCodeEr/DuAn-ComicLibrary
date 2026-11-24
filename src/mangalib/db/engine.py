"""Mở và đóng kết nối SQLite. Một trách nhiệm duy nhất: vòng đời kết nối.

Bản cũ (`core/database.py`) giữ **một connection sống lâu** với
`check_same_thread=False` và dùng nó từ ba luồng khác nhau, trong khi toàn repo
**không có một `threading.Lock` nào**. `close()` cũng không nằm trong `finally`
nên hễ truy vấn nổ là leak file handle.

Ở đây (quy tắc R3):
  * không có connection nào sống lâu — mỗi việc mở một cái rồi đóng;
  * `check_same_thread=False` biến mất, vì không còn connection bị chia sẻ;
  * WAL cho nhiều reader song song với một writer;
  * mọi lần ghi đi qua một lock, nên không bao giờ gặp "database is locked";
  * lỗi thì rollback rồi nêu lại — không nuốt (quy tắc R4);
  * `close()` nằm trong `finally`.

Repo nhận `conn` làm tham số nên test được bằng `:memory:`, không cần mock,
không tạo file.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from mangalib import paths

__all__ = [
    "SCHEMA_VERSION",
    "apply_schema",
    "connect",
    "init_db",
    "read_only",
    "schema_sql",
    "schema_version",
    "write",
]

SCHEMA_VERSION = "2"

_WRITE_LOCK = threading.Lock()
"""Mọi giao dịch ghi đi qua đây. WAL + busy_timeout là lưới an toàn thứ hai."""

_BUSY_TIMEOUT_MS = 5_000


def schema_sql() -> str:
    """Nội dung `schema.sql` đi kèm package."""
    return (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")


def _configure(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Mở kết nối, commit khi xong, rollback khi lỗi, luôn đóng.

    Không tự lấy lock: dùng `write()` cho giao dịch ghi, `read_only()` để đọc.
    """
    target = str(path) if path is not None else str(paths.db_path())
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target, timeout=_BUSY_TIMEOUT_MS / 1000)
    try:
        _configure(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def write(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Giao dịch ghi: giữ lock trong suốt giao dịch."""
    with _WRITE_LOCK, connect(path) as conn:
        yield conn


@contextmanager
def read_only(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Chỉ đọc. Nhờ WAL nên chạy song song với một writer mà không chặn nhau."""
    with connect(path) as conn:
        yield conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Tạo bảng nếu chưa có và ghi số phiên bản schema vào bảng `meta`."""
    conn.executescript(schema_sql())
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (SCHEMA_VERSION,),
    )


def schema_version(conn: sqlite3.Connection) -> str | None:
    """Phiên bản schema của DB đang mở, hoặc None khi DB còn trống."""
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    except sqlite3.OperationalError:
        return None
    return row["value"] if row else None


def init_db(path: Path | str | None = None) -> Path:
    """Tạo DB (nếu cần) và áp schema. Gọi tường minh, không bao giờ lúc import."""
    target = Path(path) if path is not None else paths.db_path()
    with write(target) as conn:
        apply_schema(conn)
    return target
