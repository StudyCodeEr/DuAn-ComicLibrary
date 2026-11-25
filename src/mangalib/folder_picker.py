"""Hộp thoại chọn thư mục của Windows.

Vì sao không dùng `tkinter.filedialog`: file spec đóng gói cố ý loại `tkinter` ra,
và kéo nó vào chỉ để hiện một hộp thoại thì tốn vài MB cùng một bộ DLL nữa. Vì sao
không dùng `window.showDirectoryPicker()` của trình duyệt: nó trả về handle chứ
KHÔNG trả về đường dẫn thật, đúng thứ ta cần để ghi vào config.

Nên gọi PowerShell - thứ Windows nào cũng có sẵn, 0 byte thêm vào gói.

Đặt ở module lá chứ không trong `shell/`: import bất cứ thứ gì trong `shell/` sẽ
chạy `shell/__init__.py`, kéo luôn `pystray` và `PIL` vào tiến trình server chỉ
để hiện một hộp thoại.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys

__all__ = ["pick_folder"]

logger = logging.getLogger(__name__)

# -STA bat buoc: hop thoai WinForms khong chay duoc o che do MTA.
_SCRIPT = """
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = 'Chon thu muc luu truyen'
$d.ShowNewFolderButton = $true
if ($env:MLIB_START -and (Test-Path $env:MLIB_START)) { $d.SelectedPath = $env:MLIB_START }
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }
"""


def pick_folder(start: str = "", *, timeout: int = 300) -> str | None:
    """Mở hộp thoại chọn thư mục. Trả None nếu người dùng bấm Huỷ hoặc không mở được.

    Chặn luồng gọi cho tới khi người dùng đóng hộp thoại. Route gọi nó là route
    đồng bộ nên FastAPI chạy trong threadpool, không chặn server.
    """
    if not sys.platform.startswith("win"):
        return None
    try:
        # Lệnh cố định, tham số truyền qua biến môi trường chứ không nối chuỗi.
        done = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-STA", "-Command", _SCRIPT],
            capture_output=True,
            text=True,
            timeout=timeout,
            # Duong dan khoi dau di qua BIEN MOI TRUONG, khong noi vao script:
            # noi chuoi se cho phep dau nhay dong script PowerShell.
            env={"MLIB_START": start, "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("không mở được hộp thoại chọn thư mục: %s", exc)
        return None

    chosen = done.stdout.strip()
    return chosen or None
