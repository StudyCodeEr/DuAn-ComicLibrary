"""Tạo ứng dụng FastAPI: API + web UI + UDP discovery.

Lưu ý Windows: KHÔNG đặt WindowsSelectorEventLoopPolicy. Playwright cần subprocess
nên phải dùng Proactor loop (mặc định của Python 3.8+ trên Windows).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mangalib import __version__, config, paths
from mangalib.api import discovery, routes_jobs, routes_library, routes_settings
from mangalib.db import engine
from mangalib.errors import UnsafePathError
from mangalib.jobs.queue import WORKER

__all__ = ["create_app"]

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    paths.ensure_data_dirs()
    engine.init_db()

    cfg = config.ensure_lan_token(config.load())
    if not config.load().lan_token:
        config.save(cfg)
        logger.info("đã tạo token LAN mới")

    WORKER.start()
    discovery_task = await discovery.start()
    try:
        yield
    finally:
        discovery.stop(discovery_task)
        WORKER.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Comic Library", version=__version__, lifespan=_lifespan)
    app.include_router(routes_library.router, prefix="/api/v1")
    app.include_router(routes_jobs.router, prefix="/api/v1")
    app.include_router(routes_settings.router, prefix="/api/v1")

    web_dir = paths.package_dir() / "web"
    if web_dir.is_dir():
        app.mount("/static", StaticFiles(directory=web_dir), name="static")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            """Tab chinh la TAI TRUYEN, khong phai thu vien: mo app ra la de tai."""
            return FileResponse(web_dir / "downloads.html")

        @app.get("/assets/{name}", include_in_schema=False)
        def asset(name: str) -> FileResponse:
            """Anh nen di kem app. safe_join chan duong dan vuot ra ngoai assets/."""
            try:
                target = paths.safe_join(paths.assets_dir(), name)
            except UnsafePathError as exc:
                # Khong de lo ra 500: ".." hay duong dan tuyet doi la 404, khong phai loi server.
                raise HTTPException(404, "tên asset không hợp lệ") from exc
            if not target.is_file():
                raise HTTPException(404, f"khong co asset {name}")
            return FileResponse(target)

        @app.get("/favicon.ico", include_in_schema=False)
        def favicon() -> FileResponse:
            """app_icon.ico la cam ket thuong hieu, khong phai favicon rong."""
            for candidate in (
                paths.app_dir() / "app_icon.ico",
                paths.repo_root() / "app_icon.ico",
            ):
                if candidate.is_file():
                    return FileResponse(candidate, media_type="image/x-icon")
            raise HTTPException(404, "khong tim thay app_icon.ico")

        @app.get("/{page_name}.html", include_in_schema=False)
        def page(page_name: str) -> FileResponse:
            target = paths.safe_join(web_dir, f"{page_name}.html")
            if not target.is_file():
                return FileResponse(web_dir / "index.html")
            return FileResponse(target)

    return app
