"""Chương truyện.

Hai thứ ở đây sửa trực tiếp bug #4 của bản cũ ("✅ Xong: N ảnh" với N là số URL
tìm thấy, nên chương trắng vẫn báo thành công):

* `status` của chương **được suy ra từ số liệu**, không phải từ việc vòng lặp tải
  đã chạy hết. `decide_status()` so `saved` với `expected`;
* `complete_dir_names()` cho tầng tải biết chương nào đã đủ ảnh để **bỏ hẳn** —
  không mở browser, không request nào. Đây là tầng resume tiết kiệm nhất.
"""

from __future__ import annotations

import sqlite3

from mangalib.db.models import Chapter, ChapterStatus

__all__ = [
    "complete_dir_names",
    "count_for_manga",
    "decide_status",
    "delete",
    "get",
    "list_for_manga",
    "record_result",
    "upsert",
]


def decide_status(saved: int, expected: int | None) -> ChapterStatus:
    """Trạng thái chương, suy ra từ số liệu thật.

    Không có ảnh nào mà vẫn gọi là xong là chính xác cái bug cần diệt.
    """
    if saved <= 0:
        return "failed" if expected else "pending"
    if expected is None:
        return "complete"
    return "complete" if saved >= expected else "partial"


def _row_to_chapter(row: sqlite3.Row) -> Chapter:
    return Chapter(
        id=int(row["id"]),
        manga_id=int(row["manga_id"]),
        number=row["number"],
        title=row["title"],
        dir_name=row["dir_name"],
        source_url=row["source_url"],
        page_count=int(row["page_count"]),
        expected_page_count=row["expected_page_count"],
        status=row["status"],
        downloaded_at=row["downloaded_at"],
    )


def upsert(conn: sqlite3.Connection, manga_id: int, chapter: Chapter) -> int:
    """Thêm hoặc cập nhật chương, khớp theo `(manga_id, dir_name)`.

    Không ghi đè `status`/`page_count` đã có: chỉ `record_result()` được đổi hai
    cột đó, vì chỉ nó biết kết quả tải thật.
    """
    # Khong loc deleted_at: tai lai mot chuong da xoa mem la HOI SINH no, khong
    # phai tao ban ghi thu hai trung (manga_id, dir_name).
    row = conn.execute(
        "SELECT id FROM chapter WHERE manga_id = ? AND dir_name = ?",
        (manga_id, chapter.dir_name),
    ).fetchone()

    if row is not None:
        chapter_id = int(row["id"])
        conn.execute(
            """
            UPDATE chapter
               SET number = ?, title = ?, source_url = COALESCE(?, source_url),
                   expected_page_count = COALESCE(?, expected_page_count)
             WHERE id = ?
            """,
            (
                chapter.number,
                chapter.title,
                chapter.source_url,
                chapter.expected_page_count,
                chapter_id,
            ),
        )
        return chapter_id

    cursor = conn.execute(
        """
        INSERT INTO chapter (manga_id, number, title, dir_name, source_url,
                             expected_page_count, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            manga_id,
            chapter.number,
            chapter.title,
            chapter.dir_name,
            chapter.source_url,
            chapter.expected_page_count,
            chapter.status,
        ),
    )
    return int(cursor.lastrowid)


def record_result(
    conn: sqlite3.Connection,
    chapter_id: int,
    *,
    saved: int,
    expected: int | None,
) -> ChapterStatus:
    """Ghi kết quả tải thật và trả về trạng thái đã quyết định."""
    status = decide_status(saved, expected)
    conn.execute(
        """
        UPDATE chapter
           SET page_count = ?, expected_page_count = ?, status = ?,
               downloaded_at = datetime('now')
         WHERE id = ?
        """,
        (saved, expected, status, chapter_id),
    )
    return status


def list_for_manga(conn: sqlite3.Connection, manga_id: int) -> list[Chapter]:
    """Chương theo thứ tự đọc: số nhỏ trước, chương không số xuống cuối."""
    rows = conn.execute(
        """
        SELECT * FROM chapter
        WHERE manga_id = ? AND deleted_at IS NULL
        -- sort_index la thu tu nguoi dung tu keo; chua keo thi xep theo so chuong.
        ORDER BY sort_index IS NULL, sort_index ASC,
                 number IS NULL, number ASC, dir_name ASC
        """,
        (manga_id,),
    ).fetchall()
    return [_row_to_chapter(row) for row in rows]


def get(conn: sqlite3.Connection, chapter_id: int) -> Chapter | None:
    row = conn.execute(
        "SELECT * FROM chapter WHERE id = ? AND deleted_at IS NULL", (chapter_id,)
    ).fetchone()
    return _row_to_chapter(row) if row else None


def complete_dir_names(conn: sqlite3.Connection, manga_id: int) -> set[str]:
    """Tên thư mục của những chương đã đủ ảnh — tầng tải bỏ hẳn, không mở browser."""
    rows = conn.execute(
        """
        SELECT dir_name FROM chapter
        WHERE manga_id = ? AND deleted_at IS NULL AND status = 'complete'
          AND (expected_page_count IS NULL OR page_count >= expected_page_count)
        """,
        (manga_id,),
    ).fetchall()
    return {row["dir_name"] for row in rows}


def count_for_manga(conn: sqlite3.Connection, manga_id: int) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) AS total FROM chapter WHERE manga_id = ? AND deleted_at IS NULL",
            (manga_id,),
        ).fetchone()["total"]
    )


def delete(conn: sqlite3.Connection, chapter_id: int) -> bool:
    """Xoá mềm. File ảnh của chương vẫn nằm nguyên trên đĩa."""
    return bool(
        conn.execute(
            "UPDATE chapter SET deleted_at = datetime('now') "
            "WHERE id = ? AND deleted_at IS NULL",
            (chapter_id,),
        ).rowcount
    )


def set_order(conn: sqlite3.Connection, manga_id: int, chapter_ids: list[int]) -> int:
    """Ghi thứ tự người dùng tự sắp. Một lệnh phục vụ cả kéo thả lẫn nút A-Z/Z-A."""
    rows = [(i, cid, manga_id) for i, cid in enumerate(chapter_ids)]
    conn.executemany(
        "UPDATE chapter SET sort_index = ? WHERE id = ? AND manga_id = ?", rows
    )
    return len(rows)
