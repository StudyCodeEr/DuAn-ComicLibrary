"""Thể loại — giữ phần bản cũ làm đúng, sửa phần ghi đè tag gắn tay."""

from __future__ import annotations

import pytest

from mangalib.db import manga_repo, tag_repo


def test_case_insensitive_no_duplicate(conn):
    assert tag_repo.upsert(conn, "Action") == tag_repo.upsert(conn, "action")
    assert len(tag_repo.list_all(conn)) == 1


def test_rejects_too_long_tag(conn):
    """Chuỗi dài hơn 50 ký tự là rác lọt vào, không phải thể loại."""
    with pytest.raises(ValueError, match="không phải tên thể loại"):
        tag_repo.upsert(conn, "x" * 51)


def test_set_for_manga_deduplicates(conn, make_manga):
    manga_id = make_manga("Một Truyện")
    written = tag_repo.set_for_manga(conn, manga_id, ["Action", "action", "  Action  "])
    assert written == 1
    assert [t.name for t in tag_repo.list_for_manga(conn, manga_id)] == ["Action"]


def test_manual_tags_survive_redownload(conn, make_manga):
    manga_id = make_manga("Một Truyện")
    tag_repo.set_for_manga(conn, manga_id, ["Action"])
    tag_repo.set_for_manga(conn, manga_id, ["Tôi Tự Gắn"], origin="manual")

    tag_repo.set_for_manga(conn, manga_id, ["Comedy"])  # tải lại

    names = {t.name for t in tag_repo.list_for_manga(conn, manga_id)}
    assert names == {"Comedy", "Tôi Tự Gắn"}


def test_list_all_counts_and_orders_by_popularity(conn, make_manga):
    for title in ("A", "B", "C"):
        tag_repo.set_for_manga(conn, make_manga(title), ["Phổ Biến"])
    tag_repo.set_for_manga(conn, make_manga("D"), ["Ít Dùng"])

    assert tag_repo.list_all(conn) == [("Phổ Biến", 3), ("Ít Dùng", 1)]


def test_manga_ids_by_name(conn, make_manga):
    first = make_manga("A")
    make_manga("B")
    tag_repo.set_for_manga(conn, first, ["Action"])
    assert tag_repo.manga_ids_by_name(conn, "Action") == [first]


def test_delete_manga_prunes_orphan_tags_but_keeps_shared(conn, make_manga):
    shared_a = make_manga("A")
    shared_b = make_manga("B")
    tag_repo.set_for_manga(conn, shared_a, ["Dùng Chung", "Chỉ Riêng A"])
    tag_repo.set_for_manga(conn, shared_b, ["Dùng Chung"])

    slug = manga_repo.get_by_id(conn, shared_a).slug
    manga_repo.delete(conn, slug)

    assert tag_repo.list_all(conn) == [("Dùng Chung", 1)]
