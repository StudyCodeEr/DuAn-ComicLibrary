"""Định dạng `metadata.json` — nền của lời hứa "mất DB không mất dữ liệu"."""

from __future__ import annotations

import json

import pytest

from mangalib.db.models import Author, Chapter, Manga, Tag
from mangalib.errors import MetadataError
from mangalib.library import metadata


def _record() -> metadata.LibraryRecord:
    return metadata.LibraryRecord(
        manga=Manga(
            slug="thien-duong",
            title="Thiên Đường Không Hồi Kết",
            title_sort="thien duong khong hoi ket",
            source_url="https://example.com/truyen/thien-duong",
            cover_file="cover.jpg",
            authors=(
                Author(name="Người Vẽ", role="artist", origin="scraped"),
                Author(name="Tôi Gắn Tay", role="author", origin="manual"),
            ),
            tags=(Tag(name="Action"), Tag(name="Tự Gắn", origin="manual")),
        ),
        chapters=(
            Chapter(
                title="Chương 1",
                dir_name="0001 - Chương 1",
                number=1.0,
                page_count=20,
                expected_page_count=20,
                status="complete",
            ),
        ),
    )


def test_write_then_read_roundtrip(tmp_path):
    folder = tmp_path / "thien-duong"
    metadata.write(folder, _record())

    loaded = metadata.read(folder)
    assert loaded is not None
    assert loaded.manga.title == "Thiên Đường Không Hồi Kết"
    assert loaded.manga.cover_file == "cover.jpg"
    assert loaded.chapters[0].expected_page_count == 20
    assert loaded.chapters[0].status == "complete"


def test_roundtrip_preserves_origin_and_role(tmp_path):
    """Đây là điều kiện để `scan` dựng lại đúng thứ người dùng sửa tay."""
    folder = tmp_path / "a"
    metadata.write(folder, _record())
    loaded = metadata.read(folder)

    authors = {a.name: (a.role, a.origin) for a in loaded.manga.authors}
    assert authors == {
        "Người Vẽ": ("artist", "scraped"),
        "Tôi Gắn Tay": ("author", "manual"),
    }
    tags = {t.name: t.origin for t in loaded.manga.tags}
    assert tags == {"Action": "scraped", "Tự Gắn": "manual"}


def test_write_leaves_no_temp_file(tmp_path):
    folder = tmp_path / "a"
    metadata.write(folder, _record())
    assert [p.name for p in folder.iterdir()] == [metadata.FILE_NAME]


def test_read_returns_none_when_absent(tmp_path):
    folder = tmp_path / "chua-co"
    folder.mkdir()
    assert metadata.read(folder) is None


def test_read_raises_on_broken_json(tmp_path):
    folder = tmp_path / "a"
    folder.mkdir()
    (folder / metadata.FILE_NAME).write_text("{ khong phai json", encoding="utf-8")

    with pytest.raises(MetadataError, match="không đọc được JSON"):
        metadata.read(folder)


def test_read_raises_when_title_missing(tmp_path):
    folder = tmp_path / "a"
    folder.mkdir()
    (folder / metadata.FILE_NAME).write_text('{"slug": "a"}', encoding="utf-8")

    with pytest.raises(MetadataError, match="title"):
        metadata.read(folder)


def test_read_accepts_plain_string_lists(tmp_path):
    """Người dùng tự sửa file bằng tay thì dạng gọn cũng phải chấp nhận được."""
    folder = tmp_path / "a"
    folder.mkdir()
    (folder / metadata.FILE_NAME).write_text(
        json.dumps({"title": "A", "authors": ["Người A"], "tags": ["Action"]}),
        encoding="utf-8",
    )
    loaded = metadata.read(folder)
    assert [a.name for a in loaded.manga.authors] == ["Người A"]
    assert [t.name for t in loaded.manga.tags] == ["Action"]


def test_read_ignores_unknown_fields(tmp_path):
    """Phiên bản sau thêm trường mới thì phiên bản này không được vỡ."""
    folder = tmp_path / "a"
    folder.mkdir()
    (folder / metadata.FILE_NAME).write_text(
        json.dumps({"title": "A", "truong_tuong_lai": 123, "schema": 99}),
        encoding="utf-8",
    )
    assert metadata.read(folder).manga.title == "A"


def test_read_raises_when_authors_not_a_list(tmp_path):
    folder = tmp_path / "a"
    folder.mkdir()
    (folder / metadata.FILE_NAME).write_text(
        json.dumps({"title": "A", "authors": "Người A"}), encoding="utf-8"
    )
    with pytest.raises(MetadataError, match="'authors'"):
        metadata.read(folder)


def test_slug_defaults_to_folder_name(tmp_path):
    folder = tmp_path / "ten-thu-muc"
    folder.mkdir()
    (folder / metadata.FILE_NAME).write_text('{"title": "A"}', encoding="utf-8")
    assert metadata.read(folder).manga.slug == "ten-thu-muc"
