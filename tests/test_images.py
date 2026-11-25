"""Test đổi định dạng ảnh. Pillow chỉ được dùng trong `download/images.py`."""

from __future__ import annotations

import io

import pytest

from mangalib.download.images import convert, sniff_ext


@pytest.fixture
def anh_png() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGBA", (40, 60), (200, 30, 30, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_original_khong_dong_vao_bytes(anh_png):
    """Mặc định phải giữ nguyên bản gốc, không mã hoá lại."""
    assert convert(anh_png, "original") is None


def test_doi_sang_webp(anh_png):
    data, ext = convert(anh_png, "webp")

    assert ext == "webp"
    assert sniff_ext(data) == "webp"


def test_doi_sang_jpeg_phang_duoc_anh_co_alpha(anh_png):
    """JPEG không có kênh alpha; không phẳng về RGB trước thì Pillow ném lỗi."""
    data, ext = convert(anh_png, "jpeg")

    assert ext == "jpg"
    assert sniff_ext(data) == "jpg"


def test_dinh_dang_la_thi_giu_ban_goc_thay_vi_ne_loi(anh_png):
    assert convert(anh_png, "bmp") is None


def test_du_lieu_hong_thi_giu_ban_goc(anh_png):
    assert convert(b"day khong phai anh", "webp") is None
