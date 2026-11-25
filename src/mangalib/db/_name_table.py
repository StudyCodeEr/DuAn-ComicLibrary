"""Phần dùng chung của hai bảng tên: `tag` và `author`.

Cả hai đều là "bảng tên duy nhất + bảng liên kết tới truyện", nên ba việc này
giống nhau hoàn toàn: thêm tên nếu chưa có, đếm số truyện mỗi tên, và dọn tên
không còn truyện nào dùng.

Phần KHÁC nhau nằm ở repo riêng: tác giả có thêm chiều `role` (tác giả / họa sĩ),
tag thì không. Tách ở đây đủ để không nhân đôi code, mà không gộp hai thứ khác
bản chất vào một lớp trừu tượng chung.

Module riêng tư (tiền tố `_`): chỉ `author_repo` và `tag_repo` dùng.
"""

from __future__ import annotations

import sqlite3

__all__ = ["count_by_name", "prune_orphans", "upsert_name"]


def upsert_name(
    conn: sqlite3.Connection,
    table: str,
    name: str,
    *,
    sort_column: str | None = None,
    sort_value: str | None = None,
) -> int:
    """Trả id của `name` trong `table`, thêm mới nếu chưa có.

    So khớp không phân biệt hoa thường nhờ `COLLATE NOCASE` trên cột `name`,
    nên "Action" và "action" là một.
    """
    row = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return int(row["id"])

    if sort_column is not None:
        cursor = conn.execute(
            f"INSERT INTO {table} (name, {sort_column}) VALUES (?, ?)",
            (name, sort_value or ""),
        )
    else:
        cursor = conn.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    return int(cursor.lastrowid)


def count_by_name(
    conn: sqlite3.Connection,
    table: str,
    link_table: str,
    link_column: str,
) -> list[tuple[str, int]]:
    """`[(tên, số truyện)]`, nhiều nhất trước, rồi theo thứ tự chữ cái.

    Có số đếm thì UI xếp được tag/tác giả hay dùng lên trước — việc mà bản cũ
    không làm được vì `get_all_tags()` chỉ trả tên.
    """
    rows = conn.execute(
        f"""
        SELECT t.name AS name, COUNT(m.id) AS total
        FROM {table} t
        LEFT JOIN {link_table} l ON l.{link_column} = t.id
        -- Dem theo m.id chu khong phai l.manga_id: truyen da xoa mem khong duoc
        -- tinh, neu khong thi bo loc van hien tag cua truyen khong con thay.
        LEFT JOIN manga m ON m.id = l.manga_id AND m.deleted_at IS NULL
        GROUP BY t.id
        ORDER BY total DESC, t.name COLLATE NOCASE ASC
        """
    ).fetchall()
    return [(row["name"], int(row["total"])) for row in rows]


def prune_orphans(
    conn: sqlite3.Connection,
    table: str,
    link_table: str,
    link_column: str,
) -> int:
    """Xoá những tên không còn truyện nào dùng. Trả về số dòng đã xoá."""
    cursor = conn.execute(
        f"""
        DELETE FROM {table}
        WHERE id NOT IN (SELECT {link_column} FROM {link_table})
        """
    )
    return int(cursor.rowcount or 0)
