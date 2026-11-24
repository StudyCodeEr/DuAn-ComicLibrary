"""Truyện: ghi, đọc, tìm kiếm có phân trang."""

from __future__ import annotations

from mangalib.db import author_repo, manga_repo, tag_repo
from mangalib.db.models import Author, Manga


def test_upsert_is_idempotent_by_source_url(conn):
    """Tải lại cùng một link không được tạo bản ghi trùng."""
    manga = Manga(slug="a", title="Truyện A", source_url="https://example.com/a")
    first = manga_repo.upsert(conn, manga)
    second = manga_repo.upsert(conn, manga)
    assert first == second
    assert manga_repo.count(conn) == 1


def test_upsert_keeps_added_at_and_updates_title(conn):
    manga_id = manga_repo.upsert(
        conn, Manga(slug="a", title="Tên Cũ", source_url="https://example.com/a")
    )
    added_at = manga_repo.get_by_id(conn, manga_id).added_at

    manga_repo.upsert(
        conn, Manga(slug="a", title="Tên Mới", source_url="https://example.com/a")
    )
    updated = manga_repo.get_by_id(conn, manga_id)
    assert updated.title == "Tên Mới"
    assert updated.added_at == added_at


def test_upsert_does_not_wipe_cover_with_none(conn):
    """Lần quét sau không có bìa thì không được xoá bìa đã có."""
    manga_repo.upsert(conn, Manga(slug="a", title="A", cover_file="cover.jpg"))
    manga_repo.upsert(conn, Manga(slug="a", title="A", cover_file=None))
    assert manga_repo.get_by_slug(conn, "a").cover_file == "cover.jpg"


def test_title_sort_is_generated_without_diacritics(conn):
    manga_repo.upsert(conn, Manga(slug="a", title="Thiên Đường"))
    assert manga_repo.get_by_slug(conn, "a").title_sort == "thien duong"


def test_unique_slug_avoids_collision(conn):
    manga_repo.upsert(conn, Manga(slug="thien-duong", title="Thiên Đường"))
    assert manga_repo.unique_slug(conn, "Thiên Đường") == "thien-duong-2"


def test_get_by_slug_hydrates_authors_and_tags(conn):
    manga_id = manga_repo.upsert(conn, Manga(slug="a", title="A"))
    author_repo.set_for_manga(conn, manga_id, [Author(name="Người Vẽ", role="artist")])
    tag_repo.set_for_manga(conn, manga_id, ["Action", "Comedy"])

    manga = manga_repo.get_by_slug(conn, "a")
    assert [a.name for a in manga.authors] == ["Người Vẽ"]
    assert [t.name for t in manga.tags] == ["Action", "Comedy"]


def test_search_matches_title_without_diacritics(conn):
    manga_repo.upsert(conn, Manga(slug="a", title="Thiên Đường Không Hồi Kết"))
    items, total = manga_repo.search(conn, q="thien duong")
    assert total == 1
    assert items[0].title == "Thiên Đường Không Hồi Kết"


def test_search_matches_author_name(conn):
    """Ô tìm kiếm khớp cả tên tác giả, không chỉ tên truyện."""
    manga_id = manga_repo.upsert(conn, Manga(slug="a", title="Không Liên Quan"))
    author_repo.set_for_manga(conn, manga_id, [Author(name="Trần Đăng Khoa")])

    items, total = manga_repo.search(conn, q="tran dang")
    assert total == 1
    assert items[0].slug == "a"


def test_search_include_tags_requires_all(conn, make_manga):
    both = make_manga("Có Cả Hai")
    one = make_manga("Chỉ Một")
    tag_repo.set_for_manga(conn, both, ["Action", "Comedy"])
    tag_repo.set_for_manga(conn, one, ["Action"])

    items, total = manga_repo.search(conn, include_tags=["Action", "Comedy"])
    assert total == 1
    assert items[0].id == both


def test_search_exclude_tags(conn, make_manga):
    keep = make_manga("Giữ Lại")
    drop = make_manga("Loại Ra")
    tag_repo.set_for_manga(conn, keep, ["Action"])
    tag_repo.set_for_manga(conn, drop, ["Action", "Horror"])

    items, total = manga_repo.search(conn, include_tags=["Action"], exclude_tags=["Horror"])
    assert total == 1
    assert items[0].id == keep


def test_search_filter_by_author(conn, make_manga):
    mine = make_manga("Của Tôi")
    other = make_manga("Của Người Khác")
    author_repo.set_for_manga(conn, mine, [Author(name="Người A")])
    author_repo.set_for_manga(conn, other, [Author(name="Người B")])

    items, total = manga_repo.search(conn, author="Người A")
    assert total == 1
    assert items[0].id == mine


def test_search_pagination_reports_total_not_page_size(conn, make_manga):
    for index in range(25):
        make_manga(f"Truyện {index:02d}")

    page_one, total = manga_repo.search(conn, per_page=10, page=1)
    page_three, _ = manga_repo.search(conn, per_page=10, page=3)

    assert total == 25
    assert len(page_one) == 10
    assert len(page_three) == 5
    assert {m.id for m in page_one}.isdisjoint({m.id for m in page_three})


def test_search_sort_by_title(conn, make_manga):
    make_manga("Zebra")
    make_manga("Áo Dài")
    items, _ = manga_repo.search(conn, sort="title")
    assert [m.title for m in items] == ["Áo Dài", "Zebra"]


def test_search_sort_last_read_puts_unread_last(conn, make_manga):
    read = make_manga("Đã Đọc")
    make_manga("Chưa Đọc")
    manga_repo.touch_read(conn, read)

    items, _ = manga_repo.search(conn, sort="last_read")
    assert items[0].id == read


def test_counts_come_from_query_not_filesystem(conn, make_manga):
    manga_id = make_manga("A")
    conn.execute(
        "INSERT INTO chapter (manga_id, title, dir_name, page_count) VALUES (?, ?, ?, ?)",
        (manga_id, "Chương 1", "0001", 12),
    )
    conn.execute(
        "INSERT INTO chapter (manga_id, title, dir_name, page_count) VALUES (?, ?, ?, ?)",
        (manga_id, "Chương 2", "0002", 8),
    )
    manga = manga_repo.get_by_id(conn, manga_id)
    assert manga.chapter_count == 2
    assert manga.page_count == 20


def test_delete_returns_false_for_unknown_slug(conn):
    assert manga_repo.delete(conn, "khong-ton-tai") is False
