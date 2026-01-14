import json
import os
from DrissionPage import ChromiumPage

CONFIG_FILE = "sites.json"

def load_sites():
    """Đọc file cấu hình"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_sites(data):
    """Lưu cấu hình mới"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_and_update_domain(site_key, browser: ChromiumPage):
    """
    Truy cập domain cũ, xem có bị redirect sang domain mới không.
    Nếu có -> Cập nhật JSON ngay lập tức.
    """
    sites = load_sites()
    if site_key not in sites:
        return None

    current_url = sites[site_key]["url"]
    print(f"📡 Đang kiểm tra domain: {current_url}")

    try:
        # Truy cập trang chủ
        browser.get(current_url)
        
        # Lấy URL thực tế sau khi load xong
        real_url = browser.url
        
        # Chuẩn hóa URL (bỏ dấu / ở cuối nếu có)
        current_clean = current_url.rstrip("/")
        real_clean = real_url.rstrip("/")

        # So sánh: Nếu domain khác nhau => Đã bị Redirect
        if current_clean not in real_clean:
            print(f"🔄 Phát hiện đổi Domain! {current_clean} -> {real_clean}")
            
            # Cập nhật vào data
            sites[site_key]["url"] = real_clean
            save_sites(sites)
            return real_clean
        else:
            print("✅ Domain vẫn sống tốt.")
            return current_clean

    except Exception as e:
        print(f"⚠️ Lỗi kiểm tra domain: {e}")
        return current_url