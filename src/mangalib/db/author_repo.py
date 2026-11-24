"""Tác giả và họa sĩ. Bản cũ không có khái niệm này.

Điểm thiết kế quan trọng nhất ở đây: `origin`. Khi tải lại một truyện, scraper
chỉ được phép thay những liên kết nó tự tạo (`origin='scraped'`), còn thứ người
dùng sửa tay (`origin='manual'`) phải sống sót. Bản cũ ghi đè tag mỗi lần tải nên
công sửa tay mất sạch.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence

from mangalib import naming
from mangalib.db import _name_table
from mangalib.db.models import Author, Origin

__all__ = [
    "list_all",
    "list_for_manga",
    "manga_ids_by_name",
    "prune_orphans",
    "set_for_manga",
    "upsert",
]

_TABLE = "author"
_LINK = "manga_author"


def upsert(conn: sqlite3.Connection, name: str) -> int:
    """Thêm tác giả nếu chưa có; trả id. `name_sort` không dấu để tìm được."""
    clean = naming.normalize_person_name(name)
    if not clean or naming.is_placeholder_person(clean):
        raise ValueError(f"không phải tên tác giả hợp lệ: {name!r}")
    return _name_table.upsert_name(
        conn,
        _TABLE,
        clean,
        sort_column="name_sort",
        sort_value=naming.sort_key(clean),
    )


def set_for_manga(
    conn: sqlite3.Connection,
    manga_id: int,
    authors: Sequence[Author] | Iterable[Author],
    *,
    origin: Origin = "scraped",
) -> int:
    """Đặt lại danh sách tác giả của một truyện **trong phạm vi một `origin`**.

    Chỉ xoá các liên kết cùng `origin`, nên gọi với `origin='scraped'` không bao
    giờ chạm tới thứ người dùng gắn tay.
    """
    conn.execute(
        f"DELETE FROM {_LINK} WHERE manga_id = ? AND origin = ?",
        (manga_id, origin),
    )

    written = 0
    for author in authors:
        clean = naming.normalize_person_name(author.name)
        if not clean or naming.is_placeholder_person(clean):
            continue
        author_id = upsert(conn, clean)
        conn.execute(
            f"""
            INSERT INTO {_LINK} (manga_id, author_id, role, origin)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(manga_id, author_id, role) DO UPDATE SET origin = excluded.origin
            """,
            (manga_id, author_id, author.role, origin),
        )
        written += 1
    return written


def list_for_manga(conn: sqlite3.Connection, manga_id: int) -> tuple[Author, ...]:
    rows = conn.execute(
        f"""
        SELECT a.id, a.name, l.role, l.origin
        FROM {_LINK} l
        JOIN {_TABLE} a ON a.id = l.author_id
        WHERE l.manga_id = ?
        ORDER BY l.role, a.name COLLATE NOCASE
        """,
        (manga_id,),
    ).fetchall()
    return tuple(
        Author(id=row["id"], name=row["name"], role=row["role"], origin=row["origin"])
        for row in rows
    )


def list_all(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """`[(tên tác giả, số truyện)]` để UI dựng bộ lọc."""
    return _name_table.count_by_name(conn, _TABLE, _LINK, "author_id")


def manga_ids_by_name(conn: sqlite3.Connection, name: str) -> list[int]:
    """Mọi truyện của một tác giả — hỗ trợ "truyện khác của tác giả này".

    So khớp theo `name_sort` nên gõ không dấu cũng ra.
    """
    rows = conn.execute(
        f"""
        SELECT DISTINCT l.manga_id
        FROM {_LINK} l
        JOIN {_TABLE} a ON a.id = l.author_id
        WHERE a.name = ? OR a.name_sort = ?
        """,
        (naming.normalize_person_name(name), naming.sort_key(name)),
    ).fetchall()
    return [int(row["manga_id"]) for row in rows]


def prune_orphans(conn: sqlite3.Connection) -> int:
    return _name_table.prune_orphans(conn, _TABLE, _LINK, "author_id")
