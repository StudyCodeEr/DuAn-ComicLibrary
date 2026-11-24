"""Tầng dữ liệu của mangalib.

Mỗi file một trách nhiệm, thay cho `DatabaseManager` của bản cũ (một class gánh
cả mở kết nối, tạo bảng, lưu truyện, xử lý tag và tìm kiếm):

    engine.py   vòng đời kết nối, WAL, lock ghi, áp schema
    models.py   dataclass thuần mà tầng trên nhận được
    schema.sql  định nghĩa bảng (dữ liệu, không phải code)

Các repo (một file cho mỗi nhóm bảng) được thêm ngay sau đây trong Phase 2.
"""

from __future__ import annotations

from mangalib.db import engine
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
    "engine",
]
