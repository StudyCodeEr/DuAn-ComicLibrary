"""Tầng HTTP: lấy metadata không cần browser.

    client.py   HTTP client khớp fingerprint Chrome
    parse.py    bóc dữ liệu từ HTML theo spec khai báo
    rules.py    rule YAML của từng site
    generic.py  một class chạy mọi site qua rule
    models.py   kiểu dữ liệu scraper trả về

Quy tắc R9: tầng này KHÔNG được import playwright.
"""

from __future__ import annotations

from mangalib.meta.client import HttpClient
from mangalib.meta.generic import GenericSource
from mangalib.meta.models import ChapterRef, MangaMeta
from mangalib.meta.rules import SiteRule, load_all, rule_for_url

__all__ = [
    "ChapterRef",
    "GenericSource",
    "HttpClient",
    "MangaMeta",
    "SiteRule",
    "load_all",
    "rule_for_url",
]
