"""Vị trí đọc.

Đây là bảng làm nên tính năng mà PRODUCT.md gọi là không sao chép được: đọc tới
trang 12 trên PC, mở điện thoại là vào đúng trang 12, trong khi toàn bộ nội dung
chưa bao giờ rời khỏi máy người dùng.

Bản cũ không lưu vị trí đọc ở đâu cả.
"""

from __future__ import annotations

import sqlite3

from mangalib.db.models import Progress

__all__ = ["clear", "get", "save"]


def get(conn: sqlite3.Connection, manga_id: int) -> Progress | None:
    row = conn.execute(
        "SELECT * FROM progress WHERE manga_id = ?", (manga_id,)
    ).fetchone()
    if row is None:
        return None
    return Progress(
        manga_id=int(row["manga_id"]),
        chapter_id=int(row["chapter_id"]),
        page_idx=int(row["page_idx"]),
        updated_at=row["updated_at"],
    )


def save(
    conn: sqlite3.Connection,
    manga_id: int,
    chapter_id: int,
    page_idx: int = 0,
) -> Progress:
    """Ghi vị trí đọc và cập nhật `manga.last_read_at` trong cùng giao dịch.

    Hai thứ này phải đi cùng nhau: nếu lệch, dải "Đọc tiếp" sẽ xếp sai thứ tự so
    với vị trí thật.
    """
    conn.execute(
        """
        INSERT INTO progress (manga_id, chapter_id, page_idx, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(manga_id) DO UPDATE SET
            chapter_id = excluded.chapter_id,
            page_idx   = excluded.page_idx,
            updated_at = excluded.updated_at
        """,
        (manga_id, chapter_id, max(0, int(page_idx))),
    )
    conn.execute(
        "UPDATE manga SET last_read_at = datetime('now') WHERE id = ?", (manga_id,)
    )
    result = get(conn, manga_id)
    assert result is not None  # vừa ghi xong nên không thể None
    return result


def clear(conn: sqlite3.Connection, manga_id: int) -> bool:
    """Xoá vị trí đọc (người dùng chọn "đánh dấu chưa đọc")."""
    return bool(
        conn.execute("DELETE FROM progress WHERE manga_id = ?", (manga_id,)).rowcount
    )
