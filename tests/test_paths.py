"""Mỗi test ở đây chặn một bug thật của bản cũ."""

from __future__ import annotations

from pathlib import Path

import pytest

from mangalib import paths
from mangalib.errors import UnsafePathError


def test_data_root_independent_of_cwd(tmp_path, monkeypatch):
    """Bug #3: cwd quyết định nơi lưu, nên autostart (cwd = System32) ghi sai chỗ."""
    monkeypatch.delenv(paths.ENV_DATA_ROOT, raising=False)

    monkeypatch.chdir(tmp_path)
    from_temp = paths.data_root()

    other = tmp_path / "noi-khac"
    other.mkdir()
    monkeypatch.chdir(other)
    from_other = paths.data_root()

    assert from_temp == from_other
    assert "System32" not in str(from_temp)


def test_env_override_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV_DATA_ROOT, str(tmp_path))
    assert paths.data_root() == tmp_path.resolve()
    assert paths.library_dir() == tmp_path.resolve() / "library"
    assert paths.db_path() == tmp_path.resolve() / "library.db"


def test_frozen_uses_exe_dir(tmp_path, monkeypatch):
    """Bản .exe onedir phải ghi data cạnh exe, không vào thư mục tạm _internal."""
    monkeypatch.delenv(paths.ENV_DATA_ROOT, raising=False)
    exe = tmp_path / "ComicLibrary.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(exe))

    assert paths.data_root() == tmp_path.resolve() / "data"


@pytest.mark.parametrize(
    "parts",
    [
        ("..",),
        ("..", "..", "Users"),
        ("truyen", "..", "..", "etc"),
        ("C:/Windows/System32",),
        ("/etc/passwd",),
        ("",),
    ],
)
def test_safe_join_rejects_traversal(tmp_path, parts):
    """Lỗ hổng #1: `GET /manga/..%2F..%2FUsers` liệt kê thư mục ngoài thư viện."""
    with pytest.raises(UnsafePathError):
        paths.safe_join(tmp_path, *parts)


def test_safe_join_allows_normal_names(tmp_path):
    result = paths.safe_join(tmp_path, "ten-truyen", "0001 - Chương 1", "001.webp")
    assert result.is_relative_to(tmp_path.resolve())
    assert result.name == "001.webp"


def test_safe_join_allows_unicode_names(tmp_path):
    result = paths.safe_join(tmp_path, "Thiên Đường Không Hồi Kết")
    assert result.name == "Thiên Đường Không Hồi Kết"


def test_manga_dir_rejects_escape(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV_DATA_ROOT, str(tmp_path))
    with pytest.raises(UnsafePathError):
        paths.manga_dir("../../Windows")


def test_import_creates_nothing(tmp_path, monkeypatch):
    """Quy tắc R2: import module không được tạo thư mục nào."""
    monkeypatch.setenv(paths.ENV_DATA_ROOT, str(tmp_path / "chua-ton-tai"))
    paths.data_root()
    paths.logs_dir()
    paths.library_dir()
    assert not (tmp_path / "chua-ton-tai").exists()


def test_ensure_data_dirs_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV_DATA_ROOT, str(tmp_path / "data"))
    created = paths.ensure_data_dirs()
    assert created.exists()
    for child in ("library", "thumbs", "logs", "sites"):
        assert (created / child).is_dir()


def test_describe_lists_every_path(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV_DATA_ROOT, str(tmp_path))
    described = paths.describe()
    assert str(tmp_path.resolve()) in described["data_root"]
    assert "cwd (KHÔNG ảnh hưởng gì)" in described
    assert all(isinstance(value, str) for value in described.values())


def test_no_module_computes_its_own_root():
    """Quy tắc R1: chỉ paths.py được tính đường dẫn gốc."""
    source_dir = Path(paths.package_dir())
    offenders = []
    for file in source_dir.rglob("*.py"):
        if file.name == "paths.py":
            continue
        text = file.read_text(encoding="utf-8")
        for pattern in ('abspath(".")', "_MEIPASS", "dirname(__file__)"):
            if pattern in text:
                offenders.append(f"{file.name}: {pattern}")
    assert not offenders, f"module tự tính đường dẫn gốc: {offenders}"
