from connectors.base import BaseConnector
from urllib.parse import urlparse

class MangaConnectConnector(BaseConnector):
    def __init__(self, browser_page, domain_url="https://example-site.invalid"):
        """
        domain_url: Địa chỉ trang web hiện tại (lấy từ sites.json).
        Ví dụ: Nếu web đổi sang example-site-2.invalid, tham số này sẽ là example-site-2.invalid
        """
        super().__init__(browser_page)
        self.base_url = domain_url.rstrip("/") # Xóa dấu / ở cuối nếu có
        
        # Tự động lấy "host" để nhận diện (ví dụ: example-site.invalid)
        self.domain = urlparse(self.base_url).netloc

    def get_manga_title(self):
        try:
            # Ưu tiên lấy từ thẻ Span tiêu đề trong trang chi tiết
            if self.page.ele('span.font-semibold.text-lg'):
                return self.page.ele('span.font-semibold.text-lg').text
            
            # Fallback 1: Lấy từ thẻ H1 (phổ biến ở nhiều web)
            if self.page.ele('h1'):
                return self.page.ele('h1').text
                
            # Fallback 2: Lấy từ thẻ Title của trình duyệt
            return self.page.title.split('-')[0].strip()
        except:
            return "Unknown Manga"

    def get_chapters(self):
        """
        Quét danh sách chương dựa trên cấu trúc HTML của trang web cụ thể này.
        """
        chapters = []
        try:
            # 1. Tìm khung chứa danh sách (ul có class overflow-y-auto)
            ul_list = self.page.ele('ul.overflow-y-auto')
            
            if not ul_list:
                # Nếu web đổi giao diện, thử tìm fallback khác
                print("⚠️ Không tìm thấy ul.overflow-y-auto, thử tìm danh sách chung...")
                links = self.page.eles('a[href*="/truyen/"][href*="/chap"]') 
                # (Logic tìm fallback có thể mở rộng sau)
            else:
                # 2. Lấy danh sách thẻ <a> bên trong
                links = ul_list.eles('tag:a')

            if not links:
                return []

            for link in links:
                relative_url = link.attr('href') # Dạng: /truyen/abc/oneshot
                
                # Lấy tên chương (Oneshot, Chap 1...)
                # Tìm thẻ span có class text-ellipsis bên trong thẻ a
                span_name = link.ele('.text-ellipsis')
                title = span_name.text if span_name else link.text.strip()
                
                if not title:
                    title = "Unknown Chapter"

                if relative_url:
                    # Logic ghép Domain động:
                    # Nếu link là tương đối (/truyen...), ghép với self.base_url
                    if not relative_url.startswith("http"):
                        full_url = self.base_url + relative_url
                    else:
                        full_url = relative_url
                        
                    chapters.append({'title': title, 'url': full_url})
            
            # Đảo ngược để tải từ chương cũ nhất -> mới nhất (Tùy chọn)
            # chapters.reverse() 
            
            return chapters

        except Exception as e:
            print(f"Lỗi tìm chapter: {e}")
            return []

    def get_chapter_images(self, chapter_url):
        print(f"Đang phân tích chapter: {chapter_url}")
        self.page.get(chapter_url)
        
        try:
            # Chờ trang tải xong
            self.page.wait.load_start()
            
            # Lấy toàn bộ thẻ img
            images = self.page.eles('tag:img')
            image_urls = []
            
            # Danh sách đen (những từ khóa trong link ảnh rác)
            blacklist = ['logo', 'icon', 'avatar', 'banner', 'ads', 'tracking']

            for img in images:
                # Lấy link ảnh ưu tiên data-src (lazy load) rồi mới tới src
                src = img.attr('data-src') if img.attr('data-src') else img.attr('src')
                
                if src and "http" in src:
                    # Lọc bỏ ảnh rác
                    if not any(bad_word in src for bad_word in blacklist):
                        image_urls.append(src)
            
            return image_urls
        except Exception as e:
            print(f"Lỗi lấy ảnh: {e}")
            return []