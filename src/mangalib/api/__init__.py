"""Tầng HTTP: API cho web UI và điện thoại.

    deps.py            xác thực LAN, giải đường dẫn file an toàn
    routes_library.py  thư viện, chi tiết truyện, trang ảnh, vị trí đọc
    routes_jobs.py     hàng đợi tải, SSE, nhận payload userscript
    discovery.py       UDP discovery
    app.py             lắp ứng dụng

Quy tắc R8: tầng này không import playwright hay curl_cffi trực tiếp.
"""

from __future__ import annotations

from mangalib.api.app import create_app

__all__ = ["create_app"]
