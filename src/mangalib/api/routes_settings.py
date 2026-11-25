"""Cài đặt và ghép đôi điện thoại. Chỉ dùng được từ chính máy chủ."""

from __future__ import annotations

import socket
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from mangalib import config, paths
from mangalib.api.deps import require_local
from mangalib.config import AppConfig, ImageFormat

router = APIRouter(dependencies=[Depends(require_local)])


def _lan_ips() -> list[str]:
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                ips.add(address)
    except OSError:
        pass
    return sorted(ips)


@router.get("/settings")
def get_settings() -> dict:
    cfg = config.ensure_lan_token(config.load())
    if not config.load().lan_token:
        config.save(cfg)
    return {
        "image_format": cfg.image_format,
        "concurrency": cfg.concurrency,
        "theme": cfg.theme,
        "lan_token": cfg.lan_token,
        "lan_ips": _lan_ips(),
        "data_root": str(paths.data_root()),
        "library_dir": str(paths.library_dir()),
        # Gia tri THO de o nhap hien dung cai nguoi dung da dat, khong phai duong
        # dan da giai ra - neu khong, bo trong se bi ghi de thanh duong dan mac dinh.
        "library_override": cfg.library_override,
    }


class SettingsIn(BaseModel):
    """Chỉ những trường người dùng sửa được từ giao diện."""

    image_format: ImageFormat | None = None
    library_override: str | None = None

    model_config = {"extra": "forbid"}


@router.patch("/settings")
def update_settings(payload: SettingsIn) -> dict:
    """Ghi cấu hình. Router này đã chỉ cho localhost nên máy khác không sửa được."""
    data = config.load().model_dump()
    data.update(payload.model_dump(exclude_none=True))
    updated = AppConfig(**data)

    if updated.library_override:
        folder = Path(updated.library_override).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise HTTPException(400, f"không dùng được thư mục này: {exc}") from exc

    config.save(updated)
    return {
        "image_format": updated.image_format,
        "library_override": updated.library_override,
        "library_dir": str(paths.library_dir()),
    }


@router.get("/settings/qr.svg")
def pairing_qr(port: int = 8000) -> Response:
    """Mã QR để điện thoại quét một lần là ghép đôi xong."""
    import segno

    cfg = config.ensure_lan_token(config.load())
    host = (_lan_ips() or ["127.0.0.1"])[0]
    url = f"http://{host}:{port}/api/v1/pair?token={cfg.lan_token}"
    qr = segno.make(url, error="m")
    buffer: list[str] = []
    qr.save(buffer_writer := __import__("io").BytesIO(), kind="svg", scale=5, dark="#0f172a")
    del buffer
    return Response(buffer_writer.getvalue(), media_type="image/svg+xml")
