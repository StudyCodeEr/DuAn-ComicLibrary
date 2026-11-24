"""Tầng dữ liệu của mangalib.

Mỗi file một trách nhiệm, thay cho `DatabaseManager` của bản cũ (một class gánh
cả mở kết nối, tạo bảng, lưu truyện, xử lý tag và tìm kiếm):

    engine.py        vòng đời kết nối, WAL, lock ghi, áp schema
    models.py        dataclass thuần mà tầng trên nhận được
    schema.sql       định nghĩa bảng (dữ liệu, không phải code)
    manga_repo.py    truyện: ghi, đọc, tìm kiếm có phân trang
    author_repo.py   tác giả và họa sĩ
    tag_repo.py      thể loại
    _name_table.py   phần dùng chung của hai bảng tên ở trên (riêng tư)

Còn thiếu trong Phase 2: chapter_repo, page_repo, progress_repo, job_repo.
"""

from __future__ import annotations

from mangalib.db import author_repo, engine, manga_repo, tag_repo
from mangalib.db.models import (
    Author,
    Chapter,
    Job,
    Manga,
    Page,
    Progress,
    Tag,
)

__all__ = [
    "Author",
    "Chapter",
    "Job",
    "Manga",
    "Page",
    "Progress",
    "Tag",
    "author_repo",
    "engine",
    "manga_repo",
    "tag_repo",
]
