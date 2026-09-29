import os
import json
import customtkinter as ctk

# 윈도우 탐색기 마우스 드래그 앤 드롭 지원
try:
    import windnd
except ImportError:
    windnd = None

# 모듈화된 부품들 불러오기
from config import *
from ui_common import FloatingProgressWidget
from ui_tab_bg import TabBackground
from ui_tab_eraser import TabEraser
from ui_tab_upscale import TabUpscale
from ui_tab_settings import TabSettings

class CleanCutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 1. 환경 설정 및 테마 로드
        self.settings = self.load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))

        # 2. 메인 윈도우 기본 설정
        self.title("CleanCut Studio Pro")
        self.geometry("880x600")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 3. 전역 상태 변수
        self.current_page_name = "bg"
        self.floating_prog = FloatingProgressWidget(self)

        # 4. 사이드바 및 페이지(탭) 생성
        self.setup_sidebar()
        self.setup_pages()
        self.select_page("bg")

        # 5. 윈도우 파일 드래그 앤 드롭 훅 연결
        if windnd is not None:
            try:
                windnd.hook_dropfiles(self, func=self.on_drop_files)
            except Exception:
                pass

    # ==========================================
    # 윈도우 액션 및 설정 관련 헬퍼 함수
    # ==========================================
    def shake_window(self):
        """오류 발생 시 창 전체를 좌우로 흔들어 경고를 줍니다."""
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
        """설정 탭에 입력된 텍스트 값을 전역 설정 딕셔너리로 즉시 동기화합니다."""
        if hasattr(self, 'page_settings'):
            self.settings["custom_out_dir"] = self.page_settings.entry_out_dir.get().strip()
            self.settings["filename_suffix"] = self.page_settings.entry_suffix.get().strip()

    # ==========================================
    # 사이드바 구성
    # ==========================================
    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=BG_SIDEBAR, border_width=1, border_color=BORDER_COLOR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        title_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_box.pack(fill="x", padx=24, pady=(32, 28))
        ctk.CTkLabel(title_box, text="CLEANCUT", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="ALL-IN-ONE IMAGE STUDIO", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w")

        ctk.CTkLabel(self.sidebar, text="WORKSPACE", font=("맑은 고딕", 10, "bold"), text_color=TEXT_SUB).pack(anchor="w", padx=24, pady=(0, 8))

        self.nav_bg_btn = ctk.CTkButton(
            self.sidebar, text="  1. 배경 투명화 & 변환", anchor="w", height=42, corner_radius=8,
            font=FONT_CARD_TITLE, command=lambda: self.select_page("bg")
        )
        self.nav_bg_btn.pack(fill="x", padx=16, pady=4)

        self.nav_eraser_btn = ctk.CTkButton(
            self.sidebar, text="  2. 매직 지우개 (복원)", anchor="w", height=42, corner_radius=8,
            font=FONT_CARD_TITLE, command=lambda: self.select_page("eraser")
        )
        self.nav_eraser_btn.pack(fill="x", padx=16, pady=4)

        self.nav_upscale_btn = ctk.CTkButton(
            self.sidebar, text="  3. AI 화질 복원 (업스케일)", anchor="w", height=42, corner_radius=8,
            font=FONT_CARD_TITLE, command=lambda: self.select_page("upscale")
        )
        self.nav_upscale_btn.pack(fill="x", padx=16, pady=4)

        bottom_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_box.pack(side="bottom", fill="x", padx=16, pady=20)

        self.nav_settings_btn = ctk.CTkButton(
            bottom_box, text="  ⚙  환경 설정", anchor="w", height=38, corner_radius=8,
            font=FONT_DEFAULT_BOLD, fg_color="transparent", text_color=TEXT_SUB,
            hover_color=BG_INNER, command=lambda: self.select_page("settings")
        )
        self.nav_settings_btn.pack(fill="x", pady=(0, 12))

        status_box = ctk.CTkFrame(bottom_box, fg_color="transparent")
        status_box.pack(fill="x", padx=8)
        self.engine_dot = ctk.CTkLabel(status_box, text="● Modular Engine Ready", font=FONT_SMALL, text_color=SUCCESS_COLOR)
        self.engine_dot.pack(anchor="w")
        ctk.CTkLabel(status_box, text="Version 1.0.0 Pro", font=FONT_SMALL, text_color=TEXT_SUB).pack(anchor="w")

    # ==========================================
    # 페이지(탭) 생성 및 전환 로직
    # ==========================================
    def setup_pages(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # 각 파일로 쪼개진 UI 클래스들을 불러와 컨테이너에 부착
        self.page_bg = TabBackground(self.container, self)
        self.page_eraser = TabEraser(self.container, self)
        self.page_upscale = TabUpscale(self.container, self)
        self.page_settings = TabSettings(self.container, self)

    def select_page(self, page_name):
        self.current_page_name = page_name
        for page in [self.page_bg, self.page_eraser, self.page_upscale, self.page_settings]:
            page.pack_forget()
        for btn in [self.nav_bg_btn, self.nav_eraser_btn, self.nav_upscale_btn, self.nav_settings_btn]:
            btn.configure(fg_color="transparent", text_color=TEXT_SUB, hover_color=BG_INNER)

        if page_name == "bg":
            self.page_bg.pack(fill="both", expand=True)
            self.nav_bg_btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
        elif page_name == "eraser":
            self.page_eraser.pack(fill="both", expand=True)
            self.nav_eraser_btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
        elif page_name == "upscale":
            self.page_upscale.pack(fill="both", expand=True)
            self.nav_upscale_btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
        elif page_name == "settings":
            self.page_settings.pack(fill="both", expand=True)
            self.nav_settings_btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)

    # ==========================================
    # 전역 드래그 앤 드롭 라우터
    # ==========================================
    def on_drop_files(self, dropped_items):
        # 현재 보고 있는 화면(탭)으로 드래그 앤 드롭 이벤트를 전달
        if self.current_page_name == "bg" and hasattr(self.page_bg, "on_drop_files"):
            self.page_bg.on_drop_files(dropped_items)


if __name__ == "__main__":
    app = CleanCutApp()
    app.mainloop()