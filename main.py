import flet as ft
import threading
import time
import os
from DrissionPage import ChromiumPage, ChromiumOptions

# --- IMPORT CÁC MODULE CỦA CHÚNG TA ---
from gui.app_layout import MangaApp  # Sửa lỗi "MangaApp is not defined"
from connectors.mangaconnect import MangaConnectConnector # Sửa lỗi "ViHentaiConnector..."
from core.image_manager import save_image
from core.domain_manager import check_and_update_domain, load_sites
from utils.text_helper import clean_filename

class AppController(MangaApp):
    def start_download_process(self, e):
        """
        Hàm xử lý khi bấm nút Tải
        """
        url = self.url_input.value
        if not url:
            self.log("❌ Chưa nhập Link!", "red")
            return

        self.btn_download.disabled = True
        self.log(f"🚀 Khởi động trình duyệt ngầm...", "cyan")

        # Chạy tác vụ nặng trong luồng riêng (Thread)
        threading.Thread(target=self._run_background_task, args=(url,), daemon=True).start()

    def _run_background_task(self, url):
        browser = None
        try: # Sửa lỗi "Try statement must have..."
            # 1. Cấu hình trình duyệt
            co = ChromiumOptions()
            co.set_user_data_path("BrowserProfile") # Lưu tài khoản/cookie
            
            browser = ChromiumPage(co)
            
            # 2. Load cấu hình sites.json
            sites = load_sites()
            active_site_key = None
            
            # Kiểm tra xem link nhập vào thuộc trang nào trong config
            for key, info in sites.items():
                if key in url or info['url'] in url:
                    active_site_key = key
                    break
            
            final_domain = "https://example-site.invalid" # Giá trị mặc định
            
            if active_site_key:
                # Tự động check domain mới nếu web đổi tên miền
                updated_domain = check_and_update_domain(active_site_key, browser)
                if updated_domain:
                    final_domain = updated_domain
            else:
                self.log("⚠️ Link này chưa có trong sites.json, sẽ thử dùng cấu hình mặc định.", "yellow")

            # 3. Khởi tạo Connector (Dùng tên mới MangaConnectConnector)
            connector = MangaConnectConnector(browser, domain_url=final_domain)
            self.log(f"✅ Đã kết nối tới: {connector.base_url}", "green")

            # 4. Truy cập trang truyện
            self.log(f"🌍 Đang truy cập: {url}")
            browser.get(url)
            
            manga_title = connector.get_manga_title()
            safe_manga_title = clean_filename(manga_title)
            self.log(f"📖 Truyện: {manga_title}", "green")

            # 5. Quét Chapter
            self.log("🔍 Đang quét danh sách chương...", "yellow")
            chapters = connector.get_chapters()
            
            if not chapters:
                self.log("❌ Không tìm thấy chương nào! Có thể lỗi Cloudflare hoặc sai link.", "red")
                return

            self.log(f"✅ Tìm thấy {len(chapters)} chương.", "cyan")

            # 6. Tải từng chương
            save_format = self.format_dropdown.value 
            base_folder = "Downloads"

            for i, chap in enumerate(chapters):
                chap_name = chap['title']
                chap_url = chap['url']
                
                self.log(f"⬇️ [{i+1}/{len(chapters)}] Đang tải: {chap_name}...", "white")
                
                image_urls = connector.get_chapter_images(chap_url)
                
                if not image_urls:
                    self.log(f"   ⚠️ Lỗi: Không tìm thấy ảnh.", "red")
                    continue

                # Tạo thư mục lưu
                safe_chap_name = clean_filename(chap_name)
                save_path = os.path.join(base_folder, safe_manga_title, safe_chap_name)
                
                # Tải ảnh
                for idx, img_url in enumerate(image_urls):
                    try:
                        img_bytes = browser.download(img_url, r_content=True)
                        if img_bytes:
                            file_name = f"Trang_{idx:03d}"
                            save_image(img_bytes, save_path, file_name, save_format)
                    except Exception as err:
                        print(f"Lỗi tải ảnh {idx}: {err}")

                self.log(f"   ✅ Xong chương: {chap_name}", "green")
                time.sleep(1)

            self.log("🎉🎉 TẤT CẢ ĐÃ HOÀN TẤT!", "green")

        except Exception as e:
            self.log(f"❌ Lỗi nghiêm trọng: {e}", "red")
            import traceback
            traceback.print_exc() # In lỗi chi tiết ra Terminal để debug
            
        finally:
            # Luôn đóng trình duyệt dù có lỗi hay không
            if browser:
                browser.quit()
            self.btn_download.disabled = False
            self.page.update()

if __name__ == "__main__":
    ft.app(target=AppController)