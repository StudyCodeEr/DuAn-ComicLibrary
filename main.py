import flet as ft
import threading
import time
import os
import sys
import json
import requests

# --- THƯ VIỆN SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from utils.logger import log_info, log_error, log_crash
except ImportError:
    def log_info(msg): print(f"[INFO] {msg}")
    def log_error(msg): print(f"[ERROR] {msg}")
    def log_crash(e): print(f"[CRASH] {e}")

try:
    from gui.app_layout import MangaApp
    from core.image_manager import save_image
    from core.domain_manager import load_sites
    from utils.text_helper import clean_filename
except ImportError as e:
    print("❌ LỖI IMPORT: Thiếu file hoặc sai cấu trúc thư mục!")
    sys.exit(1)

class AppController(MangaApp):
    def start_download_process(self, e):
        url = self.url_input.value
        if not url:
            self.log("❌ Chưa nhập Link!", "red")
            return

        self.btn_download.disabled = True
        self.log(f"🚀 Khởi động (Chiến thuật: Bắt đầu đọc -> Menu Select)...", "cyan")
        
        threading.Thread(target=self._run_safe_background_task, args=(url,), daemon=True).start()

    def _run_safe_background_task(self, url):
        try:
            self._run_logic(url)
        except Exception as e:
            self.log(f"❌ LỖI KHÔNG XÁC ĐỊNH: {str(e)}", "red")
            log_crash(e)
        finally:
            self.btn_download.disabled = False
            self.page.update()

    def _run_logic(self, url):
        driver = None
        try:
            # 1. Cấu hình Selenium
            chrome_options = Options()
            chrome_options.add_argument("--headless=new") 
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--log-level=3")
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 2. Truy cập Link gốc
            self.log(f"🌍 Đang truy cập: {url}")
            driver.get(url)
            time.sleep(2)
            
            # Lấy tên truyện
            try:
                page_title = driver.title.split("-")[0].strip()
            except:
                page_title = "Manga_Unknown"
            
            title = clean_filename(page_title)
            self.log(f"📖 Truyện: {title}", "green")
            
            # ========================================================
            # 3. CHIẾN THUẬT: NHẢY VÀO TRANG ĐỌC ĐỂ LẤY LIST
            # ========================================================
            self.log("🔍 Đang tìm đường vào giao diện đọc...", "yellow")
            chapters = []
            
            # Bước A: Kiểm tra xem có phải đang ở trang đọc sẵn không? (Có thẻ select)
            is_reading_page = False
            try:
                driver.find_element(By.ID, "chapter-selector")
                is_reading_page = True
                self.log("⚡ Link bạn nhập là link đang đọc -> Quét luôn!", "cyan")
            except:
                pass

            # Bước B: Nếu chưa ở trang đọc, tìm nút "Bắt đầu đọc"
            if not is_reading_page:
                try:
                    # Tìm thẻ A chứa chữ "Bắt đầu đọc" hoặc "Đọc từ đầu"
                    # XPath này tìm thẻ a có chứa text đó, bất kể nó nằm sâu trong span/div con
                    start_btn = None
                    keywords = ["Bắt đầu đọc", "Đọc từ đầu", "Đọc ngay"]
                    
                    for kw in keywords:
                        try:
                            # Tìm thẻ A chứa text (case insensitive trick trong xpath hơi dài nên dùng python lọc)
                            links = driver.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                if kw.lower() in link.text.lower():
                                    start_btn = link
                                    break
                            if start_btn: break
                        except: pass
                    
                    if start_btn:
                        read_url = start_btn.get_attribute("href")
                        self.log(f"➡️ Tìm thấy nút 'Bắt đầu đọc', đang chuyển hướng...", "white")
                        driver.get(read_url)
                        time.sleep(3) # Chờ trang đọc load
                    else:
                        self.log("⚠️ Không thấy nút 'Bắt đầu đọc'. Thử quét thủ công...", "yellow")
                        # Fallback: Quét list cũ (nếu web lạ không có nút này)
                except Exception as e:
                    self.log(f"⚠️ Lỗi khi tìm nút đọc: {e}", "yellow")

            # Bước C: Quét cái Menu Dropdown (Select) thần thánh
            try:
                select_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "chapter-selector"))
                )
                
                self.log("✅ Đã vào giao diện đọc. Đang trích xuất danh sách...", "cyan")
                options = select_elem.find_elements(By.TAG_NAME, "option")
                
                # Tính domain gốc để ghép link (vì value trong option thường là link tương đối)
                # VD: url hiện tại là https://example-site.invalid/truyen/...
                base_domain = "/".join(driver.current_url.split("/")[:3]) 
                
                for opt in options:
                    val = opt.get_attribute("value")
                    txt = opt.text.strip()
                    
                    if val:
                        # Xử lý link
                        if val.startswith("/"): full_url = base_domain + val
                        elif "http" not in val: full_url = base_domain + "/" + val
                        else: full_url = val
                        
                        chapters.append({
                            "title": txt, # Tên sạch: "Chap 1", "Chap 2"...
                            "url": full_url
                        })
                
                # Dropdown thường xếp Mới -> Cũ hoặc Cũ -> Mới tùy web
                # Nhưng thường ta muốn đọc từ 1, nên ta kiểm tra
                # Nếu chap đầu tiên là chap lớn nhất (Chap 19), ta đảo ngược
                if chapters and "1" in chapters[-1]['title'] and "1" not in chapters[0]['title']:
                     chapters.reverse()
                     
            except Exception as e:
                self.log("❌ Không tìm thấy menu chọn chương (Dropdown).", "red")
                return

            if not chapters:
                self.log("❌ Danh sách chương trống!", "red")
                return

            self.log(f"✅ Tìm thấy {len(chapters)} chapter chuẩn xác.", "cyan")

            # 4. Config Path
            save_fmt = self.format_dropdown.value
            base_dir = "Downloads"
            if os.path.exists("config.json"):
                try:
                    with open("config.json", "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        if "download_path" in cfg: base_dir = cfg["download_path"]
                except: pass
            
            self.log(f"📂 Lưu tại: {base_dir}", "cyan")
            
            # 5. Loop Download
            for i, chap in enumerate(chapters):
                # Tên chapter lấy từ dropdown rất sạch, chỉ cần clean ký tự cấm
                c_name = clean_filename(chap['title'])
                c_url = chap['url']
                
                chap_dir = os.path.join(base_dir, clean_filename(title), c_name)
                if not os.path.exists(chap_dir): os.makedirs(chap_dir)
                
                self.log(f"📚 [{i+1}/{len(chapters)}] Đang xử lý: {c_name}", "white")
                
                # Vào trang đọc
                if driver.current_url != c_url:
                    driver.get(c_url)
                    time.sleep(2)
                
                # Lấy ảnh
                img_urls = []
                try:
                    # Tìm container
                    container = None
                    try:
                        container = driver.find_element(By.CSS_SELECTOR, "#chapter-content")
                    except:
                        try: container = driver.find_element(By.CSS_SELECTOR, ".reading-content")
                        except: pass
                    
                    target = container if container else driver
                    imgs = target.find_elements(By.TAG_NAME, "img")
                    
                    for img in imgs:
                        src = img.get_attribute("data-original") or img.get_attribute("data-src") or img.get_attribute("src")
                        if src:
                            low = src.lower()
                            if any(ext in low for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                if not any(bad in low for bad in ['logo', 'icon', 'avatar', 'banner', 'loader']):
                                    if src not in img_urls: img_urls.append(src)
                except: pass
                
                self.log(f"   ∑ Tìm thấy: {len(img_urls)} ảnh", "cyan")

                # Setup Session
                s = requests.Session()
                for cookie in driver.get_cookies():
                    s.cookies.set(cookie['name'], cookie['value'])
                
                headers = {
                    "User-Agent": driver.execute_script("return navigator.userAgent;"),
                    "Referer": c_url
                }

                for idx, img_url in enumerate(img_urls):
                    try:
                        # Tên file theo thứ tự idx: Trang_000, Trang_001...
                        file_name = f"Trang_{idx:03d}"
                        self.log(f"   ⬇️ Tải ảnh {idx+1}...", "white")
                        
                        r = s.get(img_url, headers=headers, timeout=20)
                        if r.status_code == 200:
                            save_image(r.content, chap_dir, file_name, save_fmt)
                        else:
                            self.log(f"      ❌ Lỗi HTTP {r.status_code}", "red")
                    except Exception as err:
                        self.log(f"      ❌ Lỗi: {err}", "red")

                self.log(f"   ✅ Xong: {c_name}", "green")
                time.sleep(0.5)

            self.log("🎉 TẤT CẢ ĐÃ HOÀN TẤT!", "green")

        finally:
            if driver:
                self.log("👋 Đang đóng trình duyệt...", "cyan")
                driver.quit()

def main():
    try:
        ft.app(target=AppController)
    except Exception as e:
        print("❌ CRASH NGHIÊM TRỌNG!")
        log_crash(e)

if __name__ == "__main__":
    main()