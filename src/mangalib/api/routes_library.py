"""Thư viện, chi tiết truyện, trang ảnh, vị trí đọc."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mangalib import paths
from mangalib.api.deps import require_lan_token, require_local, resolve_page_file
from mangalib.db import (
    author_repo,
    chapter_repo,
    engine,
    manga_repo,
    page_repo,
    progress_repo,
    tag_repo,
)
from mangalib.db.models import Author

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
        # Vi tri doc duoc tinh ra day: the truyen phai noi duoc DUOC BAO XA, khong
        # phai ten chuong - ten do con la rac lay tu site (xem PRODUCT.md).
        "page_pos": found.page_idx + 1,
        "chapter_pages": pages,
        "chapter_index": index + 1,
        "chapter_total": max(1, len(chapters)),
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


class MangaEdit(BaseModel):
    """Sửa tay khi máy nhận diện sai. Trường nào bỏ trống thì giữ nguyên."""

    title: str | None = None
    authors: list[str] | None = None
    tags: list[str] | None = None

    model_config = {"extra": "forbid"}


class ChapterOrder(BaseModel):
    ids: list[int]

    model_config = {"extra": "forbid"}


def _manga_id_or_404(conn, slug: str) -> int:
    manga = manga_repo.get_by_slug(conn, slug)
    if manga is None:
        raise HTTPException(404, "Không tìm thấy truyện")
    return manga.id


# Moi lenh SUA/XOA chi cho localhost: dien thoai trong LAN doc duoc nhung khong
# duoc xoa thu vien. Token LAN chi la bearer tren HTTP tran, khong du de tin.
@router.patch("/manga/{slug}", dependencies=[Depends(require_local)])
def edit_manga(slug: str, payload: MangaEdit) -> dict:
    with engine.write() as conn:
        manga_id = _manga_id_or_404(conn, slug)
        if payload.title is not None:
            title = payload.title.strip()
            if not title:
                raise HTTPException(400, "Tên truyện không được để trống")
            manga_repo.set_title(conn, slug, title)
        # Sua tay la quyet dinh cuoi cung: xoa luon nhom 'scraped', neu khong thi
        # tac gia/the loai site gan sai van con nguyen ben canh ban sua.
        if payload.authors is not None:
            author_repo.set_for_manga(conn, manga_id, [], origin="scraped")
            author_repo.set_for_manga(
                conn,
                manga_id,
                [Author(name=n) for n in payload.authors if n.strip()],
                origin="manual",
            )
        if payload.tags is not None:
            tag_repo.set_for_manga(conn, manga_id, [], origin="scraped")
            tag_repo.set_for_manga(
                conn, manga_id, [x for x in payload.tags if x.strip()], origin="manual"
            )
    with engine.read_only() as conn:
        return _manga_json(manga_repo.get_by_slug(conn, slug), detail=True)


@router.delete("/manga/{slug}", dependencies=[Depends(require_local)])
def delete_manga(slug: str) -> dict:
    """Xoá mềm: truyện biến khỏi thư viện, file ảnh vẫn nằm nguyên trên đĩa."""
    with engine.write() as conn:
        if not manga_repo.delete(conn, slug):
            raise HTTPException(404, "Không tìm thấy truyện")
    return {"slug": slug, "deleted": True}


@router.delete("/manga/{slug}/chapters/{chapter_id}", dependencies=[Depends(require_local)])
def delete_chapter(slug: str, chapter_id: int) -> dict:
    with engine.write() as conn:
        manga_id = _manga_id_or_404(conn, slug)
        chapter = chapter_repo.get(conn, chapter_id)
        if chapter is None or chapter.manga_id != manga_id:
            raise HTTPException(404, "Không tìm thấy chương trong truyện này")
        chapter_repo.delete(conn, chapter_id)
    return {"chapter_id": chapter_id, "deleted": True}


@router.put("/manga/{slug}/chapter-order", dependencies=[Depends(require_local)])
def set_chapter_order(slug: str, payload: ChapterOrder) -> dict:
    """Ghi thứ tự chương. Kéo thả, nút lên/xuống và nút A-Z đều gọi vào đây."""
    with engine.write() as conn:
        manga_id = _manga_id_or_404(conn, slug)
        hop_le = {c.id for c in chapter_repo.list_for_manga(conn, manga_id)}
        if set(payload.ids) != hop_le:
            raise HTTPException(400, "Danh sách phải gồm đúng các chương của truyện này")
        chapter_repo.set_order(conn, manga_id, payload.ids)
    return {"ordered": len(payload.ids)}


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
