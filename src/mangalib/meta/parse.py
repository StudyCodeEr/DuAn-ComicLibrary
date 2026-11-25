"""Bóc dữ liệu từ HTML theo spec khai báo trong rule YAML.

Mỗi spec là một dict có đúng một khoá, ví dụ `{css: "h1"}` hay
`{meta: "og:title"}`. Thêm kiểu bóc mới = thêm một hàm vào `_HANDLERS`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser as HTMLParser

__all__ = ["extract", "parse_html"]

_STYLE_URL = re.compile(r"url\((['\"]?)(.*?)\1\)")


def parse_html(html: str) -> HTMLParser:
    return HTMLParser(html)


def _texts(nodes: Iterable) -> list[str]:
    out = []
    for node in nodes:
        text = (node.text() or "").strip()
        if text:
            out.append(" ".join(text.split()))
    return out


def _scoped(tree: HTMLParser, within: str | None):
    if not within:
        return [tree.body or tree.root]
    found = [node for selector in within.split(",") for node in tree.css(selector.strip())]
    return found or []


def _h_css(tree, spec, base):
    return _texts(node for root in _scoped(tree, spec.get("within")) for node in root.css(spec["css"]))


def _h_css_attr(tree, spec, base):
    cfg = spec["css_attr"]
    out = []
    for root in _scoped(tree, cfg.get("within")):
        for node in root.css(cfg["sel"]):
            value = node.attributes.get(cfg["attr"])
            if value:
                out.append(urljoin(base, value))
    return out


def _h_css_style_url(tree, spec, base):
    out = []
    for selector in str(spec["css_style_url"]).split(","):
        for node in tree.css(selector.strip()):
            match = _STYLE_URL.search(node.attributes.get("style") or "")
            if match:
                out.append(urljoin(base, match.group(2)))
    return out


def _h_meta(tree, spec, base):
    name = spec["meta"]
    for node in tree.css("meta"):
        attrs = node.attributes
        if attrs.get("property") == name or attrs.get("name") == name:
            content = attrs.get("content")
            if content:
                return [content.strip()]
    return []


def _h_page_title(tree, spec, base):
    node = tree.css_first("title")
    return [node.text().strip()] if node and node.text() else []


def _h_labeled_links(tree, spec, base):
    """Tìm nhãn (ví dụ "Tác giả") rồi lấy link trong khối chứa nhãn đó."""
    cfg = spec["labeled_links"]
    labels = [str(x).lower().rstrip(": ") for x in cfg.get("label_any", [])]
    link_sel = cfg.get("link", "a")
    out: list[str] = []
    for node in tree.css("li, div, p, tr, span"):
        text = (node.text() or "").lower()
        if not text or not any(label in text for label in labels):
            continue
        links = _texts(node.css(link_sel))
        if links and len(text) < 400:
            out.extend(links)
    return out


def _h_link_text_any(tree, spec, base):
    wanted = [str(x).lower() for x in spec["link_text_any"]]
    out = []
    for node in tree.css("a"):
        text = (node.text() or "").strip().lower()
        href = node.attributes.get("href")
        if href and text and any(w in text for w in wanted):
            out.append(urljoin(base, href))
    return out


def _h_select_options(tree, spec, base):
    """`<select>` của trang đọc: mỗi `<option>` là một chương."""
    out = []
    for select in tree.css(spec["select_options"]):
        for option in select.css("option"):
            value = option.attributes.get("value")
            if value:
                out.append(f"{(option.text() or '').strip()}\t{urljoin(base, value)}")
    return out


def _h_link_list(tree, spec, base):
    cfg = spec["link_list"]
    out = []
    for root in _scoped(tree, cfg.get("container")):
        for node in root.css(cfg.get("link", "a")):
            href = node.attributes.get("href")
            if not href:
                continue
            title_node = node.css_first(cfg["title_sel"]) if cfg.get("title_sel") else None
            title = ((title_node or node).text() or "").strip()
            out.append(f"{' '.join(title.split())}\t{urljoin(base, href)}")
    return out


_HANDLERS: dict[str, Callable] = {
    "css": _h_css,
    "css_attr": _h_css_attr,
    "css_style_url": _h_css_style_url,
    "meta": _h_meta,
    "page_title": _h_page_title,
    "labeled_links": _h_labeled_links,
    "link_text_any": _h_link_text_any,
    "select_options": _h_select_options,
    "link_list": _h_link_list,
}


def extract(tree: HTMLParser, specs: list[dict], base_url: str, *, first_only: bool = False) -> list[str]:
    """Chạy lần lượt các spec; `first_only` thì dừng ở spec đầu tiên có kết quả."""
    results: list[str] = []
    for spec in specs:
        keys = [k for k in spec if k in _HANDLERS]
        if not keys:
            continue
        values = _HANDLERS[keys[0]](tree, spec, base_url)
        if values:
            if first_only:
                return values
            results.extend(values)
    return results
