# connectors/base.py

class BaseConnector:
    """
    Class cha (Base Class) quy định các hàm chuẩn.
    File này ĐỊNH NGHĨA class, không được import chính nó.
    """
    def __init__(self, browser_page):
        self.page = browser_page
        self.domain = "example.com"
        self.base_url = "https://example.com"

    def can_handle(self, url):
        """Kiểm tra xem Connector này có xử lý được link này không"""
        return self.domain in url

    def get_manga_title(self):
        """Lấy tên truyện"""
        raise NotImplementedError("Class con phải viết lại hàm này")

    def get_chapters(self):
        """Lấy danh sách chương"""
        raise NotImplementedError("Class con phải viết lại hàm này")

    def get_chapter_images(self, chapter_url):
        """Lấy danh sách ảnh của chương"""
        raise NotImplementedError("Class con phải viết lại hàm này")