class BaseConnector:
    def __init__(self, browser_page, domain_url=None):
        """
        Khởi tạo Connector.
        :param browser_page: Đối tượng trình duyệt (DrissionPage)
        :param domain_url: Link trang chủ (VD: https://example-site.invalid), được truyền từ main.py
        """
        self.page = browser_page
        self.base_url = domain_url
        self.domain = ""
        
        # Tự động lấy domain từ URL nếu có
        if self.base_url:
            try:
                self.domain = self.base_url.split("://")[-1].split("/")[0]
            except:
                self.domain = self.base_url

    def can_handle(self, url):
        """Kiểm tra xem Connector này có xử lý được link này không"""
        if self.domain and self.domain in url:
            return True
        return False

    def get_manga_title(self):
        """Lấy tên truyện (Class con phải viết lại hàm này)"""
        raise NotImplementedError("Class con phải viết lại hàm này")

    def get_chapters(self):
        """Lấy danh sách chương (Class con phải viết lại hàm này)"""
        raise NotImplementedError("Class con phải viết lại hàm này")

    def get_chapter_images(self, chapter_url):
        """Lấy danh sách ảnh (Class con phải viết lại hàm này)"""
        raise NotImplementedError("Class con phải viết lại hàm này")