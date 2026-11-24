"""Dựng lại DB từ những gì có thật trên đĩa.

Nguyên tắc: **đĩa là sự thật**. DB chỉ là chỉ mục để tìm nhanh, nên quét lại luôn
có thể tái tạo nó. Hệ quả (quy tắc R6): mất `library.db` không mất dữ liệu, và bản
đại tu này không cần script migration nào cho DB cũ.

Trách nhiệm duy nhất: đi qua cây thư mục, đối chiếu với `metadata.json`, rồi ghi
vào các repo. Định dạng file thuộc `metadata.py`; truy vấn SQL thuộc `db/`.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field, replace
from pathlib import Path

from mangalib import naming, paths
from mangalib.db import author_repo, chapter_repo, manga_repo, page_repo, tag_repo
from mangalib.db.models import Chapter, Manga, Page
from mangalib.errors import MetadataError
from mangalib.library import metadata

__all__ = ["IMAGE_SUFFIXES", "ScanReport", "scan"]

IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"})
"""Chỉ dùng để nhận ra ảnh ĐÃ nằm trên đĩa. Khi tải mới, Phase 3 kiểm bằng magic
byte chứ không tin phần mở rộng."""

_COVER_STEMS = ("cover", "thumb", "bia")
_NUMBER_CHUNK = re.compile(r"(\d+)")


@dataclass(slots=True)
class ScanReport:
    """Kết quả một lần quét. Luôn báo số thật, kể cả khi có lỗi giữa đường."""

    manga: int = 0
    chapters: int = 0
    pages: int = 0
    inferred: int = 0
    pruned: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _natural_key(name: str) -> tuple[tuple[int, int, str], ...]:
    """Sắp tên theo số, nên `Trang_2` đứng trước `Trang_10`.

    Mỗi phần được bọc thành `(loại, số, chữ)` để khoá **ổn định kiểu**: nếu trả
    thẳng `int` lẫn `str` thì so sánh `"0001 - Chương 1"` với `"Chương 1"` sẽ ném
    `TypeError: '<' not supported between 'str' and 'int'`.
    """
    parts: list[tuple[int, int, str]] = []
    for chunk in _NUMBER_CHUNK.split(name):
        if chunk == "":
            continue
        if chunk.isdigit():
            parts.append((0, int(chunk), ""))
        else:
            parts.append((1, 0, chunk.lower()))
    return tuple(parts)


def _page_files(chapter_dir: Path) -> list[Path]:
    files = [
        item
        for item in chapter_dir.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
    ]
    return sorted(files, key=lambda item: _natural_key(item.name))


def _find_cover(folder: Path) -> str | None:
    for item in sorted(folder.iterdir(), key=lambda p: p.name):
        if not item.is_file() or item.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if item.stem.lower() in _COVER_STEMS:
            return item.name
    return None


def _infer_record(folder: Path) -> metadata.LibraryRecord:
    """Thư mục không có `metadata.json`: đoán từ chính cây thư mục.

    Dùng khi nhập thư viện cũ, hoặc khi người dùng tự copy truyện vào.
    """
    title = folder.name
    chapters = [
        Chapter(
            title=child.name,
            dir_name=child.name,
            number=naming.parse_chapter_number(child.name),
        )
        for child in sorted(folder.iterdir(), key=lambda p: _natural_key(p.name))
        if child.is_dir()
    ]
    return metadata.LibraryRecord(
        manga=Manga(slug=folder.name, title=title, title_sort=naming.sort_key(title)),
        chapters=tuple(chapters),
    )


def _write_links(conn: sqlite3.Connection, manga_id: int, record: metadata.LibraryRecord) -> None:
    """Ghi tác giả và thể loại, **tách theo `origin`**.

    Nhờ tách, thứ người dùng sửa tay (`manual`) được dựng lại đúng là `manual`,
    nên lần tải sau scraper vẫn không ghi đè nó.
    """
    for origin in ("scraped", "manual"):
        authors = [a for a in record.manga.authors if a.origin == origin]
        tags = [t for t in record.manga.tags if t.origin == origin]
        if authors or origin == "scraped":
            author_repo.set_for_manga(conn, manga_id, authors, origin=origin)
        if tags or origin == "scraped":
            tag_repo.set_for_manga(conn, manga_id, tags, origin=origin)


def scan(
    conn: sqlite3.Connection, *, root: Path | None = None, prune: bool = False
) -> ScanReport:
    """Quét thư mục thư viện và đồng bộ DB theo đĩa."""
    library = Path(root) if root is not None else paths.library_dir()
    report = ScanReport()
    if not library.is_dir():
        return report

    seen_slugs: set[str] = set()

    for folder in sorted((p for p in library.iterdir() if p.is_dir()), key=lambda p: p.name):
        record: metadata.LibraryRecord | None = None
        try:
            record = metadata.read(folder)
        except MetadataError as exc:
            # Một thư mục hỏng không được làm dừng cả lần quét.
            report.errors.append(str(exc))

        if record is None:
            record = _infer_record(folder)
            report.inferred += 1

        manga = record.manga
        if manga.cover_file is None or not (folder / manga.cover_file).exists():
            # dataclass co slots=True nen KHONG co __dict__: phai dung replace()
            manga = replace(manga, cover_file=_find_cover(folder))

        manga_id = manga_repo.upsert(conn, manga)
        seen_slugs.add(manga.slug)
        report.manga += 1

        _write_links(conn, manga_id, record)

        known = {chapter.dir_name: chapter for chapter in record.chapters}
        on_disk: set[str] = set()

        for child in sorted(
            (p for p in folder.iterdir() if p.is_dir()), key=lambda p: _natural_key(p.name)
        ):
            files = _page_files(child)
            if not files:
                continue

            on_disk.add(child.name)
            declared = known.get(child.name)
            chapter = declared or Chapter(
                title=child.name,
                dir_name=child.name,
                number=naming.parse_chapter_number(child.name),
            )
            chapter_id = chapter_repo.upsert(conn, manga_id, chapter)

            pages = [
                Page(idx=index, file_name=item.name, byte_size=item.stat().st_size)
                for index, item in enumerate(files)
            ]
            page_repo.replace_for_chapter(conn, chapter_id, pages)

            # Giữ `expected` do metadata khai báo, nên chương thiếu ảnh vẫn là
            # `partial` chứ không bị đĩa "làm tròn" thành đủ.
            expected = declared.expected_page_count if declared else None
            chapter_repo.record_result(conn, chapter_id, saved=len(pages), expected=expected)

            report.chapters += 1
            report.pages += len(pages)

        # DB phải phản chiếu đĩa: chương không còn thư mục thì bỏ khỏi DB.
        for stale in chapter_repo.list_for_manga(conn, manga_id):
            if stale.dir_name not in on_disk and stale.id is not None:
                chapter_repo.delete(conn, stale.id)

    if prune:
        for row in conn.execute("SELECT slug FROM manga").fetchall():
            if row["slug"] not in seen_slugs and manga_repo.delete(conn, row["slug"]):
                report.pruned += 1

    return report
