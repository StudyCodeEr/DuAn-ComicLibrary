"""Định dạng `metadata.json` — mỗi thư mục truyện tự mô tả được (quy tắc R6).

Nhờ file này, **mất DB không mất dữ liệu**: `mangalib scan` dựng lại toàn bộ thư
viện từ đĩa, kể cả tác giả và thể loại người dùng đã sửa tay (`origin='manual'`).
Đó cũng là lý do bản đại tu này không cần viết script migration cho DB cũ.

Trách nhiệm duy nhất của module: đọc/ghi một file JSON thành kiểu dữ liệu của
`db.models`. Việc đi tìm thư mục và đối chiếu với đĩa thuộc `scanner.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mangalib.db.models import Author, Chapter, Manga, Tag
from mangalib.errors import MetadataError

__all__ = ["FILE_NAME", "SCHEMA", "LibraryRecord", "read", "write"]

FILE_NAME = "metadata.json"
SCHEMA = 1


@dataclass(frozen=True, slots=True)
class LibraryRecord:
    """Những gì một thư mục truyện tự nói về nó."""

    manga: Manga
    chapters: tuple[Chapter, ...] = ()


def read(folder: Path) -> LibraryRecord | None:
    """Đọc `metadata.json` trong thư mục truyện. Trả None khi file không tồn tại.

    Raises:
        MetadataError: khi file có nhưng không đọc được hoặc thiếu trường bắt buộc.
    """
    path = folder / FILE_NAME
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise MetadataError(path, f"không đọc được JSON ({exc})") from exc

    if not isinstance(raw, dict):
        raise MetadataError(path, "nội dung không phải một object JSON")

    title = str(raw.get("title") or "").strip()
    if not title:
        raise MetadataError(path, "thiếu trường bắt buộc 'title'")

    slug = str(raw.get("slug") or folder.name).strip()

    manga = Manga(
        slug=slug,
        title=title,
        title_sort=str(raw.get("title_sort") or ""),
        source_key=raw.get("source_key"),
        source_url=raw.get("source_url"),
        cover_file=raw.get("cover_file"),
        description=raw.get("description"),
        authors=tuple(_read_authors(raw.get("authors"), path)),
        tags=tuple(_read_tags(raw.get("tags"), path)),
    )
    return LibraryRecord(manga=manga, chapters=tuple(_read_chapters(raw.get("chapters"), path)))


def _read_authors(value: object, path: Path) -> list[Author]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MetadataError(path, "'authors' phải là một danh sách")
    authors: list[Author] = []
    for item in value:
        if isinstance(item, str):
            authors.append(Author(name=item))
        elif isinstance(item, dict) and item.get("name"):
            authors.append(
                Author(
                    name=str(item["name"]),
                    role=item.get("role", "author"),
                    origin=item.get("origin", "scraped"),
                )
            )
    return authors


def _read_tags(value: object, path: Path) -> list[Tag]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MetadataError(path, "'tags' phải là một danh sách")
    tags: list[Tag] = []
    for item in value:
        if isinstance(item, str):
            tags.append(Tag(name=item))
        elif isinstance(item, dict) and item.get("name"):
            tags.append(Tag(name=str(item["name"]), origin=item.get("origin", "scraped")))
    return tags


def _read_chapters(value: object, path: Path) -> list[Chapter]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MetadataError(path, "'chapters' phải là một danh sách")
    chapters: list[Chapter] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        dir_name = str(item.get("dir_name") or "").strip()
        if not dir_name:
            continue
        chapters.append(
            Chapter(
                title=str(item.get("title") or dir_name),
                dir_name=dir_name,
                number=item.get("number"),
                source_url=item.get("source_url"),
                page_count=int(item.get("page_count") or 0),
                expected_page_count=item.get("expected_page_count"),
                status=item.get("status", "pending"),
            )
        )
    return chapters


def write(folder: Path, record: LibraryRecord) -> Path:
    """Ghi `metadata.json` theo kiểu nguyên tử (`.tmp` rồi `replace`).

    Ctrl+C giữa lúc ghi không để lại file JSON hỏng.
    """
    manga = record.manga
    payload = {
        "schema": SCHEMA,
        "slug": manga.slug,
        "title": manga.title,
        "title_sort": manga.title_sort,
        "source_key": manga.source_key,
        "source_url": manga.source_url,
        "cover_file": manga.cover_file,
        "description": manga.description,
        "authors": [
            {"name": a.name, "role": a.role, "origin": a.origin} for a in manga.authors
        ],
        "tags": [{"name": t.name, "origin": t.origin} for t in manga.tags],
        "chapters": [
            {
                "dir_name": c.dir_name,
                "title": c.title,
                "number": c.number,
                "source_url": c.source_url,
                "page_count": c.page_count,
                "expected_page_count": c.expected_page_count,
                "status": c.status,
            }
            for c in record.chapters
        ],
    }

    folder.mkdir(parents=True, exist_ok=True)
    path = folder / FILE_NAME
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temp.replace(path)
    return path
