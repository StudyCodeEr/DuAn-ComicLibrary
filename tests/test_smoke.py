"""Test khoi dong: bao ve quy tac R2 (module khong lam I/O luc import).

Day la bug that cua ban cu: utils/logger.py goi os.makedirs("logs") o module scope
voi duong dan TUONG DOI, nen khi autostart (--hidden, cwd = C:\\Windows\\System32)
app nem PermissionError NGAY LUC IMPORT, chet truoc khi ve UI.
"""

from __future__ import annotations

import subprocess
import sys

import mangalib


def test_version_is_exposed():
    assert mangalib.__version__


def test_import_does_no_filesystem_write(tmp_path):
    """Import mangalib tu mot cwd chi-doc-duoc khong duoc tao file/thu muc nao."""
    code = "import mangalib, pathlib, sys; " "print(len(list(pathlib.Path('.').iterdir())))"
    before = len(list(tmp_path.iterdir()))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    after = len(list(tmp_path.iterdir()))
    assert after == before, f"import da tao file trong cwd: {list(tmp_path.iterdir())}"
    assert result.stdout.strip() == "0"


def test_cli_version_runs():
    result = subprocess.run(
        [sys.executable, "-m", "mangalib.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "mangalib" in result.stdout
