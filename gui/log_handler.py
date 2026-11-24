"""Đưa log của hệ thống vào tab Console của UI, qua đúng một đường.

Thay cho `FletLogger` của bản cũ, thứ **chiếm `sys.stdout` và `sys.stderr`**
(`main.py:364-365`). Hậu quả của cách cũ: mọi `print()` từ bất kỳ luồng nào —
uvicorn, UDP listener, handler FastAPI — đều chạy `page.update()` trên luồng
ngoài, và `utils/logger.py` còn có `StreamHandler` ghi ra `sys.stderr` đã bị thay,
nên mỗi `self.log()` sinh ra hai dòng UI và hai lần `page.update()`.

Ở đây log chảy một chiều: `logging` → handler này → tab Console. `sys.stdout`
được trả lại cho hệ điều hành, nên `print()` không còn kéo UI theo nữa.

File này cố tình nhỏ và chỉ làm một việc: Phase 5 thay cả `gui/` bằng web UI,
lúc đó handler này được thay bằng Server-Sent Events.
"""

from __future__ import annotations

import logging
from typing import Protocol


class _ConsoleSink(Protocol):
    """Thứ duy nhất handler cần biết về UI: một hàm nhận chuỗi."""

    def __call__(self, message: str) -> None: ...


class UiLogHandler(logging.Handler):
    """Handler đẩy mỗi log record vào tab Console của app."""

    def __init__(self, sink: _ConsoleSink, level: int = logging.INFO) -> None:
        super().__init__(level=level)
        self._sink = sink
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._sink(self.format(record))
        except RecursionError:
            raise
        except Exception:
            # logging.Handler.handleError là đường xử lý chuẩn: nó KHÔNG nuốt im
            # lặng, mà in ra stderr thật khi logging.raiseExceptions bật.
            self.handleError(record)


def attach_ui_console(sink: _ConsoleSink, level: int = logging.INFO) -> UiLogHandler:
    """Gắn tab Console vào logger gốc. Gọi lại nhiều lần không cộng dồn handler."""
    root = logging.getLogger()
    for existing in list(root.handlers):
        if isinstance(existing, UiLogHandler):
            root.removeHandler(existing)

    handler = UiLogHandler(sink, level=level)
    root.addHandler(handler)
    if root.level > level:
        root.setLevel(level)
    return handler
