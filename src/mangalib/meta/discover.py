"""Suy ra cách đọc một trang lạ, khi không có file rule `.yml` nào khớp domain.

Vì sao cần: rule YAML viết tay là thứ CHẶN người dùng — cài xong mà chưa có file
nào thì dán link nào cũng báo "không có rule khớp". Module này đảo lại vai trò của
rule: rule trở thành thứ *tăng tốc và sửa sai*, không còn là điều kiện bắt buộc.

Ba tầng tín hiệu, xếp theo độ bền, dùng cái nào ra trước thì dừng:

1. **Metadata chuẩn** (`og:title`, `og:image`, JSON-LD). Site khác nhau rất xa về
   HTML nhưng gần như site nào cũng có thẻ `og:` vì cần hiển thị đẹp khi chia sẻ.
2. **Cấu trúc lặp lại**, không phải tên class. Danh sách chương là một cụm link
   cùng tiền tố đường dẫn, số lượng lớn, phần lớn text có con số. Tên class đổi
   theo theme, còn hình dạng này thì không.
3. **Từ khoá trong text link**, đa ngôn ngữ, chỉ dùng để phá hoà — nó phụ thuộc
   ngôn ngữ nên không bao giờ được là tín hiệu chính.
"""

from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urljoin, urlsplit

from mangalib import naming
from mangalib.meta.models import ChapterRef
from mangalib.meta.rules import (
    ChaptersRule,
    FieldRule,
    FiltersRule,
    PagesRule,
    SiteRule,
    rule_for_url,
)

__all__ = ["default_rule", "discover_chapters", "looks_like_chapter", "rule_for"]

# Tu khoa cho "nut doc truyen hoac tuong duong". `link_text_any` so khop chuoi
# thuong TRUC TIEP, khong bo dau - nen phai liet ke dung dang co dau.
READ_WORDS = [
    "đọc truyện",
    "đọc từ đầu",
    "đọc ngay",
    "đọc tiếp",
    "bắt đầu đọc",
    "xem truyện",
    "read now",
    "start reading",
    "read first",
    "first chapter",
    "chương 1",
    "chapter 1",
    "tập 1",
]

# Link dieu huong chung cua site, khong bao gio la chuong truyen.
_NAV_WORDS = {
    "trang chu", "home", "dang nhap", "login", "dang ky", "register", "lien he",
    "contact", "gioi thieu", "about", "dieu khoan", "terms", "bao loi", "report",
    "the loai", "genre", "tag", "tac gia", "author", "tim kiem", "search",
    "bang xep hang", "ranking", "lich su", "history", "theo doi", "follow",
}

_NUMBER_IN_TEXT = re.compile(r"\d")

# Khoi thong tin truyen. Khong site nao giong site nao nen liet ke cac ten pho bien;
# khong khop cai nao thi nguon ke tiep se quet ca trang.
_INFO_SCOPE = "main, article, [class*='info'], [id*='info']"
_TAG_SELECTOR = (
    "a[href*='/the-loai/'], a[href*='/genre/'], a[href*='/tag/'], a[href*='/category/']"
)
_AUTHOR_SELECTOR = "a[href*='/tac-gia/'], a[href*='/author/'], a[href*='/artist/']"


def looks_like_chapter(title: str, url: str) -> bool:
    """Text hoặc URL có dáng một chương: có số, và không phải link điều hướng."""
    key = naming.sort_key(title)
    if key in _NAV_WORDS:
        return False
    if naming.parse_chapter_number(title) is not None:
        return True
    # Nhieu site dat text la ten chuong khong co so ("Ngoai truyen"), nhung URL
    # thi gan nhu luon co so hoac slug rieng cho tung chuong.
    return bool(_NUMBER_IN_TEXT.search(urlsplit(url).path.rsplit("/", 1)[-1]))


def _same_site(a: str, b: str) -> bool:
    ha, hb = urlsplit(a).hostname or "", urlsplit(b).hostname or ""
    return ha.removeprefix("www.") == hb.removeprefix("www.")


def _links(tree, base_url: str) -> list[tuple[str, str]]:
    """Link cùng site, mỗi URL một lần.

    Cùng một chương thường được trỏ tới hai lần: một nút ("Đọc từ đầu", "Đọc Chap
    Mới") và một dòng trong danh sách ("Chương 2"). Giữ cái gặp trước sẽ lấy phải
    tên nút - mất số chương. Nên khi trùng URL thì ưu tiên tên CÓ số.
    """
    best: dict[str, str] = {}
    for node in tree.css("a[href]"):
        href = (node.attributes.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        url = urljoin(base_url, href).split("#")[0]
        if not _same_site(url, base_url):
            continue
        title = " ".join(node.text().split())
        cu = best.get(url)
        if cu is None or (
            naming.parse_chapter_number(cu) is None
            and naming.parse_chapter_number(title) is not None
        ):
            best[url] = title
    return [(title, url) for url, title in best.items()]


def discover_chapters(tree, base_url: str) -> list[ChapterRef]:
    """Tìm danh sách chương bằng hình dạng của trang, không dựa vào tên class.

    Gom link theo thư mục cha rồi chấm điểm từng cụm. Cụm thắng là cụm vừa đông
    vừa có tỉ lệ link "có dáng chương" cao — một menu thể loại cũng đông nhưng
    text của nó không có số, nên nó thua.
    """
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for title, url in _links(tree, base_url):
        parent = urlsplit(url).path.rsplit("/", 1)[0]
        groups[parent].append((title, url))

    # Menu the loai cung dong va text cung co so ("Action 1200") nen cham diem
    # thuan tuy se chon nham - dung con bug 645 link cua ban cu. Dau hieu chac
    # chan: chuong nam DUOI duong dan cua chinh trang dang xem, menu thi khong.
    page_path = urlsplit(base_url).path.rstrip("/")

    noi_dai = [
        m
        for m in _links(tree, base_url)
        if urlsplit(m[1]).path.rstrip("/") != page_path
        and urlsplit(m[1]).path.startswith(page_path)
        and looks_like_chapter(*m)
    ]
    if len(noi_dai) >= 2:
        return _sap_xep(noi_dai)

    def duoi_trang_nay(parent: str) -> bool:
        return parent == page_path or parent.startswith(f"{page_path}/") or (
            bool(parent) and page_path.startswith(f"{parent}/")
        )

    scoped = {k: v for k, v in groups.items() if duoi_trang_nay(k)}
    candidates = scoped or groups

    best: list[tuple[str, str]] = []
    best_score = 0.0
    for members in candidates.values():
        if len(members) < 2:
            continue
        hits = [m for m in members if looks_like_chapter(*m)]
        if not hits:
            continue
        # Ti le quyet dinh cum co phai danh sach chuong khong; so luong chi pha hoa.
        score = (len(hits) / len(members)) * 100 + len(hits)
        if score > best_score:
            best_score, best = score, hits

    return _sap_xep(best)


def _sap_xep(members: list[tuple[str, str]]) -> list[ChapterRef]:
    refs = [
        ChapterRef(
            title=title or url.rstrip("/").rsplit("/", 1)[-1],
            url=url,
            number=naming.parse_chapter_number(title),
        )
        for title, url in members
    ]
    refs.sort(key=lambda c: (c.number is None, c.number or 0.0, c.title))
    return refs


def rule_for(url: str) -> SiteRule:
    """Rule cho URL này: file `.yml` nếu có, không thì suy ra từ chính trang.

    Mọi nơi cần rule phải đi qua đây. Trước đó `pipeline` và `cli probe` mỗi chỗ
    tự gọi `rule_for_url` rồi tự xử lý None, nên vá một chỗ là sót chỗ kia.
    """
    return rule_for_url(url) or default_rule(url)


def default_rule(url: str) -> SiteRule:
    """Rule suy ra từ quy ước chung của web, dùng khi không có `.yml` nào khớp.

    Chỉ dùng các handler `parse.py` đã có, nên không thêm đường chạy mới — vẫn là
    `GenericSource` chạy, chỉ khác bộ chọn.
    """
    host = (urlsplit(url).hostname or "unknown").removeprefix("www.")
    return SiteRule(
        key=f"auto:{host}",
        name=host,
        domains=[host],
        failover=False,
        auto_discover=True,
        title=FieldRule.model_validate(
            {
                # h1 TRUOC og:title: og:title thuong dinh duoi SEO ("- Doc Online",
                # "| Ten Site") con h1 la ten sach se cua chinh trang do.
                "from": [{"css": "h1"}, {"meta": "og:title"}, {"page_title": True}]
            }
        ),
        cover=FieldRule.model_validate(
            {
                "from": [
                    {"meta": "og:image"},
                    {"css_attr": {"sel": "article img, .detail img, main img", "attr": "src"}},
                ]
            }
        ),
        author=FieldRule.model_validate(
            {
                "from": [
                    {"css": _AUTHOR_SELECTOR, "within": _INFO_SCOPE},
                    {"css": _AUTHOR_SELECTOR},
                    {
                        "labeled_links": {
                            "label_any": ["Tác giả", "Author", "Họa sĩ", "Artist", "Nhóm dịch"]
                        }
                    },
                ],
                "deny": ["Đang cập nhật", "N/A", "-", "Updating"],
                "strip_trailing_count": True,
            }
        ),
        tags=FieldRule.model_validate(
            {
                # Nguon KHOANH VUNG dung truoc, toan trang dung sau. Menu header cua
                # site thuong chua hang tram link the loai; quet ca trang la hut het
                # ve lam the - dung con bug 645 link cua ban cu. `_scoped` tra rong
                # khi khong khop nen site khong co <main> van roi xuong nguon sau.
                # KHONG co nguon quet ca trang: nhieu site co dam may tag toan site
                # (truyenggvn.com co 53 the loai trong mot khoi chung). Tha khong co
                # the loai con hon gan sai 53 cai.
                "from": [{"css": _TAG_SELECTOR, "within": _INFO_SCOPE}],
                "strip_trailing_count": True,
                "max_len": 40,
            }
        ),
        read_entry=FieldRule.model_validate({"from": [{"link_text_any": READ_WORDS}]}),
        chapters=ChaptersRule.model_validate(
            {"from": [{"select_options": "select"}], "order": "ascending_by_number"}
        ),
        # Nguong 20KB mac dinh loai nham trang that: webtoon cat thanh lat dai,
        # lat mau phang chi vai KB. Tang loc that su la `min_width` (do ngay trong
        # browser) va magic byte; nguong byte chi con de chan pixel theo doi va
        # phan hoi bi cat ngang.
        filters=FiltersRule.model_validate({"min_bytes": 1_000}),
        pages=PagesRule.model_validate(
            {
                "strategy": ["browser"],
                "image_selector": "img",
                # Tran cuon mac dinh 30s la qua ngan cho chuong dai: do thu mot
                # chuong 37 trang thi dung o 33 trang vi het gio, bi danh partial.
                # 120s la gia tri da chay on tren rule viet tay.
                "scroll": {"idle_ms": 900, "max_ms": 120_000, "step_px": 1_600},
            }
        ),
    )
