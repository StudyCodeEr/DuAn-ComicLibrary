import json
import os
import re
import unicodedata

from mangalib import paths

CONFIG_FILE = str(paths.repo_root() / "sites.json")
# File mẫu (template) được commit vào repo, KHÔNG chứa địa chỉ thật.
# File cấu hình thật (sites.json) là file local, đã được .gitignore bỏ qua.
EXAMPLE_FILE = str(paths.repo_root() / "sites.example.json")


def _load_example_sites():
    """Đọc danh sách nguồn mẫu từ sites.example.json (nếu có)."""
    if os.path.exists(EXAMPLE_FILE):
        try:
            with open(EXAMPLE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Không đọc được {EXAMPLE_FILE}: {e}")
    return {}


def load_sites():
    """Đọc file cấu hình"""
    if not os.path.exists(CONFIG_FILE):
        # Lần đầu chạy: tạo sites.json từ file mẫu.
        # Người dùng tự nhập/cập nhật link thật trong app.
        defaults = _load_example_sites()
        save_sites(defaults)
        return defaults
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Lỗi đọc {CONFIG_FILE}: {e}")
        return _load_example_sites()

def save_sites(data):
    """Lưu cấu hình"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_site_url(site_key, new_url):
    """Cập nhật URL cho site đã có"""
    sites = load_sites()
    if site_key in sites:
        sites[site_key]["url"] = new_url.rstrip("/")
        save_sites(sites)
        return True, f"Đã cập nhật link cho {sites[site_key]['name']}"
    return False, "Không tìm thấy nguồn này!"

def add_new_site(name, url):
    """Thêm nguồn truyện mới"""
    sites = load_sites()
    
    # Hàm tạo slug (ID) từ tên hiển thị
    def slugify(value):
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        return re.sub(r'[-\s]+', '', value).strip()

    key = slugify(name)
    # Nếu tạo key bị rỗng (do tên toàn ký tự đặc biệt) thì tạo key ngẫu nhiên
    if not key: 
        key = "custom_site_" + str(len(sites))

    if key in sites:
        return False, "Tên nguồn này đã tồn tại!"

    # Mặc định dùng connector chung 'mangaconnect'
    sites[key] = {
        "name": name,
        "url": url.rstrip("/"),
        "connector": "mangaconnect" 
    }
    save_sites(sites)
    return True, f"Đã thêm nguồn mới: {name}"
