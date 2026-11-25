"""Tải ảnh song song. Ghi nguyên tử, bỏ qua trang đã có, báo đúng số lưu được."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from curl_cffi import requests as curl_requests
from curl_cffi.requests.errors import RequestsError

from mangalib.download.images import convert, sniff_ext
from mangalib.errors import NetworkLost

__all__ = ["FetchOutcome", "download_images"]

logger = logging.getLogger(__name__)

_IMAGE_EXTS = ("jpg", "jpeg", "png", "webp", "avif", "gif")
_NO_RETRY_STATUS = (404, 410)


@dataclass(slots=True)
class FetchOutcome:
    saved: int = 0
    skipped: int = 0
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)
    """Số trang (1-based) không lấy được — để báo ĐÚNG trang nào thiếu."""

    @property
    def total(self) -> int:
        return self.saved + self.skipped


class _SessionPool:
    """Một curl_cffi Session cho mỗi luồng: Session không an toàn đa luồng."""

    def __init__(self, cookies: dict[str, str], user_agent: str) -> None:
        self._local = threading.local()
        self._cookies = cookies
        self._user_agent = user_agent
        self._all: list[curl_requests.Session] = []
        self._lock = threading.Lock()

    def get(self) -> curl_requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            headers = {"User-Agent": self._user_agent} if self._user_agent else None
            session = curl_requests.Session(
                impersonate="chrome", timeout=30, headers=headers, cookies=self._cookies
            )
            self._local.session = session
            with self._lock:
                self._all.append(session)
        return session

    def close(self) -> None:
        with self._lock:
            for session in self._all:
                session.close()
            self._all.clear()


def _existing_file(chapter_dir: Path, stem: str, min_bytes: int) -> Path | None:
    for ext in _IMAGE_EXTS:
        candidate = chapter_dir / f"{stem}.{ext}"
        if candidate.is_file() and candidate.stat().st_size >= min_bytes:
            return candidate
    return None


_NGUONG_MAT_MANG = 5


def _con_mang(url: str) -> bool:
    """Máy chủ ảnh còn vào được không. Dùng để phân biệt mất mạng với lỗi lẻ tẻ."""
    if not url:
        return False
    try:
        with curl_requests.Session() as session:
            session.get(url, timeout=6, stream=True).close()
    except (RequestsError, OSError):
        return False
    return True


def download_images(
    urls: list[str],
    chapter_dir: Path,
    *,
    referer: str,
    cookies: dict[str, str] | None = None,
    user_agent: str = "",
    concurrency: int = 5,
    min_bytes: int = 20_000,
    retries: int = 3,
    image_format: str = "original",
) -> FetchOutcome:
    """Tải danh sách URL vào `chapter_dir`. Tên file là số thứ tự: `001.webp`."""
    chapter_dir.mkdir(parents=True, exist_ok=True)
    outcome = FetchOutcome()
    pool = _SessionPool(cookies or {}, user_agent)
    lock = threading.Lock()
    mang_hong: list[int] = []

    def worker(index_url: tuple[int, str]) -> None:
        index, url = index_url
        stem = f"{index + 1:03d}"

        existing = _existing_file(chapter_dir, stem, min_bytes)
        if existing is not None:
            with lock:
                outcome.skipped += 1
                outcome.files.append(existing.name)
            return

        error: str | None = None
        for attempt in range(retries):
            try:
                response = pool.get().get(url, headers={"Referer": referer})
            except (RequestsError, OSError) as exc:
                error = f"lỗi mạng: {exc}"
            else:
                if response.status_code in _NO_RETRY_STATUS:
                    error = f"HTTP {response.status_code} (ảnh không còn)"
                    break
                if response.status_code >= 400:
                    error = f"HTTP {response.status_code}"
                else:
                    data = response.content or b""
                    ext = sniff_ext(data)
                    if ext is None:
                        error = f"dữ liệu không phải ảnh ({data[:8]!r})"
                        break
                    if len(data) < min_bytes:
                        error = f"ảnh quá nhỏ ({len(data)} byte)"
                        break
                    converted = convert(data, image_format)
                    if converted is not None:
                        data, ext = converted
                    target = chapter_dir / f"{stem}.{ext}"
                    part = target.with_suffix(target.suffix + ".part")
                    part.write_bytes(data)
                    part.replace(target)  # ghi nguyên tử: Ctrl+C không để lại file hỏng
                    with lock:
                        outcome.saved += 1
                        outcome.files.append(target.name)
                    return
            if attempt + 1 < retries:
                threading.Event().wait(0.4 * 2**attempt)

        with lock:
            outcome.errors.append(f"trang {index + 1}: {error}")
            outcome.missing.append(index + 1)
            if error and error.startswith("lỗi mạng"):
                mang_hong.append(index)

    def chay(cong_viec: list[tuple[int, str]]) -> None:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            list(executor.map(worker, cong_viec))

    try:
        chay(list(enumerate(urls)))

        # Mat mang thi thu lai cung vo ich, va de chuong sau tai tiep chi tao ra
        # mot loat chuong thieu anh. Dung han de nguoi dung biet ma noi lai mang.
        if len(mang_hong) >= _NGUONG_MAT_MANG and not _con_mang(urls[0] if urls else ""):
            raise NetworkLost(
                f"{len(mang_hong)} trang lỗi mạng liên tiếp và không còn vào được "
                "máy chủ ảnh — đã dừng, hãy kiểm tra kết nối rồi tải lại"
            )

        # Mot luot thu lai CHI nhung trang con thieu. Loi mang chop nhoang rat hay
        # gap; khong co luot nay thi chuong bi danh thieu anh oan.
        if outcome.missing:
            thieu = sorted(set(outcome.missing))
            logger.info("thử lại %d trang còn thiếu: %s", len(thieu), thieu[:12])
            outcome.errors.clear()
            outcome.missing.clear()
            mang_hong.clear()
            chay([(i - 1, urls[i - 1]) for i in thieu])
    finally:
        pool.close()

    outcome.files.sort()
    outcome.missing.sort()
    return outcome
