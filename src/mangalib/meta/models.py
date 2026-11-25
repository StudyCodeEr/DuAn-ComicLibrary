"""Kiểu dữ liệu scraper trả về. Không phụ thuộc HTTP hay DB."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ChapterRef", "MangaMeta"]


@dataclass(frozen=True, slots=True)
class ChapterRef:
    title: str
    url: str
    number: float | None = None


@dataclass(frozen=True, slots=True)
class MangaMeta:
    """Metadata của một truyện. `authors` là `(tên, vai trò)`."""

    title: str
    url: str
    authors: tuple[tuple[str, str], ...] = ()
    tags: tuple[str, ...] = ()
    cover_url: str | None = None
    chapters: tuple[ChapterRef, ...] = ()
    source_key: str | None = None

    def describe(self) -> list[str]:
        """Dòng mô tả cho `probe` / `--dry-run`. Thiếu thì nói rõ là thiếu."""
        missing = "(không tìm thấy)"
        authors = ", ".join(f"{n} [{r}]" for n, r in self.authors) or missing
        return [
            f"Tên truyện : {self.title or missing}",
            f"Tác giả    : {authors}",
            f"Thể loại   : {', '.join(self.tags) or missing}",
            f"Ảnh bìa    : {'có' if self.cover_url else missing}",
            f"Số chương  : {len(self.chapters) or missing}",
        ]
