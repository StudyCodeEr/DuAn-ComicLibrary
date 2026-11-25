"""Thư viện, chi tiết truyện, trang ảnh, vị trí đọc."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mangalib import paths
from mangalib.api.deps import require_lan_token, resolve_page_file
from mangalib.db import (
    author_repo,
    chapter_repo,
    engine,
    manga_repo,
    page_repo,
    progress_repo,
    tag_repo,
)

router = APIRouter(dependencies=[Depends(require_lan_token)])

_IMAGE_CACHE = "public, max-age=31536000, immutable"


def _manga_json(manga, *, detail: bool = False) -> dict:
    data = {
        "id": manga.id,
        "slug": manga.slug,
        "title": manga.title,
        "cover": f"/api/v1/files/{manga.slug}/__cover__" if manga.cover_file else None,
        "authors": [{"name": a.name, "role": a.role} for a in manga.authors],
        "tags": [t.name for t in manga.tags],
        "chapter_count": manga.chapter_count,
        "page_count": manga.page_count,
        "added_at": manga.added_at,
        "last_read_at": manga.last_read_at,
    }
    if detail:
        data["source_url"] = manga.source_url
    return data


def _progress_json(conn, manga) -> dict | None:
    """Tiến độ đọc kèm tỉ lệ, để thẻ truyện vẽ được dải 2px dưới bìa."""
    found = progress_repo.get(conn, manga.id)
    if found is None:
        return None
    chapters = chapter_repo.list_for_manga(conn, manga.id)
    index = next((i for i, c in enumerate(chapters) if c.id == found.chapter_id), 0)
    pages = next((c.page_count for c in chapters if c.id == found.chapter_id), 0) or 1
    within = min(1.0, (found.page_idx + 1) / pages)
    ratio = (index + within) / max(1, len(chapters))
    return {
        "chapter_id": found.chapter_id,
        "page_idx": found.page_idx,
        "ratio": round(ratio, 4),
        "chapter_title": chapters[index].title if chapters else None,
    }


@router.get("/health")
def health() -> dict:
    with engine.read_only() as conn:
        total = manga_repo.count(conn)
    return {"app": "mangalib", "data_root": str(paths.data_root()), "manga_count": total}


@router.get("/library")
def library(
    q: str = "",
    include_tags: str = "",
    exclude_tags: str = "",
    author: str | None = None,
    sort: str = "added",
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=200),
) -> dict:
    split = lambda value: [t for t in (value or "").split(",") if t.strip()]  # noqa: E731
    with engine.read_only() as conn:
        items, total = manga_repo.search(
            conn,
            q=q,
            include_tags=split(include_tags),
            exclude_tags=split(exclude_tags),
            author=author,
            sort=sort if sort in ("added", "title", "last_read") else "added",
            page=page,
            per_page=per_page,
        )
        progress = {item.slug: _progress_json(conn, item) for item in items}
    return {
        "items": [{**_manga_json(m), "progress": progress.get(m.slug)} for m in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/tags")
def tags() -> list[dict]:
    with engine.read_only() as conn:
        return [{"name": name, "count": count} for name, count in tag_repo.list_all(conn)]


@router.get("/authors")
def authors() -> list[dict]:
    with engine.read_only() as conn:
        return [{"name": name, "count": count} for name, count in author_repo.list_all(conn)]


@router.get("/manga/{slug}")
def manga_detail(slug: str) -> dict:
    with engine.read_only() as conn:
        manga = manga_repo.get_by_slug(conn, slug)
        if manga is None:
            raise HTTPException(404, "Không tìm thấy truyện")
        chapters = chapter_repo.list_for_manga(conn, manga.id)
        progress_data = _progress_json(conn, manga)
    return {
        **_manga_json(manga, detail=True),
        "chapters": [
            {
                "id": c.id,
                "number": c.number,
                "title": c.title,
                "page_count": c.page_count,
                "expected_page_count": c.expected_page_count,
                "status": c.status,
            }
            for c in chapters
        ],
        "progress": progress_data,
    }


@router.get("/manga/{slug}/chapters/{chapter_id}/pages")
def chapter_pages(slug: str, chapter_id: int) -> dict:
    with engine.read_only() as conn:
        manga = manga_repo.get_by_slug(conn, slug)
        chapter = chapter_repo.get(conn, chapter_id)
        if manga is None or chapter is None or chapter.manga_id != manga.id:
            raise HTTPException(404, "Không tìm thấy chương")
        pages = page_repo.list_for_chapter(conn, chapter_id)
    # URL do server sinh từ DB, không nhận đường dẫn từ client.
    return {
        "chapter": {"id": chapter.id, "title": chapter.title, "status": chapter.status},
        "pages": [
            {
                "idx": p.idx,
                "url": f"/api/v1/files/{slug}/{chapter.dir_name}/{p.file_name}",
                "width": p.width,
                "height": p.height,
            }
            for p in pages
        ],
    }


class ProgressIn(BaseModel):
    chapter_id: int
    page_idx: int = 0


@router.put("/progress/{slug}")
def save_progress(slug: str, payload: ProgressIn) -> dict:
    with engine.write() as conn:
        manga = manga_repo.get_by_slug(conn, slug)
        if manga is None:
            raise HTTPException(404, "Không tìm thấy truyện")
        saved = progress_repo.save(conn, manga.id, payload.chapter_id, payload.page_idx)
    return {"chapter_id": saved.chapter_id, "page_idx": saved.page_idx}


@router.get("/files/{slug}/__cover__")
def cover(slug: str) -> FileResponse:
    with engine.read_only() as conn:
        manga = manga_repo.get_by_slug(conn, slug)
    if manga is None or not manga.cover_file:
        raise HTTPException(404, "Không có ảnh bìa")
    target = paths.safe_join(paths.library_dir(), slug, manga.cover_file)
    if not target.is_file():
        raise HTTPException(404, "Ảnh bìa không còn trên đĩa")
    return FileResponse(target, headers={"Cache-Control": _IMAGE_CACHE})


@router.get("/files/{slug}/{chapter_dir}/{file_name}")
def page_file(slug: str, chapter_dir: str, file_name: str) -> FileResponse:
    target = resolve_page_file(slug, chapter_dir, file_name)
    return FileResponse(target, headers={"Cache-Control": _IMAGE_CACHE})


@router.get("/pair")
def pair(request: Request, token: str = "") -> dict:
    """Ghép đôi điện thoại: quét QR một lần, cookie được đặt, xong mãi mãi."""
    from fastapi.responses import JSONResponse

    from mangalib import config

    if token != config.load().lan_token or not token:
        raise HTTPException(401, "Token không đúng")
    response = JSONResponse({"ok": True})
    response.set_cookie("mlib_token", token, max_age=10 * 365 * 24 * 3600, samesite="lax")
    return response
