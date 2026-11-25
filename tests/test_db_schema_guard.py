"""Chặn việc áp schema v2 lên một file DB của bản cũ.

Gặp thật khi làm Phase 2: bản Flet cũ (`core/database.py`, schema v1) tạo file DB
ở đúng đường dẫn mới. `CREATE TABLE IF NOT EXISTS` giữ nguyên bảng `manga` của v1,
rồi lệnh tạo index trên cột `title_sort` chết — nên mọi bảng sau đó (`chapter`,
`page`, `author`...) không bao giờ được tạo, và lỗi chỉ lộ ra sau đó rất xa dưới
dạng "no such column: title_sort" / "no such table: chapter".
"""

from __future__ import annotations

import sqlite3

import pytest

from mangalib.db import engine
from mangalib.errors import SchemaMismatchError


def _make_v1_db(path):
    """Dựng lại đúng bảng `manga` của schema v1 (core/database.py bản cũ)."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE manga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            path TEXT,
            cover_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


def test_init_db_refuses_old_schema_with_actionable_message(tmp_path):
    path = tmp_path / "library.db"
    _make_v1_db(path)

    with pytest.raises(SchemaMismatchError) as caught:
        engine.init_db(path)

    message = str(caught.value)
    assert "scan --reset" in message, "thông điệp phải nói rõ phải làm gì"
    assert str(path) in message


def test_init_db_accepts_empty_file(tmp_path):
    """File rỗng (chưa có bảng nào) thì vẫn áp schema bình thường."""
    path = tmp_path / "library.db"
    sqlite3.connect(path).close()

    engine.init_db(path)

    with engine.read_only(path) as conn:
        assert engine.schema_version(conn) == engine.SCHEMA_VERSION


def test_init_db_is_idempotent_on_its_own_schema(tmp_path):
    path = tmp_path / "library.db"
    engine.init_db(path)
    engine.init_db(path)

    with engine.read_only(path) as conn:
        assert engine.schema_version(conn) == engine.SCHEMA_VERSION
        assert engine.has_user_tables(conn) is True


def test_has_user_tables_false_on_fresh_db(tmp_path):
    path = tmp_path / "trong.db"
    with engine.connect(path) as conn:
        assert engine.has_user_tables(conn) is False


def _make_v2_db(path):
    """DB đúng hình dạng v2: schema hiện tại trừ ba cột thêm ở v3."""
    sql = engine.schema_sql()
    for dong in (
        "    -- Xoa mem: file anh van nam nguyen tren dia, nen hoan tac duoc.\n"
        "    deleted_at   TEXT\n",
        "    deleted_at          TEXT,\n"
        "    -- Thu tu do nguoi dung tu keo. NULL = xep theo `number` nhu mac dinh.\n"
        "    sort_index          INTEGER,\n",
    ):
        assert dong in sql, "schema.sql đã đổi — sửa lại fixture này"
        sql = sql.replace(dong, "", 1)
    # Bo dau phay thua o dong truoc `deleted_at` cua bang manga.
    sql = sql.replace("    last_read_at TEXT,\n);", "    last_read_at TEXT\n);", 1)

    conn = sqlite3.connect(path)
    conn.executescript(sql)
    conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', '2')")
    conn.execute(
        "INSERT INTO manga (slug, title, title_sort) VALUES ('abc', 'Truyện A', 'truyen a')"
    )
    conn.commit()
    conn.close()


def test_nang_cap_v2_len_v3_giu_nguyen_du_lieu(tmp_path):
    """Nâng cấp tại chỗ, không bắt người dùng quét lại thư viện từ đĩa."""
    path = tmp_path / "library.db"
    _make_v2_db(path)

    engine.init_db(path)

    with engine.connect(path) as conn:
        assert engine.schema_version(conn) == engine.SCHEMA_VERSION
        row = conn.execute("SELECT title, deleted_at FROM manga WHERE slug = 'abc'").fetchone()
        assert row["title"] == "Truyện A", "dữ liệu cũ phải còn nguyên"
        assert row["deleted_at"] is None
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(chapter)")}
        assert {"deleted_at", "sort_index"} <= cols
