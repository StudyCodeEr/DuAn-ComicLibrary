import os
import socket
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# 1. CẤU HÌNH THƯ MỤC
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Downloads")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Mount thư mục ảnh để điện thoại tải được
app.mount("/images", StaticFiles(directory=DOWNLOAD_DIR), name="images")

# 2. API LIBRARY
@app.get("/library")
def get_library():
    mangas = []
    if os.path.exists(DOWNLOAD_DIR):
        for item in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, item)
            if os.path.isdir(path):
                cover_path = os.path.join(path, "cover.jpg")
                if os.path.exists(cover_path):
                    cover_url = f"/images/{item}/cover.jpg"
                    mangas.append({"title": item, "cover": cover_url})
    return mangas

# 3. API CHAPTERS
@app.get("/manga/{manga_name}")
def get_chapters(manga_name: str):
    manga_path = os.path.join(DOWNLOAD_DIR, manga_name)
    chapters = []
    if os.path.exists(manga_path):
        for item in sorted(os.listdir(manga_path)):
            path = os.path.join(manga_path, item)
            if os.path.isdir(path):
                images = []
                for img in sorted(os.listdir(path)):
                    if img.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        images.append(f"/images/{manga_name}/{item}/{img}")
                if images:
                    chapters.append({"name": item, "images": images})
    return chapters

# 4. API DOWNLOAD
class DownloadRequest(BaseModel):
    url: str

@app.post("/download")
def trigger_download(req: DownloadRequest):
    print(f"📡 NHẬN LỆNH TỪ ĐIỆN THOẠI: {req.url}")
    return {"status": "Đã nhận", "url": req.url}

# 5. UDP DISCOVERY
def run_discovery_listener():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_socket.bind(('', 55555))
        print("✅ Server sẵn sàng kết nối điện thoại.")
        while True:
            data, addr = udp_socket.recvfrom(1024)
            if data.decode('utf-8') == "DISCOVER_MANGA_SERVER":
                udp_socket.sendto("I_AM_MANGA_SERVER".encode('utf-8'), addr)
    except Exception as e:
        print(f"⚠️ Lỗi Discovery: {e}")