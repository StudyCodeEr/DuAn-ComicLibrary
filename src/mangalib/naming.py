"""Chuẩn hoá tên: file, slug, tên người, số chương, khoá sắp xếp không dấu.

Mọi hàm ở đây là hàm thuần — không I/O, không mạng, nên test được trong vài
millisecond. Chúng sửa những lỗi thật của bản cũ:

* tên truyện bị dính đuôi SEO của trang nguồn (có thật trên đĩa:
  `... - Việt Hentai - Hentai Vietsub HD`);
* chương sắp xếp theo tên thư mục nên chương 10 đứng trước chương 2;
* heuristic đảo thứ tự chương dựa vào việc tên có chứa ký tự "1"
  (`main.py:245`) — "Chapter 10" cũng chứa "1";
* tìm kiếm `LIKE '%...%'` thất bại khi gõ không dấu.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence

__all__ = [
    "chapter_dir_name",
    "clean_filename",
    "is_placeholder_person",
    "normalize_person_name",
    "parse_chapter_number",
    "slugify",
    "sort_key",
    "split_people",
    "strip_diacritics",
    "strip_site_suffix",
    "unique_name",
]

MAX_NAME_LENGTH = 100
"""Giới hạn độ dài một thành phần tên. Windows giới hạn cả đường dẫn ở 260 ký tự."""

_FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*]')
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
_EN_DASH = chr(0x2013)

_RESERVED_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(1, 10)]
    + [f"LPT{i}" for i in range(1, 10)]
)

_PLACEHOLDER_PEOPLE = frozenset(
    {
        "",
        "-",
        "--",
        "?",
        "n/a",
        "na",
        "unknown",
        "chua ro",
        "chua co",
        "khong ro",
        "dang cap nhat",
        "updating",
        "tac gia",
        "author",
    }
)

# Neo theo từ khoá chương: "Chương 10", "Chapter 9.5", "Chap 3", "ch.7".
# \b chặn việc khớp vào giữa từ khác ("chính 5" không phải chương 5).
_CHAPTER_WORD = re.compile(
    r"\b(?:chương|chuong|chapter|chap|ch)\.?\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_BARE_NUMBER = re.compile(r"(\d+(?:[.,]\d+)?)")


def strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt. `đ`/`Đ` phải xử lý riêng vì NFD không tách chúng."""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def sort_key(text: str) -> str:
    """Khoá sắp xếp/tìm kiếm: không dấu, chữ thường, khoảng trắng gộp.

    Dùng cho `manga.title_sort` và `author.name_sort`, nên gõ "the loai" tìm ra
    "Thể loại" và "tran dang khoa" tìm ra "Trần Đăng Khoa".
    """
    return _WHITESPACE.sub(" ", strip_diacritics(text)).strip().lower()


def clean_filename(name: str, *, max_length: int = MAX_NAME_LENGTH) -> str:
    """Biến một chuỗi bất kỳ thành tên file/thư mục an toàn trên Windows."""
    if not name or not name.strip():
        return "Khong-ten"

    # Thay bằng dấu cách, không xoá trắng: "Tên\ntruyện" phải ra "Tên truyện",
    # không phải "Têntruyện".
    cleaned = _CONTROL_CHARS.sub(" ", str(name))
    cleaned = _FORBIDDEN_CHARS.sub("-", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")

    # Tên thiết bị DOS: "CON", "NUL", "COM1"... không dùng được làm tên file,
    # kể cả khi có phần mở rộng. Lỗi này chưa ai gặp nhưng sẽ gặp.
    stem = cleaned.split(".")[0].upper()
    if stem in _RESERVED_NAMES:
        cleaned = f"_{cleaned}"

    return cleaned or "Khong-ten"


def slugify(name: str, *, max_length: int = 80) -> str:
    """Slug ASCII dùng làm tên thư mục truyện và khoá trong DB."""
    base = sort_key(name)
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if len(base) > max_length:
        base = base[:max_length].rstrip("-")
    return base or "khong-ten"


def unique_name(base: str, taken: Iterable[str]) -> str:
    """Thêm hậu tố `-2`, `-3`... khi tên đã bị chiếm."""
    existing = set(taken)
    if base not in existing:
        return base
    for index in range(2, 1000):
        candidate = f"{base}-{index}"
        if candidate not in existing:
            return candidate
    raise ValueError(f"không tìm được tên duy nhất cho {base!r}")


def strip_site_suffix(
    title: str,
    suffixes: Sequence[str] = (),
    separators: Sequence[str] = (" - ", " | ", f" {_EN_DASH} "),
) -> str:
    """Bỏ đuôi SEO mà trang nguồn gắn vào tên truyện.

    Trường hợp thật trên đĩa: `"<tên truyện> - Việt Hentai - Hentai Vietsub HD"`.
    `suffixes` khai báo trong rule YAML của từng site nên sửa web không phải sửa code.
    """
    result = title.strip()
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            if suffix and result.lower().endswith(suffix.strip().lower()):
                result = result[: -len(suffix.strip())].strip()
                changed = True
        for separator in separators:
            for suffix in suffixes:
                tail = f"{separator}{suffix.strip()}"
                if suffix and result.lower().endswith(tail.lower()):
                    result = result[: -len(tail)].strip()
                    changed = True
    return result.strip(" -|" + _EN_DASH) or title.strip()


def normalize_person_name(name: str) -> str:
    """Chuẩn hoá tên tác giả/họa sĩ: bỏ nhãn còn sót, gộp khoảng trắng."""
    text = _WHITESPACE.sub(" ", str(name)).strip()
    text = re.sub(
        rf"^(tác giả|tac gia|author|họa sĩ|hoa si|artist|nhóm dịch)\s*[:\-{_EN_DASH}]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return text.strip(" ,;/&-")


def is_placeholder_person(name: str) -> bool:
    """`"Đang cập nhật"`, `"N/A"`, `"-"`... không được lưu thành tác giả."""
    return sort_key(normalize_person_name(name)) in _PLACEHOLDER_PEOPLE


def split_people(value: str, separators: Sequence[str] = (",", "&", "/", ";")) -> list[str]:
    """Tách một ô chứa nhiều tên thành danh sách, bỏ placeholder và trùng lặp."""
    parts = [value]
    for separator in separators:
        parts = [piece for part in parts for piece in part.split(separator)]

    people: list[str] = []
    seen: set[str] = set()
    for part in parts:
        person = normalize_person_name(part)
        if not person or is_placeholder_person(person):
            continue
        key = sort_key(person)
        if key not in seen:
            seen.add(key)
            people.append(person)
    return people


def parse_chapter_number(title: str) -> float | None:
    """Rút số chương từ tên chương. Trả None khi chương không có số.

    Ưu tiên số đứng sau từ khoá chương, nên `"Tập 2 - Chương 3"` ra 3 chứ không ra 2.
    `"Oneshot"` và `"Nội dung trực tiếp"` (hai trường hợp thật trên đĩa) ra None.
    """
    text = str(title).strip()
    if not text:
        return None

    matches = _CHAPTER_WORD.findall(text)
    if not matches:
        matches = _BARE_NUMBER.findall(text)
    if not matches:
        return None

    raw = matches[-1].replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def chapter_dir_name(number: float | None, title: str) -> str:
    """Tên thư mục chương, đệm số 0 để sắp đúng cả ngoài app.

    `(10, "Chương 10")` → `"0010 - Chương 10"`; `(9.5, ...)` → `"0009.5 - ..."`.
    Chương không số thì không có tiền tố.
    """
    clean = clean_filename(title)
    if number is None:
        return clean
    whole = int(number)
    if float(number) == whole:
        prefix = f"{whole:04d}"
    else:
        fraction = f"{float(number) - whole:.3f}".rstrip("0").lstrip("0")
        prefix = f"{whole:04d}{fraction}"
    return clean_filename(f"{prefix} - {clean}")
