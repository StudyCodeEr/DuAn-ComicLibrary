"""UDP discovery: điện thoại tìm máy chủ trong LAN mà không phải nhập IP.

Viết bằng asyncio DatagramProtocol, không cần thread riêng như bản cũ.
"""

from __future__ import annotations

import asyncio
import json
import logging

from mangalib import __version__

__all__ = ["PORT", "start", "stop"]

logger = logging.getLogger(__name__)

PORT = 55555
_PROBE = b"DISCOVER_MANGALIB"
_LEGACY_PROBE = b"DISCOVER_MANGA_SERVER"


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, http_port: int) -> None:
        self._http_port = http_port
        self._transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport) -> None:
        self._transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if data.strip() not in (_PROBE, _LEGACY_PROBE) or self._transport is None:
            return
        reply = json.dumps(
            {"app": "mangalib", "version": __version__, "port": self._http_port}
        ).encode("utf-8")
        self._transport.sendto(reply, addr)


async def start(http_port: int = 8000):
    """Mở listener UDP. Trả về transport để đóng khi tắt app."""
    try:
        transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: _Protocol(http_port), local_addr=("0.0.0.0", PORT), reuse_port=False
        )
    except OSError as exc:
        logger.warning("không mở được UDP discovery cổng %d: %s", PORT, exc)
        return None
    logger.info("UDP discovery đang lắng nghe cổng %d", PORT)
    return transport


def stop(transport) -> None:
    if transport is not None:
        transport.close()
