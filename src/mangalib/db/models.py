"""Kiểu dữ liệu của tầng DB — dataclass thuần, không phụ thuộc sqlite.

Repo trả về những kiểu này chứ không trả `sqlite3.Row`, nên tầng trên (API, CLI,
pipeline tải) không cần biết gì về SQL. Đây là lý do `repo` test được bằng
`:memory:` và tầng API test được mà không cần DB thật.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "Author",
    "AuthorRole",
    "Chapter",
    "ChapterStatus",
    "Job",
    "JobState",
    "Manga",
    "Origin",
    "Page",
    "Progress",
    "Tag",
]

ChapterStatus = Literal["pending", "partial", "complete", "failed"]
AuthorRole = Literal["author", "artist"]
Origin = Literal["scraped", "manual"]
JobState = Literal["queued", "running", "done", "failed", "cancelled", "needs_login"]


@dataclass(frozen=True, slots=True)
class Author:
    name: str
    role: AuthorRole = "author"
    origin: Origin = "scraped"
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Tag:
    name: str
    origin: Origin = "scraped"
    id: int | None = None
    count: int = 0


@dataclass(frozen=True, slots=True)
class Page:
    idx: int
    file_name: str
    source_url: str | None = None
    width: int | None = None
    height: int | None = None
    byte_size: int | None = None


@dataclass(frozen=True, slots=True)
class Chapter:
    title: str
    dir_name: str
    number: float | None = None
    source_url: str | None = None
    page_count: int = 0
    expected_page_count: int | None = None
    status: ChapterStatus = "pending"
    downloaded_at: str | None = None
    id: int | None = None
    manga_id: int | None = None

    @property
    def is_complete(self) -> bool:
        """Chương đủ ảnh. Đây là thứ quyết định có bỏ qua khi tải lại hay không."""
        if self.status != "complete":
            return False
        if self.expected_page_count is None:
            return self.page_count > 0
        return self.page_count >= self.expected_page_count


@dataclass(frozen=True, slots=True)
class Manga:
    slug: str
    title: str
    title_sort: str = ""
    source_key: str | None = None
    source_url: str | None = None
    cover_file: str | None = None
    description: str | None = None
    added_at: str | None = None
    updated_at: str | None = None
    last_read_at: str | None = None
    id: int | None = None
    authors: tuple[Author, ...] = field(default_factory=tuple)
    tags: tuple[Tag, ...] = field(default_factory=tuple)
    chapter_count: int = 0
    page_count: int = 0


@dataclass(frozen=True, slots=True)
class Progress:
    manga_id: int
    chapter_id: int
    page_idx: int = 0
    updated_at: str | None = None


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    url: str
    state: JobState = "queued"
    manga_id: int | None = None
    phase: str | None = None
    done: int = 0
    total: int = 0
    error: str | None = None
    created_at: str | None = None
    finished_at: str | None = None
