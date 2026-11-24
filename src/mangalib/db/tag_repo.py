"""Thể loại. Giữ hai thứ bản cũ làm đúng, sửa một thứ bản cũ làm sai.

Giữ lại: `name TEXT UNIQUE COLLATE NOCASE` nên "Action" và "action" là một tag,
và logic lọc AND/NOT IN của `search_advanced` (bản cũ viết đúng chỗ này).

Sửa: bản cũ ghi đè tag mỗi lần tải lại, nên tag người dùng gắn tay mất sạch.
Ở đây `origin` tách hai thế giới ra, giống `author_repo`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from mangalib import naming
from mangalib.db import _name_table
from mangalib.db.models import Origin, Tag

__all__ = [
    "list_all",
    "list_for_manga",
    "manga_ids_by_name",
    "prune_orphans",
    "set_for_manga",
    "upsert",
]

_TABLE = "tag"
_LINK = "manga_tag"

_MAX_TAG_LENGTH = 50
"""Bản cũ cũng giới hạn 50 ký tự (`main.py:178`): chuỗi dài hơn là rác lọt vào."""


def upsert(conn: sqlite3.Connection, name: str) -> int:
    clean = " ".join(str(name).split())
    if not clean or len(clean) > _MAX_TAG_LENGTH:
        raise ValueError(f"không phải tên thể loại hợp lệ: {name!r}")
    return _name_table.upsert_name(conn, _TABLE, clean)


def set_for_manga(
    conn: sqlite3.Connection,
    manga_id: int,
    tags: Iterable[str | Tag],
    *,
    origin: Origin = "scraped",
) -> int:
    """Đặt lại thể loại của truyện trong phạm vi một `origin`.

    Gọi với `origin='scraped'` không chạm tới tag người dùng gắn tay.
    """
    conn.execute(
        f"DELETE FROM {_LINK} WHERE manga_id = ? AND origin = ?",
        (manga_id, origin),
    )

    written = 0
    seen: set[str] = set()
    for item in tags:
        raw = item.name if isinstance(item, Tag) else item
        clean = " ".join(str(raw).split())
        if not clean or len(clean) > _MAX_TAG_LENGTH:
            continue
        key = naming.sort_key(clean)
        if key in seen:
            continue
        seen.add(key)

        tag_id = upsert(conn, clean)
        conn.execute(
            f"""
            INSERT INTO {_LINK} (manga_id, tag_id, origin) VALUES (?, ?, ?)
            ON CONFLICT(manga_id, tag_id) DO UPDATE SET origin = excluded.origin
            """,
            (manga_id, tag_id, origin),
        )
        written += 1
    return written


def list_for_manga(conn: sqlite3.Connection, manga_id: int) -> tuple[Tag, ...]:
    rows = conn.execute(
        f"""
        SELECT t.id, t.name, l.origin
        FROM {_LINK} l
        JOIN {_TABLE} t ON t.id = l.tag_id
        WHERE l.manga_id = ?
        ORDER BY t.name COLLATE NOCASE
        """,
        (manga_id,),
    ).fetchall()
    return tuple(Tag(id=row["id"], name=row["name"], origin=row["origin"]) for row in rows)


def list_all(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    return _name_table.count_by_name(conn, _TABLE, _LINK, "tag_id")


def manga_ids_by_name(conn: sqlite3.Connection, name: str) -> list[int]:
    rows = conn.execute(
        f"""
        SELECT DISTINCT l.manga_id
        FROM {_LINK} l JOIN {_TABLE} t ON t.id = l.tag_id
        WHERE t.name = ?
        """,
        (" ".join(str(name).split()),),
    ).fetchall()
    return [int(row["manga_id"]) for row in rows]


def prune_orphans(conn: sqlite3.Connection) -> int:
    return _name_table.prune_orphans(conn, _TABLE, _LINK, "tag_id")
