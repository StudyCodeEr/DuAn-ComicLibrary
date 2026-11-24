"""Nguồn chân lý DUY NHẤT về đường dẫn (quy tắc R1).

Bản cũ có **năm** định nghĩa "thư mục gốc" xung đột nhau:

  1. `utils/system_helper.get_app_dir()` — đúng
  2. `main.py:50 resource_path()`        — dựa vào cwd
  3. `gui/app_layout.py:35 self.base_dir`— LỆCH 1 CẤP, trỏ vào `.../gui`
  4. `server_pc.py:19 BASE_DIR`          — đúng
  5. đường dẫn tương đối thuần ("sites.json", "config.json", "Downloads", "logs/")

Hậu quả thật: khởi động cùng Windows bằng `--hidden` thì cwd = `C:\\Windows\\System32`,
nên ảnh tải vào sai chỗ và điện thoại không thấy ảnh; còn `smart_path_resolve` thì
không bao giờ chạy đúng ở bản dev vì nó tìm trong `.../gui/Downloads`.

Module này KHÔNG làm I/O lúc import (quy tắc R2) — mọi hàm chỉ tính đường dẫn.
Việc tạo thư mục là tường minh qua `ensure_data_dirs()`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mangalib.errors import UnsafePathError

ENV_DATA_ROOT = "MANGALIB_DATA"
"""Biến môi trường ghi đè thư mục dữ liệu (dùng trong test và khi chuyển ổ đĩa)."""

__all__ = [
    "ENV_DATA_ROOT",
    "app_dir",
    "browser_dir",
    "chapter_dir",
    "config_path",
    "data_root",
    "db_path",
    "describe",
    "ensure_data_dirs",
    "library_dir",
    "logs_dir",
    "manga_dir",
    "package_dir",
    "repo_root",
    "safe_join",
    "sites_dir",
    "thumbs_dir",
]


def package_dir() -> Path:
    """Thư mục chứa chính package này (`src/mangalib`). Chỉ để ĐỌC asset."""
    return Path(__file__).resolve().parent


def app_dir() -> Path:
    """Thư mục gốc của ứng dụng để đọc tài nguyên đi kèm.

    Chạy từ source: thư mục package. Chạy từ `.exe` PyInstaller: thư mục chứa exe
    (hoặc `sys._MEIPASS` khi đóng gói one-file).
    """
    if getattr(sys, "frozen", False):
        bundled = getattr(sys, "_MEIPASS", None)
        if bundled:
            return Path(bundled).resolve()
        return Path(sys.executable).resolve().parent
    return package_dir()


def repo_root() -> Path:
    """Thư mục gốc repo khi chạy từ source (`src/mangalib` → lùi hai cấp)."""
    return package_dir().parent.parent


def assets_dir() -> Path:
    """Ảnh nền và icon đi kèm ứng dụng (tài sản bắt buộc giữ theo PRODUCT.md).

    Khi đóng gói, asset nằm cạnh exe; khi chạy từ source, nằm ở gốc repo.
    Bản cũ dùng `resource_path("assets")` = `os.path.abspath("./assets")`, nên
    chạy từ cwd khác là không tìm thấy ảnh nền.
    """
    bundled = app_dir() / "assets"
    if bundled.is_dir():
        return bundled
    return repo_root() / "assets"


def data_root() -> Path:
    """Nơi chứa MỌI thứ runtime. Thứ tự quyết định, không phụ thuộc cwd.

    1. `$MANGALIB_DATA` nếu được đặt
    2. cạnh file `.exe` khi đã đóng gói
    3. `<repo>/data` khi chạy từ source
    """
    override = os.environ.get(ENV_DATA_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return repo_root() / "data"


def library_dir() -> Path:
    return data_root() / "library"


def thumbs_dir() -> Path:
    return data_root() / "thumbs"


def logs_dir() -> Path:
    return data_root() / "logs"


def browser_dir() -> Path:
    """user-data-dir của Edge khi tầng pagegrab cần phân giải danh sách URL ảnh."""
    return data_root() / "browser"


def sites_dir() -> Path:
    """Rule YAML của site thật. Thư mục này được .gitignore (quy tắc R7)."""
    return data_root() / "sites"


def db_path() -> Path:
    return data_root() / "library.db"


def config_path() -> Path:
    return data_root() / "config.toml"


def safe_join(root: Path, *parts: str) -> Path:
    """Ghép đường dẫn và từ chối mọi thứ thoát ra ngoài `root`.

    Đây là hàm duy nhất được phép dựng đường dẫn từ dữ liệu người dùng gửi lên
    (tên truyện, tên chương, tên file trong URL).

    Raises:
        UnsafePathError: khi một thành phần là đường dẫn tuyệt đối, chứa `..`,
            hoặc kết quả nằm ngoài `root`.
    """
    root = root.resolve()
    for part in parts:
        text = str(part)
        if not text or text in {".", ".."}:
            raise UnsafePathError(root, part)
        candidate = Path(text)
        if candidate.is_absolute() or candidate.drive or candidate.root:
            raise UnsafePathError(root, part)
        if ".." in candidate.parts:
            raise UnsafePathError(root, part)

    resolved = root.joinpath(*[str(p) for p in parts]).resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise UnsafePathError(root, "/".join(str(p) for p in parts))
    return resolved


def manga_dir(slug: str) -> Path:
    """Thư mục của một truyện, dựng từ `slug` trong DB — KHÔNG từ path client gửi.

    DB lưu `slug` chứ không lưu đường dẫn tuyệt đối (quy tắc R5), nên di chuyển cả
    thư viện sang ổ khác chỉ cần đổi `data_root`; `smart_path_resolve` của bản cũ
    trở thành không cần thiết.
    """
    return safe_join(library_dir(), slug)


def chapter_dir(slug: str, dir_name: str) -> Path:
    return safe_join(library_dir(), slug, dir_name)


def ensure_data_dirs() -> Path:
    """Tạo cây thư mục dữ liệu. Gọi TƯỜNG MINH từ cli/serve, không bao giờ lúc import."""
    for path in (data_root(), library_dir(), thumbs_dir(), logs_dir(), sites_dir()):
        path.mkdir(parents=True, exist_ok=True)
    return data_root()


def describe() -> dict[str, str]:
    """Mọi đường dẫn mangalib sẽ dùng, cho lệnh `mangalib doctor-paths`."""
    frozen = bool(getattr(sys, "frozen", False))
    return {
        "đóng gói (.exe)": str(frozen),
        f"${ENV_DATA_ROOT}": os.environ.get(ENV_DATA_ROOT, "(không đặt)"),
        "cwd (KHÔNG ảnh hưởng gì)": str(Path.cwd()),
        "app_dir (đọc asset)": str(app_dir()),
        "data_root": str(data_root()),
        "library_dir": str(library_dir()),
        "thumbs_dir": str(thumbs_dir()),
        "logs_dir": str(logs_dir()),
        "sites_dir": str(sites_dir()),
        "browser_dir": str(browser_dir()),
        "db_path": str(db_path()),
        "config_path": str(config_path()),
    }
