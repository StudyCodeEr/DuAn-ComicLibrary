"""Một class chạy MỌI site qua rule YAML. Thêm site = thêm file `.yml`."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from mangalib import naming
from mangalib.errors import PageFetchError
from mangalib.meta import discover, parse
from mangalib.meta.client import HttpClient, Page
from mangalib.meta.models import ChapterRef, MangaMeta
from mangalib.meta.rules import FieldRule, SiteRule

__all__ = ["GenericSource"]

logger = logging.getLogger(__name__)

# Nhieu site gan so dem truyen vao text cua link: "Blowjob 17513".
_TRAILING_COUNT = re.compile(r"\s+\d[\d.,]*$")


def _strip_count(text: str, enabled: bool) -> str:
    return _TRAILING_COUNT.sub("", text).strip() if enabled else text


class GenericSource:
    def __init__(self, rule: SiteRule) -> None:
        self.rule = rule

    # ----- domain failover -------------------------------------------------
    def _candidates(self, url: str) -> list[str]:
        parts = urlsplit(url)
        urls = [url]
        if self.rule.failover:
            for domain in self.rule.domains:
                if domain and domain != parts.hostname:
                    urls.append(urlunsplit(parts._replace(netloc=domain)))
        return urls

    def fetch(self, client: HttpClient, url: str, *, referer: str | None = None) -> Page:
        """Thử lần lượt các domain của rule, dùng domain nào trả về được."""
        last: Exception | None = None
        for candidate in self._candidates(url):
            try:
                return client.get_page(candidate, referer=referer)
            except PageFetchError as exc:
                logger.info("không lấy được %s (%s), thử domain khác", candidate, exc)
                last = exc
        raise last or PageFetchError(url, "không có domain nào trả về được")

    # ----- từng trường -----------------------------------------------------
    def _title(self, tree, base: str) -> str:
        raw = parse.extract(tree, self.rule.title.sources, base, first_only=True)
        if not raw:
            return ""
        return naming.strip_site_suffix(raw[0], self.rule.title.strip_suffixes)

    def _authors(self, tree, base: str) -> tuple[tuple[str, str], ...]:
        rule = self.rule.author
        raw = parse.extract(tree, rule.sources, base, first_only=True)
        separators = rule.split_separators or [",", "&", "/", ";"]
        deny = {naming.sort_key(d) for d in rule.deny}

        people: list[tuple[str, str]] = []
        seen: set[str] = set()
        for value in raw:
            for name in naming.split_people(
                _strip_count(value, rule.strip_trailing_count), separators
            ):
                key = naming.sort_key(name)
                if key in seen or key in deny or naming.is_placeholder_person(name):
                    continue
                seen.add(key)
                role = "author"
                for label, mapped in rule.role_hint.items():
                    if naming.sort_key(label) in naming.sort_key(value):
                        role = mapped
                people.append((name, role))
        return tuple(people)

    def _tags(self, tree, base: str) -> tuple[str, ...]:
        rule = self.rule.tags
        deny = {naming.sort_key(d) for d in rule.deny}
        limit = rule.max_len or 50
        out: list[str] = []
        seen: set[str] = set()
        for value in parse.extract(tree, rule.sources, base, first_only=True):
            name = " ".join(_strip_count(value, rule.strip_trailing_count).split())
            key = naming.sort_key(name)
            if not name or len(name) > limit or key in seen or key in deny:
                continue
            seen.add(key)
            out.append(name)
        return tuple(out)

    def _cover(self, tree, base: str) -> str | None:
        found = parse.extract(tree, self.rule.cover.sources, base, first_only=True)
        # `og:image` duoc phep la duong dan tuong doi. Handler `meta` khong ghep
        # base vi no con dung cho og:title la van ban thuan, nen ghep o day.
        return urljoin(base, found[0]) if found else None

    # ----- chương ----------------------------------------------------------
    def _chapter_refs(self, tree, base: str) -> list[ChapterRef]:
        rule = self.rule.chapters
        deny = [naming.sort_key(d) for d in rule.deny_titles]
        refs: dict[str, ChapterRef] = {}

        for line in parse.extract(tree, rule.sources, base, first_only=True):
            title, _, url = line.partition("\t")
            if not url:
                continue
            key = naming.sort_key(title)
            if key and any(bad in key for bad in deny):
                continue
            refs[url] = ChapterRef(
                title=title or url.rsplit("/", 1)[-1],
                url=url,
                number=naming.parse_chapter_number(title),
            )

        chapters = list(refs.values())
        if rule.order == "ascending_by_number":
            chapters.sort(key=lambda c: (c.number is None, c.number or 0.0, c.title))
        return chapters

    def _read_entry(self, tree, base: str) -> str | None:
        found = parse.extract(tree, self.rule.read_entry.sources, base, first_only=True)
        return found[0] if found else None

    def _auto_chapters(self, client: HttpClient, detail: Page, tree) -> list[ChapterRef]:
        """Trang lạ: tìm NÚT ĐỌC trước, rồi mới tìm chương — thứ tự này bền hơn.

        Trang chi tiết của site lạ thường chỉ có nút "Đọc truyện"; danh sách chương
        nằm ở trang đọc. Bám vào nút đọc trước nên không phụ thuộc việc trang chi
        tiết có liệt kê chương hay không.

        Không bao giờ coi là thất bại: nếu không suy ra được chương nào thì lấy
        chính trang người dùng dán làm một chương, để trình duyệt duyệt qua một
        lượt. Dán nhầm trang không phải truyện thì kết quả là 0 ảnh, chứ không
        phải một thông báo từ chối.
        """
        entry = self._read_entry(tree, detail.url)
        if entry and entry.split("#")[0] != detail.url.split("#")[0]:
            try:
                read_page = self.fetch(client, entry, referer=detail.url)
            except PageFetchError as exc:
                logger.info("không mở được nút đọc %s: %s", entry, exc)
            else:
                read_tree = parse.parse_html(read_page.html)
                found = self._chapter_refs(read_tree, read_page.url) or discover.discover_chapters(
                    read_tree, read_page.url
                )
                if found:
                    return found

        found = self._chapter_refs(tree, detail.url) or discover.discover_chapters(
            tree, detail.url
        )
        if found:
            return found

        logger.info("không suy ra được chương nào từ %s, duyệt chính trang này", detail.url)
        return [ChapterRef(title=self._title(tree, detail.url) or "Trang đã dán", url=detail.url)]

    # ----- điểm vào --------------------------------------------------------
    def fetch_manga(self, client: HttpClient, url: str) -> MangaMeta:
        detail = self.fetch(client, url)
        tree = parse.parse_html(detail.html)

        if self.rule.auto_discover:
            chapters = self._auto_chapters(client, detail, tree)
        else:
            chapters = self._chapter_refs(tree, detail.url)
            if not chapters:
                # Danh sách chương thường nằm ở trang đọc, không ở trang chi tiết.
                entry = self._read_entry(tree, detail.url)
                if entry:
                    read_page = self.fetch(client, entry, referer=detail.url)
                    chapters = self._chapter_refs(
                        parse.parse_html(read_page.html), read_page.url
                    )

        return MangaMeta(
            title=self._title(tree, detail.url),
            url=detail.url,
            authors=self._authors(tree, detail.url),
            tags=self._tags(tree, detail.url),
            cover_url=self._cover(tree, detail.url),
            chapters=tuple(chapters),
            source_key=self.rule.key,
        )


def _unused(_: FieldRule) -> None:  # pragma: no cover - giữ import cho type hint
    return None
