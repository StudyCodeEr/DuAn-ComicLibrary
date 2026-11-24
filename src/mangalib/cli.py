"""Diem vao dong lenh cua mangalib.

Cac subcommand duoc them dan theo tung phase cua ke hoach dai tu:
  Phase 1: paths (da co), doctor-paths
  Phase 2: scan
  Phase 3: probe, doctor-render, download
  Phase 4: serve
"""

from __future__ import annotations

import argparse
import sys

from mangalib import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mangalib",
        description="Thu vien truyen tranh cuc bo: tai, quan ly, doc tren PC va dien thoai",
    )
    parser.add_argument("--version", action="version", version=f"mangalib {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<lenh>")

    sub.add_parser("doctor-paths", help="In moi duong dan mangalib se dung (Phase 1)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "doctor-paths":
        # Phase 1 se noi vao mangalib.paths
        print("doctor-paths: chua cai dat (Phase 1)", file=sys.stderr)
        return 2

    parser.error(f"lenh khong biet: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
