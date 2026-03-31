import flet as ft
import threading
import time
import os
import sys
import json
import requests
import re
import shutil 
import multiprocessing
import uvicorn

# --- CẤU HÌNH ĐƯỜNG DẪN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- IMPORT SERVER ---
try:
    import server_pc
    from server_pc import app, run_discovery_listener
except ImportError:
    print("❌ LỖI: Không tìm thấy file server_pc.py")
    sys.exit(1)

# --- THƯ VIỆN SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

# --- IMPORT MODULE ---
try:
    from gui.app_layout import MangaApp
    from core.image_manager import save_image
    from core.domain_manager import load_sites
    from core.database import DatabaseManager 
    from utils.text_helper import clean_filename
    
    # Logger dự phòng nếu lỗi import
    def log_crash(e): print(f"[CRASH] {e}")
except ImportError as e:
    print(f"❌ LỖI IMPORT SYSTEM: {e}")
    sys.exit(1)

# --- HÀM TÌM RESOURCE ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- [QUAN TRỌNG] LOGGER CHUYỂN HƯỚNG PRINT VÀO APP ---
class FletLogger:
    def __init__(self, app_instance):
        self.app = app_instance 

    def write(self, message):
        if message.strip():
            # Gọi hàm log_server bên app_layout để in vào Tab Console
            # Kiểm tra xem hàm có tồn tại không để tránh lỗi
            if hasattr(self.app, 'log_server'):
                self.app.log_server(message.strip())
            else:
                pass # Bỏ qua nếu UI chưa sẵn sàng

    def flush(self): pass

# --- CONTROLLER CHÍNH ---
class AppController(MangaApp):
    def __init__(self, page):
        super().__init__(page) # Gọi init của cha (MangaApp)
        # Bắt đầu luồng lắng nghe lệnh từ Server
        threading.Thread(target=self.monitor_remote_commands, daemon=True).start()

    # [THÊM MỚI] Hàm liên tục kiểm tra xem có thư trong hàng đợi không
    def monitor_remote_commands(self):
        while True:
            # Lấy URL từ hàng đợi (Lệnh này sẽ chờ/block nếu hàng đợi rỗng)
            url = server_pc.download_queue.get()
            if url:
                self.log(f"📡 NHẬN LỆNH REMOTE: {url}", "cyan")
                # Gọi hàm tải thật (Sử dụng hàm có sẵn _run_safe_background_task)
                # Lưu ý: Hàm này sẽ chặn luồng này cho đến khi tải xong.
                # Điều này tốt vì giúp tải lần lượt, không bị loạn Selenium.
                self._run_safe_background_task(url)

    def start_download_process(self, e):
        url = self.url_input.value
        if not url:
            self.log("❌ Chưa nhập Link!", "red")
            return

        self.btn_download.disabled = True
        self.log(f"🚀 Khởi động...", "cyan")
        
        threading.Thread(target=self._run_safe_background_task, args=(url,), daemon=True).start()

    def _run_safe_background_task(self, url):
        try:
            self._run_logic(url)
        except Exception as e:
            self.log(f"❌ LỖI HỆ THỐNG: {str(e)}", "red")
            log_crash(e)
        finally:
            self.btn_download.disabled = False
            # Dùng self.page.update() vì kiến trúc Direct Page
            if self.page: self.page.update()

    def _run_logic(self, url):
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url

        driver = None
        try:
            # 1. CẤU HÌNH SELENIUM
            chrome_options = Options()
            chrome_options.add_argument("--headless=new") 
            chrome_options.page_load_strategy = 'eager'
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--mute-audio")
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 2. TRUY CẬP
            self.log(f"🌍 Đang truy cập: {url}")
            try:
                driver.get(url)
            except WebDriverException:
                self.log(f"❌ Lỗi kết nối! Kiểm tra lại Link hoặc Mạng.", "red")
                return

            try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except: pass
            
            # Lấy tên truyện
            try:
                h1_elem = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                page_title = h1_elem.text.strip()
            except:
                try: page_title = driver.title.split("-")[0].strip()
                except: page_title = "Manga_Unknown"
            
            title = clean_filename(page_title)
            self.log(f"📖 Truyện: {title}", "green")
            
            # Tạo thư mục
            base_dir = "Downloads"
            if os.path.exists("config.json"):
                try:
                    with open("config.json", "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        if "download_path" in cfg: base_dir = cfg["download_path"]
                except: pass
            
            final_manga_path = os.path.join(base_dir, clean_filename(title))
            if not os.path.exists(final_manga_path):
                os.makedirs(final_manga_path)

            # 3. LẤY TAGS
            manga_tags = []
            try:
                xpath_tags = "//span[contains(text(), 'Thể loại')]/../a"
                tag_elements = driver.find_elements(By.XPATH, xpath_tags)
                for elem in tag_elements:
                    t = elem.text.strip() or elem.get_attribute("innerText").strip()
                    if t and len(t) < 50 and t not in manga_tags:
                        manga_tags.append(t)
            except: pass
            if not manga_tags: manga_tags = ["Chưa phân loại"]
            self.log(f"🏷️ Tags: {', '.join(manga_tags)}", "cyan")

            # 4. TẢI ẢNH BÌA
            cover_local_path = ""
            try:
                cover_url = None
                cover_div = None
                try: cover_div = driver.find_element(By.CSS_SELECTOR, "div.cover-frame, .cover-image, .manga-poster")
                except: pass
                
                if cover_div:
                    style_attr = cover_div.get_attribute("style")
                    if style_attr and "url" in style_attr:
                        match = re.search(r'url\((["\']?)(.*?)\1\)', style_attr)
                        if match: cover_url = match.group(2)
                    if not cover_url: cover_url = cover_div.get_attribute("src")

                if not cover_url:
                    try:
                        img_elem = driver.find_element(By.CSS_SELECTOR, ".manga-info img, .detail-info img")
                        cover_url = img_elem.get_attribute("src")
                    except: pass

                if cover_url:
                    self.log(f"📸 Tìm thấy bìa: {cover_url[:20]}...", "white")
                    headers = { "User-Agent": driver.execute_script("return navigator.userAgent;"), "Referer": url }
                    r_cover = requests.get(cover_url, headers=headers, timeout=10)
                    if r_cover.status_code == 200:
                        cover_local_path = os.path.join(final_manga_path, "cover.jpg")
                        with open(cover_local_path, "wb") as f:
                            f.write(r_cover.content)
            except Exception as e:
                self.log(f"⚠️ Chưa tải được bìa gốc: {e}", "yellow")

            # 5. TÌM NÚT ĐỌC
            self.log("🔍 Tìm nút 'Bắt đầu đọc'...", "yellow")
            try:
                start_btn = driver.find_element(By.XPATH, "//span[contains(text(), 'Bắt đầu đọc')]/ancestor::a")
                read_url = start_btn.get_attribute("href")
                self.log("➡️ Chuyển hướng...", "cyan")
                driver.get(read_url)
                try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "img")))
                except: pass
            except:
                self.log("⚠️ Quét trang hiện tại...", "yellow")

            # 6. QUÉT CHƯƠNG
            chapters = []
            try:
                select_elem = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "chapter-selector")))
                options = select_elem.find_elements(By.TAG_NAME, "option")
                base_domain = "/".join(driver.current_url.split("/")[:3]) 
                for opt in options:
                    val = opt.get_attribute("value")
                    txt = opt.text.strip()
                    if val:
                        if val.startswith("/"): full_url = base_domain + val
                        elif "http" not in val: full_url = base_domain + "/" + val
                        else: full_url = val
                        chapters.append({"title": txt, "url": full_url})
            except: pass

            chapters = list({v['url']:v for v in chapters}.values())
            if chapters and "1" in chapters[-1]['title'] and "1" not in chapters[0]['title']:
                  chapters.reverse()

            if not chapters:
                self.log("❌ Không tìm thấy chương nào!", "red")
                return

            self.log(f"✅ Tìm thấy {len(chapters)} chương.", "cyan")
            
            # 7. TẢI ẢNH
            save_fmt = "PNG"
            # Truy cập biến format_dropdown từ self (kế thừa MangaApp)
            if hasattr(self, 'format_dropdown') and self.format_dropdown.value:
                save_fmt = self.format_dropdown.value

            s = requests.Session() 
            for cookie in driver.get_cookies(): s.cookies.set(cookie['name'], cookie['value'])
            
            for i, chap in enumerate(chapters):
                c_name = clean_filename(chap['title'])
                c_url = chap['url']
                chap_dir = os.path.join(final_manga_path, c_name)
                if not os.path.exists(chap_dir): os.makedirs(chap_dir)
                
                self.log(f"📚 [{i+1}/{len(chapters)}] Xử lý: {c_name}", "white")
                
                if driver.current_url != c_url:
                    try:
                        driver.get(c_url)
                        try: WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img")))
                        except: pass
                    except WebDriverException:
                         self.log(f"❌ Lỗi tải chap: {c_name}", "red")
                         continue

                img_urls = []
                try:
                    target = driver
                    potential_containers = ["#chapter-content", ".reading-content", ".page-chapter", "#vungdoc", ".box-doc", "#content", ".list-image-detail"]
                    for sel in potential_containers:
                        try:
                            found = driver.find_element(By.CSS_SELECTOR, sel)
                            target = found
                            break
                        except: continue
                    
                    imgs = target.find_elements(By.TAG_NAME, "img")
                    for img in imgs:
                        src = img.get_attribute("data-original") or img.get_attribute("data-src") or img.get_attribute("src")
                        if src:
                            low = src.lower()
                            bad = ['logo', 'icon', 'avatar', 'banner', 'loader', 'fav', 'gif']
                            if any(ext in low for ext in ['.jpg', '.jpeg', '.png', '.webp']) and not any(b in low for b in bad):
                                if src not in img_urls: img_urls.append(src)
                except: pass
                
                headers = { "User-Agent": driver.execute_script("return navigator.userAgent;"), "Referer": c_url }

                for idx, img_url in enumerate(img_urls):
                    try:
                        file_name = f"Trang_{idx:03d}"
                        r = s.get(img_url, headers=headers, timeout=10)
                        if r.status_code == 200:
                            save_image(r.content, chap_dir, file_name, save_fmt)
                    except: pass
                
                self.log(f"   ✅ Xong: {len(img_urls)} ảnh", "green")

            # 8. LƯU DB
            final_cover_path = ""
            if cover_local_path and os.path.exists(cover_local_path) and os.path.getsize(cover_local_path) > 1024:
                final_cover_path = cover_local_path
            else:
                self.log("⚠️ Tạo bìa dự phòng...", "yellow")
                try:
                    found_fallback = False
                    for root, dirs, files in os.walk(final_manga_path):
                        for file in files:
                            if file.startswith("Trang_000") or file.startswith("Trang_001"):
                                src_path = os.path.join(root, file)
                                dest_path = os.path.join(final_manga_path, "cover.jpg")
                                shutil.copy2(src_path, dest_path)
                                final_cover_path = dest_path
                                found_fallback = True
                                break
                        if found_fallback: break
                except: pass

            try:
                db = DatabaseManager()
                db.save_manga(url, title, final_manga_path, cover_path=final_cover_path, tags=manga_tags)
                db.close()
                self.log("💾 Đã lưu Thư viện!", "green")
                self.cached_tags = None # Xóa cache cũ để lần sau mở lọc nó sẽ tự tải lại tag mới từ DB
                # Gọi hàm load thư viện từ class cha
                self.load_library_advanced(None)
            except Exception as e:
                self.log(f"⚠️ Lỗi DB: {e}", "red")

            self.log("🎉 HOÀN TẤT!", "green")

        finally:
            if driver:
                self.log("👋 Đóng trình duyệt...", "cyan")
                try: driver.quit()
                except: pass

# --- HÀM KHỞI CHẠY CHÍNH ---
def main():
    assets_dir = resource_path("assets")
    
    # Định nghĩa hàm Wrapper để Flet chạy
    def app_main(page: ft.Page):
        # 1. Khởi tạo AppController
        # (Nó sẽ gọi MangaApp.__init__ -> setup UI -> tạo biến self.server_log_view)
        my_app = AppController(page)
        
        # 2. Bẻ hướng Print -> Tab Console
        # Lúc này my_app đã có hàm log_server và biến server_log_view
        sys.stdout = FletLogger(my_app)
        sys.stderr = FletLogger(my_app)
        
        print("🚀 Hệ thống đã sẵn sàng...") # Dòng này sẽ hiện lên Console Tab ngay lập tức

        # 3. Chạy Server ở luồng riêng
        def start_server_thread():
            print("📡 Đang khởi động Server PC...")
            try:
                # [ĐÃ SỬA] Thêm log_level="warning" để chặn các thông báo gây lỗi
                uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None, log_level="warning")
            except Exception as e:
                print(f"❌ Lỗi Server: {e}")

        server_thread = threading.Thread(target=start_server_thread, daemon=True)
        server_thread.start()

    # Chạy App
    try: 
        ft.app(target=app_main, assets_dir=assets_dir)
    except Exception as e: 
        log_crash(e)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()