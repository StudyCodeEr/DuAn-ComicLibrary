"""Hàng đợi tải: trạng thái và **lỗi** của từng việc.

Cột `error` là lý do bảng này tồn tại. Bản cũ có 17 chỗ `except: pass`, nên khi
một lần tải thất bại thì không còn dấu vết nào: người dùng chỉ thấy nó không chạy.
Ở đây mọi thất bại được ghi lại kèm thông điệp, và UI đọc được.
"""

from __future__ import annotations

import sqlite3
import uuid

from mangalib.db.models import Job, JobState

__all__ = [
    "cancel",
    "create",
    "finish",
    "get",
    "list_jobs",
    "update_progress",
]

_ACTIVE_STATES = ("queued", "running", "needs_login")


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        url=row["url"],
        manga_id=row["manga_id"],
        state=row["state"],
        phase=row["phase"],
        done=int(row["done"]),
        total=int(row["total"]),
        error=row["error"],
        created_at=row["created_at"],
        finished_at=row["finished_at"],
    )


def create(conn: sqlite3.Connection, url: str, *, job_id: str | None = None) -> Job:
    identifier = job_id or uuid.uuid4().hex
    conn.execute(
        "INSERT INTO job (id, url, state) VALUES (?, ?, 'queued')",
        (identifier, url),
    )
    job = get(conn, identifier)
    assert job is not None  # vừa ghi xong
    return job


def get(conn: sqlite3.Connection, job_id: str) -> Job | None:
    row = conn.execute("SELECT * FROM job WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def list_jobs(
    conn: sqlite3.Connection,
    *,
    state: JobState | None = None,
    active_only: bool = False,
    limit: int = 50,
) -> list[Job]:
    """Việc mới nhất trước. `active_only` lấy những việc chưa kết thúc."""
    if state is not None:
        rows = conn.execute(
            "SELECT * FROM job WHERE state = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (state, limit),
        ).fetchall()
    elif active_only:
        placeholders = ",".join("?" * len(_ACTIVE_STATES))
        rows = conn.execute(
            f"""SELECT * FROM job WHERE state IN ({placeholders})
                ORDER BY created_at DESC, id DESC LIMIT ?""",
            (*_ACTIVE_STATES, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM job ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_job(row) for row in rows]


def update_progress(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    state: JobState | None = None,
    phase: str | None = None,
    done: int | None = None,
    total: int | None = None,
) -> None:
    """Cập nhật tiến trình. Chỉ đổi những cột được truyền vào."""
    conn.execute(
        """
        UPDATE job
           SET state = COALESCE(?, state),
               phase = COALESCE(?, phase),
               done  = COALESCE(?, done),
               total = COALESCE(?, total)
         WHERE id = ?
        """,
        (state, phase, done, total, job_id),
    )


def finish(
    conn: sqlite3.Connection,
    job_id: str,
    state: JobState,
    *,
    error: str | None = None,
    manga_id: int | None = None,
) -> None:
    """Kết thúc một việc. Thất bại thì **lỗi được lưu**, không bị nuốt."""
    conn.execute(
        """
        UPDATE job
           SET state = ?, error = ?, manga_id = COALESCE(?, manga_id),
               finished_at = datetime('now')
         WHERE id = ?
        """,
        (state, error, manga_id, job_id),
    )


def cancel(conn: sqlite3.Connection, job_id: str) -> bool:
    """Chỉ huỷ được việc chưa kết thúc. Trả False nếu nó đã xong hoặc đã lỗi."""
    placeholders = ",".join("?" * len(_ACTIVE_STATES))
    cursor = conn.execute(
        f"""
        UPDATE job SET state = 'cancelled', finished_at = datetime('now')
         WHERE id = ? AND state IN ({placeholders})
        """,
        (job_id, *_ACTIVE_STATES),
    )
    return bool(cursor.rowcount)
