from connectors.base import BaseConnector
import re

class MangaConnectConnector(BaseConnector):
    def __init__(self, browser_page, domain_url=None):
        super().__init__(browser_page, domain_url)

    def get_manga_title(self):
        try:
            # Lấy title nhanh, xử lý chuỗi gọn gàng
            return self.page.title.split("-")[0].strip()
        except:
            return "Manga_Unknown"

    def get_chapters(self):
        # [TỐI ƯU 1] Xóa bỏ time.sleep(2).
        # Chỉ chờ nhẹ 0.5s để đảm bảo DOM đã render xong phần cơ bản
        self.page.wait.load_start()
        
        # --- CHIẾN THUẬT 1: BẮN TỈA DROPDOWN (Siêu tốc) ---
        # Đây là cấu trúc chuẩn của example-site, lấy được cái này là xong việc ngay.
        try:
            select_box = self.page.ele('#chapter-selector', timeout=2) # Chỉ chờ tối đa 2s
            if select_box:
                print("⚡ [FAST MODE] Tìm thấy menu chọn chương!")
                return self._parse_dropdown(select_box)
        except:
            pass

        # --- CHIẾN THUẬT 2: QUÉT LIST THÔNG MINH (Dự phòng) ---
        # Nếu không có dropdown, ta quét thẻ A nhưng có KHOANH VÙNG
        print("🐢 [NORMAL MODE] Đang quét danh sách...")
        return self._parse_list_smart()

    def _parse_dropdown(self, select_box):
        """Hàm xử lý dữ liệu từ Dropdown nhanh gọn"""
        chapters = []
        current_url = self.page.url
        parts = current_url.split("/")
        domain = f"{parts[0]}//{parts[2]}" # VD:

        # Lấy toàn bộ options một lần (nhanh hơn lặp từng cái)
        options = select_box.eles('tag:option')
        
        for opt in options:
            val = opt.attr('value')
            title = opt.text.strip()
            
            if val:
                # Ghép link siêu tốc
                if val.startswith("http"): full_url = val
                elif val.startswith("/"): full_url = domain + val
                else: full_url = domain + "/" + val
                
                chapters.append({"title": title, "url": full_url})
        
        return chapters

    def _parse_list_smart(self):
        """Hàm quét thẻ A nhưng có lọc rác ngay từ đầu"""
        current_url = self.page.url
        base_url = current_url.split("?")[0].rstrip("/")
        
        # Danh sách từ khóa rác cần loại bỏ ngay
        BAD_KEYWORDS = {
            "đọc chương cuối", 
             "theo dõi", "bình luận", "đăng nhập", 
            "thể loại", "lịch sử", "tác giả", "nhóm dịch"
        }

        chapters_map = {}
        
        # [TỐI ƯU 2] Khoanh vùng tìm kiếm
        # Thay vì quét toàn bộ trang, thử tìm container chứa list chapter
        # Các class thường gặp ở web truyện: 'list-chapters', 'chapter-list', 'row'
        # Nếu không tìm thấy container cụ thể, mới quét toàn trang (body)
        container = self.page.ele('.list-chapters') or self.page.ele('#list-chapter') or self.page.ele('.chapters-list') or self.page.ele('body')
        
        # Chỉ lấy thẻ a có href chứa link cơ sở (Lọc thô)
        # Cách này giảm 90% số lượng thẻ a cần xử lý
        all_links = container.eles(f'tag:a@@href:{base_url.split("//")[-1]}') 

        parts = current_url.split("/")
        domain = f"{parts[0]}//{parts[2]}"

        for link in all_links:
            try:
                href = link.attr('href')
                if not href: continue
                
                # Chuẩn hóa Link
                if href.startswith("/"): href = domain + href
                href_clean = href.split("?")[0].rstrip("/")

                # Logic: Link con phải dài hơn link cha
                if len(href_clean) > len(base_url):
                    
                    # Lấy tên (Ưu tiên span để sạch rác)
                    chap_title = ""
                    el_span = link.ele('.text-ellipsis') or link.ele('tag:span')
                    if el_span: chap_title = el_span.text.strip()
                    else: chap_title = link.text.split("\n")[0].strip()

                    if not chap_title: chap_title = href_clean.split("/")[-1]

                    # Check từ khóa cấm (dùng set lookup cực nhanh)
                    if any(bad in chap_title.lower() for bad in BAD_KEYWORDS): continue
                    if len(chap_title) > 80: continue # Tên quá dài là rác

                    chapters_map[href_clean] = chap_title

            except: continue
        
        # Chuyển map sang list
        final = [{"title": t, "url": u} for u, t in chapters_map.items()]
        final.reverse() # Đảo ngược để tải từ 1->Mới
        return final

    def get_chapter_images(self, chapter_url):
        # [TỐI ƯU 3] Không load lại trang nếu URL trùng (Tránh lặp)
        if self.page.url != chapter_url:
            self.page.get(chapter_url)
        
        # Chờ phần tử quan trọng xuất hiện thay vì chờ cứng 2s
        # Chỉ chờ tối đa 3s cho ảnh load
        try:
            self.page.wait.ele('tag:img', timeout=3) 
        except: pass
        
        image_urls = []
        
        # Chiến thuật tìm container chứa ảnh chính xác
        container = (
            self.page.ele('#chapter-content') or 
            self.page.ele('.reading-content') or 
            self.page.ele('.page-chapter')
        )
        
        target = container if container else self.page
        
        # Lấy tất cả ảnh trong 1 lệnh duy nhất
        imgs = target.eles('tag:img')
        
        for img in imgs:
            # Lấy data-src trước (lazyload), rồi đến src
            src = img.attr('data-original') or img.attr('data-src') or img.attr('src')
            if not src: continue
            
            # Lọc nhanh đuôi file
            src_lower = src.lower()
            if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                # Lọc rác (icon, logo)
                if not any(bad in src_lower for bad in ['avatar', 'logo', 'icon', 'banner', 'fav']):
                    image_urls.append(src)

        return list(dict.fromkeys(image_urls))