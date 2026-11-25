"""Cho phép `python -m mangalib`."""

from __future__ import annotations

from mangalib.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
