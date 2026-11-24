import os
import sqlite3
import socket
import threading
import uvicorn
import queue  # <--- [THÊM] Thư viện hàng đợi
from urllib.parse import quote
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- [THÊM] HÀNG ĐỢI LỆNH TOÀN CỤC ---
download_queue = queue.Queue() 

app = FastAPI()

# Duong dan do mangalib.paths quyet dinh - khong phu thuoc cwd (quy tac R1).
from mangalib import paths

BASE_DIR = str(paths.data_root())
DOWNLOAD_DIR = str(paths.library_dir())
DB_PATH = str(paths.db_path())

# Tao thu muc o day la I/O luc import (vi pham R2), nhung StaticFiles ben duoi
# doi thu muc phai ton tai. Phase 4 thay ca file nay bang api/ nen chi giu tam.
paths.ensure_data_dirs()

# Mount thư mục ảnh để điện thoại có thể truy cập qua URL (http://ip:8000/images/...)
app.mount("/images", StaticFiles(directory=DOWNLOAD_DIR), name="images")


# --- 1. API: LẤY THƯ VIỆN (KÈM TAGS) ---
@app.get("/library")
def get_library():
    try:
        if not os.path.exists(DB_PATH):
            return []

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # SQL: Lấy Title, Cover và gộp danh sách Tags thành chuỗi
        query = """
            SELECT 
                m.title, 
                m.cover_path, 
                GROUP_CONCAT(t.name, ',') as tags
            FROM manga m
            LEFT JOIN manga_tags mt ON m.id = mt.manga_id
            LEFT JOIN tags t ON mt.tag_id = t.id
            GROUP BY m.id
            ORDER BY m.created_at DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            title = row[0]
            cover_path = row[1]
            tags_string = row[2] # Ví dụ: "Action,Adventure" hoặc None
            
            # Xử lý ảnh bìa
            if cover_path:
                manga_folder = os.path.basename(os.path.dirname(cover_path))
                cover_url = f"/images/{quote(manga_folder)}/cover.jpg"
            else:
                cover_url = ""

            # Xử lý Tags: "Tag1,Tag2" -> ["Tag1", "Tag2"]
            tag_list = []
            if tags_string:
                tag_list = tags_string.split(",")
            
            results.append({
                "title": title, 
                "cover": cover_url,
                "tags": tag_list # Gửi danh sách tag cho điện thoại lọc
            })
            
        return results

    except Exception as e:
        print(f"❌ Lỗi Server (Library): {e}")
        return []


# --- 2. API: LẤY DANH SÁCH CHAPTER VÀ ẢNH ---
@app.get("/manga/{manga_name}")
def get_chapters(manga_name: str):
    try:
        # Giải mã tên folder (vì URL gửi lên có thể đã được encode)
        # Lưu ý: FastAPI thường tự decode path param, nhưng cẩn thận vẫn hơn
        manga_path = os.path.join(DOWNLOAD_DIR, manga_name)
        
        chapters = []
        if os.path.exists(manga_path):
            # Duyệt các thư mục con (Chapter)
            for item in sorted(os.listdir(manga_path)):
                path = os.path.join(manga_path, item)
                if os.path.isdir(path):
                    images = []
                    # Duyệt các file ảnh trong Chapter
                    for img in sorted(os.listdir(path)):
                        if img.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            # Tạo URL ảnh
                            images.append(f"/images/{quote(manga_name)}/{quote(item)}/{quote(img)}")
                    
                    if images:
                        chapters.append({"name": item, "images": images})
        return chapters
    except Exception as e:
        print(f"❌ Lỗi Server (Chapters): {e}")
        return []


# --- 3. API: NHẬN LỆNH TẢI (CHẠY NGẦM) ---
# --- 4. SỬA API DOWNLOAD (QUAN TRỌNG) ---

class DownloadRequest(BaseModel):
    url: str

# Hàm này không tải nữa, mà chỉ chuyển thư
def run_download_task(url: str):
    print(f"🚀 [Server] Nhận lệnh từ điện thoại: {url}")
    # Đẩy link vào hàng đợi
    download_queue.put(url)
    print(f"✅ [Server] Đã chuyển lệnh sang bộ xử lý chính.")

@app.post("/download")
async def trigger_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    print(f"📡 API NHẬN: {req.url}")
    background_tasks.add_task(run_download_task, req.url)
    return {"status": "ok", "message": "Đã nhận lệnh", "url": req.url}

# --- 5. UDP DISCOVERY (Đã fix lỗi 10048) ---
def run_discovery_listener():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Fix lỗi chiếm cổng
    try:
        udp_socket.bind(('', 55555))
        print("📡 UDP Discovery đang chạy...")
        while True:
            data, addr = udp_socket.recvfrom(1024)
            if data.decode('utf-8') == "DISCOVER_MANGA_SERVER":
                udp_socket.sendto("I_AM_MANGA_SERVER".encode('utf-8'), addr)
    except Exception as e:
        print(f"⚠️ UDP Info: {e}")
    finally:
        udp_socket.close()

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=run_discovery_listener, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)