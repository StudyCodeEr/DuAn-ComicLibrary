import flet as ft
import os
import sys
import json
import re
import logging

from mangalib import config as app_config
from mangalib import paths
from core.domain_manager import load_sites, update_site_url, add_new_site
from mangalib.db import engine, manga_repo, tag_repo
from utils.startup_helper import is_startup_enabled, toggle_startup

logger = logging.getLogger("mangalib.gui")

class MangaApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.download_path = str(paths.library_dir())
        self.sites_data = {}
        
        # --- QUẢN LÝ TAG STATE ---
        self.tag_states = {}    
        self.cached_tags = None 

        # --- BIẾN TRẠNG THÁI READER ---
        self.current_manga_path = ""
        self.chapters_list = []
        self.current_chap_index = -1
        self.reader_theme = "dark"
        self.is_taskbar_expanded = False
        self.current_zoom = 1.0
        self.is_ui_visible = True

        # Truoc day: dirname(__file__) -> tro vao .../gui, lech 1 cap, nen
        # smart_path_resolve chua bao gio chay dung o ban dev.
        self.base_dir = str(paths.data_root())

        self.load_config()
        self.setup_page()
        try:
            self.build_ui()
        except Exception as e:
            raise e

    # --- CONFIG & SETUP ---
    def load_config(self):
        """Doc config qua mangalib.config - mot duong duy nhat, khong nuot loi."""
        try:
            cfg = app_config.load()
        except app_config.ConfigError as exc:
            logger.error("config.toml co van de, dung mac dinh: %s", exc)
            cfg = app_config.AppConfig()
        self.download_path = cfg.library_override or str(paths.library_dir())
        os.makedirs(self.download_path, exist_ok=True)

    def save_config(self):
        cfg = app_config.load()
        app_config.save(cfg.model_copy(update={"library_override": self.download_path}))

    def setup_page(self):
        self.page.title = "Manga Local Library"
        self.page.window_icon = "app_icon.ico"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0f172a"
        self.page.window_width = 1100
        self.page.window_height = 800
        self.page.padding = 0
        self.page.window_prevent_close = True
        # API cu `page.on_window_event = handler` VO trong flet 0.24.1: shim
        # deprecated cua no gan `.handler` len page.window.on_event, ma getter
        # do tra ve chinh handler (None luc dau) -> AttributeError khi khoi tao.
        try:
            self.page.window.on_event = self.on_window_event
        except AttributeError:
            self.page.on_window_event = self.on_window_event
        if "--hidden" in sys.argv:
            self.page.window_visible = False
            self.page.window_minimized = True

        self.file_picker = ft.FilePicker(on_result=self.on_directory_selected)
        self.page.overlay.append(self.file_picker)

    def on_window_event(self, e):
        if e.data == "close":
            self.page.window_visible = False
            self.page.update()
            if hasattr(self, 'on_hide_to_tray'):
                self.on_hide_to_tray()


    def on_directory_selected(self, e):
        if e.path:
            self.download_path = e.path
            self.path_input.value = self.download_path
            self.path_input.update()
            self.save_config()

    def build_ui(self):
        PRIMARY = "#06b6d4"
        BG_CARD = "#1e293b"
        TEXT_HINT = "#64748b"
        SMOOTH_CURVE = ft.AnimationCurve.EASE_OUT_CUBIC

        # =================================================================
        # 1. GIAO DIỆN READER
        # =================================================================
        self.reader_list_view = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.padding.only(top=60, bottom=100)
        )

        self.reader_bg_container = ft.Container(
            content=self.reader_list_view,
            image_src="bg-dark.jpg",
            image_repeat=ft.ImageRepeat.REPEAT,
            image_fit=ft.ImageFit.NONE,
            expand=True,
            on_click=self.toggle_reader_ui
        )

        self.reader_title = ft.Text(
            "Đang đọc...", size=16, weight="bold", color="white",
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS
        )

        self.slider_zoom = ft.Slider(
            min=0.2, max=1.0, value=1.0, divisions=8, label="{value}",
            width=150, active_color=PRIMARY, inactive_color="grey",
            on_change=self.on_zoom_change
        )

        zoom_controls = ft.Row(
            [
                ft.Icon(ft.icons.ZOOM_OUT, color="white", size=16),
                self.slider_zoom,
                ft.Icon(ft.icons.ZOOM_IN, color="white", size=16),
            ],
            alignment=ft.MainAxisAlignment.CENTER, spacing=5
        )

        self.btn_theme_toggle = ft.IconButton(
            icon=ft.icons.LIGHT_MODE, icon_color="yellow",
            tooltip="Đổi giao diện Sáng/Tối", on_click=self.toggle_reader_theme
        )

        self.reader_header = ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon="arrow_back", icon_color="white",
                        on_click=self.close_reader, tooltip="Thoát"
                    ),
                    ft.Container(content=self.reader_title, expand=True),
                    ft.Container(content=zoom_controls, padding=ft.padding.only(right=10)),
                    self.btn_theme_toggle,
                    ft.IconButton(
                        icon="folder_open", icon_color="white", tooltip="Mở thư mục gốc",
                        on_click=lambda e: self.open_folder(self.current_manga_path)
                    ),
                ]
            ),
            padding=5, bgcolor="#0f172a",
            border=ft.border.only(bottom=ft.border.BorderSide(1, "#334155")),
            animate_opacity=300
        )

        self.btn_prev_chap = ft.IconButton(
            icon=ft.icons.SKIP_PREVIOUS, icon_color="white",
            on_click=lambda e: self.nav_chapter(-1), tooltip="Chap trước"
        )
        self.btn_next_chap = ft.IconButton(
            icon=ft.icons.SKIP_NEXT, icon_color="white",
            on_click=lambda e: self.nav_chapter(1), tooltip="Chap sau"
        )
        self.dd_chapters = ft.Dropdown(
            width=250, height=35, content_padding=5, text_size=13,
            bgcolor="#334155", border_color="white", color="white",
            on_change=self.on_chapter_selected
        )

        self.taskbar_controls = ft.Container(
            content=ft.Row(
                [self.btn_prev_chap, self.dd_chapters, self.btn_next_chap],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            bgcolor="#1e293b", padding=5, border_radius=30,
            border=ft.border.all(1, PRIMARY), visible=False, animate_opacity=300
        )

        self.btn_taskbar_toggle = ft.FloatingActionButton(
            icon=ft.icons.MENU, bgcolor=PRIMARY, mini=True,
            on_click=self.toggle_taskbar, tooltip="Mở thanh điều hướng",
            animate_opacity=300
        )

        self.reader_layer = ft.Stack(
            [
                self.reader_bg_container,
                ft.Column([self.reader_header], alignment=ft.MainAxisAlignment.START),
                ft.Column(
                    [
                        ft.Row([self.taskbar_controls], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row([ft.Container(expand=True), self.btn_taskbar_toggle], alignment=ft.MainAxisAlignment.END),
                    ],
                    alignment=ft.MainAxisAlignment.END, bottom=5, left=10, right=10
                ),
            ],
            visible=False, expand=True
        )

        # ==========================
        # 2. CÁC TAB CHÍNH
        # ==========================
        header_title = ft.Text("MANGA DOWNLOADER", size=30, weight="bold", color="white")
        header_sub = ft.Text("Tải truyện & Xây dựng kho truyện Local", size=12, color=TEXT_HINT)

        self.url_input = ft.TextField(
            hint_text="Dán Link truyện vào đây...", hint_style=ft.TextStyle(color=TEXT_HINT),
            border="none", bgcolor="transparent", text_size=15, cursor_color=PRIMARY,
            content_padding=10, selection_color=PRIMARY, keyboard_type=ft.KeyboardType.URL,
            expand=True
        )

        input_container = ft.Container(
            content=ft.Row([ft.Icon(name="link", color=PRIMARY, size=24), self.url_input]),
            padding=ft.padding.only(left=15, right=5, top=2, bottom=2),
            border=ft.border.all(2, PRIMARY), border_radius=15, bgcolor="#0f172a",
            animate=ft.animation.Animation(400, SMOOTH_CURVE)
        )

        self.btn_download = ft.ElevatedButton(
            text="KHỞI ĐỘNG TẢI XUỐNG", icon="download",
            style=ft.ButtonStyle(
                color="white", bgcolor=PRIMARY, padding=22,
                shape=ft.RoundedRectangleBorder(radius=12), elevation=10,
                animation_duration=400,
            ),
            width=400, on_click=self.start_download_process,
            animate_scale=ft.animation.Animation(100, ft.AnimationCurve.BOUNCE_OUT)
        )

        self.log_view = ft.Column(scroll=ft.ScrollMode.AUTO, auto_scroll=False, spacing=4)
        log_container = ft.Container(
            content=self.log_view, border=ft.border.all(1, "#334155"),
            border_radius=10, padding=15, bgcolor="black", height=250, width=float("inf")
        )

        tab_home_layout = ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=20),
                    ft.Column([header_title, header_sub], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(height=40, color="transparent"),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("LINK TRUYỆN", size=12, weight="bold", color=TEXT_HINT),
                                ft.Container(height=5),
                                input_container,
                            ]
                        ),
                        padding=25, bgcolor=BG_CARD, border_radius=15,
                        shadow=ft.BoxShadow(blur_radius=15, color="black"),
                    ),
                    ft.Divider(height=20, color="transparent"),
                    ft.Row([self.btn_download], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=20, color="transparent"),
                    ft.Text("TERMINAL LOGS:", font_family="Consolas", color=TEXT_HINT, size=12),
                    log_container,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True
            ),
            padding=30, alignment=ft.alignment.top_center, width=900, expand=True
        )

        self.library_grid = ft.GridView(
            runs_count=4, max_extent=250, child_aspect_ratio=0.7,
            spacing=20, run_spacing=20, expand=True
        )
        self.txt_search = ft.TextField(
            hint_text="Tìm truyện...", prefix_icon="search", height=40,
            content_padding=10, expand=True, on_submit=self.load_library_advanced
        )
        self.btn_filter = ft.ElevatedButton(
            "Bộ lọc Tag", icon="filter_list", bgcolor="#334155", color="white",
            on_click=self.open_tag_dialog
        )
        self.tag_summary_row = ft.Row(wrap=True)

        # --- KHỞI TẠO DIALOG TĨNH & GẮN VÀO OVERLAY ---
        # [QUAN TRỌNG] Tạo Dialog 1 lần duy nhất và nạp vào Overlay ngay lập tức
        self.tag_container_ref = ft.Column(
            scroll=ft.ScrollMode.AUTO, 
            height=300,
            expand=True
        )

        self.tag_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Bộ lọc"),
            content=ft.Container(
                content=self.tag_container_ref,
                width=600, height=400, padding=10
            ),
            actions=[
                ft.TextButton("Đóng", on_click=self.close_tag_dialog),
                ft.TextButton("Đặt lại", on_click=self.reset_tags),
                ft.ElevatedButton(
                    "Áp dụng", bgcolor=PRIMARY, color="white",
                    on_click=self.apply_filter,
                ),
            ],
        )
        # Nạp dialog vào overlay của page để đảm bảo nó luôn sẵn sàng hiển thị
        self.page.overlay.append(self.tag_dialog)

        tab_library_layout = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("KHO TRUYỆN LOCAL", size=24, weight="bold", color="white"),
                            ft.IconButton(icon="refresh", on_click=lambda e: self.load_library_advanced(None)),
                        ]
                    ),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            self.txt_search,
                            self.btn_filter,
                            ft.ElevatedButton(
                                "Tìm kiếm", on_click=self.load_library_advanced,
                                bgcolor=PRIMARY, color="white",
                            ),
                        ]
                    ),
                    self.tag_summary_row,
                    ft.Divider(color="#334155"),
                    ft.Container(content=self.library_grid, expand=True),
                ]
            ),
            padding=30, bgcolor=BG_CARD, expand=True
        )

        self.sites_data = load_sites()
        self.dd_sites = ft.Dropdown(
            label="Chọn nguồn", options=[], border_radius=10,
            bgcolor="#0f172a", width=float("inf"), on_change=self.on_site_dropdown_change
        )
        self.inp_site_name = ft.TextField(label="Tên hiển thị", border_radius=10, bgcolor="#0f172a", read_only=True)
        self.inp_site_url = ft.TextField(label="URL", border_radius=10, bgcolor="#0f172a")
        self.btn_save_site = ft.ElevatedButton(
            text="Lưu thay đổi", bgcolor="#059669", color="white",
            width=float("inf"), on_click=self.save_site_data
        )
        self.format_dropdown = ft.Dropdown(
            label="Định dạng ảnh", value="PNG",
            options=[
                ft.dropdown.Option("PNG"), 
                ft.dropdown.Option("JPEG"), 
                ft.dropdown.Option("ORIGINAL", text="Mặc định (Gốc)")
            ],
            border_radius=10, bgcolor="#0f172a"
        )
        self.path_input = ft.TextField(
            value=self.download_path, label="Thư mục lưu", read_only=True,
            border_radius=10, bgcolor="#0f172a", expand=True
        )
        self.sw_startup = ft.Switch(
            label="Tự khởi động cùng hệ thống (Ẩn dưới Tray)", 
            value=is_startup_enabled(),
            active_color=PRIMARY,
            on_change=lambda e: toggle_startup(self.sw_startup.value)
        )

        tab_settings_layout = ft.Container(
            content=ft.Column(
                [
                    ft.Text("CÀI ĐẶT HỆ THỐNG", size=24, weight="bold", color="white"),
                    ft.Divider(color="#334155"),
                    ft.Container(
                        content=ft.Column([ft.Text("HỆ THỐNG", weight="bold", color=PRIMARY), self.sw_startup]),
                        padding=20, bgcolor=BG_CARD, border_radius=10
                    ),
                    ft.Divider(height=10, color="transparent"),
                    ft.Container(
                        content=ft.Column([ft.Text("HÌNH ẢNH", weight="bold", color=PRIMARY), self.format_dropdown]),
                        padding=20, bgcolor=BG_CARD, border_radius=10
                    ),
                    ft.Divider(height=10, color="transparent"),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("QUẢN LÝ NGUỒN TRUYỆN", weight="bold", color=PRIMARY),
                                ft.Text("Sửa link cũ hoặc thêm web mới.", size=12, italic=True, color=TEXT_HINT),
                                ft.Container(height=10),
                                self.dd_sites, self.inp_site_name, self.inp_site_url,
                                ft.Container(height=10), self.btn_save_site,
                            ]
                        ),
                        padding=20, bgcolor=BG_CARD, border_radius=10
                    ),
                    ft.Divider(height=10, color="transparent"),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("THƯ MỤC LƯU TRỮ", weight="bold", color=PRIMARY),
                                ft.Row(
                                    [
                                        self.path_input,
                                        ft.IconButton(
                                            icon="folder_open", icon_color="yellow", bgcolor="#334155",
                                            on_click=lambda _: self.file_picker.get_directory_path(),
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        padding=20, bgcolor=BG_CARD, border_radius=10
                    ),
                ],
                scroll=ft.ScrollMode.AUTO
            ),
            padding=30, alignment=ft.alignment.top_center, width=900, expand=True
        )

        self.server_log_view = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        server_log_container = ft.Container(
            content=self.server_log_view, border=ft.border.all(1, "#334155"),
            border_radius=10, padding=15, bgcolor="black", expand=True
        )

        tab_console_layout = ft.Container(
            content=ft.Column(
                [
                    ft.Text("SERVER CONSOLE", size=24, weight="bold", color="white"),
                    ft.Text("Nhật ký hệ thống & Kết nối điện thoại", size=12, color=TEXT_HINT),
                    ft.Divider(color="#334155"),
                    server_log_container,
                ],
                expand=True
            ),
            padding=30, bgcolor=BG_CARD, expand=True
        )

        self.tabs = ft.Tabs(
            selected_index=0, indicator_color=PRIMARY, label_color=PRIMARY,
            tabs=[
                ft.Tab(text="DASHBOARD", icon="download", content=tab_home_layout),
                ft.Tab(text="THƯ VIỆN", icon="library_books", content=tab_library_layout),
                ft.Tab(text="SETTINGS", icon="settings", content=tab_settings_layout),
                ft.Tab(text="CONSOLE", icon="terminal", content=tab_console_layout)
            ],
            expand=True
        )

        self.main_stack = ft.Stack([self.tabs, self.reader_layer], expand=True)
        self.page.add(self.main_stack)

        self.fill_site_options()
        self.load_library_advanced(None)

    # --- SERVER LOG ---
    def log_server(self, message):
        self.server_log_view.controls.append(ft.Text(f"{message}", color="#fde047", font_family="Consolas", size=13))
        self.page.update()
        try: self.server_log_view.scroll_to(offset=-1, duration=100)
        except: pass

    # --- SETTINGS LOGIC ---
    def fill_site_options(self):
        opts = [ft.dropdown.Option(key, text=info["name"]) for key, info in self.sites_data.items()]
        opts.append(ft.dropdown.Option("NEW_SITE_ADD", text="➕ Thêm nguồn mới..."))
        self.dd_sites.options = opts
        self.dd_sites.update()

    def on_site_dropdown_change(self, e):
        key = self.dd_sites.value
        if key == "NEW_SITE_ADD":
            self.inp_site_name.value = ""
            self.inp_site_name.read_only = False
            self.inp_site_name.focus()
            self.inp_site_url.value = ""
            self.btn_save_site.text = "Thêm nguồn mới"
            self.btn_save_site.bgcolor = "#06b6d4"
        elif key in self.sites_data:
            info = self.sites_data[key]
            self.inp_site_name.value = info["name"]
            self.inp_site_name.read_only = True
            self.inp_site_url.value = info["url"]
            self.btn_save_site.text = "Cập nhật Link"
            self.btn_save_site.bgcolor = "#059669"
        self.inp_site_name.update()
        self.inp_site_url.update()
        self.btn_save_site.update()

    def save_site_data(self, e):
        key = self.dd_sites.value
        name = self.inp_site_name.value
        url = self.inp_site_url.value
        if not url or "http" not in url:
            self.log("❌ URL không hợp lệ!", "red")
            return
        if key == "NEW_SITE_ADD":
            if not name:
                self.log("⚠️ Hãy nhập tên nguồn!", "yellow")
                return
            success, msg = add_new_site(name, url)
            if success:
                self.sites_data = load_sites()
                self.fill_site_options()
                self.dd_sites.value = None
                self.inp_site_name.value = ""
                self.inp_site_url.value = ""
                self.dd_sites.update()
                self.inp_site_name.update()
                self.inp_site_url.update()
        else:
            success, msg = update_site_url(key, url)
            if success:
                self.sites_data = load_sites()
        self.log(msg, "green" if success else "red")

    # --- READER LOGIC ---
    def open_reader(self, path, title, manga_id=None):
        # Khong con khoi "tu sua duong dan trong DB" nua: DB luu slug, nen duong
        # dan luon la paths.library_dir()/slug. SQL tho trong lop UI cung di theo.
        real_path = path

        self.current_manga_path = real_path
        self.reader_title.value = title
        self.is_taskbar_expanded = False
        self.taskbar_controls.visible = False
        self.btn_taskbar_toggle.icon = ft.icons.MENU
        self.btn_taskbar_toggle.bgcolor = "#06b6d4"
        self.slider_zoom.value = 1.0
        self.current_zoom = 1.0

        self.is_ui_visible = True
        self.reader_header.opacity = 1
        self.btn_taskbar_toggle.opacity = 1
        self.taskbar_controls.opacity = 0

        self.chapters_list = []
        if os.path.exists(real_path):
            try:
                all_items = os.listdir(real_path)
                folders = [f for f in all_items if os.path.isdir(os.path.join(real_path, f))]
                if folders:
                    self.chapters_list = folders
                    self.dd_chapters.options = [ft.dropdown.Option(c) for c in self.chapters_list]
                    self.load_chapter_content(0)
                else:
                    self.chapters_list = ["Oneshot/Full"]
                    self.dd_chapters.options = [ft.dropdown.Option("Oneshot/Full")]
                    self.load_chapter_content(0, is_flat=True)
            except Exception as e:
                self.reader_list_view.controls = [ft.Text(f"Lỗi: {e}", color="red")]
        else:
            self.reader_list_view.controls = [ft.Text(f"Không tìm thấy thư mục: {real_path}", color="red", size=20)]

        self.reader_layer.visible = True
        self.reader_layer.update()

    def toggle_reader_ui(self, e):
        self.is_ui_visible = not self.is_ui_visible
        new_opacity = 1 if self.is_ui_visible else 0
        self.reader_header.opacity = new_opacity
        self.btn_taskbar_toggle.opacity = new_opacity
        if self.is_taskbar_expanded:
            self.taskbar_controls.opacity = new_opacity
        self.reader_layer.update()

    def load_chapter_content(self, index, is_flat=False):
        self.current_chap_index = index
        self.reader_list_view.controls.clear()
        if 0 <= index < len(self.chapters_list):
            self.dd_chapters.value = self.chapters_list[index]
            self.dd_chapters.update()
            self.btn_prev_chap.disabled = index == 0
            self.btn_next_chap.disabled = index == len(self.chapters_list) - 1
            self.btn_prev_chap.update()
            self.btn_next_chap.update()

        if is_flat:
            chap_path = self.current_manga_path
        else:
            chap_path = os.path.join(self.current_manga_path, self.chapters_list[index])

        if os.path.exists(chap_path):
            files = sorted([f for f in os.listdir(chap_path) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])
            if not files:
                self.reader_list_view.controls.append(
                    ft.Container(content=ft.Text("Chapter trống!", size=20, color="grey"), alignment=ft.alignment.center, padding=50)
                )
            else:
                current_window_width = self.page.width if self.page.width else 1000
                display_width = current_window_width * self.current_zoom
                for f in files:
                    img_path = os.path.join(chap_path, f)
                    img = ft.Image(src=img_path, fit=ft.ImageFit.CONTAIN, width=display_width, gapless_playback=True)
                    self.reader_list_view.controls.append(ft.Row([img], alignment=ft.MainAxisAlignment.CENTER, spacing=0))
        try:
            self.reader_list_view.scroll_to(offset=0, duration=100)
        except:
            pass
        self.reader_layer.update()

    def on_zoom_change(self, e):
        self.current_zoom = e.control.value
        current_window_width = self.page.width if self.page.width else 1000
        new_width = current_window_width * self.current_zoom
        for control in self.reader_list_view.controls:
            if isinstance(control, ft.Row) and control.controls:
                img_widget = control.controls[0]
                if isinstance(img_widget, ft.Image):
                    img_widget.width = new_width
        self.reader_list_view.update()

    def nav_chapter(self, delta):
        new_index = self.current_chap_index + delta
        if 0 <= new_index < len(self.chapters_list):
            self.load_chapter_content(new_index)

    def on_chapter_selected(self, e):
        val = self.dd_chapters.value
        if val in self.chapters_list:
            self.load_chapter_content(self.chapters_list.index(val))

    def toggle_taskbar(self, e):
        self.is_taskbar_expanded = not self.is_taskbar_expanded
        self.taskbar_controls.visible = self.is_taskbar_expanded
        self.taskbar_controls.opacity = 1 if self.is_taskbar_expanded else 0
        if self.is_taskbar_expanded:
            self.btn_taskbar_toggle.icon = ft.icons.CLOSE
            self.btn_taskbar_toggle.bgcolor = "#ef4444"
        else:
            self.btn_taskbar_toggle.icon = ft.icons.MENU
            self.btn_taskbar_toggle.bgcolor = "#06b6d4"
        self.reader_layer.update()

    def toggle_reader_theme(self, e):
        if self.reader_theme == "dark":
            self.reader_theme = "light"
            self.reader_bg_container.image_src = "bg-light.jpg"
            self.btn_theme_toggle.icon = ft.icons.DARK_MODE
            self.btn_theme_toggle.icon_color = "black"
            self.reader_title.color = "black"
            self.reader_header.bgcolor = "white"
            self.reader_header.border = ft.border.only(bottom=ft.border.BorderSide(1, "#e2e8f0"))
            for ctrl in self.reader_header.content.controls:
                if isinstance(ctrl, ft.IconButton):
                    ctrl.icon_color = "black"
        else:
            self.reader_theme = "dark"
            self.reader_bg_container.image_src = "bg-dark.jpg"
            self.btn_theme_toggle.icon = ft.icons.LIGHT_MODE
            self.btn_theme_toggle.icon_color = "yellow"
            self.reader_title.color = "white"
            self.reader_header.bgcolor = "#0f172a"
            self.reader_header.border = ft.border.only(bottom=ft.border.BorderSide(1, "#334155"))
            for ctrl in self.reader_header.content.controls:
                if isinstance(ctrl, ft.IconButton) and ctrl != self.btn_theme_toggle:
                    ctrl.icon_color = "white"
        self.reader_layer.update()

    def close_reader(self, e):
        self.reader_layer.visible = False
        self.reader_layer.update()
        self.reader_list_view.controls.clear()

    def open_folder(self, path):
        real_path = path
        if os.path.exists(real_path):
            os.startfile(real_path)

    def log(self, message, color="white"):
        msg_color = {"cyan": "#22d3ee", "red": "#ef4444", "green": "#4ade80"}.get(color, color)
        self.log_view.controls.append(ft.Text(f"> {message}", color=msg_color, font_family="Consolas", size=13))
        self.page.update()
        try:
            self.log_view.scroll_to(offset=-1, duration=500, curve=ft.AnimationCurve.EASE_OUT_QUINT)
        except:
            pass
        if color == "red":
            logger.error(message)
        else:
            logger.info(message)

    # -------------------------------------------------------------
    # LOGIC BỘ LỌC ĐÃ SỬA LỖI KHÔNG PHẢN HỒI (DÙNG OVERLAY)
    # -------------------------------------------------------------

    def get_tags_safe(self):
        """Tải tag từ Cache hoặc DB."""
        if self.cached_tags is not None and len(self.cached_tags) > 0:
            return self.cached_tags
        try:
            with engine.read_only() as conn:
                # list_all tra (ten, so truyen); UI cu chi can ten.
                self.cached_tags = [name for name, _count in tag_repo.list_all(conn)]
        except Exception as exc:
            logger.error("Khong tai duoc danh sach the loai: %s", exc)
            return []
        return self.cached_tags

    def open_tag_dialog(self, e):
        """
        Chỉ cập nhật dữ liệu và hiển thị Dialog (vốn đã có sẵn trong Overlay).
        """
        # 1. Vẽ lại nội dung vào khung đã có
        self.render_tag_grid()

        # 2. Bật hiển thị Dialog
        self.tag_dialog.open = True
        self.tag_dialog.update() # Chỉ cần update dialog là đủ

    def render_tag_grid(self):
        """
        Tạo danh sách nút mới và gán đè vào Column cũ.
        """
        all_tags = self.get_tags_safe()
        
        controls_list = []
        if not all_tags:
             controls_list.append(ft.Text("Không tải được danh sách Tag hoặc DB trống!", color="red"))
        else:
            for tag in all_tags:
                state = self.tag_states.get(tag, 0)
                btn = ft.ElevatedButton(
                    text=tag,
                    data=tag,
                    on_click=self.on_tag_clicked,
                    style=self.get_pure_style(state),
                )
                controls_list.append(btn)

        # [QUAN TRỌNG] Gán đè list controls (Thay vì append)
        self.tag_container_ref.controls = [
            ft.Row(
                controls=controls_list,
                wrap=True, spacing=5, run_spacing=5
            )
        ]
        # Cập nhật UI của cột tag
        self.tag_container_ref.update()

    def on_tag_clicked(self, e):
        tag = e.control.data
        current_state = self.tag_states.get(tag, 0)
        new_state = (current_state + 1) % 3

        if new_state == 0:
            if tag in self.tag_states: del self.tag_states[tag]
        else:
            self.tag_states[tag] = new_state

        self.render_tag_grid()

    def get_pure_style(self, state):
        if state == 1: return ft.ButtonStyle(bgcolor="#22c55e", color="white") 
        elif state == 2: return ft.ButtonStyle(bgcolor="#ef4444", color="white")
        else: return ft.ButtonStyle(bgcolor="#334155", color="#94a3b8")

    def reset_tags(self, e):
        self.tag_states.clear()
        self.render_tag_grid()

    def apply_filter(self, e):
        self.tag_dialog.open = False
        self.tag_dialog.update()
        self.load_library_advanced(None)

    def close_tag_dialog(self, e):
        self.tag_dialog.open = False
        self.tag_dialog.update()

    def load_library_advanced(self, e):
        keyword = self.txt_search.value
        include = [t for t, s in self.tag_states.items() if s == 1]
        exclude = [t for t, s in self.tag_states.items() if s == 2]
        
        self.tag_summary_row.controls.clear()
        for t in include:
            self.tag_summary_row.controls.append(ft.Container(content=ft.Text(f"+ {t}", size=12), bgcolor="#22c55e", padding=5, border_radius=5))
        for t in exclude:
            self.tag_summary_row.controls.append(ft.Container(content=ft.Text(f"- {t}", size=12), bgcolor="#ef4444", padding=5, border_radius=5))
        self.tag_summary_row.update()
        
        with engine.read_only() as conn:
            items, _total = manga_repo.search(
                conn,
                q=keyword or "",
                include_tags=include,
                exclude_tags=exclude,
                per_page=200,
            )
        # Duong dan dung tu slug (quy tac R5), nen khong con cho nao luu path tuyet doi.
        results = [
            (
                item.id,
                item.title,
                str(paths.manga_dir(item.slug)),
                str(paths.manga_dir(item.slug) / item.cover_file) if item.cover_file else None,
            )
            for item in items
        ]
        
        self.library_grid.controls.clear()
        if not results:
            self.library_grid.controls.append(ft.Text("Không tìm thấy truyện phù hợp!", color="grey"))
        else:
            for m_id, title, path, real_cover_path in results:
                image_content = ft.Image(
                    src=(real_cover_path if real_cover_path and os.path.exists(real_cover_path) else "assets/icon.png"),
                    fit=ft.ImageFit.COVER, width=float("inf"), height=float("inf"),
                    error_content=ft.Icon("broken_image"), opacity=1 if real_cover_path else 0.5
                )
                card = ft.Container(
                    content=ft.Stack(
                        [
                            ft.Container(content=image_content, border_radius=10),
                            ft.Container(
                                gradient=ft.LinearGradient(
                                    begin=ft.alignment.top_center, end=ft.alignment.bottom_center,
                                    colors=[ft.colors.with_opacity(0, "black"), ft.colors.with_opacity(0.9, "black")], stops=[0.5, 1.0]
                                ),
                                border_radius=10
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(title, size=14, weight="bold", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, color="white"),
                                        ft.ElevatedButton(
                                            "Đọc ngay",
                                            style=ft.ButtonStyle(padding=10, bgcolor="#06b6d4", color="white", shape=ft.RoundedRectangleBorder(radius=8)),
                                            width=float("inf"),
                                            on_click=lambda _, p=path, t=title, m=m_id: self.open_reader(p, t, m)
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END, spacing=5
                                ),
                                padding=10, alignment=ft.alignment.bottom_center
                            ),
                        ]
                    ),
                    bgcolor="#1e293b", border=ft.border.all(1, "#334155"), border_radius=10,
                    on_click=lambda _, p=path, t=title, m=m_id: self.open_reader(p, t, m), tooltip=title
                )
                self.library_grid.controls.append(card)
        self.library_grid.update()

    def start_download_process(self, e):
        pass

def run_app():
    ft.app(target=MangaApp)