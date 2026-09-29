import customtkinter as ctk
from config import *

class TabEraser(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="매직 지우개 (텍스트 / 마크 복원)", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="지우고 싶은 글씨나 로고 위를 마우스로 칠하면 주변 배경에 맞춰 자연스럽게 복원합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        ctrl_bar = ctk.CTkFrame(self, height=48, corner_radius=10, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        ctrl_bar.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(ctrl_bar, text="이미지 열기", width=95, height=32, corner_radius=6, fg_color="#262936", hover_color="#323646", font=FONT_DEFAULT_BOLD).pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(ctrl_bar, text="브러시 두께", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(side="left", padx=(12, 6))
        ctk.CTkSlider(ctrl_bar, from_=5, to=60, width=150, button_color=ACCENT, progress_color=ACCENT).pack(side="left", padx=4)
        ctk.CTkButton(ctrl_bar, text="칠한 영역 초기화", width=110, height=32, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, hover_color="#262936", text_color=TEXT_MAIN, font=FONT_DEFAULT).pack(side="right", padx=12, pady=8)

        canvas_card = ctk.CTkFrame(self, corner_radius=12, fg_color=BG_INNER, border_width=1, border_color=BORDER_COLOR)
        canvas_card.pack(fill="both", expand=True, pady=(0, 14))
        ctk.CTkLabel(canvas_card, text="다음 단계에서 engine_eraser.py 부품이 연결됩니다", font=("맑은 고딕", 13), text_color=TEXT_SUB).pack(expand=True)

        bot_bar = ctk.CTkFrame(self, fg_color="transparent")
        bot_bar.pack(fill="x", side="bottom")
        ctk.CTkButton(bot_bar, text="칠한 영역 흔적 없이 지우기", height=46, corner_radius=10, font=FONT_CARD_TITLE, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(bot_bar, text="결과물 저장하기", width=160, height=46, corner_radius=10, font=FONT_CARD_TITLE, fg_color="#262936", hover_color="#323646").pack(side="right", padx=(6, 0))