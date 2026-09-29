import customtkinter as ctk
from config import *

class TabUpscale(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="AI 초고화질 복원 (업스케일링)", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="저해상도 이미지의 깨진 픽셀과 노이즈를 제거하고 최대 4배까지 선명하게 확대합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        up_drop_card = ctk.CTkFrame(self, height=135, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_drop_card.pack(fill="x", pady=(0, 16))
        up_drop_card.pack_propagate(False)

        ctk.CTkLabel(up_drop_card, text="+  화질을 높일 이미지 불러오기", font=("맑은 고딕", 15, "bold"), text_color=TEXT_MAIN).pack(pady=(30, 4))
        ctk.CTkLabel(up_drop_card, text="다음 단계에서 engine_upscale.py 부품이 연결됩니다", font=FONT_DEFAULT, text_color=TEXT_SUB).pack()

        up_badge = ctk.CTkLabel(up_drop_card, text=" 현재 선택된 파일: 0개 ", font=FONT_SMALL_BOLD, text_color=ACCENT, fg_color=BG_INNER, corner_radius=6)
        up_badge.pack(pady=(10, 0), ipadx=8, ipady=2)

        up_grid = ctk.CTkFrame(self, fg_color="transparent")
        up_grid.pack(fill="x", pady=(0, 16))
        up_grid.grid_columnconfigure((0, 1), weight=1)

        up_left = ctk.CTkFrame(up_grid, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(up_left, text="AI UPSCALE ENGINE", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(up_left, text="화질 복원 엔진 선택", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 12))

        self.up_engine_seg = ctk.CTkSegmentedButton(
            up_left, values=["고속 선명화 (OpenCV)", "초고화질 복원 (Real-ESRGAN)"], height=34,
            font=FONT_SMALL_BOLD, fg_color=BG_INNER, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER
        )
        self.up_engine_seg.set("고속 선명화 (OpenCV)")
        self.up_engine_seg.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(up_left, text="원본 이미지 맞춤 최적화", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", padx=18, pady=(0, 6))
        self.up_type_seg = ctk.CTkSegmentedButton(
            up_left, values=["실사 / 인물 / 상품", "일러스트 / 로고 / 텍스트"], height=32,
            font=FONT_SMALL, fg_color=BG_INNER, selected_color="#32384D", selected_hover_color="#3E455E"
        )
        self.up_type_seg.set("실사 / 인물 / 상품")
        self.up_type_seg.pack(fill="x", padx=18, pady=(0, 18))

        up_right = ctk.CTkFrame(up_grid, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(up_right, text="RESOLUTION & DETAIL", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(up_right, text="확대 배율 및 후보정", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 12))

        self.scale_seg = ctk.CTkSegmentedButton(
            up_right, values=["2배 확대 (2x)", "4배 확대 (4x · 4K급)"], height=34,
            font=FONT_DEFAULT_BOLD, fg_color=BG_INNER, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER
        )
        self.scale_seg.set("2배 확대 (2x)")
        self.scale_seg.pack(fill="x", padx=18, pady=(0, 14))

        self.denoise_sw = ctk.CTkSwitch(up_right, text="JPG 압축 노이즈(깍두기) 자동 제거", font=FONT_DEFAULT, text_color=TEXT_MAIN, progress_color=ACCENT)
        self.denoise_sw.select()
        self.denoise_sw.pack(anchor="w", padx=18, pady=4)

        self.sharpen_sw = ctk.CTkSwitch(up_right, text="외곽선 선명도(Sharpening) 강화", font=FONT_DEFAULT, text_color=TEXT_MAIN, progress_color=ACCENT)
        self.sharpen_sw.select()
        self.sharpen_sw.pack(anchor="w", padx=18, pady=(4, 16))

        up_run_btn = ctk.CTkButton(
            self, text="AI 화질 복원 및 확대 시작", height=48, corner_radius=10,
            font=("맑은 고딕", 15, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER
        )
        up_run_btn.pack(fill="x", side="bottom")