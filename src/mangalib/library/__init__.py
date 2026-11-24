"""Thư viện trên đĩa: định dạng tự mô tả và việc quét lại.

    metadata.py  đọc/ghi `metadata.json` của một thư mục truyện
    scanner.py   đi qua cây thư mục và đồng bộ DB theo đĩa

Hai việc này tách riêng vì chúng đổi vì lý do khác nhau: định dạng file đổi khi
thêm trường metadata, còn việc quét đổi khi cách bố trí thư mục đổi.
"""

from __future__ import annotations

from mangalib.library import metadata, scanner
from mangalib.library.scanner import ScanReport, scan

__all__ = ["ScanReport", "metadata", "scan", "scanner"]
