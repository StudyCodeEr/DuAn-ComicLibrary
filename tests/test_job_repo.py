"""Hàng đợi tải. Cột `error` là lý do bảng này tồn tại."""

from __future__ import annotations

from mangalib.db import job_repo


def test_create_starts_queued(conn):
    job = job_repo.create(conn, "https://example.com/truyen/a")
    assert job.state == "queued"
    assert job.done == 0
    assert job.error is None
    assert job_repo.get(conn, job.id) == job


def test_update_progress_only_changes_given_columns(conn):
    job = job_repo.create(conn, "https://example.com/a")
    job_repo.update_progress(conn, job.id, state="running", total=20)
    job_repo.update_progress(conn, job.id, done=7)

    updated = job_repo.get(conn, job.id)
    assert (updated.state, updated.done, updated.total) == ("running", 7, 20)


def test_finish_stores_the_error_message(conn):
    """Bản cũ có 17 chỗ `except: pass`, nên thất bại không để lại dấu vết nào."""
    job = job_repo.create(conn, "https://example.com/a")
    job_repo.finish(conn, job.id, "failed", error="Không tìm thấy chương nào")

    failed = job_repo.get(conn, job.id)
    assert failed.state == "failed"
    assert failed.error == "Không tìm thấy chương nào"
    assert failed.finished_at is not None


def test_finish_can_link_the_manga_it_produced(conn, make_manga):
    manga_id = make_manga("A")
    job = job_repo.create(conn, "https://example.com/a")
    job_repo.finish(conn, job.id, "done", manga_id=manga_id)
    assert job_repo.get(conn, job.id).manga_id == manga_id


def test_cancel_only_affects_unfinished_jobs(conn):
    active = job_repo.create(conn, "https://example.com/a")
    assert job_repo.cancel(conn, active.id) is True
    assert job_repo.get(conn, active.id).state == "cancelled"

    done = job_repo.create(conn, "https://example.com/b")
    job_repo.finish(conn, done.id, "done")
    assert job_repo.cancel(conn, done.id) is False
    assert job_repo.get(conn, done.id).state == "done"


def test_needs_login_is_cancellable(conn):
    """Job đang chờ người dùng vượt challenge vẫn phải huỷ được."""
    job = job_repo.create(conn, "https://example.com/a")
    job_repo.update_progress(conn, job.id, state="needs_login")
    assert job_repo.cancel(conn, job.id) is True


def test_list_active_only_hides_finished(conn):
    running = job_repo.create(conn, "https://example.com/a", job_id="job-a")
    waiting = job_repo.create(conn, "https://example.com/b", job_id="job-b")
    finished = job_repo.create(conn, "https://example.com/c", job_id="job-c")

    job_repo.update_progress(conn, running.id, state="running")
    job_repo.finish(conn, finished.id, "done")

    active_ids = {job.id for job in job_repo.list_jobs(conn, active_only=True)}
    assert active_ids == {running.id, waiting.id}


def test_list_by_state(conn):
    first = job_repo.create(conn, "https://example.com/a", job_id="job-a")
    second = job_repo.create(conn, "https://example.com/b", job_id="job-b")
    job_repo.finish(conn, first.id, "failed", error="lỗi mạng")

    failed = job_repo.list_jobs(conn, state="failed")
    assert [job.id for job in failed] == [first.id]
    assert second.id not in {job.id for job in failed}


def test_list_respects_limit(conn):
    for index in range(5):
        job_repo.create(conn, f"https://example.com/{index}", job_id=f"job-{index}")
    assert len(job_repo.list_jobs(conn, limit=3)) == 3
