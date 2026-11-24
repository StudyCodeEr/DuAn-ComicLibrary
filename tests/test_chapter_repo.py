"""Chương: trạng thái suy ra từ số liệu, và tầng resume theo chương."""

from __future__ import annotations

import pytest

from mangalib.db import chapter_repo
from mangalib.db.models import Chapter


@pytest.mark.parametrize(
    ("saved", "expected", "status"),
    [
        (0, None, "pending"),
        (0, 20, "failed"),
        (12, 20, "partial"),
        (20, 20, "complete"),
        (21, 20, "complete"),
        (5, None, "complete"),
    ],
)
def test_decide_status_from_counts(saved, expected, status):
    """Bug #4: bản cũ báo xong dựa vào việc vòng lặp đã chạy, không dựa vào số liệu."""
    assert chapter_repo.decide_status(saved, expected) == status


def test_upsert_is_idempotent_by_dir_name(conn, make_manga):
    manga_id = make_manga("A")
    chapter = Chapter(title="Chương 1", dir_name="0001 - Chuong 1", number=1)
    first = chapter_repo.upsert(conn, manga_id, chapter)
    second = chapter_repo.upsert(conn, manga_id, chapter)
    assert first == second
    assert chapter_repo.count_for_manga(conn, manga_id) == 1


def test_upsert_does_not_clobber_download_result(conn, make_manga):
    """Quét lại metadata không được xoá kết quả tải đã có."""
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(
        conn, manga_id, Chapter(title="Chương 1", dir_name="0001", number=1)
    )
    chapter_repo.record_result(conn, chapter_id, saved=20, expected=20)

    chapter_repo.upsert(
        conn, manga_id, Chapter(title="Chương 1 (sửa tên)", dir_name="0001", number=1)
    )

    chapter = chapter_repo.get(conn, chapter_id)
    assert chapter.title == "Chương 1 (sửa tên)"
    assert chapter.status == "complete"
    assert chapter.page_count == 20


def test_record_result_marks_partial_when_pages_missing(conn, make_manga):
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(
        conn, manga_id, Chapter(title="Chương 1", dir_name="0001")
    )
    status = chapter_repo.record_result(conn, chapter_id, saved=12, expected=20)

    assert status == "partial"
    chapter = chapter_repo.get(conn, chapter_id)
    assert chapter.page_count == 12
    assert chapter.expected_page_count == 20
    assert chapter.downloaded_at is not None
    assert chapter.is_complete is False


def test_list_for_manga_sorts_numerically_with_unnumbered_last(conn, make_manga):
    manga_id = make_manga("A")
    for number, dir_name in [
        (10, "0010"),
        (2, "0002"),
        (None, "Oneshot"),
        (1, "0001"),
        (9.5, "0009.5"),
    ]:
        chapter_repo.upsert(
            conn, manga_id, Chapter(title=dir_name, dir_name=dir_name, number=number)
        )

    order = [c.dir_name for c in chapter_repo.list_for_manga(conn, manga_id)]
    assert order == ["0001", "0002", "0009.5", "0010", "Oneshot"]


def test_complete_dir_names_only_returns_finished(conn, make_manga):
    manga_id = make_manga("A")
    done = chapter_repo.upsert(conn, manga_id, Chapter(title="xong", dir_name="d1"))
    half = chapter_repo.upsert(conn, manga_id, Chapter(title="thieu", dir_name="d2"))
    chapter_repo.upsert(conn, manga_id, Chapter(title="chua", dir_name="d3"))

    chapter_repo.record_result(conn, done, saved=20, expected=20)
    chapter_repo.record_result(conn, half, saved=5, expected=20)

    assert chapter_repo.complete_dir_names(conn, manga_id) == {"d1"}


def test_complete_but_short_is_not_treated_as_done(conn, make_manga):
    """Chốt an toàn: status='complete' mà thiếu ảnh thì vẫn phải tải lại."""
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="x", dir_name="d1"))
    conn.execute(
        """UPDATE chapter SET status = 'complete', page_count = 5,
                              expected_page_count = 20 WHERE id = ?""",
        (chapter_id,),
    )
    assert chapter_repo.complete_dir_names(conn, manga_id) == set()


def test_delete_chapter(conn, make_manga):
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="x", dir_name="d1"))
    assert chapter_repo.delete(conn, chapter_id) is True
    assert chapter_repo.get(conn, chapter_id) is None
