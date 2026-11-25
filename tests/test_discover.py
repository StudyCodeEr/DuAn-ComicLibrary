"""Test suy ra danh sách chương từ trang lạ, không cần file rule `.yml`."""

from __future__ import annotations

from mangalib.meta import parse
from mangalib.meta.discover import default_rule, discover_chapters, looks_like_chapter

TRANG = """
<html><body>
  <header>
    <a href="/">Trang chủ</a>
    <a href="/the-loai/action">Action 1200</a>
    <a href="/the-loai/romance">Romance 980</a>
    <a href="/the-loai/comedy">Comedy 777</a>
    <a href="/the-loai/drama">Drama 654</a>
    <a href="/the-loai/school">School Life 432</a>
  </header>
  <main>
    <a href="/truyen/abc/chuong-1">Chương 1</a>
    <a href="/truyen/abc/chuong-10">Chương 10</a>
    <a href="/truyen/abc/chuong-2">Chương 2</a>
  </main>
</body></html>
"""


def _chuong(html: str, base: str):
    return discover_chapters(parse.parse_html(html), base)


def test_bo_qua_menu_the_loai_du_no_dong_hon():
    """Menu thể loại cũng có số trong text và còn đông hơn danh sách chương.

    Đây đúng là con bug của bản cũ: quét cả trang thì hút về hàng trăm link thể
    loại. Dấu hiệu phân biệt là chương nằm dưới đường dẫn của chính trang này.
    """
    chuong = _chuong(TRANG, "https://site.test/truyen/abc")

    assert [c.title for c in chuong] == ["Chương 1", "Chương 2", "Chương 10"]


def test_sap_theo_so_khong_theo_chu():
    """Sắp theo tên thì chương 10 đứng trước chương 2."""
    chuong = _chuong(TRANG, "https://site.test/truyen/abc")

    assert [c.number for c in chuong] == [1.0, 2.0, 10.0]


def test_tim_duoc_ca_khi_dang_dung_o_trang_doc():
    """Trang đọc nằm sâu hơn một cấp, chương vẫn phải nhận ra được."""
    chuong = _chuong(TRANG, "https://site.test/truyen/abc/chuong-1")

    assert len(chuong) == 3


def test_bo_link_sang_site_khac():
    html = """<html><body><main>
      <a href="https://quang-cao.test/a/1">Chương 1</a>
      <a href="https://quang-cao.test/a/2">Chương 2</a>
    </main></body></html>"""

    assert _chuong(html, "https://site.test/truyen/abc") == []


def test_trang_khong_phai_truyen_thi_tra_rong_chu_khong_no():
    """Không suy ra được thì trả rỗng; phía trên sẽ duyệt chính trang đã dán."""
    html = "<html><body><p>Chỉ là một bài viết.</p><a href='/lien-he'>Liên hệ</a></body></html>"

    assert _chuong(html, "https://site.test/bai-viet") == []


def test_looks_like_chapter_tu_choi_link_dieu_huong():
    assert looks_like_chapter("Chương 7", "/truyen/abc/chuong-7")
    assert not looks_like_chapter("Trang chủ", "/")
    assert not looks_like_chapter("Đăng nhập", "/login")


def test_default_rule_bat_che_do_tu_suy():
    rule = default_rule("https://www.site.test/truyen/abc")

    assert rule.auto_discover
    assert rule.domains == ["site.test"], "bỏ www. để khớp domain cho đúng"
    assert rule.failover is False, "domain suy ra chỉ có một, không có gì để thử thay"


TRANG_NOI_DAI = """
<html><body>
  <a href="/truyen-tranh/abc-25756-chap-2.html">Đọc từ đầu</a>
  <a href="/truyen-tranh/abc-25756-chap-11.html">Đọc Chap Mới</a>
  <a href="/truyen-tranh/truyen-khac-999">Truyện khác 999</a>
  <main>
    <a href="/truyen-tranh/abc-25756-chap-11.html">Chương 11</a>
    <a href="/truyen-tranh/abc-25756-chap-3.html">Chương 3</a>
    <a href="/truyen-tranh/abc-25756-chap-2.html">Chương 2</a>
  </main>
</body></html>
"""
GOC = "https://site.test/truyen-tranh/abc-25756"


def test_uu_tien_ten_co_so_khi_hai_link_cung_mot_url():
    """Nút "Đọc từ đầu" và dòng "Chương 2" cùng trỏ một URL.

    Giữ cái gặp trước sẽ lấy tên nút và mất số chương — chương đó tụt xuống cuối.
    """
    chuong = _chuong(TRANG_NOI_DAI, GOC)

    assert [c.number for c in chuong] == [2.0, 3.0, 11.0]


def test_bo_truyen_khac_nam_cung_thu_muc():
    """`/truyen-tranh/` chứa cả chương lẫn truyện khác.

    Chương nối dài đường dẫn của chính trang này, truyện khác thì không.
    """
    chuong = _chuong(TRANG_NOI_DAI, GOC)

    assert all("abc-25756" in c.url for c in chuong)
    assert not any("truyen-khac" in c.url for c in chuong)
