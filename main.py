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
            chrome_options.add_argument("--mute-audio")
            
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
            # 3. CHIẾN THUẬT: TÌM ĐƯỜNG VÀO TRANG ĐỌC
            # ========================================================
            self.log("🔍 Đang tìm đường vào giao diện đọc...", "yellow")
            chapters = []
            
            # Bước A: Kiểm tra xem có phải đang ở trang đọc sẵn không?
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
                    start_btn = None
                    keywords = ["Bắt đầu đọc", "Đọc từ đầu", "Đọc ngay"]
                    
                    # Tìm thẻ a có chứa từ khóa
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        # Lấy text an toàn (bao gồm cả text ẩn trong span con)
                        txt = link.get_attribute("innerText") or link.text
                        if any(k.lower() in txt.lower() for k in keywords):
                            start_btn = link
                            break
                    
                    if start_btn:
                        read_url = start_btn.get_attribute("href")
                        self.log(f"➡️ Tìm thấy nút 'Bắt đầu đọc', đang chuyển hướng...", "white")
                        driver.get(read_url)
                        time.sleep(3) 
                    else:
                        self.log("⚠️ Không thấy nút 'Bắt đầu đọc'. Vẫn thử quét...", "yellow")
                except Exception as e:
                    self.log(f"⚠️ Lỗi khi tìm nút đọc: {e}", "yellow")

            # Bước C: Quét Menu Dropdown
            try:
                select_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "chapter-selector"))
                )
                
                self.log("✅ Đã vào giao diện đọc. Đang trích xuất danh sách...", "cyan")
                options = select_elem.find_elements(By.TAG_NAME, "option")
                
                base_domain = "/".join(driver.current_url.split("/")[:3]) 
                
                for opt in options:
                    val = opt.get_attribute("value")
                    txt = opt.text.strip()
                    
                    if val:
                        if val.startswith("/"): full_url = base_domain + val
                        elif "http" not in val: full_url = base_domain + "/" + val
                        else: full_url = val
                        
                        chapters.append({
                            "title": txt, 
                            "url": full_url
                        })
                
                # Đảo ngược nếu cần (để đọc từ chap 1)
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
                c_name = clean_filename(chap['title'])
                c_url = chap['url']
                
                chap_dir = os.path.join(base_dir, clean_filename(title), c_name)
                if not os.path.exists(chap_dir): os.makedirs(chap_dir)
                
                self.log(f"📚 [{i+1}/{len(chapters)}] Đang xử lý: {c_name}", "white")
                
                if driver.current_url != c_url:
                    driver.get(c_url)
                    time.sleep(2)
                
                # Lấy ảnh
                img_urls = []
                try:
                    # Tìm container
                    container = None
                    try: container = driver.find_element(By.CSS_SELECTOR, "#chapter-content")
                    except:
                        try: container = driver.find_element(By.CSS_SELECTOR, ".reading-content")
                        except: pass
                    
                    target = container if container else driver
                    imgs = target.find_elements(By.TAG_NAME, "img")
                    
                    for img in imgs:
                        src = img.get_attribute("data-original") or img.get_attribute("data-src") or img.get_attribute("src")
                        if src:
                            low = src.lower()
                            # [BỘ LỌC QUAN TRỌNG] Đã thêm 'fav' vào danh sách đen
                            bad_keywords = ['logo', 'icon', 'avatar', 'banner', 'loader', 'fav', 'gif']
                            
                            if any(ext in low for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                if not any(bad in low for bad in bad_keywords):
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