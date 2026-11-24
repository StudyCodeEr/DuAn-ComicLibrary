"""Vòng đời kết nối và các ràng buộc của schema v2.

Những test này chặn đúng bug #6 của bản cũ: một connection sống lâu với
`check_same_thread=False`, dùng từ ba luồng, không có lock nào, và `close()`
không nằm trong `finally`.
"""

from __future__ import annotations

import sqlite3
import threading

import pytest

from mangalib.db import engine


@pytest.fixture
def db(tmp_path):
    """DB thật trên đĩa (không dùng `:memory:` vì mỗi kết nối sẽ là một DB mới)."""
    path = tmp_path / "library.db"
    engine.init_db(path)
    return path


def test_init_db_creates_file_and_records_version(tmp_path):
    path = tmp_path / "sub" / "library.db"
    engine.init_db(path)
    assert path.exists()
    with engine.read_only(path) as conn:
        assert engine.schema_version(conn) == engine.SCHEMA_VERSION


def test_schema_version_is_none_on_empty_db(tmp_path):
    path = tmp_path / "trong.db"
    with engine.connect(path) as conn:
        assert engine.schema_version(conn) is None


def test_wal_and_foreign_keys_enabled(db):
    with engine.read_only(db) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_rows_are_mappings(db):
    with engine.write(db) as conn:
        conn.execute(
            "INSERT INTO manga (slug, title, title_sort) VALUES (?, ?, ?)",
            ("mot-truyen", "Một Truyện", "mot truyen"),
        )
    with engine.read_only(db) as conn:
        row = conn.execute("SELECT slug, title FROM manga").fetchone()
    assert row["slug"] == "mot-truyen"
    assert row["title"] == "Một Truyện"


def test_foreign_key_violation_raises(db):
    """Chương trỏ tới truyện không tồn tại phải bị từ chối, không ghi âm thầm."""
    with pytest.raises(sqlite3.IntegrityError), engine.write(db) as conn:
        conn.execute(
            "INSERT INTO chapter (manga_id, title, dir_name) VALUES (?, ?, ?)",
            (999, "Chương 1", "0001 - Chuong 1"),
        )


def test_check_constraint_rejects_unknown_status(db):
    with engine.write(db) as conn:
        conn.execute(
            "INSERT INTO manga (id, slug, title, title_sort) VALUES (1, 'a', 'A', 'a')"
        )
    with pytest.raises(sqlite3.IntegrityError), engine.write(db) as conn:
        conn.execute(
            "INSERT INTO chapter (manga_id, title, dir_name, status) VALUES (?, ?, ?, ?)",
            (1, "Chương 1", "0001", "xong-roi"),
        )


def test_delete_manga_cascades(db):
    with engine.write(db) as conn:
        conn.execute(
            "INSERT INTO manga (id, slug, title, title_sort) VALUES (1, 'a', 'A', 'a')"
        )
        conn.execute(
            "INSERT INTO chapter (id, manga_id, title, dir_name) VALUES (1, 1, 'C1', 'd1')"
        )
        conn.execute(
            "INSERT INTO page (chapter_id, idx, file_name) VALUES (1, 0, '001.webp')"
        )
        conn.execute("INSERT INTO tag (id, name) VALUES (1, 'Action')")
        conn.execute("INSERT INTO manga_tag (manga_id, tag_id) VALUES (1, 1)")

    with engine.write(db) as conn:
        conn.execute("DELETE FROM manga WHERE id = 1")

    with engine.read_only(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM chapter").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM page").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM manga_tag").fetchone()[0] == 0
        # Tag vẫn còn: nó dùng chung cho nhiều truyện, không phải con của truyện nào.
        assert conn.execute("SELECT COUNT(*) FROM tag").fetchone()[0] == 1


def test_rollback_on_exception(db):
    """Lỗi giữa giao dịch không được để lại dữ liệu nửa vời."""
    with pytest.raises(RuntimeError), engine.write(db) as conn:
        conn.execute(
            "INSERT INTO manga (slug, title, title_sort) VALUES ('b', 'B', 'b')"
        )
        raise RuntimeError("lỗi giữa đường")

    with engine.read_only(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM manga").fetchone()[0] == 0


def test_connection_closed_on_exception(db):
    """Bug #6: `db.close()` của bản cũ không có `finally` nên leak file handle."""
    leaked: list[sqlite3.Connection] = []
    with pytest.raises(RuntimeError), engine.connect(db) as conn:
        leaked.append(conn)
        raise RuntimeError("nổ")

    assert leaked, "fixture không chạy"
    with pytest.raises(sqlite3.ProgrammingError):
        leaked[0].execute("SELECT 1")


def test_concurrent_writes_do_not_raise_database_is_locked(db):
    """Bug #6 trực tiếp: nhiều luồng ghi cùng lúc, không lock nào ở bản cũ."""
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=10)
            with engine.write(db) as conn:
                conn.execute(
                    "INSERT INTO manga (slug, title, title_sort) VALUES (?, ?, ?)",
                    (f"truyen-{index}", f"Truyện {index}", f"truyen {index}"),
                )
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert not errors, f"ghi song song bị lỗi: {errors!r}"
    with engine.read_only(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM manga").fetchone()[0] == 8


def test_reader_works_while_writer_holds_lock(db):
    """WAL: đọc không bị chặn bởi một giao dịch ghi đang mở."""
    with engine.write(db) as writer:
        writer.execute(
            "INSERT INTO manga (slug, title, title_sort) VALUES ('c', 'C', 'c')"
        )
        with engine.read_only(db) as reader:
            assert reader.execute("SELECT COUNT(*) FROM manga").fetchone()[0] == 0

    with engine.read_only(db) as reader:
        assert reader.execute("SELECT COUNT(*) FROM manga").fetchone()[0] == 1


def test_schema_is_idempotent(db):
    """Áp lại schema trên DB đã có dữ liệu không được làm mất gì."""
    with engine.write(db) as conn:
        conn.execute(
            "INSERT INTO manga (slug, title, title_sort) VALUES ('d', 'D', 'd')"
        )
    engine.init_db(db)
    with engine.read_only(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM manga").fetchone()[0] == 1
