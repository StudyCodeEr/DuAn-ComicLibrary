"""Cấu hình người dùng, đọc/ghi `data/config.toml`.

Bản cũ có **hai** bản logic đọc config độc lập (`gui/app_layout.py:53-62` và
`main.py:160-165`), cả hai dùng đường dẫn tương đối, và cả hai nuốt lỗi JSON hỏng
rồi âm thầm quay về `"Downloads"` — nên truyện tải vào sai chỗ không dấu vết.

Ở đây chỉ còn một đường: `load()` / `save()`, đường dẫn do `paths.config_path()`
quyết định, và file hỏng thì nêu `ConfigError` chứ không im lặng.
"""

from __future__ import annotations

import secrets
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from mangalib import paths
from mangalib.errors import ConfigError

__all__ = ["AppConfig", "ensure_lan_token", "load", "save"]

ImageFormat = Literal["original", "jpeg", "png", "webp"]


class AppConfig(BaseModel):
    """Chỉ những thứ người dùng thật sự đổi được. Mặc định phải dùng được ngay."""

    image_format: ImageFormat = "original"
    """`original` giữ nguyên bytes gốc. Bản cũ mặc định PNG nên re-encode mọi ảnh,
    làm file lớn gấp 3-5 lần và reader qua LAN bị lag."""

    concurrency: int = Field(default=5, ge=1, le=16)
    """Số ảnh tải song song cho mỗi host. Bản cũ tải tuần tự từng ảnh."""

    min_delay_ms: int = Field(default=50, ge=0, le=5_000)
    library_override: str = ""
    """Thư mục lưu truyện do người dùng tự chọn. Rỗng = dùng paths.library_dir()."""

    lan_token: str = ""
    autostart: bool = False
    theme: Literal["dark", "light"] = "dark"

    model_config = {"extra": "forbid"}


def load(path: Path | None = None) -> AppConfig:
    """Đọc config. File chưa có thì trả mặc định và **không** ghi gì ra đĩa."""
    config_file = Path(path) if path is not None else paths.config_path()
    if not config_file.exists():
        return AppConfig()

    try:
        raw = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as exc:
        raise ConfigError(f"không đọc được {config_file}: {exc}") from exc

    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{config_file} có giá trị không hợp lệ: {exc}") from exc


def save(config: AppConfig, path: Path | None = None) -> Path:
    """Ghi config dạng TOML phẳng, ghi nguyên tử qua file `.tmp`."""
    config_file = Path(path) if path is not None else paths.config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Cấu hình Comic Library. File này KHÔNG được commit.", ""]
    for key, value in config.model_dump().items():
        lines.append(f"{key} = {_toml_value(value)}")

    temp_file = config_file.with_suffix(config_file.suffix + ".tmp")
    temp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temp_file.replace(config_file)
    return config_file


def ensure_lan_token(config: AppConfig) -> AppConfig:
    """Sinh token LAN lần đầu. Request từ 127.0.0.1 được miễn token."""
    if config.lan_token:
        return config
    return config.model_copy(update={"lan_token": secrets.token_urlsafe(24)})


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise ConfigError(f"kiểu dữ liệu không ghi được ra TOML: {type(value)!r}")
