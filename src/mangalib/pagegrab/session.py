"""Browser CHỈ làm một việc: phân giải danh sách URL ảnh của một chương.

Trang nguồn dựng ảnh bằng JS (manifest bị mã hoá trong HTML), nên tầng HTTP không
lấy được danh sách trang. Nhưng sau khi trang chạy, ảnh là `<img src="https://...">`
bình thường — nên ta chỉ cần lấy danh sách URL rồi đóng browser, còn việc tải file
do `download/fetcher.py` làm song song. Được file gốc, không re-encode.

Dùng Edge đã cài sẵn (`channel="msedge"`), không tải Chromium riêng 150 MB.
Import playwright nằm trong hàm (quy tắc R9): mở app để ĐỌC truyện không nạp nó.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from mangalib import paths
from mangalib.errors import ChallengeRequired, NetworkLost, NoPagesFound
from mangalib.meta.rules import SiteRule

__all__ = ["AD_MARKERS", "BrowserSession", "GrabResult"]

logger = logging.getLogger(__name__)

AD_MARKERS = (
    "ads", "adserv", "adsystem", "popads", "popcash", "tyserving", "tyrotation",
    "cdn4ads", "doubleclick", "googlesyndication", "googletagmanager",
    "google-analytics", "clarity.ms", "recaptcha", "hotjar",
)
_BLOCKED_TYPES = ("font", "media")
_CHALLENGE_MARKERS = ("just a moment", "challenge-form", "cf-browser-verification")

_COLLECT_JS = """
(selector) => {
  const all = document.querySelectorAll(selector);
  const items = [];
  all.forEach((img, order) => {
    const src = img.currentSrc || img.src || '';
    items.push({src, w: img.naturalWidth, h: img.naturalHeight, order});
  });
  return {
    items,
    declared: all.length,
    // `complete` false nghia la anh VAN DANG TAI. Khong co so nay thi "so anh
    // khong tang" bi hieu nham la da xong, trong khi thuc ra dang cho mang.
    loading: [...all].filter((img) => !img.complete).length,
    online: navigator.onLine,
    atBottom: (window.scrollY + window.innerHeight) >= (document.body.scrollHeight - 80),
  };
}
"""


@dataclass(slots=True)
class GrabResult:
    """URL ảnh cùng cookie/UA của chính phiên browser, để tải tiếp bằng HTTP."""

    image_urls: list[str] = field(default_factory=list)
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    declared_total: int = 0
    """Số trang do chính reader khai báo (số thẻ ảnh nó tạo ra).

    Đây mới là `expected` đúng. Nếu lấy `len(image_urls)` làm expected thì một lần
    cuộn chưa đủ sẽ cho saved == expected và chương bị đánh `complete` sai."""


class BrowserSession:
    def __init__(self, *, headless: bool = True, channel: str = "msedge") -> None:
        self._headless = headless
        self._channel = channel
        self._playwright = None
        self._context = None

    def __enter__(self) -> BrowserSession:
        from playwright.sync_api import sync_playwright

        profile = paths.browser_dir()
        profile.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            channel=self._channel,
            headless=self._headless,
            viewport={"width": 1400, "height": 1000},
            args=["--disable-blink-features=AutomationControlled", "--mute-audio"],
        )
        return self

    def __exit__(self, *_exc: object) -> None:
        for closer in (self._context, self._playwright):
            if closer is None:
                continue
            try:
                closer.close() if closer is self._context else closer.stop()
            except Exception as exc:  # noqa: BLE001 - đóng browser không được che lỗi chính
                logger.warning("lỗi khi đóng browser: %s", exc)
        self._context = None
        self._playwright = None

    def _block_junk(self, route) -> None:
        request = route.request
        url = request.url.lower()
        if request.resource_type in _BLOCKED_TYPES or any(m in url for m in AD_MARKERS):
            route.abort()
        else:
            route.continue_()

    def grab_chapter(self, url: str, rule: SiteRule) -> GrabResult:
        """Mở chương, cuộn tới khi hết ảnh placeholder, trả danh sách URL ảnh."""
        if self._context is None:
            raise RuntimeError("BrowserSession phải dùng trong khối `with`")

        pages_rule = rule.pages
        page = self._context.new_page()
        try:
            page.route("**/*", self._block_junk)
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)

            if any(m in (page.title() or "").lower() for m in _CHALLENGE_MARKERS):
                raise ChallengeRequired(url)

            items, declared = self._scroll_until_loaded(page, pages_rule)
            urls = self._filter(items, rule)
            if not urls:
                raise NoPagesFound(f"không tìm thấy ảnh trang truyện nào ở {url}")

            # `declared` chi dang tin khi rule khoanh vung khung doc. Khong co
            # container thi no dem CA logo, banner, thumbnail truyen khac - mot
            # chuong 33 trang bi bao 33/37 va danh partial oan.
            if not pages_rule.container:
                declared = 0

            if declared and len(urls) < declared:
                logger.warning(
                    "chỉ render được %d/%d trang — chương sẽ được ghi là partial",
                    len(urls), declared,
                )

            return GrabResult(
                image_urls=urls,
                cookies={c["name"]: c["value"] for c in self._context.cookies()},
                user_agent=page.evaluate("navigator.userAgent"),
                declared_total=declared,
            )
        finally:
            page.close()

    def _scroll_until_loaded(self, page, pages_rule) -> tuple[list[dict], int]:
        """Cuộn tới khi render đủ số trang reader khai báo, hoặc hết thời gian.

        Reader nạp ảnh theo từng đợt cách nhau vài giây, nên "số ảnh không tăng
        trong 2 nhịp" KHÔNG phải dấu hiệu đã xong: nó chỉ là khoảng nghỉ giữa hai
        đợt. Điều kiện dừng đúng là render đủ `declared`, hoặc đã tới đáy trang mà
        số ảnh vẫn không tăng sau nhiều nhịp liền.
        """
        selector = pages_rule.image_selector
        deadline = time.monotonic() + pages_rule.scroll.max_ms / 1000
        idle = pages_rule.scroll.idle_ms / 1000
        loaded_count = 0
        stalled = 0
        snapshot: dict = {"items": [], "declared": 0, "atBottom": False}

        while time.monotonic() < deadline:
            snapshot = page.evaluate(_COLLECT_JS, selector)
            declared = int(snapshot["declared"])
            loaded = sum(1 for item in snapshot["items"] if item["w"] > 200)

            if not snapshot.get("online", True):
                raise NetworkLost("trình duyệt báo mất kết nối mạng giữa chừng")

            dang_tai = int(snapshot.get("loading") or 0)

            if declared and loaded >= declared:
                break
            # `loaded and ...`: 0 ảnh KHÔNG BAO GIỜ là trạng thái kết thúc. Lúc trang
            # vừa load, document còn ngắn nên atBottom đã True ngay, và nếu tính 0 là
            # "đứng yên" thì vòng lặp thoát sau ~5 giây với 0 ảnh.
            # `not dang_tai`: còn ảnh đang tải thì "số ảnh không tăng" chỉ là đang
            # chờ mạng, không phải đã hết trang.
            if loaded and loaded == loaded_count and not dang_tai:
                stalled += 1
                if snapshot["atBottom"] and stalled >= 6:
                    break
            else:
                stalled = 0
                loaded_count = loaded

            page.evaluate(f"window.scrollBy(0, {pages_rule.scroll.step_px})")
            time.sleep(idle)

        loaded_count = self._giu_them(page, selector, pages_rule, loaded_count)
        logger.info(
            "render được %d/%d trang", loaded_count, int(snapshot.get("declared") or 0)
        )
        final = page.evaluate(_COLLECT_JS, selector)
        return final["items"], int(final["declared"])

    def _giu_them(self, page, selector: str, pages_rule, loaded_count: int) -> int:
        """Giữ trang thêm tối đa `settle_ms` sau khi tưởng đã xong.

        Reader nạp ảnh theo từng đợt. Dừng ngay lúc số ảnh vừa đứng yên là bỏ nốt
        đợt cuối. Nhưng KHÔNG giữ cứng đủ 15 giây mỗi chương — với 8 chương thì đó
        là hai phút chờ vô ích: thoát ngay khi không còn ảnh nào đang tải và số ảnh
        không đổi qua hai nhịp liền.
        """
        han = time.monotonic() + pages_rule.scroll.settle_ms / 1000
        yen = 0
        while time.monotonic() < han:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
            snap = page.evaluate(_COLLECT_JS, selector)
            if not snap.get("online", True):
                raise NetworkLost("trình duyệt báo mất kết nối mạng giữa chừng")

            loaded = sum(1 for item in snap["items"] if item["w"] > 200)
            if loaded > loaded_count:
                logger.info("giữ thêm bắt được %d trang nữa", loaded - loaded_count)
                loaded_count = loaded
                yen = 0
            elif int(snap.get("loading") or 0) == 0:
                yen += 1
                if yen >= 2:
                    break
            else:
                yen = 0
        return loaded_count

    @staticmethod
    def _filter(found: list[dict], rule: SiteRule) -> list[str]:
        allow = [host.lower() for host in rule.pages.cdn_allowlist]
        placeholders = [p.lower() for p in rule.pages.placeholder_url_substrings]
        deny = [d.lower() for d in rule.filters.deny_url_substrings]
        min_width = rule.filters.min_width

        urls: list[str] = []
        seen: set[str] = set()
        for item in sorted(found, key=lambda i: i["order"]):
            src = item["src"]
            lowered = src.lower()
            if src in seen or not lowered.startswith("http"):
                continue
            if any(p in lowered for p in placeholders) or any(d in lowered for d in deny):
                continue
            if allow and not any(host in lowered for host in allow):
                continue
            # w == 0 nghia la anh chua bao gio render (placeholder): bo qua.
            # Viet `if item["w"] and ...` la bo qua chinh truong hop nay, vi 0 falsy.
            if item["w"] < min_width:
                continue
            seen.add(src)
            urls.append(src)
        return urls
