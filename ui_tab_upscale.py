import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import *
from ui_common import ToolTip

class UpFileListModal(ctk.CTkToplevel):
    def __init__(self, tab_up):
        super().__init__(tab_up.app)
        self.tab_up = tab_up
        self.app = tab_up.app
        self.title("현재 선택된 업스케일링 파일 관리")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        self.transient(self.app)
        self.grab_set()

        top_bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=BG_SIDEBAR, border_width=1, border_color=BORDER_COLOR)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        self.lbl_title = ctk.CTkLabel(top_bar, text="", font=FONT_CARD_TITLE, text_color=TEXT_MAIN)
        self.lbl_title.pack(side="left", padx=20)

        ctk.CTkButton(
            top_bar, text="전체 비우기", width=86, height=28, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=ERROR_COLOR,
            text_color=ERROR_COLOR, hover_color=("#FEE2E2", "#2A1519"),
            font=FONT_SMALL_BOLD, command=self.clear_all
        ).pack(side="right", padx=20)

        self.scroll_box = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.scroll_box.pack(fill="both", expand=True, padx=20, pady=16)

        bot_bar = ctk.CTkFrame(self, fg_color="transparent")
        bot_bar.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            bot_bar, text="+ 파일 더 추가하기", height=38, corner_radius=8,
            fg_color=BG_CARD, hover_color=BORDER_COLOR, text_color=TEXT_MAIN,
            border_width=1, border_color=BORDER_COLOR, font=FONT_DEFAULT_BOLD,
            command=self.add_more_files
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            bot_bar, text="확인 (닫기)", height=38, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=FONT_DEFAULT_BOLD, command=self.destroy
        ).pack(side="right", fill="x", expand=True, padx=(6, 0))

        self.render_list()

    def render_list(self):
        for child in self.scroll_box.winfo_children():
            child.destroy()

        count = len(self.tab_up.up_file_list)
        self.lbl_title.configure(text=f"선택된 이미지 목록 ({count}개)")

        if count == 0:
            ctk.CTkLabel(
                self.scroll_box, text="선택된 파일이 없습니다.",
                font=FONT_DEFAULT, text_color=TEXT_SUB
            ).pack(pady=80)
            return

        for idx, fpath in enumerate(self.tab_up.up_file_list):
            row = ctk.CTkFrame(self.scroll_box, corner_radius=8, fg_color=BG_INNER, height=42)
            row.pack(fill="x", pady=3, padx=4)
            row.pack_propagate(False)

            fname = os.path.basename(fpath)
            folder = os.path.basename(os.path.dirname(fpath))
            display_txt = f"{idx + 1}.  {fname}   ({folder})"
            if len(display_txt) > 45:
                display_txt = display_txt[:42] + "..."

            ctk.CTkLabel(row, text=display_txt, font=FONT_DEFAULT, text_color=TEXT_MAIN).pack(side="left", padx=12)

            ctk.CTkButton(
                row, text="✕ 취소", width=56, height=26, corner_radius=6,
                fg_color="transparent", hover_color=("#FEE2E2", "#2A1519"),
                text_color=ERROR_COLOR, font=FONT_SMALL_BOLD,
                command=lambda p=fpath: self.remove_one(p)
            ).pack(side="right", padx=8)

    def remove_one(self, path_to_remove):
        if path_to_remove in self.tab_up.up_file_list:
            self.tab_up.up_file_list.remove(path_to_remove)
            self.tab_up.refresh_file_badge()
            self.render_list()

    def clear_all(self):
        self.tab_up.up_file_list.clear()
        self.tab_up.refresh_file_badge()
        self.destroy()

    def add_more_files(self):
        self.tab_up.select_up_files()
        self.render_list()


class TabUpscale(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # 파일 목록 및 상태 관리 변수
        self.up_file_list = []
        self.selected_engine = "고속 선명화"
        self.selected_type = "실사 사진"
        self.selected_scale = "2배 (2x)"
        self.file_warn_timer = None
        
        self.engine_btns = {}
        self.type_btns = {}
        self.scale_btns = {}
        
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="AI 초고화질 복원 (업스케일링)", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="저해상도 이미지의 깨진 픽셀과 노이즈를 제거하고 최대 4배까지 선명하게 확대합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        # 파일 드롭 및 추가 영역 (1번 탭과 동일)
        self.drop_card = ctk.CTkFrame(self, height=130, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR, cursor="hand2")
        self.drop_card.pack(fill="x", pady=(0, 16))
        self.drop_card.pack_propagate(False)

        lbl1 = ctk.CTkLabel(self.drop_card, text="+  화질을 높일 이미지 파일 추가하기 (클릭 또는 드래그 앤 드롭)", font=("맑은 고딕", 15, "bold"), text_color=TEXT_MAIN)
        lbl1.pack(pady=(22, 4))
        lbl2 = ctk.CTkLabel(self.drop_card, text="여러 폴더의 이미지를 나눠서 추가할 수 있으며, 아래 배지를 누르면 개별 취소할 수 있습니다", font=FONT_DEFAULT, text_color=TEXT_SUB)
        lbl2.pack()

        self.file_badge = ctk.CTkButton(
            self.drop_card, text=" 현재 선택된 파일: 0개 ", height=28, corner_radius=6,
            font=FONT_SMALL_BOLD, text_color=ACCENT, fg_color=BG_INNER,
            hover_color=BORDER_COLOR, command=self.on_click_file_badge
        )
        self.file_badge.pack(pady=(10, 0))

        for widget in [self.drop_card, lbl1, lbl2]:
            widget.bind("<Button-1>", lambda e: self.select_up_files())

        up_grid = ctk.CTkFrame(self, fg_color="transparent")
        up_grid.pack(fill="x", pady=(0, 14))
        up_grid.grid_columnconfigure((0, 1), weight=1)

        # ==========================================
        # 좌측 카드: 엔진 및 유형 선택
        # ==========================================
        up_left = ctk.CTkFrame(up_grid, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(up_left, text="AI UPSCALE ENGINE", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(up_left, text="복원 엔진 선택", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 12))

        engine_row = ctk.CTkFrame(up_left, fg_color="transparent")
        engine_row.pack(fill="x", padx=18, pady=(0, 16))
        engine_row.grid_columnconfigure((0, 1), weight=1, uniform="up_engine")

        for idx, e_name in enumerate(["고속 선명화", "정밀 AI 복원"]):
            btn = ctk.CTkButton(
                engine_row, text=e_name, height=36, corner_radius=6,
                font=FONT_DEFAULT_BOLD,
                command=lambda e=e_name: self.set_engine(e)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.engine_btns[e_name] = btn
            # [신규] 툴팁 추가
            ToolTip(
                btn,
                "• 고속 선명화: 가벼운 알고리즘으로 빠르게 해상도를 높입니다. (저사양 추천)\n"
                "• 정밀 AI 복원: 딥러닝 기반으로 픽셀을 정교하게 재창조합니다. (고품질)" if e_name == "정밀 AI 복원" else "• 고속 선명화: 가벼운 알고리즘으로 빠르게 해상도를 높입니다. (저사양 추천)\n• 정밀 AI 복원: 딥러닝 기반으로 픽셀을 정교하게 재창조합니다. (고품질)"
            )

        ctk.CTkLabel(up_left, text="이미지 유형 최적화", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", padx=18, pady=(0, 6))
        
        type_row = ctk.CTkFrame(up_left, fg_color="transparent")
        type_row.pack(fill="x", padx=18, pady=(0, 18))
        type_row.grid_columnconfigure((0, 1), weight=1, uniform="up_type")

        for idx, t_name in enumerate(["실사 사진", "일러스트 / 그래픽"]):
            btn = ctk.CTkButton(
                type_row, text=t_name, height=34, corner_radius=6,
                font=FONT_SMALL_BOLD,
                command=lambda t=t_name: self.set_type(t)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.type_btns[t_name] = btn
            # [신규] 툴팁 추가
            ToolTip(
                btn,
                "• 실사 사진: 풍경, 인물, 상품 등 자연스러운 질감 표현에 최적화됩니다.\n"
                "• 일러스트 / 그래픽: 선이 뚜렷한 만화, 애니메이션, 2D 그래픽에 최적화됩니다." if t_name == "일러스트 / 그래픽" else "• 실사 사진: 풍경, 인물, 상품 등 자연스러운 질감 표현에 최적화됩니다.\n• 일러스트 / 그래픽: 선이 뚜렷한 만화, 애니메이션, 2D 그래픽에 최적화됩니다."
            )

        # ==========================================
        # 우측 카드: 배율 및 스위치
        # ==========================================
        up_right = ctk.CTkFrame(up_grid, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(up_right, text="RESOLUTION & DETAIL", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(up_right, text="확대 배율", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 12))

        scale_row = ctk.CTkFrame(up_right, fg_color="transparent")
        scale_row.pack(fill="x", padx=18, pady=(0, 16))
        scale_row.grid_columnconfigure((0, 1), weight=1, uniform="up_scale")

        for idx, s_name in enumerate(["2배 (2x)", "4배 (4x · 4K급)"]):
            btn = ctk.CTkButton(
                scale_row, text=s_name, height=36, corner_radius=6,
                font=FONT_DEFAULT_BOLD,
                command=lambda s=s_name: self.set_scale(s)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.scale_btns[s_name] = btn
            # [신규] 툴팁 추가
            ToolTip(btn, f"원본 해상도의 가로/세로를 각각 {s_name.split('배')[0]}배(면적 기준 {int(s_name.split('배')[0])**2}배)로 확대합니다.")

        ctk.CTkLabel(up_right, text="후보정 옵션", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", padx=18, pady=(0, 6))

        self.denoise_sw = ctk.CTkSwitch(
            up_right, text="JPG 손상/노이즈 부드럽게 제거", font=FONT_DEFAULT, 
            text_color=TEXT_MAIN, progress_color=ACCENT
        )
        self.denoise_sw.select()
        self.denoise_sw.pack(anchor="w", padx=18, pady=4)
        ToolTip(self.denoise_sw, "인터넷에서 다운로드한 이미지 특유의 자글자글한 압축 노이즈(블록 현상)를 매끄럽게 폅니다.")

        self.sharpen_sw = ctk.CTkSwitch(
            up_right, text="외곽선 뚜렷하게 (샤프닝 적용)", font=FONT_DEFAULT, 
            text_color=TEXT_MAIN, progress_color=ACCENT
        )
        self.sharpen_sw.select()
        self.sharpen_sw.pack(anchor="w", padx=18, pady=(4, 16))
        ToolTip(self.sharpen_sw, "뿌옇게 흐려진 경계선을 더욱 또렷하고 선명하게 강조합니다.")

        # ==========================================
        # 하단 액션 버튼 영역 (1번 탭과 동일한 분할 구조 적용)
        # ==========================================
        self.bottom_action_box = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_action_box.pack(fill="x", side="bottom")
        self.bottom_action_box.grid_columnconfigure(0, weight=1)
        self.bottom_action_box.grid_columnconfigure(1, weight=2)

        self.up_preview_btn = ctk.CTkButton(
            self.bottom_action_box, text="결과 미리보기", height=48, corner_radius=10,
            font=FONT_CARD_TITLE, fg_color=BG_CARD, hover_color=BORDER_COLOR,
            text_color=TEXT_MAIN, border_width=1, border_color=BORDER_COLOR,
            command=self.show_placeholder_msg
        )
        self.up_preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.up_run_btn = ctk.CTkButton(
            self.bottom_action_box, text="AI 화질 복원 및 확대 시작", height=48, corner_radius=10,
            font=("맑은 고딕", 15, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#FFFFFF", command=self.show_placeholder_msg
        )
        self.up_run_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.update_button_styles()

    # ==========================================
    # 상호작용 및 UI 제어 로직
    # ==========================================
    def set_engine(self, name):
        self.selected_engine = name
        self.update_button_styles()

    def set_type(self, name):
        self.selected_type = name
        self.update_button_styles()

    def set_scale(self, name):
        self.selected_scale = name
        self.update_button_styles()

    def update_button_styles(self):
        for name, btn in self.engine_btns.items():
            if name == self.selected_engine:
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)
        
        for name, btn in self.type_btns.items():
            if name == self.selected_type:
                btn.configure(fg_color="#32384D", text_color="#FFFFFF", hover_color="#3E455E", border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

        for name, btn in self.scale_btns.items():
            if name == self.selected_scale:
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

    # ==========================================
    # 파일 추가 및 리스트 관리 로직 (1번 탭과 완벽 동일)
    # ==========================================
    def refresh_file_badge(self):
        if self.file_warn_timer:
            self.after_cancel(self.file_warn_timer)
            self.file_warn_timer = None
        self.drop_card.configure(border_color=BORDER_COLOR, border_width=1)
        count = len(self.up_file_list)
        if count > 0:
            self.file_badge.configure(text=f" 현재 선택된 파일: {count}개 (클릭하여 관리/취소) ", text_color=SUCCESS_COLOR)
        else:
            self.file_badge.configure(text=" 현재 선택된 파일: 0개 ", text_color=ACCENT)

    def show_file_card_warning(self, msg):
        self.app.shake_window()
        self.drop_card.configure(border_color=ERROR_COLOR, border_width=2)
        self.file_badge.configure(text=f" {msg} ", text_color=ERROR_COLOR)
        if self.file_warn_timer:
            self.after_cancel(self.file_warn_timer)
        self.file_warn_timer = self.after(2300, self.refresh_file_badge)

    def show_soft_warning(self, msg):
        self.drop_card.configure(border_color=WARN_COLOR, border_width=1)
        self.file_badge.configure(text=f" {msg} ", text_color=WARN_COLOR)
        if self.file_warn_timer:
            self.after_cancel(self.file_warn_timer)
        self.file_warn_timer = self.after(3000, self.refresh_file_badge)

    def add_up_files(self, raw_paths):
        if not raw_paths: return

        valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        existing_norm = {os.path.normcase(os.path.abspath(p)) for p in self.up_file_list}

        added_count = 0
        dup_count = 0
        invalid_count = 0

        for p in raw_paths:
            if os.path.isdir(p):
                for root_d, _, files in os.walk(p):
                    for fn in files:
                        full_p = os.path.join(root_d, fn)
                        if full_p.lower().endswith(valid_exts):
                            norm_p = os.path.normcase(os.path.abspath(full_p))
                            if norm_p in existing_norm:
                                dup_count += 1
                            else:
                                self.up_file_list.append(full_p)
                                existing_norm.add(norm_p)
                                added_count += 1
                        else:
                            invalid_count += 1
            else:
                if not p.lower().endswith(valid_exts):
                    invalid_count += 1
                    continue
                norm_p = os.path.normcase(os.path.abspath(p))
                if norm_p in existing_norm:
                    dup_count += 1
                else:
                    self.up_file_list.append(p)
                    existing_norm.add(norm_p)
                    added_count += 1

        if dup_count > 0 or invalid_count > 0:
            if added_count > 0:
                parts = []
                if dup_count > 0: parts.append(f"중복 {dup_count}개")
                if invalid_count > 0: parts.append(f"미지원 {invalid_count}개")
                self.show_soft_warning(f"✅ {added_count}개 추가 (" + ", ".join(parts) + " 제외)")
            else:
                if invalid_count > 0 and dup_count == 0:
                    self.show_file_card_warning("! 지원하지 않는 파일 형식입니다 (PNG, JPG, WEBP, BMP 지원)")
                else:
                    self.show_file_card_warning(f"! 이미 추가된 중복 파일입니다 ({dup_count}개)")
        else:
            self.refresh_file_badge()

    def on_drop_files(self, dropped_items):
        if self.app.current_page_name != "upscale": return
        decoded = []
        for item in dropped_items:
            if isinstance(item, bytes):
                try: decoded.append(item.decode("mbcs"))
                except Exception: decoded.append(item.decode("utf-8", errors="ignore"))
            else:
                decoded.append(str(item))
        self.add_up_files(decoded)

    def on_click_file_badge(self):
        if not self.up_file_list:
            self.select_up_files()
        else:
            UpFileListModal(self)

    def select_up_files(self):
        files = filedialog.askopenfilenames(
            title="업스케일링할 이미지 추가 선택 (여러 폴더에서 반복 추가 가능)",
            filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("모든 파일", "*.*")]
        )
        if files:
            self.add_up_files(list(files))

    def show_placeholder_msg(self):
        if not self.up_file_list:
            self.show_file_card_warning("! 먼저 작업할 이미지 파일을 선택해주세요")
            return
        messagebox.showinfo("안내", "UI 뼈대 이식이 완료되었습니다!\n(백엔드 엔진 연결 및 미리보기 기능은 추후 구현됩니다.)")