"""Trang ảnh: danh sách cho reader, và tầng resume mịn nhất."""

from __future__ import annotations

import pytest

from mangalib.db import chapter_repo, page_repo
from mangalib.db.models import Chapter, Page


@pytest.fixture
def chapter_id(conn, make_manga):
    manga_id = make_manga("Một Truyện")
    return chapter_repo.upsert(conn, manga_id, Chapter(title="Chương 1", dir_name="0001"))


def test_upsert_many_then_list_in_order(conn, chapter_id):
    page_repo.upsert_many(
        conn,
        chapter_id,
        [
            Page(idx=2, file_name="003.webp"),
            Page(idx=0, file_name="001.webp"),
            Page(idx=1, file_name="002.webp"),
        ],
    )
    assert [p.file_name for p in page_repo.list_for_chapter(conn, chapter_id)] == [
        "001.webp",
        "002.webp",
        "003.webp",
    ]


def test_upsert_many_updates_without_deleting_others(conn, chapter_id):
    page_repo.upsert_many(conn, chapter_id, [Page(idx=0, file_name="001.webp")])
    page_repo.upsert_many(conn, chapter_id, [Page(idx=1, file_name="002.webp")])

    assert page_repo.count_for_chapter(conn, chapter_id) == 2


def test_upsert_keeps_known_size_when_new_row_has_none(conn, chapter_id):
    """Lần ghi sau không biết kích thước thì không được xoá kích thước đã biết."""
    page_repo.upsert_many(
        conn, chapter_id, [Page(idx=0, file_name="001.webp", width=1400, height=1986)]
    )
    page_repo.upsert_many(conn, chapter_id, [Page(idx=0, file_name="001.avif")])

    page = page_repo.list_for_chapter(conn, chapter_id)[0]
    assert page.file_name == "001.avif"
    assert (page.width, page.height) == (1400, 1986)


def test_replace_for_chapter_drops_old_pages(conn, chapter_id):
    page_repo.upsert_many(
        conn,
        chapter_id,
        [Page(idx=0, file_name="001.webp"), Page(idx=1, file_name="002.webp")],
    )
    page_repo.replace_for_chapter(conn, chapter_id, [Page(idx=0, file_name="001.webp")])

    assert page_repo.count_for_chapter(conn, chapter_id) == 1


def test_saved_indexes_reports_what_is_missing(conn, chapter_id):
    page_repo.upsert_many(
        conn,
        chapter_id,
        [Page(idx=0, file_name="001.webp"), Page(idx=3, file_name="004.webp")],
    )
    saved = page_repo.saved_indexes(conn, chapter_id)
    assert saved == {0, 3}
    assert sorted(set(range(5)) - saved) == [1, 2, 4]


def test_pages_disappear_with_their_chapter(conn, chapter_id):
    page_repo.upsert_many(conn, chapter_id, [Page(idx=0, file_name="001.webp")])
    chapter_repo.delete(conn, chapter_id)
    assert page_repo.count_for_chapter(conn, chapter_id) == 0
