import json
import os
import re
import unicodedata
from DrissionPage import ChromiumPage

CONFIG_FILE = "sites.json"

# Cấu hình mặc định
DEFAULT_SITES = {
    "vihentai": {
        "name": "Việt Hentai",
        "url": "https://example-site.invalid",
        "connector": "mangaconnect"
    },
    "nettruyen": {
        "name": "Việt Hentai (Server Phụ)",
        "url": "https://example-site-2.invalid",
        "connector": "mangaconnect"
    }
}

def load_sites():
    """Đọc file cấu hình"""
    if not os.path.exists(CONFIG_FILE):
        save_sites(DEFAULT_SITES)
        return DEFAULT_SITES
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_SITES

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

def check_and_update_domain(site_key, browser: ChromiumPage):
    """
    Hàm tự động kiểm tra xem Web có đổi Domain (Redirect) không.
    """
    sites = load_sites()
    if site_key not in sites: return None
    
    current_url = sites[site_key]["url"]
    
    try:
        # 1. Truy cập trang
        browser.get(current_url)
        
        # 2. Lấy URL thực tế
        real_url_raw = browser.url
        
        # 3. Làm sạch URL (xóa dấu / ở cuối) để so sánh
        current_clean = current_url.rstrip("/")
        real_clean = real_url_raw.rstrip("/") # [ĐÃ SỬA LỖI]: Định nghĩa biến real_clean ở đây

        # 4. So sánh domain (bỏ qua http/https)
        if current_clean.split("://")[-1] != real_clean.split("://")[-1]:
            print(f"🔄 Phát hiện đổi Domain! {current_clean} -> {real_clean}")
            
            # Cập nhật vào file config
            sites[site_key]["url"] = real_clean
            save_sites(sites)
            return real_clean
            
        return current_clean

    except Exception as e:
        print(f"⚠️ Lỗi check domain: {e}")
        return current_url