"""Nguồn truyện. `manga.source_key` tham chiếu bảng này nên phải có dòng trước."""

from __future__ import annotations

import sqlite3

__all__ = ["ensure", "list_all"]


def ensure(
    conn: sqlite3.Connection,
    key: str,
    *,
    name: str = "",
    base_url: str = "",
    rule_file: str | None = None,
) -> str:
    conn.execute(
        """
        INSERT INTO source (key, name, base_url, rule_file) VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            name = COALESCE(NULLIF(excluded.name, ''), source.name),
            base_url = COALESCE(NULLIF(excluded.base_url, ''), source.base_url),
            rule_file = COALESCE(excluded.rule_file, source.rule_file)
        """,
        (key, name or key, base_url, rule_file),
    )
    return key


def list_all(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute("SELECT key, name FROM source ORDER BY name").fetchall()
    return [(row["key"], row["name"]) for row in rows]
