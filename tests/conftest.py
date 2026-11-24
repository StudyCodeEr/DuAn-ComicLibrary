"""Fixture dùng chung cho test tầng DB.

Repo nhận `conn` làm tham số (quy tắc R3), nên test chạy trên DB thật trong
`tmp_path` mà không cần mock và không chạm vào dữ liệu của người dùng.
"""

from __future__ import annotations

import pytest

from mangalib.db import engine, manga_repo
from mangalib.db.models import Manga


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "library.db"
    engine.init_db(path)
    with engine.connect(path) as connection:
        yield connection


@pytest.fixture
def make_manga(conn):
    """Tạo nhanh một truyện, trả về id."""

    def _make(title: str, *, slug: str | None = None, url: str | None = None) -> int:
        return manga_repo.upsert(
            conn,
            Manga(
                slug=slug or manga_repo.unique_slug(conn, title),
                title=title,
                source_url=url,
            ),
        )

    return _make
