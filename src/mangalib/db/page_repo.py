"""Từng trang ảnh của một chương.

Bản cũ không có bảng này, nên reader phải `os.listdir` mỗi lần mở chương và việc
tải lại không biết trang nào đã có. Có bảng này thì:

* reader lấy danh sách trang bằng một truy vấn, kèm `width`/`height` nên bố cục
  không nhảy khi ảnh vừa tải xong;
* `saved_indexes()` cho tầng tải biết chính xác trang nào còn thiếu — tầng resume
  mịn nhất, dưới mức chương.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from mangalib.db.models import Page

__all__ = [
    "count_for_chapter",
    "list_for_chapter",
    "replace_for_chapter",
    "saved_indexes",
    "upsert_many",
]


def _row_to_page(row: sqlite3.Row) -> Page:
    return Page(
        idx=int(row["idx"]),
        file_name=row["file_name"],
        source_url=row["source_url"],
        width=row["width"],
        height=row["height"],
        byte_size=row["byte_size"],
    )


def upsert_many(
    conn: sqlite3.Connection, chapter_id: int, pages: Sequence[Page]
) -> int:
    """Ghi thêm/cập nhật từng trang, không xoá trang nào.

    Dùng khi tải tiếp một chương đang thiếu: trang cũ giữ nguyên.
    """
    for page in pages:
        conn.execute(
            """
            INSERT INTO page (chapter_id, idx, file_name, source_url,
                              width, height, byte_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chapter_id, idx) DO UPDATE SET
                file_name  = excluded.file_name,
                source_url = COALESCE(excluded.source_url, page.source_url),
                width      = COALESCE(excluded.width, page.width),
                height     = COALESCE(excluded.height, page.height),
                byte_size  = COALESCE(excluded.byte_size, page.byte_size)
            """,
            (
                chapter_id,
                page.idx,
                page.file_name,
                page.source_url,
                page.width,
                page.height,
                page.byte_size,
            ),
        )
    return len(pages)


def replace_for_chapter(
    conn: sqlite3.Connection, chapter_id: int, pages: Sequence[Page]
) -> int:
    """Thay toàn bộ danh sách trang. Dùng khi quét lại chương từ đĩa."""
    conn.execute("DELETE FROM page WHERE chapter_id = ?", (chapter_id,))
    return upsert_many(conn, chapter_id, pages)


def list_for_chapter(conn: sqlite3.Connection, chapter_id: int) -> list[Page]:
    rows = conn.execute(
        "SELECT * FROM page WHERE chapter_id = ? ORDER BY idx ASC", (chapter_id,)
    ).fetchall()
    return [_row_to_page(row) for row in rows]


def saved_indexes(conn: sqlite3.Connection, chapter_id: int) -> set[int]:
    """Số thứ tự các trang đã có trong DB — phần còn thiếu là phần cần tải."""
    rows = conn.execute(
        "SELECT idx FROM page WHERE chapter_id = ?", (chapter_id,)
    ).fetchall()
    return {int(row["idx"]) for row in rows}


def count_for_chapter(conn: sqlite3.Connection, chapter_id: int) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) AS total FROM page WHERE chapter_id = ?", (chapter_id,)
        ).fetchone()["total"]
    )
