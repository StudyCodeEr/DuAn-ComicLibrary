# -*- mode: python ; coding: utf-8 -*-
#
# File spec DUY NHAT, thay cho 12 file .spec gan nhu giong nhau cua ban cu.
# Build: pyinstaller tools/mangalib.spec --noconfirm
#
# --onedir (khong phai onefile): nho vay get_app_dir() tra ve thu muc chua .exe,
# nen data/ nam canh exe thay vi trong thu muc tam _internal.

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("../src/mangalib/web", "mangalib/web"),
    ("../src/mangalib/sites", "mangalib/sites"),
    ("../src/mangalib/db/schema.sql", "mangalib/db"),
    ("../app_icon.ico", "."),
    ("../assets", "assets"),
]
# curl_cffi mang theo libcurl-impersonate; selectolax mang theo lexbor.
datas += collect_data_files("curl_cffi")

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "curl_cffi",
    "selectolax.lexbor",
    "segno",
    "yaml",
    # pystray + PIL: bat buoc, neu thieu thi khay he thong im lang khong hoat dong
    "pystray",
    "pystray._win32",
    "PIL",
    "PIL.Image",
]

a = Analysis(
    ["../src/mangalib/__main__.py"],
    pathex=["../src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["flet", "flet_core", "flet_runtime", "selenium", "tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ComicLibrary",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=["../app_icon.ico"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ComicLibrary",
)
