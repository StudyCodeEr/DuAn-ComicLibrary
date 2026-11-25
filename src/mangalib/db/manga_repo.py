"""Truyện: ghi, đọc, tìm kiếm có phân trang.

Khác bản cũ (`core/database.py`) ở bốn điểm:

* lưu `slug` + tên file tương đối, không lưu đường dẫn tuyệt đối (quy tắc R5);
* `search()` có **phân trang** — bản cũ `load_library_advanced` vẽ cả thư viện
  một lần, không chịu được hàng nghìn truyện;
* ô tìm kiếm khớp **cả tên truyện lẫn tên tác giả**, qua `title_sort`/`name_sort`
  không dấu, nên gõ "the loai" ra "Thể loại";
* số chương và số trang được tính ngay trong truy vấn, nên thẻ truyện không phải
  `os.listdir` từng thư mục như reader cũ.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Literal

from mangalib import naming
from mangalib.db import author_repo, tag_repo
from mangalib.db.models import Manga

__all__ = [
    "count",
    "delete",
    "get_by_id",
    "get_by_slug",
    "search",
    "set_cover",
    "touch_read",
    "unique_slug",
    "upsert",
]

SortBy = Literal["added", "title", "last_read"]

_ORDER_BY: dict[str, str] = {
    "added": "m.added_at DESC, m.id DESC",
    "title": "m.title_sort COLLATE NOCASE ASC",
    # SQLite không có NULLS LAST: cột IS NULL đứng trước để đẩy truyện chưa đọc xuống.
    "last_read": "m.last_read_at IS NULL, m.last_read_at DESC",
}

# Chuong da xoa mem khong duoc tinh vao so chuong / so trang hien ra.
_COUNT_COLUMNS = """
    (SELECT COUNT(*) FROM chapter c
        WHERE c.manga_id = m.id AND c.deleted_at IS NULL) AS chapter_count,
    (SELECT COALESCE(SUM(c.page_count), 0) FROM chapter c
        WHERE c.manga_id = m.id AND c.deleted_at IS NULL) AS page_count
"""

_CON_SONG = " AND m.deleted_at IS NULL"


def unique_slug(conn: sqlite3.Connection, title: str) -> str:
    """Slug chưa bị chiếm. Hai truyện tên gần giống nhau vẫn có thư mục riêng."""
    base = naming.slugify(title)
    rows = conn.execute("SELECT slug FROM manga WHERE slug LIKE ?", (f"{base}%",)).fetchall()
    return naming.unique_name(base, {row["slug"] for row in rows})


def upsert(conn: sqlite3.Connection, manga: Manga) -> int:
    """Thêm hoặc cập nhật truyện. Khớp theo `source_url` trước, rồi `slug`.

    Nhờ vậy tải lại cùng một link không tạo bản ghi trùng — hành vi đúng mà bản
    cũ cũng có, nhưng ở đây `added_at` được giữ nguyên khi cập nhật.
    """
    existing = None
    if manga.source_url:
        existing = conn.execute(
            "SELECT id FROM manga WHERE source_url = ?", (manga.source_url,)
        ).fetchone()
    if existing is None:
        existing = conn.execute(
            "SELECT id FROM manga WHERE slug = ?", (manga.slug,)
        ).fetchone()

    title_sort = manga.title_sort or naming.sort_key(manga.title)

    if existing is not None:
        manga_id = int(existing["id"])
        conn.execute(
            """
            UPDATE manga
               SET slug = ?, title = ?, title_sort = ?, source_key = ?, source_url = ?,
                   cover_file = COALESCE(?, cover_file), description = COALESCE(?, description),
                   updated_at = datetime('now'), deleted_at = NULL
             WHERE id = ?
            """,
            (
                manga.slug,
                manga.title,
                title_sort,
                manga.source_key,
                manga.source_url,
                manga.cover_file,
                manga.description,
                manga_id,
            ),
        )
        return manga_id

    cursor = conn.execute(
        """
        INSERT INTO manga (slug, title, title_sort, source_key, source_url,
                           cover_file, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            manga.slug,
            manga.title,
            title_sort,
            manga.source_key,
            manga.source_url,
            manga.cover_file,
            manga.description,
        ),
    )
    return int(cursor.lastrowid)


def _hydrate(conn: sqlite3.Connection, row: sqlite3.Row) -> Manga:
    manga_id = int(row["id"])
    # Phải lấy khoá ra set: với sqlite3.Row, `"x" in row` duyệt GIÁ TRỊ chứ không
    # phải khoá, nên viết `in row` là một lỗi im lặng.
    columns = set(row.keys())
    return Manga(
        id=manga_id,
        slug=row["slug"],
        title=row["title"],
        title_sort=row["title_sort"],
        source_key=row["source_key"],
        source_url=row["source_url"],
        cover_file=row["cover_file"],
        description=row["description"],
        added_at=row["added_at"],
        updated_at=row["updated_at"],
        last_read_at=row["last_read_at"],
        authors=author_repo.list_for_manga(conn, manga_id),
        tags=tag_repo.list_for_manga(conn, manga_id),
        chapter_count=int(row["chapter_count"]) if "chapter_count" in columns else 0,
        page_count=int(row["page_count"]) if "page_count" in columns else 0,
    )


def get_by_slug(conn: sqlite3.Connection, slug: str) -> Manga | None:
    row = conn.execute(
        f"SELECT m.*, {_COUNT_COLUMNS} FROM manga m WHERE m.slug = ?{_CON_SONG}", (slug,)
    ).fetchone()
    return _hydrate(conn, row) if row else None


def get_by_id(conn: sqlite3.Connection, manga_id: int) -> Manga | None:
    row = conn.execute(
        f"SELECT m.*, {_COUNT_COLUMNS} FROM manga m WHERE m.id = ?{_CON_SONG}", (manga_id,)
    ).fetchone()
    return _hydrate(conn, row) if row else None


def _build_filters(
    q: str,
    include_tags: Sequence[str],
    exclude_tags: Sequence[str],
    author: str | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if q.strip():
        needle = f"%{naming.sort_key(q)}%"
        clauses.append(
            """(m.title_sort LIKE ?
                OR m.id IN (SELECT l.manga_id FROM manga_author l
                            JOIN author a ON a.id = l.author_id
                            WHERE a.name_sort LIKE ?))"""
        )
        params += [needle, needle]

    # Mỗi tag bắt buộc là một điều kiện AND riêng: truyện phải có ĐỦ các tag đó.
    for tag in include_tags:
        clauses.append(
            """m.id IN (SELECT mt.manga_id FROM manga_tag mt
                        JOIN tag t ON t.id = mt.tag_id WHERE t.name = ?)"""
        )
        params.append(tag)

    if exclude_tags:
        placeholders = ",".join("?" * len(exclude_tags))
        clauses.append(
            f"""m.id NOT IN (SELECT mt.manga_id FROM manga_tag mt
                             JOIN tag t ON t.id = mt.tag_id
                             WHERE t.name IN ({placeholders}))"""
        )
        params += list(exclude_tags)

    if author:
        clauses.append(
            """m.id IN (SELECT l.manga_id FROM manga_author l
                        JOIN author a ON a.id = l.author_id
                        WHERE a.name = ? OR a.name_sort = ?)"""
        )
        params += [naming.normalize_person_name(author), naming.sort_key(author)]

    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    return where, params


def search(
    conn: sqlite3.Connection,
    *,
    q: str = "",
    include_tags: Sequence[str] = (),
    exclude_tags: Sequence[str] = (),
    author: str | None = None,
    sort: SortBy = "added",
    page: int = 1,
    per_page: int = 40,
) -> tuple[list[Manga], int]:
    """Trả `(danh sách truyện của trang này, tổng số truyện khớp)`."""
    where, params = _build_filters(q, include_tags, exclude_tags, author)
    order = _ORDER_BY.get(sort, _ORDER_BY["added"])
    page = max(1, int(page))
    per_page = max(1, min(int(per_page), 200))

    total = int(
        conn.execute(
            f"SELECT COUNT(*) AS total FROM manga m WHERE 1=1{_CON_SONG}{where}", params
        ).fetchone()["total"]
    )

    rows = conn.execute(
        f"""
        SELECT m.*, {_COUNT_COLUMNS}
        FROM manga m
        WHERE 1=1{_CON_SONG}{where}
        ORDER BY {order}
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()

    return [_hydrate(conn, row) for row in rows], total


def set_cover(conn: sqlite3.Connection, slug: str, cover_file: str) -> bool:
    """Chỉ đổi ảnh bìa. Dùng upsert ở đây sẽ xoá mất source_key/source_url."""
    cursor = conn.execute(
        "UPDATE manga SET cover_file = ?, updated_at = datetime('now') WHERE slug = ?",
        (cover_file, slug),
    )
    return bool(cursor.rowcount)


def count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS total FROM manga WHERE deleted_at IS NULL").fetchone()["total"])


def touch_read(conn: sqlite3.Connection, manga_id: int) -> None:
    conn.execute(
        "UPDATE manga SET last_read_at = datetime('now') WHERE id = ?", (manga_id,)
    )


def delete(conn: sqlite3.Connection, slug: str) -> bool:
    """Xoá mềm: đánh dấu `deleted_at`, không xoá hàng nào.

    File ảnh và hàng trong DB đều còn nguyên, nên hoàn tác chỉ là xoá lại dấu.
    Muốn xoá thật thì dùng `purge()`.
    """
    cursor = conn.execute(
        "UPDATE manga SET deleted_at = datetime('now') WHERE slug = ? AND deleted_at IS NULL",
        (slug,),
    )
    return bool(cursor.rowcount)


def restore(conn: sqlite3.Connection, slug: str) -> bool:
    """Hoàn tác xoá mềm."""
    return bool(
        conn.execute(
            "UPDATE manga SET deleted_at = NULL WHERE slug = ?", (slug,)
        ).rowcount
    )


def purge(conn: sqlite3.Connection, slug: str) -> bool:
    """Xoá thật khỏi DB (chương, trang, liên kết rơi theo CASCADE).

    Không xoá file trên đĩa: việc đó thuộc tầng storage, không thuộc tầng DB.
    """
    cursor = conn.execute("DELETE FROM manga WHERE slug = ?", (slug,))
    deleted = bool(cursor.rowcount)
    if deleted:
        tag_repo.prune_orphans(conn)
        author_repo.prune_orphans(conn)
    return deleted
