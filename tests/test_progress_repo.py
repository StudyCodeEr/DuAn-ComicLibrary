"""Vị trí đọc — tính năng đồng bộ PC ↔ điện thoại mà bản cũ không có."""

from __future__ import annotations

from mangalib.db import chapter_repo, manga_repo, progress_repo
from mangalib.db.models import Chapter


def test_get_returns_none_when_never_read(conn, make_manga):
    manga_id = make_manga("Chưa Đọc")
    assert progress_repo.get(conn, manga_id) is None


def test_save_then_get_roundtrip(conn, make_manga):
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="C1", dir_name="d1"))

    progress_repo.save(conn, manga_id, chapter_id, page_idx=12)

    progress = progress_repo.get(conn, manga_id)
    assert (progress.chapter_id, progress.page_idx) == (chapter_id, 12)


def test_save_keeps_one_row_per_manga(conn, make_manga):
    """Đọc tiếp nhiều lần không được sinh ra nhiều dòng."""
    manga_id = make_manga("A")
    first = chapter_repo.upsert(conn, manga_id, Chapter(title="C1", dir_name="d1"))
    second = chapter_repo.upsert(conn, manga_id, Chapter(title="C2", dir_name="d2"))

    progress_repo.save(conn, manga_id, first, page_idx=3)
    progress_repo.save(conn, manga_id, second, page_idx=7)

    rows = conn.execute("SELECT COUNT(*) AS n FROM progress").fetchone()["n"]
    assert rows == 1
    progress = progress_repo.get(conn, manga_id)
    assert (progress.chapter_id, progress.page_idx) == (second, 7)


def test_save_updates_last_read_at(conn, make_manga):
    """Vị trí đọc và `last_read_at` phải đi cùng nhau, nếu không dải "Đọc tiếp" xếp sai."""
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="C1", dir_name="d1"))
    assert manga_repo.get_by_id(conn, manga_id).last_read_at is None

    progress_repo.save(conn, manga_id, chapter_id, page_idx=1)

    assert manga_repo.get_by_id(conn, manga_id).last_read_at is not None


def test_negative_page_is_clamped(conn, make_manga):
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="C1", dir_name="d1"))
    progress = progress_repo.save(conn, manga_id, chapter_id, page_idx=-5)
    assert progress.page_idx == 0


def test_clear_marks_unread(conn, make_manga):
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="C1", dir_name="d1"))
    progress_repo.save(conn, manga_id, chapter_id, page_idx=4)

    assert progress_repo.clear(conn, manga_id) is True
    assert progress_repo.get(conn, manga_id) is None
    assert progress_repo.clear(conn, manga_id) is False


def test_progress_disappears_with_manga(conn, make_manga):
    manga_id = make_manga("A")
    chapter_id = chapter_repo.upsert(conn, manga_id, Chapter(title="C1", dir_name="d1"))
    progress_repo.save(conn, manga_id, chapter_id)

    slug = manga_repo.get_by_id(conn, manga_id).slug

    # Xoá mềm phải GIỮ vị trí đọc: hoàn tác xong là đọc tiếp đúng chỗ cũ.
    manga_repo.delete(conn, slug)
    assert conn.execute("SELECT COUNT(*) AS n FROM progress").fetchone()["n"] == 1

    # Xoá thật mới quét sạch theo CASCADE.
    manga_repo.purge(conn, slug)
    assert conn.execute("SELECT COUNT(*) AS n FROM progress").fetchone()["n"] == 0
