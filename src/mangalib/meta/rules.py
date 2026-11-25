"""Rule YAML cho mỗi site: mọi thứ dễ vỡ nằm trong dữ liệu, không trong code.

Web đổi giao diện thì sửa file `.yml`, không sửa Python. Rule sai cú pháp thì nêu
`RuleError` nói rõ field, không âm thầm trả danh sách rỗng.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mangalib import paths
from mangalib.errors import RuleError

__all__ = ["SiteRule", "load_all", "load_rule", "rule_for_url"]

_MODEL_CONFIG = ConfigDict(extra="ignore", populate_by_name=True)


class FieldRule(BaseModel):
    model_config = _MODEL_CONFIG
    sources: list[dict] = Field(default_factory=list, alias="from")
    strip_suffixes: list[str] = Field(default_factory=list)
    split_separators: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    role_hint: dict[str, str] = Field(default_factory=dict)
    strip_trailing_count: bool = False
    max_len: int | None = None


class ChaptersRule(FieldRule):
    deny_titles: list[str] = Field(default_factory=list)
    order: str = "ascending_by_number"


class ScrollRule(BaseModel):
    model_config = _MODEL_CONFIG
    idle_ms: int = 800
    max_ms: int = 30_000
    step_px: int = 2_000
    settle_ms: int = 15_000
    """Giu them toi da bao lau sau khi tuong da xong, de bat not dot nap cuoi."""


class PagesRule(BaseModel):
    model_config = _MODEL_CONFIG
    strategy: list[str] = Field(default_factory=lambda: ["browser"])
    container: list[str] = Field(default_factory=list)
    image_selector: str = "img"
    cdn_allowlist: list[str] = Field(default_factory=list)
    placeholder_url_substrings: list[str] = Field(default_factory=list)
    scroll: ScrollRule = Field(default_factory=ScrollRule)
    mode: str = "urls"


class FiltersRule(BaseModel):
    model_config = _MODEL_CONFIG
    min_bytes: int = 20_000
    min_width: int = 400
    allow_content_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp", "image/avif"]
    )
    deny_url_substrings: list[str] = Field(default_factory=list)


class RequestRule(BaseModel):
    model_config = _MODEL_CONFIG
    referer: str = "chapter_url"
    concurrency: int = 5
    min_delay_ms: int = 50


class SiteRule(BaseModel):
    model_config = _MODEL_CONFIG
    key: str
    name: str = ""
    domains: list[str] = Field(default_factory=list)
    failover: bool = True
    title: FieldRule = Field(default_factory=FieldRule)
    author: FieldRule = Field(default_factory=FieldRule)
    tags: FieldRule = Field(default_factory=FieldRule)
    cover: FieldRule = Field(default_factory=FieldRule)
    read_entry: FieldRule = Field(default_factory=FieldRule)
    chapters: ChaptersRule = Field(default_factory=ChaptersRule)
    pages: PagesRule = Field(default_factory=PagesRule)
    filters: FiltersRule = Field(default_factory=FiltersRule)
    request: RequestRule = Field(default_factory=RequestRule)
    source_path: str | None = None
    auto_discover: bool = False
    """Rule suy ra tu trang, khong phai file .yml: cho phep do danh sach chuong
    bang cau truc khi bo chon khai bao san khong ra gi."""

    def matches(self, url: str) -> bool:
        host = urlsplit(url).hostname or ""
        return any(host == d or host.endswith(f".{d}") for d in self.domains)


def load_rule(path: Path) -> SiteRule:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as exc:
        raise RuleError(f"{path}: không đọc được YAML ({exc})") from exc
    if not isinstance(raw, dict):
        raise RuleError(f"{path}: nội dung không phải một mapping")
    raw.setdefault("key", path.stem)
    raw["source_path"] = str(path)
    try:
        return SiteRule.model_validate(raw)
    except ValidationError as exc:
        raise RuleError(f"{path}: {exc}") from exc


def load_all(*dirs: Path) -> dict[str, SiteRule]:
    """Rule của người dùng (`data/sites/`) thắng rule mẫu đi kèm package."""
    search = list(dirs) or [paths.sites_dir(), paths.package_dir() / "sites"]
    rules: dict[str, SiteRule] = {}
    for directory in reversed(search):
        if not directory.is_dir():
            continue
        for file in sorted(directory.glob("*.yml")):
            if file.stem.startswith("_"):
                continue
            rule = load_rule(file)
            rules[rule.key] = rule
    return rules


def rule_for_url(url: str, rules: dict[str, SiteRule] | None = None) -> SiteRule | None:
    for rule in (rules if rules is not None else load_all()).values():
        if rule.matches(url):
            return rule
    return None
