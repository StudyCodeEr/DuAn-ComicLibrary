"""Quét lại thư viện từ đĩa — chứng minh quy tắc R6: mất DB không mất dữ liệu."""

from __future__ import annotations

from mangalib.db import author_repo, chapter_repo, manga_repo, page_repo, tag_repo
from mangalib.db.models import Author, Chapter, Manga, Tag
from mangalib.library import metadata, scanner


def _page(folder, name: str, size: int = 2048) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(b"x" * size)


def _build_library(root, *, with_metadata: bool = True):
    """Dựng một thư viện giả trên đĩa giống hệt cách tầng tải sẽ ghi."""
    folder = root / "thien-duong"
    chapter_one = folder / "0001 - Chương 1"
    chapter_two = folder / "0002 - Chương 2"
    for index in range(1, 4):
        _page(chapter_one, f"{index:03d}.webp")
    for index in range(1, 3):
        _page(chapter_two, f"{index:03d}.webp")
    _page(folder, "cover.jpg")

    if with_metadata:
        metadata.write(
            folder,
            metadata.LibraryRecord(
                manga=Manga(
                    slug="thien-duong",
                    title="Thiên Đường Không Hồi Kết",
                    source_url="https://example.com/a",
                    cover_file="cover.jpg",
                    authors=(
                        Author(name="Người Vẽ", role="artist"),
                        Author(name="Tôi Gắn Tay", origin="manual"),
                    ),
                    tags=(Tag(name="Action"), Tag(name="Tự Gắn", origin="manual")),
                ),
                chapters=(
                    Chapter(title="Chương 1", dir_name="0001 - Chương 1", number=1.0),
                    Chapter(title="Chương 2", dir_name="0002 - Chương 2", number=2.0),
                ),
            ),
        )
    return folder


def test_scan_builds_library_from_disk(conn, tmp_path):
    _build_library(tmp_path)

    report = scanner.scan(conn, root=tmp_path)

    assert (report.manga, report.chapters, report.pages) == (1, 2, 5)
    assert report.ok
    manga = manga_repo.get_by_slug(conn, "thien-duong")
    assert manga.title == "Thiên Đường Không Hồi Kết"
    assert manga.cover_file == "cover.jpg"
    assert manga.chapter_count == 2
    assert manga.page_count == 5


def test_scan_restores_manual_links_as_manual(conn, tmp_path):
    """Lời hứa R6: dựng lại DB không mất thứ người dùng sửa tay."""
    _build_library(tmp_path)
    scanner.scan(conn, root=tmp_path)

    manga_id = manga_repo.get_by_slug(conn, "thien-duong").id
    authors = {a.name: a.origin for a in author_repo.list_for_manga(conn, manga_id)}
    tags = {t.name: t.origin for t in tag_repo.list_for_manga(conn, manga_id)}

    assert authors == {"Người Vẽ": "scraped", "Tôi Gắn Tay": "manual"}
    assert tags == {"Action": "scraped", "Tự Gắn": "manual"}

    # Và vì origin được giữ đúng, lần tải sau vẫn không ghi đè nó.
    author_repo.set_for_manga(conn, manga_id, [Author(name="Scraper Mới")])
    names = {a.name for a in author_repo.list_for_manga(conn, manga_id)}
    assert names == {"Scraper Mới", "Tôi Gắn Tay"}


def test_scan_infers_from_folder_tree_without_metadata(conn, tmp_path):
    """Nhập thư viện cũ, hoặc người dùng tự copy truyện vào."""
    _build_library(tmp_path, with_metadata=False)

    report = scanner.scan(conn, root=tmp_path)

    assert report.inferred == 1
    manga = manga_repo.get_by_slug(conn, "thien-duong")
    numbers = [c.number for c in chapter_repo.list_for_manga(conn, manga.id)]
    assert numbers == [1.0, 2.0]


def test_scan_sorts_pages_naturally(conn, tmp_path):
    """Tên kiểu bản cũ: `Trang_2` phải đứng trước `Trang_10`, không phải sau."""
    folder = tmp_path / "truyen"
    chapter = folder / "Chương 1"
    for index in (1, 2, 10, 11):
        _page(chapter, f"Trang_{index}.png")

    scanner.scan(conn, root=tmp_path)

    manga_id = manga_repo.get_by_slug(conn, "truyen").id
    chapter_id = chapter_repo.list_for_manga(conn, manga_id)[0].id
    names = [p.file_name for p in page_repo.list_for_chapter(conn, chapter_id)]
    assert names == ["Trang_1.png", "Trang_2.png", "Trang_10.png", "Trang_11.png"]


def test_rescan_is_idempotent(conn, tmp_path):
    _build_library(tmp_path)
    first = scanner.scan(conn, root=tmp_path)
    second = scanner.scan(conn, root=tmp_path)

    assert (first.manga, first.chapters, first.pages) == (
        second.manga,
        second.chapters,
        second.pages,
    )
    assert manga_repo.count(conn) == 1


def test_scan_keeps_expected_count_so_short_chapter_stays_partial(conn, tmp_path):
    """Đĩa chỉ có 3 ảnh nhưng metadata nói phải có 20 -> vẫn là `partial`."""
    folder = _build_library(tmp_path)
    metadata.write(
        folder,
        metadata.LibraryRecord(
            manga=Manga(slug="thien-duong", title="Thiên Đường"),
            chapters=(
                Chapter(
                    title="Chương 1",
                    dir_name="0001 - Chương 1",
                    number=1.0,
                    expected_page_count=20,
                ),
            ),
        ),
    )

    scanner.scan(conn, root=tmp_path)

    manga_id = manga_repo.get_by_slug(conn, "thien-duong").id
    chapter = next(
        c for c in chapter_repo.list_for_manga(conn, manga_id) if c.number == 1.0
    )
    assert chapter.page_count == 3
    assert chapter.status == "partial"
    assert chapter.is_complete is False


def test_scan_drops_chapter_whose_folder_disappeared(conn, tmp_path):
    folder = _build_library(tmp_path)
    scanner.scan(conn, root=tmp_path)

    for item in (folder / "0002 - Chương 2").iterdir():
        item.unlink()
    (folder / "0002 - Chương 2").rmdir()

    scanner.scan(conn, root=tmp_path)

    manga_id = manga_repo.get_by_slug(conn, "thien-duong").id
    assert [c.dir_name for c in chapter_repo.list_for_manga(conn, manga_id)] == [
        "0001 - Chương 1"
    ]


def test_scan_ignores_empty_chapter_folder(conn, tmp_path):
    _build_library(tmp_path)
    (tmp_path / "thien-duong" / "0003 - Chưa tải").mkdir()

    report = scanner.scan(conn, root=tmp_path)
    assert report.chapters == 2


def test_prune_removes_manga_without_folder(conn, tmp_path):
    _build_library(tmp_path)
    manga_repo.upsert(conn, Manga(slug="da-xoa-tay", title="Đã Xoá Tay"))

    without_prune = scanner.scan(conn, root=tmp_path)
    assert without_prune.pruned == 0
    assert manga_repo.count(conn) == 2

    with_prune = scanner.scan(conn, root=tmp_path, prune=True)
    assert with_prune.pruned == 1
    assert manga_repo.count(conn) == 1


def test_broken_metadata_reports_error_but_scan_continues(conn, tmp_path):
    """Một thư mục hỏng không được làm dừng cả lần quét."""
    _build_library(tmp_path)
    broken = tmp_path / "truyen-hong"
    _page(broken / "Chương 1", "001.webp")
    (broken / metadata.FILE_NAME).write_text("{ hong", encoding="utf-8")

    report = scanner.scan(conn, root=tmp_path)

    assert len(report.errors) == 1
    assert "không đọc được JSON" in report.errors[0]
    assert report.manga == 2  # thư mục hỏng vẫn được đoán từ cây thư mục
    assert manga_repo.get_by_slug(conn, "thien-duong") is not None


def test_scan_on_missing_library_is_not_an_error(conn, tmp_path):
    report = scanner.scan(conn, root=tmp_path / "khong-ton-tai")
    assert (report.manga, report.errors) == (0, [])
