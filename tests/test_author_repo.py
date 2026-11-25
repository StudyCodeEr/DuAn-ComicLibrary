"""Tác giả — khái niệm bản cũ không có."""

from __future__ import annotations

import pytest

from mangalib.db import author_repo, manga_repo
from mangalib.db.models import Author


def test_upsert_is_idempotent(conn):
    first = author_repo.upsert(conn, "Asahina Yoshitosi")
    second = author_repo.upsert(conn, "Asahina Yoshitosi")
    assert first == second


def test_case_insensitive_no_duplicate(conn):
    """`COLLATE NOCASE`: "asahina" và "Asahina" là một người."""
    assert author_repo.upsert(conn, "Asahina") == author_repo.upsert(conn, "asahina")
    assert len(author_repo.list_all(conn)) == 1


def test_strips_label_prefix_before_saving(conn):
    author_repo.upsert(conn, "Tác giả: Asahina Yoshitosi")
    names = [name for name, _ in author_repo.list_all(conn)]
    assert names == ["Asahina Yoshitosi"]


@pytest.mark.parametrize("value", ["Đang cập nhật", "N/A", "-", "", "   "])
def test_rejects_placeholder(conn, value):
    """Placeholder không được âm thầm trở thành một tác giả trong thư viện."""
    with pytest.raises(ValueError, match="không phải tên tác giả"):
        author_repo.upsert(conn, value)


def test_roles_are_separate_links(conn, make_manga):
    manga_id = make_manga("Một Truyện")
    author_repo.set_for_manga(
        conn,
        manga_id,
        [Author(name="Người A", role="author"), Author(name="Người B", role="artist")],
    )
    roles = {a.name: a.role for a in author_repo.list_for_manga(conn, manga_id)}
    assert roles == {"Người A": "author", "Người B": "artist"}


def test_manual_author_survives_redownload(conn, make_manga):
    """Điểm thiết kế chính: scraper chỉ được thay thứ nó tự tạo."""
    manga_id = make_manga("Một Truyện")
    author_repo.set_for_manga(conn, manga_id, [Author(name="Scraped Một")])
    author_repo.set_for_manga(
        conn, manga_id, [Author(name="Tôi Gắn Tay")], origin="manual"
    )

    # Tải lại: scraper ghi lại danh sách của nó, lần này ra tên khác.
    author_repo.set_for_manga(conn, manga_id, [Author(name="Scraped Hai")])

    names = {a.name for a in author_repo.list_for_manga(conn, manga_id)}
    assert names == {"Scraped Hai", "Tôi Gắn Tay"}


def test_set_for_manga_skips_placeholders(conn, make_manga):
    manga_id = make_manga("Một Truyện")
    written = author_repo.set_for_manga(
        conn,
        manga_id,
        [Author(name="Người Thật"), Author(name="Đang cập nhật"), Author(name="-")],
    )
    assert written == 1
    assert len(author_repo.list_for_manga(conn, manga_id)) == 1


def test_manga_ids_by_name_finds_all_their_manga(conn, make_manga):
    first = make_manga("Truyện Một")
    second = make_manga("Truyện Hai")
    third = make_manga("Truyện Ba")
    for manga_id in (first, second):
        author_repo.set_for_manga(conn, manga_id, [Author(name="Trần Đăng Khoa")])
    author_repo.set_for_manga(conn, third, [Author(name="Người Khác")])

    found = author_repo.manga_ids_by_name(conn, "Trần Đăng Khoa")
    assert sorted(found) == sorted([first, second])


def test_manga_ids_by_name_works_without_diacritics(conn, make_manga):
    manga_id = make_manga("Truyện Một")
    author_repo.set_for_manga(conn, manga_id, [Author(name="Trần Đăng Khoa")])
    assert author_repo.manga_ids_by_name(conn, "tran dang khoa") == [manga_id]


def test_list_all_counts_manga_per_author(conn, make_manga):
    for title in ("A", "B"):
        author_repo.set_for_manga(conn, make_manga(title), [Author(name="Chung")])
    author_repo.set_for_manga(conn, make_manga("C"), [Author(name="Rieng")])

    assert author_repo.list_all(conn) == [("Chung", 2), ("Rieng", 1)]


def test_xoa_mem_khong_tinh_tac_gia_nhung_xoa_that_moi_don_han(conn, make_manga):
    manga_id = make_manga("Một Truyện")
    author_repo.set_for_manga(conn, manga_id, [Author(name="Chỉ Một Truyện")])
    slug = manga_repo.get_by_id(conn, manga_id).slug

    assert manga_repo.delete(conn, slug) is True
    assert author_repo.list_all(conn) == [("Chỉ Một Truyện", 0)], "hàng còn, số đếm về 0"

    assert manga_repo.purge(conn, slug) is True
    assert author_repo.list_all(conn) == []
