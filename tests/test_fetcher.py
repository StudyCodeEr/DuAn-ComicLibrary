"""Test tầng tải ảnh: thử lại lượt hai, và báo đúng trang nào thiếu.

Không chạm mạng: thay `_SessionPool` bằng một bản giả trả về phản hồi dựng sẵn.
"""

from __future__ import annotations

import io

import pytest

from mangalib.download import fetcher


@pytest.fixture
def anh() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (600, 900), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


class _PhanHoi:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


class _SessionGia:
    """Mỗi URL có một hàng kịch bản; gọi lần thứ n thì trả phần tử thứ n."""

    def __init__(self, kich_ban: dict[str, list[_PhanHoi]]) -> None:
        self._kich_ban = kich_ban
        self.so_lan: dict[str, int] = {}

    def get(self, url, **_):
        lan = self.so_lan.get(url, 0)
        self.so_lan[url] = lan + 1
        hang = self._kich_ban[url]
        return hang[min(lan, len(hang) - 1)]


def _cam_pool(monkeypatch, session):
    class PoolGia:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def get(self):
            return session

        def close(self):
            pass

    monkeypatch.setattr(fetcher, "_SessionPool", PoolGia)


def test_thu_lai_luot_hai_cuu_duoc_trang_hong(tmp_path, monkeypatch, anh):
    """Một trang hỏng chớp nhoáng không được làm cả chương bị đánh thiếu ảnh."""
    session = _SessionGia(
        {
            "https://cdn.test/1.png": [_PhanHoi(200, anh)],
            # Hỏng ở lượt đầu, lượt thử lại thì được.
            "https://cdn.test/2.png": [_PhanHoi(500, b""), _PhanHoi(200, anh)],
        }
    )
    _cam_pool(monkeypatch, session)

    outcome = fetcher.download_images(
        ["https://cdn.test/1.png", "https://cdn.test/2.png"],
        tmp_path,
        referer="https://trang.test",
        retries=1,
        min_bytes=100,
    )

    assert outcome.saved == 2
    assert outcome.missing == []
    assert outcome.errors == []


def test_bao_dung_so_trang_con_thieu(tmp_path, monkeypatch, anh):
    """Thiếu thì phải nói THIẾU TRANG NÀO, không chỉ nói thiếu mấy trang."""
    session = _SessionGia(
        {
            "https://cdn.test/1.png": [_PhanHoi(200, anh)],
            "https://cdn.test/2.png": [_PhanHoi(404, b"")],
            "https://cdn.test/3.png": [_PhanHoi(200, anh)],
        }
    )
    _cam_pool(monkeypatch, session)

    outcome = fetcher.download_images(
        [f"https://cdn.test/{n}.png" for n in (1, 2, 3)],
        tmp_path,
        referer="https://trang.test",
        retries=1,
        min_bytes=100,
    )

    assert outcome.saved == 2
    assert outcome.missing == [2]


def test_anh_qua_nho_bi_tu_choi_nhung_khong_tinh_la_trang_thieu(tmp_path, monkeypatch, anh):
    """Spacer 300 byte không phải "trang bị thiếu" — nó chưa bao giờ là trang.

    Gặp thật: hai chương bị đánh `partial` vĩnh viễn chỉ vì một spacer ở cuối.
    """
    session = _SessionGia({"https://cdn.test/1.png": [_PhanHoi(200, anh)]})
    _cam_pool(monkeypatch, session)

    outcome = fetcher.download_images(
        ["https://cdn.test/1.png"],
        tmp_path,
        referer="https://trang.test",
        retries=1,
        min_bytes=10_000_000,
    )

    assert outcome.saved == 0
    assert outcome.rejected == 1
    assert outcome.missing == [], "bị từ chối khác hẳn bị thiếu"
