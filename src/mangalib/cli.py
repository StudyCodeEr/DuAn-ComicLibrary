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

    probe_cmd = sub.add_parser(
        "probe", help="thử lấy metadata của một link bằng HTTP thuần (không mở browser)"
    )
    probe_cmd.add_argument("url")

    dl = sub.add_parser("download", help="tải một truyện về thư viện")
    dl.add_argument("url")
    dl.add_argument("--dry-run", action="store_true", help="chỉ in metadata, không ghi gì")
    dl.add_argument("--headful", action="store_true", help="hiện cửa sổ browser")
    dl.add_argument("--limit", type=int, help="chỉ tải N chương đầu trong số cần tải")

    serve_cmd = sub.add_parser("serve", help="chạy server: web UI + API cho điện thoại")
    serve_cmd.add_argument("--host", default="0.0.0.0")
    serve_cmd.add_argument("--port", type=int, default=8000)

    scan_cmd = sub.add_parser(
        "scan",
        help="dựng lại cơ sở dữ liệu từ thư viện trên đĩa",
        description=(
            "Đĩa là sự thật, DB chỉ là chỉ mục. Lệnh này quét lại thư mục thư viện "
            "và đồng bộ DB theo đúng những gì có thật trên đĩa."
        ),
    )
    scan_cmd.add_argument(
        "--prune",
        action="store_true",
        help="xoá khỏi DB những truyện không còn thư mục trên đĩa",
    )
    scan_cmd.add_argument(
        "--root",
        help="thư mục thư viện cần quét (mặc định: data/library)",
    )
    scan_cmd.add_argument(
        "--reset",
        action="store_true",
        help="dời file DB cũ sang một bên rồi dựng lại từ đĩa (không xoá gì)",
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


def _cmd_scan(root: str | None, prune: bool, reset: bool = False) -> int:
    from datetime import datetime
    from pathlib import Path

    from mangalib.db import engine
    from mangalib.library import scanner

    paths.ensure_data_dirs()

    if reset and paths.db_path().exists():
        # Dời sang một bên, KHÔNG xoá: dữ liệu của người dùng không bị mất vì
        # một lựa chọn của chúng ta.
        aside = paths.db_path().with_suffix(f".db.bak-{datetime.now():%Y%m%d-%H%M%S}")
        paths.db_path().replace(aside)
        print(f"Đã dời DB cũ sang {aside.name}")

    engine.init_db()

    library = Path(root) if root else paths.library_dir()
    if library.resolve() != paths.library_dir().resolve():
        # DB chi luu slug, khong luu duong dan tuyet doi (quy tac R5), nen quet
        # mot thu muc ngoai thu vien se cho ra chi muc tro vao cho khong co file.
        print(f"CANH BAO: dang quet {library}")
        print(f"          nhung app se tim file o {paths.library_dir()}")
        print("          Chuyen cac thu muc truyen vao do truoc khi doc.")

    with engine.write() as conn:
        report = scanner.scan(conn, root=library, prune=prune)

    print(f"Đã quét: {report.manga} truyện, {report.chapters} chương, {report.pages} trang")
    if report.inferred:
        print(f"  {report.inferred} thư mục không có metadata.json — đã đoán từ cây thư mục")
    if report.pruned:
        print(f"  {report.pruned} truyện bị xoá khỏi DB vì không còn thư mục")

    if report.errors:
        print(f"\n{len(report.errors)} thư mục có vấn đề (các thư mục khác vẫn được quét):")
        for message in report.errors:
            print(f"  - {message}")
        return 1
    return 0


def _cmd_probe(url: str) -> int:
    from mangalib.errors import ChallengeRequired, MangalibError
    from mangalib.meta import GenericSource, HttpClient, rule_for_url

    rule = rule_for_url(url)
    if rule is None:
        print("Không có rule nào khớp domain này. Thêm một file .yml vào data/sites/")
        return 1

    print(f"Rule: {rule.key} ({rule.name}) — domain: {', '.join(rule.domains)}")
    try:
        with HttpClient(min_delay_ms=rule.request.min_delay_ms) as http:
            meta = GenericSource(rule).fetch_manga(http, url)
    except ChallengeRequired:
        print("Site trả về trang challenge: tầng HTTP không qua được.")
        print("→ Phải dùng tầng browser hoặc userscript cho site này.")
        return 2
    except MangalibError as exc:
        print(f"Không lấy được: {exc}")
        return 1

    print(f"URL cuối: {meta.url}")
    for line in meta.describe():
        print(f"  {line}")
    for chapter in meta.chapters[:5]:
        print(f"    - số={chapter.number} {chapter.title[:46]!r}")
    if len(meta.chapters) > 5:
        print(f"    ... và {len(meta.chapters) - 5} chương nữa")
    return 0


def _cmd_download(url: str, dry_run: bool, headful: bool, limit: int | None) -> int:
    from mangalib.download import pipeline
    from mangalib.errors import ChallengeRequired, MangalibError

    def show(phase: str, message: str) -> None:
        print(f"  [{phase}] {message}")

    try:
        report = pipeline.download_manga(
            url, dry_run=dry_run, headless=not headful, limit=limit, on_progress=show
        )
    except ChallengeRequired:
        print("Site trả về trang challenge. Chạy lại với --headful để tự vượt một lần.")
        return 2
    except MangalibError as exc:
        print(f"Không tải được: {exc}")
        return 1

    if report.meta:
        for line in report.meta.describe():
            print(f"  {line}")
    if dry_run:
        print("  (dry-run: không ghi gì)")
        return 0

    print(
        f"Đã lưu {report.pages_saved}/{report.pages_expected} trang · "
        f"{report.chapters_done} chương tải · {report.chapters_skipped} chương bỏ qua"
    )
    for message in report.errors[:10]:
        print(f"  - {message}")
    return 0 if report.ok else 1


def _cmd_serve(host: str, port: int) -> int:
    import uvicorn

    from mangalib.api import create_app

    print(f"Web UI: http://127.0.0.1:{port}")
    print(f"Điện thoại cùng LAN: http://<IP-máy-này>:{port} (quét QR trong Cài đặt)")
    uvicorn.run(create_app(), host=host, port=port, log_config=None, log_level="warning")
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
        if args.command == "probe":
            return _cmd_probe(args.url)
        if args.command == "download":
            return _cmd_download(args.url, args.dry_run, args.headful, args.limit)
        if args.command == "serve":
            return _cmd_serve(args.host, args.port)
        if args.command == "scan":
            return _cmd_scan(root=args.root, prune=args.prune, reset=args.reset)
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
