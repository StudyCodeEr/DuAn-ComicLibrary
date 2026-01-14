import flet as ft
import os
import subprocess
import sys
import json
from utils.logger import log_info, log_error
from core.domain_manager import load_sites, update_site_url, add_new_site

CONFIG_FILE = "config.json"

class MangaApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.download_path = "Downloads"
        self.sites_data = {} 
        self.load_config()
        self.setup_page()
        try:
            self.build_ui()
        except Exception as e:
            raise e

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.download_path = data.get("download_path", "Downloads")
            except: pass
        if not os.path.exists(self.download_path):
            try: os.makedirs(self.download_path)
            except: self.download_path = "Downloads"

    def save_config(self):
        data = {"download_path": self.download_path}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"Lỗi lưu config: {e}", "red")

    def setup_page(self):
        self.page.title = "Manga Downloader Pro"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0f172a" 
        self.page.window_width = 900
        self.page.window_height = 800
        self.page.padding = 0
        self.file_picker = ft.FilePicker(on_result=self.on_directory_selected)
        self.page.overlay.append(self.file_picker)

    def on_directory_selected(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.download_path = e.path
            self.path_input.value = self.download_path
            self.path_input.update()
            self.save_config()
            self.log(f"📂 Đã đổi thư mục lưu: {self.download_path}", "green")

    def build_ui(self):
        # --- CONSTANTS ---
        SMOOTH_CURVE = ft.AnimationCurve.EASE_OUT_CUBIC 
        PRIMARY = "#06b6d4"   
        BG_CARD = "#1e293b"   
        TEXT_HINT = "#64748b" 

        # --- 1. HEADER ---
        header_title = ft.Text("MANGA DOWNLOADER", size=30, weight="bold", color="white", font_family="Verdana")
        header_sub = ft.Text("Hỗ trợ các trang web hiện có trên thị trường tuy nhiên phải tự add trong settings (Auto Detect)", size=12, color=TEXT_HINT)

        # --- 2. INPUT BOX ---
        self.url_input = ft.TextField(
            hint_text="Dán Link truyện vào đây...",
            hint_style=ft.TextStyle(color=TEXT_HINT),
            border="none", bgcolor="transparent", text_size=15,
            cursor_color=PRIMARY, content_padding=10,
            selection_color=PRIMARY, keyboard_type=ft.KeyboardType.URL,
            expand=True
        )

        input_container = ft.Container(
            content=ft.Row(
                [ft.Icon(name="link", color=PRIMARY, size=24), self.url_input],
                alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=15, right=5, top=2, bottom=2),
            border=ft.border.all(2, PRIMARY), border_radius=15, bgcolor="#0f172a",
            animate=ft.animation.Animation(400, SMOOTH_CURVE)
        )

        # --- 3. BUTTON ---
        self.btn_download = ft.ElevatedButton(
            text="KHỞI ĐỘNG TẢI XUỐNG", icon="download",
            style=ft.ButtonStyle(
                color="white", bgcolor=PRIMARY, padding=22,
                shape=ft.RoundedRectangleBorder(radius=12), elevation=10,
                animation_duration=400
            ),
            width=400, on_click=self.start_download_process,
            animate_scale=ft.animation.Animation(100, ft.AnimationCurve.BOUNCE_OUT)
        )

        # --- 4. LOGS ---
        self.log_view = ft.Column(scroll=ft.ScrollMode.AUTO, auto_scroll=False, spacing=4, animate_opacity=300)
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, "#334155"), border_radius=10, padding=15,
            bgcolor="black", width=float('inf'), expand=True,
            animate=ft.animation.Animation(400, SMOOTH_CURVE)
        )

        # --- TAB HOME LAYOUT ---
        tab_home_layout = ft.Container(
            content=ft.Column([
                ft.Container(height=20),
                ft.Column([header_title, header_sub], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=40, color="transparent"),
                ft.Container(
                    content=ft.Column([
                        ft.Text("LINK TRUYỆN", size=12, weight="bold", color=TEXT_HINT),
                        ft.Container(height=5),
                        input_container,
                    ]),
                    padding=25, bgcolor=BG_CARD, border_radius=15,
                    shadow=ft.BoxShadow(blur_radius=15, color="black"),
                    animate_offset=ft.animation.Animation(500, SMOOTH_CURVE)
                ),
                ft.Divider(height=20, color="transparent"),
                ft.Row([self.btn_download], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=20, color="transparent"),
                ft.Text("TERMINAL LOGS:", font_family="Consolas", color=TEXT_HINT, size=12),
                log_container
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            padding=30, alignment=ft.alignment.top_center, width=900, expand=True,
            opacity=1, animate_opacity=500
        )

        # --- TAB SETTINGS LOGIC (NÂNG CẤP) ---
        self.sites_data = load_sites()
        
        # Helper tạo option cho dropdown
        def get_site_options():
            opts = [ft.dropdown.Option(key, text=info['name']) for key, info in self.sites_data.items()]
            # Thêm tùy chọn đặc biệt để add mới
            opts.append(ft.dropdown.Option("NEW_SITE_ADD", text="➕ Thêm nguồn mới..."))
            return opts

        self.dd_sites = ft.Dropdown(
            label="Chọn nguồn",
            options=get_site_options(),
            border_radius=10, bgcolor="#0f172a", width=float('inf')
        )

        # Ô nhập tên (chỉ hiện khi thêm mới hoặc hiển thị tên cũ)
        self.inp_site_name = ft.TextField(
            label="Tên hiển thị", hint_text="Ví dụ: Blog Truyện",
            prefix_icon="text_fields", border_radius=10, bgcolor="#0f172a",
            read_only=True # Mặc định là chỉ đọc (Edit Mode)
        )

        self.inp_site_url = ft.TextField(
            label="Đường dẫn (URL)", hint_text="https://...",
            prefix_icon="link", border_radius=10, bgcolor="#0f172a"
        )
        
        self.btn_save_site = ft.ElevatedButton(
            text="Lưu thay đổi", icon="save", 
            bgcolor="#059669", color="white", width=float('inf'),
            style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=lambda e: save_site_data(e)
        )

        def on_site_change(e):
            key = self.dd_sites.value
            if key == "NEW_SITE_ADD":
                # Chế độ thêm mới: Xóa trắng, cho phép nhập tên
                self.inp_site_name.value = ""
                self.inp_site_name.read_only = False
                self.inp_site_name.focus()
                
                self.inp_site_url.value = ""
                self.btn_save_site.text = "Thêm nguồn mới"
                self.btn_save_site.bgcolor = PRIMARY
            elif key in self.sites_data:
                # Chế độ sửa: Điền dữ liệu cũ, khóa tên
                info = self.sites_data[key]
                self.inp_site_name.value = info['name']
                self.inp_site_name.read_only = True # Không cho sửa tên (để tránh lỗi key)
                
                self.inp_site_url.value = info['url']
                self.btn_save_site.text = "Cập nhật Link"
                self.btn_save_site.bgcolor = "#059669"
            
            self.inp_site_name.update()
            self.inp_site_url.update()
            self.btn_save_site.update()

        self.dd_sites.on_change = on_site_change

        def save_site_data(e):
            key = self.dd_sites.value
            name = self.inp_site_name.value
            url = self.inp_site_url.value
            
            if not url or "http" not in url:
                self.log("❌ URL không hợp lệ!", "red")
                return

            if key == "NEW_SITE_ADD":
                # Logic thêm mới
                if not name:
                    self.log("⚠️ Hãy nhập tên nguồn!", "yellow")
                    return
                success, msg = add_new_site(name, url)
                if success:
                    self.sites_data = load_sites()
                    self.dd_sites.options = get_site_options() # Reload dropdown
                    self.dd_sites.value = None # Reset
                    self.dd_sites.update()
                    # Reset form
                    self.inp_site_name.value = ""
                    self.inp_site_url.value = ""
                    self.inp_site_name.update()
                    self.inp_site_url.update()
            else:
                # Logic update link
                success, msg = update_site_url(key, url)
                if success:
                    self.sites_data = load_sites() # Reload data
            
            self.log(msg, "green" if success else "red")

        # --- TAB SETTINGS LAYOUT ---
        self.format_dropdown = ft.Dropdown(
            label="Định dạng ảnh", value="PNG",
            options=[ft.dropdown.Option("PNG"), ft.dropdown.Option("JPEG"), ft.dropdown.Option("ORIGINAL")],
            border_radius=10, bgcolor="#0f172a"
        )
        self.path_input = ft.TextField(
            value=self.download_path, label="Thư mục lưu", read_only=True,
            border_radius=10, bgcolor="#0f172a", expand=True, prefix_icon="folder"
        )

        tab_settings_layout = ft.Container(
            content=ft.Column([
                ft.Text("CÀI ĐẶT HỆ THỐNG", size=24, weight="bold", color="white"),
                ft.Divider(color="#334155"),
                
                ft.Container(
                    content=ft.Column([ft.Text("HÌNH ẢNH", weight="bold", color=PRIMARY), self.format_dropdown]), 
                    padding=20, bgcolor=BG_CARD, border_radius=10, animate=ft.animation.Animation(300, SMOOTH_CURVE)
                ),
                ft.Divider(height=10, color="transparent"),
                
                # [QUẢN LÝ NGUỒN NÂNG CẤP]
                ft.Container(
                    content=ft.Column([
                        ft.Text("QUẢN LÝ NGUỒN TRUYỆN", weight="bold", color=PRIMARY),
                        ft.Text("Sửa link cũ hoặc thêm web mới.", size=12, italic=True, color=TEXT_HINT),
                        ft.Container(height=10),
                        self.dd_sites,
                        self.inp_site_name,
                        self.inp_site_url,
                        ft.Container(height=10),
                        self.btn_save_site
                    ]), 
                    padding=20, bgcolor=BG_CARD, border_radius=10, animate=ft.animation.Animation(400, SMOOTH_CURVE)
                ),
                ft.Divider(height=10, color="transparent"),

                ft.Container(
                    content=ft.Column([
                        ft.Text("THƯ MỤC LƯU TRỮ", weight="bold", color=PRIMARY),
                        ft.Row([self.path_input, ft.IconButton(icon="folder_open", icon_color="yellow", bgcolor="#334155", on_click=lambda _: self.file_picker.get_directory_path())])
                    ]), 
                    padding=20, bgcolor=BG_CARD, border_radius=10, animate=ft.animation.Animation(500, SMOOTH_CURVE)
                ),
            ], scroll=ft.ScrollMode.AUTO),
            padding=30, alignment=ft.alignment.top_center, width=900, expand=True
        )

        self.tabs = ft.Tabs(
            selected_index=0, animation_duration=500, scrollable=False,
            indicator_color=PRIMARY, label_color=PRIMARY, indicator_border_radius=10,
            tabs=[
                ft.Tab(text="DASHBOARD", icon="dashboard", content=tab_home_layout),
                ft.Tab(text="SETTINGS", icon="settings", content=tab_settings_layout),
            ], expand=True
        )
        self.page.add(self.tabs)

    def log(self, message, color="white"):
        msg_color = {"cyan": "#22d3ee", "red": "#ef4444", "green": "#4ade80"}.get(color, color)
        self.log_view.controls.append(ft.Text(f"> {message}", color=msg_color, font_family="Consolas", size=13))
        self.page.update()
        self.log_view.scroll_to(offset=-1, duration=500, curve=ft.AnimationCurve.EASE_OUT_QUINT)
        if color == "red": log_error(message)
        else: log_info(message)

    def start_download_process(self, e): pass

def run_app(): ft.app(target=MangaApp)