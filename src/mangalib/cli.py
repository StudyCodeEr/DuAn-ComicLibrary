"""Điểm vào dòng lệnh của mangalib.

Đây là một trong hai nơi duy nhất được phép `except Exception` (quy tắc R4), và nó
luôn ghi lỗi ra crash log cộng exit code khác 0 — người dùng vẫn thấy, không bị nuốt.

Các lệnh được thêm dần theo từng phase của kế hoạch đại tu:
  Phase 1: doctor-paths
  Phase 2: scan
  Phase 3: probe, doctor-render, download
  Phase 4: serve
"""

from __future__ import annotations

import argparse
import logging
import sys

from mangalib import __version__, config, logging_setup, paths
from mangalib.errors import MangalibError

logger = logging.getLogger("mangalib")


def _force_utf8_output() -> None:
    """Console Windows mặc định cp1252, không in được dấu tiếng Việt.

    Không đặt lại encoding thì `mangalib doctor-paths` sập với UnicodeEncodeError
    ngay khi in nhãn có dấu — đã gặp thật khi chạy từ `C:\\Windows\\System32`.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mangalib",
        description="Thư viện truyện tranh cục bộ: tải, quản lý, đọc trên PC và điện thoại",
    )
    parser.add_argument("--version", action="version", version=f"mangalib {__version__}")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="in log mức DEBUG ra màn hình",
    )
    sub = parser.add_subparsers(dest="command", metavar="<lệnh>")

    doctor = sub.add_parser(
        "doctor-paths",
        help="in mọi đường dẫn mangalib sẽ dùng, và tạo chúng nếu thiếu",
    )
    doctor.add_argument(
        "--create",
        action="store_true",
        help="tạo luôn cây thư mục dữ liệu",
    )

    return parser


def _cmd_doctor_paths(create: bool) -> int:
    print("Đường dẫn mangalib đang dùng")
    print("(cwd không ảnh hưởng tới bất kỳ dòng nào dưới đây — đó là điểm chính)\n")
    for key, value in paths.describe().items():
        print(f"  {key:32} {value}")

    if create:
        root = paths.ensure_data_dirs()
        print(f"\nĐã tạo cây thư mục dữ liệu tại {root}")

    cfg_path = paths.config_path()
    if cfg_path.exists():
        cfg = config.load()
        print(f"\nconfig.toml: định dạng ảnh={cfg.image_format}, song song={cfg.concurrency}")
    else:
        print("\nconfig.toml: chưa có — mangalib đang chạy bằng giá trị mặc định")
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    level = logging.DEBUG if args.verbose else logging.INFO
    logging_setup.setup_logging(level=level)

    try:
        if args.command == "doctor-paths":
            return _cmd_doctor_paths(create=args.create)
        parser.error(f"lệnh không biết: {args.command}")
        return 2
    except MangalibError as exc:
        # Lỗi do mangalib chủ động nêu: thông điệp đã đủ nghĩa cho người dùng.
        logger.error("%s", exc)
        return 1
    # Quy tắc R4 cho phép `except Exception` ở đúng hai nơi: cli.py và jobs/queue.py,
    # vì cả hai đều ghi lỗi ra ngoài (crash log + exit code) nên không có gì bị nuốt.
    except Exception as exc:
        crash_file = logging_setup.log_crash(exc)
        logger.error("Lỗi không lường trước. Chi tiết đã ghi vào %s", crash_file)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
