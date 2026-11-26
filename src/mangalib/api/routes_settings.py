"""Cài đặt và ghép đôi điện thoại. Chỉ dùng được từ chính máy chủ."""

from __future__ import annotations

import socket
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from mangalib import config, paths
from mangalib.api.deps import require_local
from mangalib.config import AppConfig, CloseAction, ImageFormat
from mangalib.shell import autostart

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
        # SU THAT cua tu khoi dong nam o Registry, khong phai o config: nguoi dung
        # co the bat/tat bang `mangalib app --autostart`, luc do config se lech.
        "autostart": autostart.is_enabled(),
        "close_action": cfg.close_action,
    }


class SettingsIn(BaseModel):
    """Chỉ những trường người dùng sửa được từ giao diện."""

    image_format: ImageFormat | None = None
    library_override: str | None = None
    autostart: bool | None = None
    close_action: CloseAction | None = None

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

    if payload.autostart is not None:
        ok = autostart.enable() if payload.autostart else autostart.disable()
        if not ok:
            raise HTTPException(500, "không ghi được vào Registry để đổi tự khởi động")

    config.save(updated)
    return {
        "image_format": updated.image_format,
        "library_override": updated.library_override,
        "library_dir": str(paths.library_dir()),
        "autostart": autostart.is_enabled(),
        "close_action": updated.close_action,
    }


@router.post("/settings/pick-folder")
def pick_library_folder() -> dict:
    """Mở hộp thoại chọn thư mục của Windows, trả đường dẫn người dùng chọn.

    Router này đã chỉ cho localhost - hộp thoại bật trên chính máy chạy app, nên
    điện thoại trong LAN không gọi được.
    """
    from mangalib.folder_picker import pick_folder

    cfg = config.load()
    return {"path": pick_folder(cfg.library_override or str(paths.library_dir()))}


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
