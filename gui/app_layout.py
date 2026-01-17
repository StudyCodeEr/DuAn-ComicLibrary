import flet as ft
import os
import sys
import json
import re
from utils.logger import log_info, log_error
from core.domain_manager import load_sites, update_site_url, add_new_site
from core.database import DatabaseManager

CONFIG_FILE = "config.json"

class MangaApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.download_path = "Downloads"
        self.sites_data = {} 
        self.tag_states = {} 
        
        # --- BIẾN TRẠNG THÁI READER ---
        self.current_manga_path = ""
        self.chapters_list = []      
        self.current_chap_index = -1 
        self.reader_theme = "dark"   
        self.is_taskbar_expanded = False 
        self.current_zoom = 1.0 
        
        self.load_config()
        self.setup_page()
        try:
            self.build_ui()
        except Exception as e:
            raise e

    # --- CONFIG & SETUP ---
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
            pass

    def setup_page(self):
        self.page.title = "Manga Local Library"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0f172a" 
        self.page.window_width = 1100
        self.page.window_height = 800
        self.page.padding = 0
        self.file_picker = ft.FilePicker(on_result=self.on_directory_selected)
        self.page.overlay.append(self.file_picker)

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
        # 1. GIAO DIỆN READER (LỚP TRÊN CÙNG)
        # =================================================================
        
        self.reader_list_view = ft.ListView(expand=True, spacing=0, padding=0)
        
        # Container chứa ảnh nền
        self.reader_bg_container = ft.Container(
            content=self.reader_list_view,
            image_src="bg-dark.jpg",            
            image_repeat=ft.ImageRepeat.REPEAT, 
            image_fit=ft.ImageFit.NONE,
            expand=True
        )

        self.reader_title = ft.Text("Đang đọc...", size=16, weight="bold", color="white", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        
        # [MỚI] Slider Zoom đưa lên Header
        self.slider_zoom = ft.Slider(
            min=0.2, max=1.0, value=1.0, divisions=8, 
            label="{value}", width=150, # Kích thước nhỏ gọn hơn cho Header
            active_color=PRIMARY, inactive_color="grey",
            on_change=self.on_zoom_change
        )
        
        zoom_controls = ft.Row([
            ft.Icon(ft.icons.ZOOM_OUT, color="white", size=16),
            self.slider_zoom,
            ft.Icon(ft.icons.ZOOM_IN, color="white", size=16),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)

        self.btn_theme_toggle = ft.IconButton(
            icon=ft.icons.LIGHT_MODE, 
            icon_color="yellow", 
            tooltip="Đổi giao diện Sáng/Tối",
            on_click=self.toggle_reader_theme
        )

        # [HEADER CẬP NHẬT] Thêm Zoom vào đây
        self.reader_header = ft.Container(
            content=ft.Row([
                ft.IconButton(icon="arrow_back", icon_color="white", on_click=self.close_reader, tooltip="Thoát"),
                ft.Container(content=self.reader_title, expand=True), 
                
                # Cụm điều khiển Zoom
                ft.Container(content=zoom_controls, padding=ft.padding.only(right=10)),
                
                self.btn_theme_toggle,
                ft.IconButton(icon="folder_open", icon_color="white", tooltip="Mở thư mục gốc", 
                              on_click=lambda e: self.open_folder(self.current_manga_path))
            ]),
            padding=5, bgcolor="#0f172a", 
            border=ft.border.only(bottom=ft.border.BorderSide(1, "#334155"))
        )

        # --- Taskbar Controls ---
        self.btn_prev_chap = ft.IconButton(icon=ft.icons.SKIP_PREVIOUS, icon_color="white", on_click=lambda e: self.nav_chapter(-1), tooltip="Chap trước")
        self.btn_next_chap = ft.IconButton(icon=ft.icons.SKIP_NEXT, icon_color="white", on_click=lambda e: self.nav_chapter(1), tooltip="Chap sau")
        self.dd_chapters = ft.Dropdown(
            width=250, height=35, content_padding=5, 
            text_size=13, bgcolor="#334155", border_color="white", color="white",
            on_change=self.on_chapter_selected
        )

        self.taskbar_controls = ft.Container(
            content=ft.Row([
                self.btn_prev_chap,
                self.dd_chapters,
                self.btn_next_chap
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#1e293b", padding=5, border_radius=30,
            border=ft.border.all(1, PRIMARY),
            visible=False, 
            animate_opacity=300
        )

        self.btn_taskbar_toggle = ft.FloatingActionButton(
            icon=ft.icons.MENU, bgcolor=PRIMARY, mini=True,
            on_click=self.toggle_taskbar, tooltip="Mở thanh điều hướng"
        )

        # [CHỈNH SỬA VỊ TRÍ] Hạ thấp sát đáy (bottom=0)
        self.reader_layer = ft.Stack([
            self.reader_bg_container, 
            ft.Column([self.reader_header], alignment=ft.MainAxisAlignment.START), 
            ft.Column([
                ft.Row([self.taskbar_controls], alignment=ft.MainAxisAlignment.CENTER),
                # Bỏ bớt khoảng trống ở đây để sát hơn
                ft.Row([ft.Container(expand=True), self.btn_taskbar_toggle], alignment=ft.MainAxisAlignment.END)
            ], 
            alignment=ft.MainAxisAlignment.END, 
            bottom=10, # Cách đáy 10px để không bị dính sát mép quá (nếu muốn dính hẳn thì để 0)
            left=10, right=10)
        ], visible=False, expand=True)

        # ==========================
        # 2. CÁC TAB CHÍNH (LỚP DƯỚI)
        # ==========================
        
        # --- TAB 1: DASHBOARD ---
        header_title = ft.Text("MANGA DOWNLOADER", size=30, weight="bold", color="white")
        header_sub = ft.Text("Tải truyện & Xây dựng kho truyện Local", size=12, color=TEXT_HINT)
        
        self.url_input = ft.TextField(
            hint_text="Dán Link truyện vào đây...",
            hint_style=ft.TextStyle(color=TEXT_HINT),
            border="none", bgcolor="transparent", text_size=15,
            cursor_color=PRIMARY, content_padding=10,
            selection_color=PRIMARY, keyboard_type=ft.KeyboardType.URL,
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
                animation_duration=400
            ),
            width=400, on_click=self.start_download_process,
            animate_scale=ft.animation.Animation(100, ft.AnimationCurve.BOUNCE_OUT)
        )

        self.log_view = ft.Column(scroll=ft.ScrollMode.AUTO, auto_scroll=False, spacing=4)
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, "#334155"), border_radius=10, padding=15,
            bgcolor="black", 
            height=250, 
            width=float('inf')
        )
        
        tab_home_layout = ft.Container(
            content=ft.Column([
                ft.Container(height=20),
                ft.Column([header_title, header_sub], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=40, color="transparent"),
                ft.Container(
                    content=ft.Column([ft.Text("LINK TRUYỆN", size=12, weight="bold", color=TEXT_HINT), ft.Container(height=5), input_container]),
                    padding=25, bgcolor=BG_CARD, border_radius=15,
                    shadow=ft.BoxShadow(blur_radius=15, color="black")
                ),
                ft.Divider(height=20, color="transparent"),
                ft.Row([self.btn_download], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=20, color="transparent"),
                ft.Text("TERMINAL LOGS:", font_family="Consolas", color=TEXT_HINT, size=12),
                log_container
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            padding=30, alignment=ft.alignment.top_center, width=900, expand=True,
        )

        # --- TAB 2: LIBRARY ---
        self.library_grid = ft.GridView(runs_count=4, max_extent=250, child_aspect_ratio=0.7, spacing=20, run_spacing=20, expand=True)
        self.txt_search = ft.TextField(hint_text="Tìm truyện...", prefix_icon="search", height=40, content_padding=10, expand=True, on_submit=self.load_library_advanced)
        self.btn_filter = ft.ElevatedButton("Bộ lọc Tag", icon="filter_list", bgcolor="#334155", color="white", on_click=self.open_tag_dialog)
        self.tag_summary_row = ft.Row(wrap=True)
        self.tag_dialog_content = ft.Row(wrap=True, spacing=5, run_spacing=5)
        self.tag_dialog = ft.AlertDialog(modal=True, title=ft.Text("Bộ lọc"), content=ft.Container(content=self.tag_dialog_content, width=600, height=400), actions=[ft.TextButton("Đóng", on_click=self.close_tag_dialog), ft.TextButton("Đặt lại", on_click=self.reset_tags), ft.ElevatedButton("Áp dụng", bgcolor=PRIMARY, color="white", on_click=self.apply_filter)])
        
        tab_library_layout = ft.Container(content=ft.Column([ft.Row([ft.Text("KHO TRUYỆN LOCAL", size=24, weight="bold", color="white"), ft.IconButton(icon="refresh", on_click=lambda e: self.load_library_advanced(None))]), ft.Container(height=10), ft.Row([self.txt_search, self.btn_filter, ft.ElevatedButton("Tìm kiếm", on_click=self.load_library_advanced, bgcolor=PRIMARY, color="white")]), self.tag_summary_row, ft.Divider(color="#334155"), ft.Container(content=self.library_grid, expand=True)]), padding=30, bgcolor=BG_CARD, expand=True)

        # --- TAB 3: SETTINGS ---
        self.sites_data = load_sites()
        self.dd_sites = ft.Dropdown(label="Chọn nguồn", options=[], border_radius=10, bgcolor="#0f172a", width=float('inf'), on_change=self.on_site_dropdown_change)
        self.inp_site_name = ft.TextField(label="Tên hiển thị", border_radius=10, bgcolor="#0f172a", read_only=True)
        self.inp_site_url = ft.TextField(label="URL", border_radius=10, bgcolor="#0f172a")
        self.btn_save_site = ft.ElevatedButton(text="Lưu thay đổi", bgcolor="#059669", color="white", width=float('inf'), on_click=self.save_site_data)
        self.format_dropdown = ft.Dropdown(
            label="Định dạng ảnh", value="PNG", 
            options=[
                ft.dropdown.Option("PNG"), 
                ft.dropdown.Option("JPEG"), 
                ft.dropdown.Option("ORIGINAL", text="Mặc định (Gốc)")
            ], 
            border_radius=10, bgcolor="#0f172a"
        )
        self.path_input = ft.TextField(value=self.download_path, label="Thư mục lưu", read_only=True, border_radius=10, bgcolor="#0f172a", expand=True)
        
        tab_settings_layout = ft.Container(content=ft.Column([
            ft.Text("CÀI ĐẶT HỆ THỐNG", size=24, weight="bold", color="white"), ft.Divider(color="#334155"), 
            ft.Container(content=ft.Column([ft.Text("HÌNH ẢNH", weight="bold", color=PRIMARY), self.format_dropdown]), padding=20, bgcolor=BG_CARD, border_radius=10), 
            ft.Divider(height=10, color="transparent"), 
            ft.Container(content=ft.Column([ft.Text("QUẢN LÝ NGUỒN TRUYỆN", weight="bold", color=PRIMARY), ft.Text("Sửa link cũ hoặc thêm web mới.", size=12, italic=True, color=TEXT_HINT), ft.Container(height=10), self.dd_sites, self.inp_site_name, self.inp_site_url, ft.Container(height=10), self.btn_save_site]), padding=20, bgcolor=BG_CARD, border_radius=10),
            ft.Divider(height=10, color="transparent"), 
            ft.Container(content=ft.Column([ft.Text("THƯ MỤC LƯU TRỮ", weight="bold", color=PRIMARY), ft.Row([self.path_input, ft.IconButton(icon="folder_open", icon_color="yellow", bgcolor="#334155", on_click=lambda _: self.file_picker.get_directory_path())])]), padding=20, bgcolor=BG_CARD, border_radius=10)
        ], scroll=ft.ScrollMode.AUTO), padding=30, alignment=ft.alignment.top_center, width=900, expand=True)

        self.tabs = ft.Tabs(selected_index=0, indicator_color=PRIMARY, label_color=PRIMARY, tabs=[ft.Tab(text="DASHBOARD", icon="download", content=tab_home_layout), ft.Tab(text="THƯ VIỆN", icon="library_books", content=tab_library_layout), ft.Tab(text="SETTINGS", icon="settings", content=tab_settings_layout)], expand=True)
        
        self.main_stack = ft.Stack([self.tabs, self.reader_layer], expand=True)
        self.page.add(self.main_stack)
        
        self.fill_site_options() 
        self.load_library_advanced(None)

    # --- LOGIC SETTINGS ---
    def fill_site_options(self):
        opts = [ft.dropdown.Option(key, text=info['name']) for key, info in self.sites_data.items()]
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
            self.inp_site_name.value = info['name']
            self.inp_site_name.read_only = True 
            self.inp_site_url.value = info['url']
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

    # --- LOGIC READER (ZOOM & NAVIGATION) ---
    def open_reader(self, path, title):
        self.current_manga_path = path
        self.reader_title.value = title
        self.is_taskbar_expanded = False
        self.taskbar_controls.visible = False
        self.btn_taskbar_toggle.icon = ft.icons.MENU
        self.btn_taskbar_toggle.bgcolor = "#06b6d4"
        self.slider_zoom.value = 1.0 # Reset zoom
        self.current_zoom = 1.0
        
        self.chapters_list = []
        if os.path.exists(path):
            try:
                all_items = os.listdir(path)
                folders = [f for f in all_items if os.path.isdir(os.path.join(path, f))]
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
        
        self.reader_layer.visible = True
        self.reader_layer.update()

    def load_chapter_content(self, index, is_flat=False):
        self.current_chap_index = index
        self.reader_list_view.controls.clear()
        if 0 <= index < len(self.chapters_list):
            self.dd_chapters.value = self.chapters_list[index]
            self.dd_chapters.update()
            self.btn_prev_chap.disabled = (index == 0)
            self.btn_next_chap.disabled = (index == len(self.chapters_list) - 1)
            self.btn_prev_chap.update()
            self.btn_next_chap.update()

        if is_flat: chap_path = self.current_manga_path
        else: chap_path = os.path.join(self.current_manga_path, self.chapters_list[index])

        if os.path.exists(chap_path):
            files = sorted([f for f in os.listdir(chap_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            if not files:
                self.reader_list_view.controls.append(ft.Container(content=ft.Text("Chapter trống!", size=20, color="grey"), alignment=ft.alignment.center, padding=50))
            else:
                current_window_width = self.page.width if self.page.width else 1000
                display_width = current_window_width * self.current_zoom
                
                for f in files:
                    img_path = os.path.join(chap_path, f)
                    img = ft.Image(
                        src=img_path, 
                        fit=ft.ImageFit.CONTAIN, 
                        width=display_width, 
                        gapless_playback=True
                    )
                    row = ft.Row([img], alignment=ft.MainAxisAlignment.CENTER, spacing=0)
                    self.reader_list_view.controls.append(row)
        
        try: self.reader_list_view.scroll_to(offset=0, duration=100)
        except: pass
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
                if isinstance(ctrl, ft.IconButton): ctrl.icon_color = "black"
        else:
            self.reader_theme = "dark"
            self.reader_bg_container.image_src = "bg-dark.jpg"
            self.btn_theme_toggle.icon = ft.icons.LIGHT_MODE
            self.btn_theme_toggle.icon_color = "yellow"
            self.reader_title.color = "white"
            self.reader_header.bgcolor = "#0f172a"
            self.reader_header.border = ft.border.only(bottom=ft.border.BorderSide(1, "#334155"))
            for ctrl in self.reader_header.content.controls:
                if isinstance(ctrl, ft.IconButton) and ctrl != self.btn_theme_toggle: ctrl.icon_color = "white"
        self.reader_layer.update()

    def close_reader(self, e):
        self.reader_layer.visible = False
        self.reader_layer.update()
        self.reader_list_view.controls.clear()

    # --- UTILS ---
    def open_folder(self, path):
        if os.path.exists(path): os.startfile(path)
    
    def log(self, message, color="white"):
        msg_color = {"cyan": "#22d3ee", "red": "#ef4444", "green": "#4ade80"}.get(color, color)
        self.log_view.controls.append(ft.Text(f"> {message}", color=msg_color, font_family="Consolas", size=13))
        self.page.update()
        try: self.log_view.scroll_to(offset=-1, duration=500, curve=ft.AnimationCurve.EASE_OUT_QUINT)
        except: pass 
        if color == "red": log_error(message)
        else: log_info(message)

    # Filter Logic
    def open_tag_dialog(self, e):
        db = DatabaseManager()
        all_tags = db.get_all_tags()
        db.close()
        self.tag_dialog_content.controls.clear()
        for tag in all_tags:
            current_state = self.tag_states.get(tag, 0)
            btn = ft.ElevatedButton(text=tag, data=tag, on_click=self.toggle_tag_state, style=self.get_tag_style(current_state))
            self.tag_dialog_content.controls.append(btn)
        self.page.dialog = self.tag_dialog
        self.tag_dialog.open = True
        self.page.update()

    def close_tag_dialog(self, e):
        self.tag_dialog.open = False
        self.page.update()

    def toggle_tag_state(self, e):
        tag = e.control.data
        current_state = self.tag_states.get(tag, 0)
        new_state = (current_state + 1) % 3
        self.tag_states[tag] = new_state
        e.control.style = self.get_tag_style(new_state)
        e.control.update()

    def get_tag_style(self, state):
        if state == 1: return ft.ButtonStyle(bgcolor="#22c55e", color="white") 
        elif state == 2: return ft.ButtonStyle(bgcolor="#ef4444", color="white")
        else: return ft.ButtonStyle(bgcolor="#334155", color="#94a3b8")

    def reset_tags(self, e):
        self.tag_states = {}
        for btn in self.tag_dialog_content.controls:
            btn.style = self.get_tag_style(0)
            btn.update()

    def apply_filter(self, e):
        self.tag_dialog.open = False
        self.page.update()
        self.load_library_advanced(None)

    def load_library_advanced(self, e):
        keyword = self.txt_search.value
        include = [t for t, s in self.tag_states.items() if s == 1]
        exclude = [t for t, s in self.tag_states.items() if s == 2]
        self.tag_summary_row.controls.clear()
        for t in include: self.tag_summary_row.controls.append(ft.Container(content=ft.Text(f"+ {t}", size=12), bgcolor="#22c55e", padding=5, border_radius=5))
        for t in exclude: self.tag_summary_row.controls.append(ft.Container(content=ft.Text(f"- {t}", size=12), bgcolor="#ef4444", padding=5, border_radius=5))
        self.tag_summary_row.update()
        db = DatabaseManager()
        results = db.search_advanced(keyword, include, exclude)
        db.close()
        self.library_grid.controls.clear()
        if not results:
            self.library_grid.controls.append(ft.Text("Không tìm thấy truyện phù hợp!", color="grey"))
        else:
            for m_id, title, path, cover_path in results:
                has_cover = cover_path and os.path.exists(cover_path) and os.path.getsize(cover_path) > 0
                image_content = ft.Image(src=cover_path if has_cover else "assets/icon.png", fit=ft.ImageFit.COVER, width=float('inf'), height=float('inf'), error_content=ft.Icon("broken_image"), opacity=1 if has_cover else 0.5)
                card = ft.Container(content=ft.Stack([ft.Container(content=image_content, border_radius=10), ft.Container(gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[ft.colors.with_opacity(0, "black"), ft.colors.with_opacity(0.9, "black")], stops=[0.5, 1.0]), border_radius=10), ft.Container(content=ft.Column([ft.Text(title, size=14, weight="bold", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, color="white"), ft.ElevatedButton("Đọc ngay", style=ft.ButtonStyle(padding=10, bgcolor="#06b6d4", color="white", shape=ft.RoundedRectangleBorder(radius=8)), width=float('inf'), on_click=lambda _, p=path, t=title: self.open_reader(p, t))], alignment=ft.MainAxisAlignment.END, spacing=5), padding=10, alignment=ft.alignment.bottom_center)]), bgcolor="#1e293b", border=ft.border.all(1, "#334155"), border_radius=10, on_click=lambda _, p=path, t=title: self.open_reader(p, t), tooltip=title)
                self.library_grid.controls.append(card)
        self.library_grid.update()

    def start_download_process(self, e): pass

def run_app(): ft.app(target=MangaApp)