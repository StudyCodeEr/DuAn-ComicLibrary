import flet as ft
import os
import subprocess
import sys
from utils.text_helper import clean_filename

class MangaApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        self.build_ui()

    def setup_page(self):
        self.page.title = "Manga Downloader Pro"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_width = 600
        self.page.window_height = 750
        self.page.padding = 10

    def build_ui(self):
        # --- TAB 1: TRANG CHỦ (DOWNLOAD) ---
        self.url_input = ft.TextField(
            label="Nhập URL truyện vào đây...",
            hint_text="Ví dụ: https://domain-truyen.com/truyen/ten-truyen",
            # SỬA LỖI: Dùng INSERT_LINK thay vì LINK
            prefix_icon=ft.icons.INSERT_LINK, 
            border_radius=10,
            keyboard_type=ft.KeyboardType.URL
        )

        self.btn_download = ft.ElevatedButton(
            text="Bắt đầu tải",
            # SỬA LỖI: Dùng DOWNLOAD thay vì DOWNLOAD_ROUNDED (để an toàn hơn)
            icon=ft.icons.DOWNLOAD,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.colors.BLUE_600,
                color="white"
            ),
            width=580, 
            on_click=self.start_download_process
        )

        # Khung hiển thị Log
        self.log_view = ft.Column(scroll=ft.ScrollMode.AUTO, height=400)
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, ft.colors.OUTLINE),
            border_radius=10,
            padding=10,
            bgcolor="#111111",
            expand=True 
        )

        tab_home = ft.Column([
            ft.Text("Tải Truyện Tranh", size=24, weight="bold"),
            ft.Divider(height=10, color="transparent"),
            self.url_input,
            self.btn_download,
            ft.Divider(height=10, color="transparent"),
            ft.Text("Nhật ký hoạt động:", size=14, italic=True),
            log_container
        ], expand=True)

        # --- TAB 2: CÀI ĐẶT (SETTINGS) ---
        
        # 1. Dropdown chọn định dạng ảnh
        self.format_dropdown = ft.Dropdown(
            label="Định dạng ảnh lưu về",
            hint_text="Chọn loại file...",
            value="PNG", # Mặc định
            options=[
                ft.dropdown.Option("PNG", text="PNG (Chất lượng cao nhất)"),
                ft.dropdown.Option("JPEG", text="JPEG (Nhẹ, tiết kiệm ổ cứng)"),
                ft.dropdown.Option("WEBP", text="WEBP (Hiện đại, tối ưu web)"),
                ft.dropdown.Option("ORIGINAL", text="Nguyên bản (Không convert)"),
            ],
            border_radius=10,
            width=400
        )

        # 2. Nút mở file cấu hình sites.json
        def open_site_config(e):
            config_file = "sites.json"
            if not os.path.exists(config_file):
                self.log(f"⚠️ Chưa có file {config_file}. Hãy chạy App một lần để tạo.", "yellow")
                return
            
            # Mở file bằng trình editor mặc định của OS
            try:
                if sys.platform == 'win32':
                    os.startfile(config_file)
                elif sys.platform == 'darwin':
                    subprocess.call(('open', config_file))
                else:
                    subprocess.call(('xdg-open', config_file))
                self.log("📂 Đã mở file cấu hình domain.", "green")
            except Exception as ex:
                self.log(f"❌ Lỗi mở file: {ex}", "red")

        btn_edit_domains = ft.ElevatedButton(
            text="Quản lý nguồn truyện (Sửa Domain)",
            # SỬA LỖI: Dùng EDIT thay vì EDIT_DOCUMENT
            icon=ft.icons.EDIT,
            on_click=open_site_config,
            style=ft.ButtonStyle(bgcolor=ft.colors.GREY_800)
        )

        tab_settings = ft.Column([
            ft.Text("Cấu hình Ứng dụng", size=24, weight="bold"),
            ft.Divider(),
            
            ft.Text("Cài đặt hình ảnh", size=16, weight="bold", color="cyan"),
            ft.Container(content=self.format_dropdown, padding=ft.padding.only(left=10, top=10)),
            ft.Text("Lưu ý: Chế độ 'Nguyên bản' sẽ tải nhanh nhất.", size=12, italic=True, color="grey"),
            
            ft.Divider(),
            
            ft.Text("Quản lý nguồn truyện", size=16, weight="bold", color="cyan"),
            ft.Text("Nếu trang web đổi tên miền (bị chặn), hãy bấm nút dưới để cập nhật:", size=13),
            ft.Container(content=btn_edit_domains, padding=ft.padding.only(left=10, top=10)),
            
            ft.Divider(),
            ft.Text("Thư mục lưu trữ", size=16, weight="bold", color="cyan"),
            ft.TextField(value=os.path.abspath("Downloads"), disabled=True, label="Đường dẫn hiện tại")
        ], scroll=ft.ScrollMode.AUTO)

        # --- GHÉP TAB ---
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Tải xuống", icon=ft.icons.HOME, content=ft.Container(content=tab_home, padding=10)),
                ft.Tab(text="Cài đặt", icon=ft.icons.SETTINGS, content=ft.Container(content=tab_settings, padding=10)),
            ],
            expand=True
        )

        self.page.add(self.tabs)

    # --- HELPER FUNCTIONS ---
    def log(self, message, color="white"):
        self.log_view.controls.append(ft.Text(message, color=color, font_family="Consolas", size=13))
        self.page.update()
        self.log_view.scroll_to(offset=-1, duration=300)

    def start_download_process(self, e):
        # Hàm này chỉ là placeholder. 
        # Logic thật sẽ được override bởi AppController trong main.py
        pass

def run_app():
    ft.app(target=MangaApp)