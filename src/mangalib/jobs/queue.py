"""Hàng đợi tải: đúng MỘT worker, nên chỉ một browser chạy tại một thời điểm (R10).

Mọi thất bại được ghi vào `job.error` nên UI đọc được — không có chỗ nào nuốt lỗi.
"""

from __future__ import annotations

import logging
import queue
import threading

from mangalib.db import engine, job_repo
from mangalib.db.models import Job
from mangalib.jobs.events import BUS, EventBus

__all__ = ["WORKER", "JobWorker"]

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, bus: EventBus = BUS) -> None:
        self._bus = bus
        self._inbox: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    # ----- vòng đời -------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="mangalib-jobs", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._inbox.put("")
        if self._thread:
            self._thread.join(timeout=timeout)

    # ----- API ------------------------------------------------------------
    def submit(self, url: str) -> Job:
        engine.init_db()
        with engine.write() as conn:
            job = job_repo.create(conn, url)
        self._inbox.put(job.id)
        self._publish(job.id, "queued", "đã vào hàng đợi")
        self.start()
        return job

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            self._cancelled.add(job_id)
        with engine.write() as conn:
            return job_repo.cancel(conn, job_id)

    # ----- bên trong ------------------------------------------------------
    def _publish(self, job_id: str, phase: str, message: str, **extra: object) -> None:
        self._bus.publish({"job_id": job_id, "phase": phase, "message": message, **extra})

    def _is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancelled

    def _run(self) -> None:
        from mangalib.download import pipeline

        while not self._stop.is_set():
            try:
                job_id = self._inbox.get(timeout=1.0)
            except queue.Empty:
                continue
            if not job_id:
                continue

            with engine.read_only() as conn:
                job = job_repo.get(conn, job_id)
            if job is None or self._is_cancelled(job_id):
                continue

            with engine.write() as conn:
                job_repo.update_progress(conn, job_id, state="running", phase="meta")
            self._publish(job_id, "running", f"bắt đầu tải {job.url}")

            try:
                report = pipeline.download_manga(
                    job.url,
                    # _id=job_id: buoc gia tri ngay, khong bat bien vong lap
                    on_progress=lambda phase, message, _id=job_id: self._publish(
                        _id, phase, message
                    ),
                )
            except Exception as exc:
                logger.exception("job %s thất bại", job_id)
                with engine.write() as conn:
                    job_repo.finish(conn, job_id, "failed", error=str(exc))
                self._publish(job_id, "failed", str(exc))
                continue

            state = "done" if report.ok else "failed"
            error = "; ".join(report.errors[:5]) or None
            with engine.write() as conn:
                job_repo.update_progress(
                    conn, job_id, done=report.pages_saved, total=report.pages_expected
                )
                job_repo.finish(conn, job_id, state, error=error)
            self._publish(
                job_id,
                state,
                f"{report.pages_saved}/{report.pages_expected} trang · {report.chapters_done} chương",
                slug=report.slug,
            )


WORKER = JobWorker()
