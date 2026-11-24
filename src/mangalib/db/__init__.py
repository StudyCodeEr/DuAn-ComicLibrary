"""Tầng dữ liệu của mangalib.

Mỗi file một trách nhiệm, thay cho `DatabaseManager` của bản cũ (một class gánh
cả mở kết nối, tạo bảng, lưu truyện, xử lý tag và tìm kiếm):

    engine.py        vòng đời kết nối, WAL, lock ghi, áp schema
    models.py        dataclass thuần mà tầng trên nhận được
    schema.sql       định nghĩa bảng (dữ liệu, không phải code)
    manga_repo.py    truyện: ghi, đọc, tìm kiếm có phân trang
    chapter_repo.py  chương: trạng thái suy ra từ số liệu, resume theo chương
    page_repo.py     trang ảnh: danh sách cho reader, resume theo trang
    author_repo.py   tác giả và họa sĩ
    tag_repo.py      thể loại
    progress_repo.py vị trí đọc (đồng bộ PC ↔ điện thoại)
    job_repo.py      hàng đợi tải, kèm lỗi
    _name_table.py   phần dùng chung của hai bảng tên (riêng tư)

Không file nào vượt 265 dòng, thay cho một class `DatabaseManager` gánh tất cả.
"""

from __future__ import annotations

from mangalib.db import (
    author_repo,
    chapter_repo,
    engine,
    job_repo,
    manga_repo,
    page_repo,
    progress_repo,
    tag_repo,
)
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
    "chapter_repo",
    "engine",
    "job_repo",
    "manga_repo",
    "page_repo",
    "progress_repo",
    "tag_repo",
]
