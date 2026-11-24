"""Cây lỗi của mangalib.

Quy tắc R4: không nuốt lỗi. Chỉ ba kiểu bắt lỗi được phép:
  1. `except LoiCuThe: log + fallback cụ thể`
  2. `raise MangalibError("ngữ cảnh") from e`
  3. `except Exception: logger.exception(...)` — CHỈ ở jobs/queue.py và cli.py,
     và cả hai nơi đó đều ghi lỗi vào job.error / exit code nên người dùng vẫn thấy.

Bản cũ có 27 chỗ `except:` trần và 17 chỗ `except: pass`; ruff bật E722 + BLE001
để chặn việc đó quay lại.
"""

from __future__ import annotations

__all__ = [
    "ChallengeRequired",
    "ConfigError",
    "Forbidden",
    "MangalibError",
    "NoPagesFound",
    "NotAnImage",
    "PageFetchError",
    "PageGone",
    "RuleError",
    "SourceNotFound",
    "UnsafePathError",
]


class MangalibError(Exception):
    """Gốc của mọi lỗi do mangalib chủ động nêu ra."""


class UnsafePathError(MangalibError):
    """Đường dẫn thoát ra ngoài thư mục gốc cho phép.

    Đây là lớp chặn lỗ hổng path traversal của bản cũ: `server_pc.py` ghép thẳng
    `manga_name` lấy từ URL vào đường dẫn, nên `GET /manga/..%2F..%2FUsers` liệt kê
    được thư mục ngoài thư viện.
    """

    def __init__(self, root: object, requested: object) -> None:
        super().__init__(f"đường dẫn {requested!r} nằm ngoài thư mục gốc {root!r}")
        self.root = root
        self.requested = requested


class ConfigError(MangalibError):
    """config.toml sai cú pháp hoặc sai giá trị.

    Bản cũ nuốt lỗi này (`gui/app_layout.py:59`) rồi âm thầm quay về "Downloads"
    tương đối, nên truyện tải vào sai chỗ mà không có dấu vết nào.
    """


class RuleError(MangalibError):
    """File rule YAML của một site sai cấu trúc. Luôn nêu rõ field nào sai."""


class SchemaMismatchError(MangalibError):
    """File DB đang dùng schema khác với schema mangalib biết.

    Gặp thật khi bản Flet cũ (`core/database.py`, schema v1) tạo file DB ở đúng
    đường dẫn mới: `CREATE TABLE IF NOT EXISTS` giữ nguyên bảng v1, rồi lệnh tạo
    index trên cột `title_sort` chết, nên mọi bảng sau đó không được tạo. Thà báo
    rõ còn hơn để người dùng gặp "no such column".
    """

    def __init__(self, path: object, found: str | None) -> None:
        found_text = f"schema {found}" if found else "schema cũ (không ghi phiên bản schema)"
        super().__init__(
            f"{path} đang dùng {found_text}, không phải schema mangalib hiện tại. "
            f"Chạy `mangalib scan --reset` để dời file cũ sang một bên rồi dựng lại "
            f"từ đĩa, hoặc tự xoá file đó nếu bạn không cần nó."
        )
        self.path = path
        self.found = found


class MetadataError(MangalibError):
    """`metadata.json` của một truyện sai cấu trúc.

    Quét thư viện nêu lỗi cho đúng thư mục đó rồi đi tiếp, chứ không dừng cả lần
    quét và cũng không âm thầm bỏ qua.
    """

    def __init__(self, path: object, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path


class SourceNotFound(MangalibError):
    """Không có rule nào khớp domain của link này."""


class ChallengeRequired(MangalibError):
    """Site trả về trang challenge (Cloudflare) thay vì nội dung.

    Không retry vô vọng: job chuyển trạng thái `needs_login` để người dùng tự vượt
    một lần trong trình duyệt, rồi chạy lại.
    """

    def __init__(self, url: str) -> None:
        super().__init__(f"site yêu cầu vượt challenge trước khi xem được: {url}")
        self.url = url


class NoPagesFound(MangalibError):
    """Không tìm được nhóm ảnh nào là trang truyện.

    Thà nêu lỗi rõ ràng còn hơn trả danh sách rỗng rồi báo "Xong: 0 ảnh" như bản cũ.
    """


class PageFetchError(MangalibError):
    """Tải một trang ảnh thất bại sau khi đã retry."""

    def __init__(self, url: str, reason: str = "") -> None:
        super().__init__(f"không tải được {url}{': ' + reason if reason else ''}")
        self.url = url


class PageGone(PageFetchError):
    """Ảnh trả 404/410 — không retry, vì retry không làm nó xuất hiện lại."""


class Forbidden(PageFetchError):
    """Ảnh trả 403 — thường là thiếu cookie hoặc User-Agent không khớp."""


class NotAnImage(MangalibError):
    """Dữ liệu tải về không phải ảnh (thường là trang lỗi HTML giả dạng ảnh).

    Bản cũ lưu thẳng nội dung này thành `Trang_007.png` hỏng.
    """

    def __init__(self, url: str, head: bytes = b"") -> None:
        super().__init__(f"dữ liệu tải về không phải ảnh: {url} (đầu file: {head[:8]!r})")
        self.url = url
        self.head = head
