import os
import json
import queue
import customtkinter as ctk

try:
    import windnd
except ImportError:
    windnd = None

from config import *
from ui_common import FloatingProgressWidget
from ui_tab_bg import TabBackground
from ui_tab_eraser import TabEraser
from ui_tab_upscale import TabUpscale
from ui_tab_settings import TabSettings

class CleanCutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.settings = self.load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))

        self.title("CleanCut Studio Pro")
        self.geometry("920x640") # 뷰포트를 살짝 넓혀 쾌적한 작업 공간 확보
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_page_name = "bg"
        self.floating_prog = FloatingProgressWidget(self)

        # [안전 장치] 드래그 앤 드롭 전용 우체통(Queue) 생성 및 확인 루틴 시작
        self.drop_queue = queue.Queue()
        self.check_drop_queue() 

        self.setup_sidebar()
        self.setup_pages()
        self.select_page("bg")

        if windnd is not None:
            try:
                windnd.hook_dropfiles(self, func=self.on_drop_files)
            except Exception:
                pass

    def check_drop_queue(self):
        """0.1초마다 우체통(Queue)을 확인해서 파일이 들어오면 메인 화면(UI)에서 안전하게 처리합니다."""
        try:
            while True:
                dropped_items = self.drop_queue.get_nowait()
                self._process_drop(dropped_items)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_drop_queue)

    def shake_window(self):
        x = self.winfo_x()
        y = self.winfo_y()
        offsets = [-10, 10, -8, 8, -5, 5, -2, 2, 0]
        for i, dx in enumerate(offsets):
            self.after(i * 28, lambda new_x=x + dx: self.geometry(f"+{new_x}+{y}"))

    def load_settings(self):
        defaults = {
            "use_custom_dir": False,
            "custom_out_dir": "",
            "theme": "dark",
            "auto_open_folder": True,
            "filename_suffix": "_cut"
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception:
                pass
        return defaults

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def sync_settings_from_ui(self):
        if hasattr(self, 'page_settings'):
            self.settings["custom_out_dir"] = self.page_settings.entry_out_dir.get().strip()
            self.settings["filename_suffix"] = self.page_settings.entry_suffix.get().strip()

    def setup_sidebar(self):
        # 사이드바 너비를 240으로 고정
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=BG_SIDEBAR, border_width=1, border_color=BORDER_COLOR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # 내부 컨텐츠에 의해 사이드바가 늘어났다 줄어드는 현상(지진) 원천 차단
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)

        title_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_box.pack(fill="x", padx=24, pady=(36, 32))
        ctk.CTkLabel(title_box, text="CLEANCUT", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="STUDIO PRO ENVIRONMENT", font=("Pretendard Variable", 10, "bold"), text_color=ACCENT).pack(anchor="w")

        ctk.CTkLabel(self.sidebar, text="WORKSPACE", font=("Pretendard Variable", 10, "bold"), text_color=TEXT_SUB).pack(anchor="w", padx=24, pady=(0, 8))

        self.nav_bg_btn = ctk.CTkButton(
            self.sidebar, text=" 🪄 배경 지우기", anchor="w", height=44, corner_radius=8,
            font=FONT_CARD_TITLE, command=lambda: self.select_page("bg")
        )
        self.nav_bg_btn.pack(fill="x", padx=16, pady=4)

        self.nav_eraser_btn = ctk.CTkButton(
            self.sidebar, text=" 🧽 매직 지우개", anchor="w", height=44, corner_radius=8,
            font=FONT_CARD_TITLE, command=lambda: self.select_page("eraser")
        )
        self.nav_eraser_btn.pack(fill="x", padx=16, pady=4)

        self.nav_upscale_btn = ctk.CTkButton(
            self.sidebar, text=" 🚀 이미지 업스케일링", anchor="w", height=44, corner_radius=8,
            font=FONT_CARD_TITLE, command=lambda: self.select_page("upscale")
        )
        self.nav_upscale_btn.pack(fill="x", padx=16, pady=4)

        bottom_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_box.pack(side="bottom", fill="x", padx=16, pady=24)

        self.nav_settings_btn = ctk.CTkButton(
            bottom_box, text=" ⚙️ 환경 설정", anchor="w", height=40, corner_radius=8,
            font=FONT_DEFAULT_BOLD, fg_color="transparent", text_color=TEXT_SUB,
            hover_color=BG_INNER, command=lambda: self.select_page("settings")
        )
        self.nav_settings_btn.pack(fill="x", pady=(0, 16))

        status_box = ctk.CTkFrame(bottom_box, fg_color="transparent")
        status_box.pack(fill="x", padx=8)
        
        self.engine_dot = ctk.CTkLabel(status_box, text="✨ Modular Engine Ready", font=FONT_SMALL_BOLD, text_color=SUCCESS_COLOR, width=190, anchor="w")
        self.engine_dot.pack(anchor="w")
        ctk.CTkLabel(status_box, text="Version 1.0.0 Pro", font=FONT_SMALL, text_color=TEXT_SUB).pack(anchor="w")

    def setup_pages(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=32, pady=28)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.page_bg = TabBackground(self.container, self)
        self.page_eraser = TabEraser(self.container, self)
        self.page_upscale = TabUpscale(self.container, self)
        self.page_settings = TabSettings(self.container, self)

    def select_page(self, page_name):
        self.current_page_name = page_name
        for page in [self.page_bg, self.page_eraser, self.page_upscale, self.page_settings]:
            page.pack_forget()
            
        for btn in [self.nav_bg_btn, self.nav_eraser_btn, self.nav_upscale_btn, self.nav_settings_btn]:
            btn.configure(fg_color="transparent", text_color=TEXT_SUB, hover_color=BG_INNER, border_width=0)

        active_config = {"fg_color": BG_CARD, "text_color": ACCENT, "border_width": 1, "border_color": BORDER_COLOR}
        
        if page_name == "bg":
            self.page_bg.pack(fill="both", expand=True)
            self.nav_bg_btn.configure(**active_config)
        elif page_name == "eraser":
            self.page_eraser.pack(fill="both", expand=True)
            self.nav_eraser_btn.configure(**active_config)
        elif page_name == "upscale":
            self.page_upscale.pack(fill="both", expand=True)
            self.nav_upscale_btn.configure(**active_config)
        elif page_name == "settings":
            self.page_settings.pack(fill="both", expand=True)
            self.nav_settings_btn.configure(**active_config)

    def on_drop_files(self, dropped_items):
        # 윈도우 OS가 파일을 던지면, 묻지도 따지지도 않고 우체통에만 쏙 넣고 빠집니다 (UI 충돌 원천 차단)
        self.drop_queue.put(dropped_items)

    def _process_drop(self, dropped_items):
        # 안전한 메인 스레드 위에서 파일 분배 진행
        if self.current_page_name == "bg" and hasattr(self.page_bg, "on_drop_files"):
            self.page_bg.on_drop_files(dropped_items)
        elif self.current_page_name == "eraser" and hasattr(self.page_eraser, "on_drop_files"):
            self.page_eraser.on_drop_files(dropped_items)
        elif self.current_page_name == "upscale" and hasattr(self.page_upscale, "on_drop_files"):
            self.page_upscale.on_drop_files(dropped_items)

if __name__ == "__main__":
    app = CleanCutApp()
    app.mainloop()