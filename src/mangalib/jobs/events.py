"""Bus sự kiện trong tiến trình, cho SSE.

Log chảy MỘT CHIỀU: `logging`/pipeline → bus → SSE → UI. Không luồng nào chạm UI,
nên lớp bug "cập nhật UI từ worker thread" của bản cũ không còn chỗ tồn tại.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from queue import Empty, Queue

__all__ = ["BUS", "EventBus"]


class EventBus:
    def __init__(self, *, maxsize: int = 500) -> None:
        self._subscribers: set[Queue] = set()
        self._lock = threading.Lock()
        self._maxsize = maxsize

    def publish(self, event: dict) -> None:
        with self._lock:
            targets = list(self._subscribers)
        for queue in targets:
            if queue.qsize() < self._maxsize:
                queue.put(event)

    @contextmanager
    def subscribe(self) -> Iterator[Queue]:
        queue: Queue = Queue()
        with self._lock:
            self._subscribers.add(queue)
        try:
            yield queue
        finally:
            with self._lock:
                self._subscribers.discard(queue)

    @staticmethod
    def drain(queue: Queue, timeout: float = 15.0) -> dict | None:
        try:
            return queue.get(timeout=timeout)
        except Empty:
            return None


BUS = EventBus()
