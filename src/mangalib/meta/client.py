"""HTTP client khớp fingerprint TLS/HTTP2 của Chrome, không chạy browser nào.

Dùng `curl_cffi` với `impersonate` nên request trông giống Chrome ở tầng mạng.
Phát hiện trang challenge và nêu `ChallengeRequired` thay vì retry vô vọng.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from curl_cffi import requests as curl_requests
from curl_cffi.requests.errors import RequestsError

from mangalib.errors import ChallengeRequired, PageFetchError

__all__ = ["HttpClient", "Page"]

logger = logging.getLogger(__name__)

_CHALLENGE_MARKERS = ("challenge-form", "just a moment", "cf-browser-verification", "turnstile")
_RETRY_STATUS = (429, 500, 502, 503, 504)


@dataclass(frozen=True, slots=True)
class Page:
    url: str
    html: str
    status: int


class HttpClient:
    def __init__(
        self,
        *,
        impersonate: str = "chrome",
        timeout: int = 30,
        min_delay_ms: int = 50,
        retries: int = 3,
    ) -> None:
        self._session = curl_requests.Session(impersonate=impersonate, timeout=timeout)
        self._min_delay = min_delay_ms / 1000
        self._retries = retries
        self._last_request = 0.0

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    @property
    def cookies(self) -> dict[str, str]:
        return {name: value for name, value in self._session.cookies.items()}

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_delay:
            time.sleep(self._min_delay - elapsed)
        self._last_request = time.monotonic()

    def get(self, url: str, *, referer: str | None = None) -> curl_requests.Response:
        headers = {"Referer": referer} if referer else None
        last_error: Exception | None = None

        for attempt in range(self._retries):
            self._wait()
            try:
                response = self._session.get(url, headers=headers, allow_redirects=True)
            except (RequestsError, OSError) as exc:
                last_error = exc
                logger.debug("lần %d lỗi mạng: %s", attempt + 1, exc)
            else:
                if response.status_code in _RETRY_STATUS and attempt + 1 < self._retries:
                    last_error = PageFetchError(url, f"HTTP {response.status_code}")
                else:
                    return response
            time.sleep(0.4 * 2**attempt)

        raise PageFetchError(url, str(last_error) if last_error else "không rõ nguyên nhân")

    def get_page(self, url: str, *, referer: str | None = None) -> Page:
        """Lấy HTML. Nêu `ChallengeRequired` nếu nhận được trang challenge."""
        response = self.get(url, referer=referer)
        html = response.text or ""
        lowered = html[:4000].lower()
        if response.status_code == 403 or any(m in lowered for m in _CHALLENGE_MARKERS):
            raise ChallengeRequired(url)
        if response.status_code >= 400:
            raise PageFetchError(url, f"HTTP {response.status_code}")
        return Page(url=str(response.url), html=html, status=response.status_code)
