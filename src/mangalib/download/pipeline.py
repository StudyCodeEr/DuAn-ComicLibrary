"""Điều phối một lần tải: metadata (HTTP) → URL ảnh (browser) → tải (HTTP) → DB.

Module DUY NHẤT biết cả tầng nguồn và tầng DB (quy tắc R8). Báo `saved/expected`
nên chương thiếu ảnh được gắn `partial` và lần sau tự vá — không bao giờ báo xong
khi chưa xong.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mangalib import config, naming, paths
from mangalib.db import (
    author_repo,
    chapter_repo,
    engine,
    manga_repo,
    page_repo,
    source_repo,
    tag_repo,
)
from mangalib.db.models import Author, Chapter, Manga, Page
from mangalib.download import fetcher
from mangalib.download.images import make_thumbnail, sniff_ext
from mangalib.library import metadata
from mangalib.meta import GenericSource, HttpClient, MangaMeta, discover, rule_for_url

__all__ = ["DownloadReport", "download_manga"]

logger = logging.getLogger(__name__)

Progress = Callable[[str, str], None]


@dataclass(slots=True)
class DownloadReport:
    url: str
    title: str = ""
    slug: str = ""
    chapters_done: int = 0
    chapters_skipped: int = 0
    pages_saved: int = 0
    pages_expected: int = 0
    errors: list[str] = field(default_factory=list)
    meta: MangaMeta | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and self.pages_saved >= self.pages_expected


def _emit(on_progress: Progress | None, phase: str, message: str) -> None:
    logger.info("[%s] %s", phase, message)
    if on_progress is not None:
        on_progress(phase, message)


def fetch_metadata(url: str) -> tuple[MangaMeta, object]:
    # Khong con tu choi link la. File .yml gio chi de TANG TOC va SUA SAI cho
    # nhung site da biet; chua co file nao thi suy ra tu chinh trang web.
    rule = rule_for_url(url) or discover.default_rule(url)
    with HttpClient(min_delay_ms=rule.request.min_delay_ms) as http:
        return GenericSource(rule).fetch_manga(http, url), rule


def _save_cover(meta: MangaMeta, folder: Path, rule) -> str | None:
    if not meta.cover_url:
        return None
    outcome = fetcher.download_images(
        [meta.cover_url], folder, referer=meta.url, min_bytes=1_000, concurrency=1
    )
    if not outcome.files:
        return None
    raw = folder / outcome.files[0]
    ext = sniff_ext(raw.read_bytes()[:16]) or "jpg"
    cover = folder / f"cover.{ext}"
    raw.replace(cover)
    make_thumbnail(cover, paths.thumbs_dir() / f"{folder.name}.webp")
    return cover.name


def download_manga(
    url: str,
    *,
    dry_run: bool = False,
    headless: bool = True,
    limit: int | None = None,
    on_progress: Progress | None = None,
) -> DownloadReport:
    report = DownloadReport(url=url)

    _emit(on_progress, "meta", "đang lấy metadata bằng HTTP (không mở browser)")
    meta, rule = fetch_metadata(url)
    report.meta = meta
    report.title = meta.title

    if dry_run:
        _emit(on_progress, "meta", "dry-run: không ghi gì")
        return report

    engine.init_db()
    with engine.write() as conn:
        # manga.source_key tham chieu bang source, nen dong nguon phai co truoc.
        source_repo.ensure(
            conn,
            rule.key,
            name=rule.name or rule.key,
            base_url=f"https://{rule.domains[0]}" if rule.domains else "",
            rule_file=rule.source_path,
        )
        slug = manga_repo.get_by_slug(conn, naming.slugify(meta.title))
        slug_value = slug.slug if slug else manga_repo.unique_slug(conn, meta.title)
        manga_id = manga_repo.upsert(
            conn,
            Manga(
                slug=slug_value,
                title=meta.title,
                source_key=meta.source_key,
                source_url=meta.url,
            ),
        )
        tag_repo.set_for_manga(conn, manga_id, list(meta.tags))
        author_repo.set_for_manga(
            conn, manga_id, [Author(name=n, role=r) for n, r in meta.authors]
        )
    report.slug = slug_value

    folder = paths.manga_dir(slug_value)
    folder.mkdir(parents=True, exist_ok=True)
    cover_file = _save_cover(meta, folder, rule)
    if cover_file:
        with engine.write() as conn:
            manga_repo.set_cover(conn, slug_value, cover_file)

    with engine.read_only() as conn:
        done_dirs = chapter_repo.complete_dir_names(conn, manga_id)

    todo = []
    for ref in meta.chapters:
        dir_name = naming.chapter_dir_name(ref.number, ref.title)
        if dir_name in done_dirs:
            report.chapters_skipped += 1
            continue
        todo.append((ref, dir_name))
    if limit:
        todo = todo[:limit]

    # Noi du ba con so TRUOC khi tai: co san trong thu vien bao nhieu, link co bao
    # nhieu, thieu bao nhieu. Nguoi dung can doi chieu de biet co dang tai trung.
    da_co = "đã có trong thư viện" if slug else "chưa có trong thư viện"
    if todo:
        _emit(
            on_progress,
            "chapters",
            f"Truyện {da_co}. Link có {len(meta.chapters)} chương, "
            f"{report.chapters_skipped} chương đã đủ ảnh, cần tải {len(todo)} chương.",
        )
    else:
        _emit(
            on_progress,
            "chapters",
            f"Truyện {da_co} và không thiếu chương nào "
            f"({report.chapters_skipped}/{len(meta.chapters)} đã đủ ảnh) — bỏ qua, "
            f"không mở trình duyệt.",
        )

    if todo:
        from mangalib.pagegrab import BrowserSession

        with BrowserSession(headless=headless) as browser:
            for position, (ref, dir_name) in enumerate(todo, start=1):
                label = f"[{position}/{len(todo)}] {ref.title[:40]}"
                try:
                    grab = browser.grab_chapter(ref.url, rule)
                except Exception as exc:  # noqa: BLE001 - một chương lỗi không dừng cả truyện
                    report.errors.append(f"{ref.title}: {exc}")
                    _emit(on_progress, "error", f"{label}: {exc}")
                    continue

                # expected lay tu so reader khai bao, khong tu so ta lay duoc:
                # neu khong, cuon thieu se cho saved == expected va bi danh 'complete' sai.
                expected = max(grab.declared_total, len(grab.image_urls))
                chapter_dir = folder / dir_name
                outcome = fetcher.download_images(
                    grab.image_urls,
                    chapter_dir,
                    referer=ref.url,
                    cookies=grab.cookies,
                    user_agent=grab.user_agent,
                    concurrency=rule.request.concurrency,
                    min_bytes=rule.filters.min_bytes,
                    image_format=config.load().image_format,
                )

                with engine.write() as conn:
                    chapter_id = chapter_repo.upsert(
                        conn,
                        manga_id,
                        Chapter(
                            title=ref.title,
                            dir_name=dir_name,
                            number=ref.number,
                            source_url=ref.url,
                            expected_page_count=expected,
                        ),
                    )
                    page_repo.replace_for_chapter(
                        conn,
                        chapter_id,
                        [
                            Page(idx=index, file_name=name)
                            for index, name in enumerate(outcome.files)
                        ],
                    )
                    status = chapter_repo.record_result(
                        conn, chapter_id, saved=outcome.total, expected=expected
                    )

                report.chapters_done += 1
                report.pages_saved += outcome.total
                report.pages_expected += expected
                report.errors.extend(f"{ref.title}: {e}" for e in outcome.errors)
                _emit(
                    on_progress,
                    "pages",
                    f"{label}: {outcome.total}/{expected} trang ({status})",
                )

    with engine.read_only() as conn:
        manga = manga_repo.get_by_id(conn, manga_id)
        chapters = chapter_repo.list_for_manga(conn, manga_id)
    metadata.write(folder, metadata.LibraryRecord(manga=manga, chapters=tuple(chapters)))
    _emit(on_progress, "done", f"xong: {report.pages_saved}/{report.pages_expected} trang")
    return report
