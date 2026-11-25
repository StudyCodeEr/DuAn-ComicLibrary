"""Test tầng API.

Trước commit này repo **không có** test nào chạm tầng API. File này chỉ phủ đúng
những nhánh vừa thêm, không phủ toàn bộ route — phần còn lại vẫn là nợ test.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mangalib import paths
from mangalib.api.app import create_app
from mangalib.db import engine, job_repo
from mangalib.jobs.queue import WORKER


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Client gắn vào DB trong tmp_path, không chạm dữ liệu thật.

    `client=("127.0.0.1", ...)`: `require_lan_token` miễn token cho localhost, còn
    TestClient mặc định gửi host `"testclient"` nên mọi request sẽ bị 401.

    KHÔNG dùng `with TestClient(...)`: vào context sẽ chạy lifespan, tức bật thread
    tải và mở UDP 55555 — test không cần, mà lại dễ vướng cổng đang bị chiếm.
    """
    monkeypatch.setenv(paths.ENV_DATA_ROOT, str(tmp_path))
    paths.ensure_data_dirs()
    engine.init_db()
    return TestClient(create_app(), client=("127.0.0.1", 5000))


def test_trang_chinh_la_tai_truyen(client):
    """Mở app ra là để tải, nên `/` phải trả trang tải chứ không phải thư viện."""
    response = client.get("/")
    assert response.status_code == 200
    assert 'class="downloads"' in response.text


def test_anh_nen_serve_duoc(client):
    response = client.get("/assets/bg-dark.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_asset_duong_dan_tuyet_doi_tra_404_khong_phai_500(client):
    """Tên asset không hợp lệ là 404, không được lộ ra lỗi 500 của server."""
    assert client.get("/assets/C:%5CWindows%5Cwin.ini").status_code == 404


def test_asset_khong_ton_tai_tra_404(client):
    assert client.get("/assets/khong-co-that.jpg").status_code == 404


def test_dan_lai_link_dang_trong_hang_doi_bi_tu_choi(client):
    """Dán cùng một link nhiều lần không được tạo thành nhiều việc trùng nhau."""
    url = "https://example.invalid/truyen/abc"
    with engine.write() as conn:
        job_repo.create(conn, url)

    response = client.post("/api/v1/jobs", json={"url": url})

    assert response.status_code == 409
    assert "hàng đợi" in response.json()["detail"]


def test_link_khac_van_duoc_nhan(client, monkeypatch):
    """Chống trùng không được chặn oan link khác."""
    # WORKER.submit() gọi start(), tức bật thread tải thật. Test không được đi ra mạng.
    monkeypatch.setattr(WORKER, "start", lambda: None)
    with engine.write() as conn:
        job_repo.create(conn, "https://example.invalid/truyen/abc")

    response = client.post(
        "/api/v1/jobs", json={"url": "https://example.invalid/truyen/xyz"}
    )

    assert response.status_code == 202


def test_luu_duoc_dinh_dang_anh_va_duong_dan_thu_vien(client, tmp_path):
    """Hai cấu hình này trước đây chỉ hiển thị, không sửa được và cũng không có tác dụng."""
    kho = tmp_path / "kho-truyen"

    response = client.patch(
        "/api/v1/settings",
        json={"image_format": "webp", "library_override": str(kho)},
    )

    assert response.status_code == 200
    assert response.json()["image_format"] == "webp"
    assert kho.is_dir(), "endpoint phải tạo sẵn thư mục người dùng chọn"
    # Đổi cấu hình phải đổi thật nơi truyện được lưu, không chỉ đổi con số hiển thị.
    assert paths.library_dir() == kho.resolve()


def test_bo_trong_duong_dan_thi_quay_ve_mac_dinh(client, tmp_path):
    client.patch("/api/v1/settings", json={"library_override": str(tmp_path / "kho")})
    client.patch("/api/v1/settings", json={"library_override": ""})

    assert paths.library_dir() == paths.data_root() / "library"


def test_dinh_dang_anh_khong_hop_le_bi_tu_choi(client):
    assert client.patch("/api/v1/settings", json={"image_format": "bmp"}).status_code == 422
