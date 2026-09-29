import os
from tkinter import filedialog
import customtkinter as ctk
from config import *

class TabSettings(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="환경 설정", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="저장 경로, 화면 테마, 파일 이름 규칙 등 작업 환경을 설정합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        card = ctk.CTkFrame(self, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="both", expand=True)

        # 1. 파일 저장 위치
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=22, pady=(20, 12))
        ctk.CTkLabel(row1, text="1. 결과물 저장 위치", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(row1, text="비워두면 원본 사진 폴더 안에 'CleanCut_결과물' 폴더가 자동 생성됩니다.", font=FONT_SMALL, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 8))

        dir_box = ctk.CTkFrame(row1, fg_color="transparent")
        dir_box.pack(fill="x")
        self.entry_out_dir = ctk.CTkEntry(dir_box, height=34, font=FONT_DEFAULT, placeholder_text="기본값 (원본 폴더 내 'CleanCut_결과물' 자동 생성)")
        self.entry_out_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if self.app.settings.get("custom_out_dir"):
            self.entry_out_dir.insert(0, self.app.settings["custom_out_dir"])

        ctk.CTkButton(
            dir_box, text="폴더 선택", width=85, height=34, corner_radius=6,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=FONT_DEFAULT_BOLD,
            command=self.choose_custom_out_dir
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            dir_box, text="기본값", width=65, height=34, corner_radius=6,
            fg_color=BG_INNER, text_color=TEXT_MAIN, hover_color=BORDER_COLOR, font=FONT_DEFAULT,
            command=self.clear_custom_out_dir
        ).pack(side="left")

        # 2. 화면 테마 모드 (독립형 버튼으로 완벽 교체 및 실시간 테마 적용)
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=22, pady=12)
        ctk.CTkLabel(row2, text="2. 화면 테마 모드", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(side="left")
        
        theme_btn_row = ctk.CTkFrame(row2, fg_color="transparent")
        theme_btn_row.pack(side="right")
        
        self.btn_dark = ctk.CTkButton(
            theme_btn_row, text="다크 모드", width=90, height=32, corner_radius=6, font=FONT_DEFAULT_BOLD,
            command=lambda: self.on_change_theme("dark")
        )
        self.btn_dark.pack(side="left", padx=(0, 6))
        
        self.btn_light = ctk.CTkButton(
            theme_btn_row, text="화이트 모드", width=90, height=32, corner_radius=6, font=FONT_DEFAULT_BOLD,
            command=lambda: self.on_change_theme("light")
        )
        self.btn_light.pack(side="left")

        # 3. 완료 후 결과 폴더 자동 열기
        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=22, pady=12)
        ctk.CTkLabel(row3, text="3. 저장 완료 후 결과물 폴더 자동으로 열기", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(side="left")
        self.sw_auto_open = ctk.CTkSwitch(row3, text="", width=46, progress_color=ACCENT, command=self.on_toggle_auto_open)
        if self.app.settings.get("auto_open_folder", True):
            self.sw_auto_open.select()
        self.sw_auto_open.pack(side="right")

        # 4. 저장 파일 이름 뒤에 붙일 글자
        row4 = ctk.CTkFrame(card, fg_color="transparent")
        row4.pack(fill="x", padx=22, pady=12)
        left_r4 = ctk.CTkFrame(row4, fg_color="transparent")
        left_r4.pack(side="left")
        ctk.CTkLabel(left_r4, text="4. 저장 파일 이름 뒤에 붙일 글자", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(left_r4, text="같은 이름의 파일이 이미 있으면 자동으로 뒤에 (1), (2) 번호가 붙어 덮어쓰기를 방지합니다.", font=FONT_SMALL, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        self.entry_suffix = ctk.CTkEntry(row4, width=140, height=34, font=FONT_DEFAULT)
        self.entry_suffix.insert(0, self.app.settings.get("filename_suffix", "_cut"))
        self.entry_suffix.pack(side="right")
        self.entry_suffix.bind("<KeyRelease>", self.on_change_suffix)

        # 초기 테마 버튼 색상 세팅
        self.update_theme_buttons()

    def choose_custom_out_dir(self):
        folder = filedialog.askdirectory(title="결과물을 저장할 고정 폴더 선택")
        if folder:
            self.entry_out_dir.delete(0, "end")
            self.entry_out_dir.insert(0, folder)
            self.app.settings["custom_out_dir"] = folder
            self.app.save_settings()

    def clear_custom_out_dir(self):
        self.entry_out_dir.delete(0, "end")
        self.app.settings["custom_out_dir"] = ""
        self.app.save_settings()

    def on_change_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self.app.settings["theme"] = mode
        self.app.save_settings()
        self.update_theme_buttons()

    def update_theme_buttons(self):
        current = self.app.settings.get("theme", "dark")
        if current == "dark":
            self.btn_dark.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            self.btn_light.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)
        else:
            self.btn_light.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            self.btn_dark.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

    def on_toggle_auto_open(self):
        self.app.settings["auto_open_folder"] = bool(self.sw_auto_open.get())
        self.app.save_settings()

    def on_change_suffix(self, event=None):
        self.app.settings["filename_suffix"] = self.entry_suffix.get().strip()
        self.app.save_settings()