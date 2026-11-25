"""Hàng đợi tải, SSE, và nhận payload từ userscript."""

from __future__ import annotations

import json
import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mangalib import naming, paths
from mangalib.api.deps import require_lan_token, require_local
from mangalib.db import chapter_repo, engine, job_repo, manga_repo, page_repo
from mangalib.db.models import Chapter, Manga, Page
from mangalib.download import fetcher
from mangalib.jobs.events import BUS
from mangalib.jobs.queue import WORKER

router = APIRouter(dependencies=[Depends(require_lan_token)])
logger = logging.getLogger(__name__)

MAX_CAPTURE_IMAGES = 2_000


class JobIn(BaseModel):
    url: str


@router.post("/jobs", status_code=202)
def create_job(payload: JobIn) -> dict:
    if not payload.url.startswith(("http://", "https://")):
        raise HTTPException(400, "Link phải bắt đầu bằng http:// hoặc https://")
    job = WORKER.submit(payload.url)
    return {"job_id": job.id, "state": job.state}


@router.get("/jobs")
def list_jobs(active_only: bool = False, limit: int = 50) -> list[dict]:
    with engine.read_only() as conn:
        jobs = job_repo.list_jobs(conn, active_only=active_only, limit=limit)
    return [
        {
            "id": j.id,
            "url": j.url,
            "state": j.state,
            "phase": j.phase,
            "done": j.done,
            "total": j.total,
            "error": j.error,
            "created_at": j.created_at,
        }
        for j in jobs
    ]


@router.delete("/jobs/{job_id}")
def cancel_job(job_id: str) -> dict:
    return {"cancelled": WORKER.cancel(job_id)}


@router.get("/jobs/events")
def job_events() -> StreamingResponse:
    """SSE: log chảy một chiều từ pipeline ra UI, không luồng nào chạm UI."""

    def stream():
        with BUS.subscribe() as queue:
            yield 'data: {"phase":"connected","message":"đã kết nối"}\n\n'
            while True:
                event = BUS.drain(queue, timeout=20.0)
                payload = event if event is not None else {"phase": "ping"}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class CaptureIn(BaseModel):
    """Payload do userscript trên trình duyệt của người dùng gửi về."""

    source_url: str
    chapter_url: str
    title: str
    chapter_title: str = ""
    images: list[str] = Field(default_factory=list)
    cookies: dict[str, str] = Field(default_factory=dict)
    user_agent: str = ""


@router.post("/capture", dependencies=[Depends(require_local)])
def capture(payload: CaptureIn, request: Request) -> dict:
    """Nhận danh sách URL ảnh từ tab đang mở rồi tải về.

    Cookie chỉ sống trong RAM của request này, không bao giờ ghi xuống đĩa.
    """
    if not payload.images:
        raise HTTPException(400, "Không có ảnh nào trong payload")
    if len(payload.images) > MAX_CAPTURE_IMAGES:
        raise HTTPException(400, f"Quá nhiều ảnh (tối đa {MAX_CAPTURE_IMAGES})")

    page_host = urlsplit(payload.chapter_url).hostname or ""
    allowed_hosts = {page_host, *_cdn_hosts(payload.chapter_url)}
    accepted: list[str] = []
    for url in payload.images:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            continue
        host = parts.hostname or ""
        if host == page_host or any(host.endswith(a) for a in allowed_hosts if a):
            accepted.append(url)
    if not accepted:
        raise HTTPException(400, "Mọi ảnh đều ở host không được phép")

    title = naming.strip_site_suffix(payload.title, ())
    with engine.write() as conn:
        existing = manga_repo.get_by_slug(conn, naming.slugify(title))
        slug = existing.slug if existing else manga_repo.unique_slug(conn, title)
        manga_id = manga_repo.upsert(
            conn, Manga(slug=slug, title=title, source_url=payload.source_url)
        )
        chapter_title = payload.chapter_title or payload.chapter_url.rstrip("/").rsplit("/", 1)[-1]
        number = naming.parse_chapter_number(chapter_title)
        dir_name = naming.chapter_dir_name(number, chapter_title)
        chapter_id = chapter_repo.upsert(
            conn,
            manga_id,
            Chapter(
                title=chapter_title,
                dir_name=dir_name,
                number=number,
                source_url=payload.chapter_url,
                expected_page_count=len(accepted),
            ),
        )

    outcome = fetcher.download_images(
        accepted,
        paths.chapter_dir(slug, dir_name),
        referer=payload.chapter_url,
        cookies=payload.cookies,
        user_agent=payload.user_agent,
    )

    with engine.write() as conn:
        page_repo.replace_for_chapter(
            conn,
            chapter_id,
            [Page(idx=i, file_name=name) for i, name in enumerate(outcome.files)],
        )
        status = chapter_repo.record_result(
            conn, chapter_id, saved=outcome.total, expected=len(accepted)
        )

    BUS.publish(
        {
            "phase": "capture",
            "message": f"{title}: {outcome.total}/{len(accepted)} trang ({status})",
        }
    )
    return {
        "slug": slug,
        "saved": outcome.saved,
        "skipped": outcome.skipped,
        "expected": len(accepted),
        "status": status,
        "errors": outcome.errors[:5],
    }


def _cdn_hosts(chapter_url: str) -> set[str]:
    from mangalib.meta import rule_for_url

    rule = rule_for_url(chapter_url)
    return set(rule.pages.cdn_allowlist) if rule else set()
