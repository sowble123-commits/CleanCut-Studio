import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from config import *
from ui_common import ToolTip, FloatingProgressWidget, InteractiveImageCanvas
import engine_upscale

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

class UpPreviewWindow(ctk.CTkToplevel):
    def __init__(self, tab_up, items_data):
        super().__init__(tab_up.app)
        self.tab_up = tab_up
        self.app = tab_up.app
        self.items = items_data
        self.current_idx = 0
        
        self.title("업스케일링 결과 미리보기")
        self.geometry("1000x720")
        self.resizable(True, True)
        self.transient(self.app)
        self.configure(fg_color=BG_MAIN)
        self.build_ui()
        self.load_item()

    def build_ui(self):
        top_bar = ctk.CTkFrame(self, height=54, fg_color=BG_SIDEBAR, border_width=1, border_color=BORDER_COLOR)
        top_bar.pack(fill="x")
        self.lbl_filename = ctk.CTkLabel(top_bar, text="", font=FONT_CARD_TITLE, text_color=TEXT_MAIN)
        self.lbl_filename.pack(side="left", padx=22, pady=12)
        
        btn_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_row.pack(side="right", padx=22, pady=10)
        ctk.CTkButton(btn_row, text="전체 저장", width=100, height=32, corner_radius=6, font=FONT_DEFAULT_BOLD, fg_color=ACCENT, command=self.save_all_items).pack(side="right")
        ctk.CTkButton(btn_row, text="개별 저장", width=88, height=32, corner_radius=6, font=FONT_DEFAULT_BOLD, fg_color=("#E2E8F0", "#262936"), text_color=TEXT_MAIN, command=self.save_current_item).pack(side="right", padx=8)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=22, pady=18)
        
        zoom_bar = ctk.CTkFrame(body, fg_color="transparent")
        zoom_bar.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(zoom_bar, text="◀ 이전", width=60, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, font=FONT_SMALL_BOLD, text_color=TEXT_MAIN, command=self.prev_item).pack(side="left", padx=2)
        self.lbl_page = ctk.CTkLabel(zoom_bar, text="1 / 1", font=FONT_DEFAULT_BOLD, text_color=TEXT_MAIN, width=40)
        self.lbl_page.pack(side="left", padx=4)
        ctk.CTkButton(zoom_bar, text="다음 ▶", width=60, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, font=FONT_SMALL_BOLD, text_color=TEXT_MAIN, command=self.next_item).pack(side="left", padx=(2, 16))
        
        ctk.CTkLabel(zoom_bar, text="슬라이더: 화면 비교  |  Spacebar+드래그: 화면 이동", font=FONT_SMALL, text_color=TEXT_SUB).pack(side="left")
        
        ctk.CTkButton(zoom_bar, text="1:1", width=44, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, font=FONT_SMALL_BOLD, text_color=TEXT_MAIN, command=lambda: self.canvas.zoom_1to1()).pack(side="right", padx=2)
        ctk.CTkButton(zoom_bar, text="맞춤", width=44, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, font=FONT_SMALL_BOLD, text_color=TEXT_MAIN, command=lambda: self.canvas.fit_to_screen()).pack(side="right", padx=2)
        ctk.CTkButton(zoom_bar, text="-", width=36, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, font=FONT_SMALL_BOLD, text_color=TEXT_MAIN, command=lambda: self.canvas.zoom_out()).pack(side="right", padx=2)
        ctk.CTkButton(zoom_bar, text="+", width=36, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, font=FONT_SMALL_BOLD, text_color=TEXT_MAIN, command=lambda: self.canvas.zoom_in()).pack(side="right", padx=(16, 2))
        
        self.btn_view_orig = ctk.CTkButton(zoom_bar, text="원본", width=50, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("toggle_orig"))
        self.btn_view_orig.pack(side="right", padx=2)
        self.btn_view_split = ctk.CTkButton(zoom_bar, text="스플릿", width=50, height=28, corner_radius=6, fg_color=ACCENT, border_width=0, text_color="#FFFFFF", hover_color=ACCENT_HOVER, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("split"))
        self.btn_view_split.pack(side="right", padx=2)
        self.btn_view_res = ctk.CTkButton(zoom_bar, text="결과물", width=50, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("toggle_res"))
        self.btn_view_res.pack(side="right", padx=2)

        bg_col = BG_INNER[1] if self.app.settings.get("theme") == "dark" else BG_INNER[0]
        self.canvas = InteractiveImageCanvas(body, bg_color=bg_col, draw_mode=False)
        self.canvas.pack(fill="both", expand=True)

    def load_item(self):
        if not self.items: return self.destroy()
        item = self.items[self.current_idx]
        self.lbl_filename.configure(text=os.path.basename(item["path"]))
        self.lbl_page.configure(text=f"{self.current_idx + 1} / {len(self.items)}")
        
        self.on_view_change("split")
        self.canvas.set_comparison(item["orig_img"], item["res_img"], mode="split")
        self.after(100, lambda: self.canvas.fit_to_screen())

    def on_view_change(self, mode):
        self.canvas.set_view_mode(mode)
        self.btn_view_split.configure(fg_color=ACCENT if mode=="split" else "transparent", text_color="#FFFFFF" if mode=="split" else TEXT_MAIN, border_width=0 if mode=="split" else 1)
        self.btn_view_res.configure(fg_color=ACCENT if mode=="toggle_res" else "transparent", text_color="#FFFFFF" if mode=="toggle_res" else TEXT_MAIN, border_width=0 if mode=="toggle_res" else 1)
        self.btn_view_orig.configure(fg_color=ACCENT if mode=="toggle_orig" else "transparent", text_color="#FFFFFF" if mode=="toggle_orig" else TEXT_MAIN, border_width=0 if mode=="toggle_orig" else 1)

    def prev_item(self):
        if len(self.items) > 1: 
            self.current_idx = (self.current_idx - 1) % len(self.items)
            self.load_item()
            
    def next_item(self):
        if len(self.items) > 1: 
            self.current_idx = (self.current_idx + 1) % len(self.items)
            self.load_item()

    def save_current_item(self):
        if hasattr(self.app, 'sync_settings_from_ui'): self.app.sync_settings_from_ui()
        engine_upscale.save_upscaled_image(self.items[self.current_idx]["res_img"], self.items[self.current_idx]["path"], self.app.settings.get("custom_out_dir", ""))
        messagebox.showinfo("저장", "개별 저장 완료", parent=self)

    def save_all_items(self):
        if hasattr(self.app, 'sync_settings_from_ui'): self.app.sync_settings_from_ui()
        last_dir = ""
        for it in self.items:
            last_dir, _ = engine_upscale.save_upscaled_image(it["res_img"], it["path"], self.app.settings.get("custom_out_dir", ""))
        messagebox.showinfo("저장", "전체 저장 완료!", parent=self)
        if self.app.settings.get("auto_open_folder", True) and last_dir: os.startfile(last_dir)
        self.destroy()

class TabUpscale(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        self.up_file_list = []
        self.selected_engine = "기본 선명화 (빠름)"
        self.selected_type = "사진"
        self.selected_scale = "2x"
        self.file_warn_timer = None
        
        self.engine_btns = {}
        self.type_btns = {}
        self.scale_btns = {}
        
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="이미지 업스케일링", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="저해상도 이미지의 깨진 픽셀과 노이즈를 제거하고 최대 4배까지 선명하게 확대합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        self.drop_card = ctk.CTkFrame(self, height=130, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR, cursor="hand2")
        self.drop_card.pack(fill="x", pady=(0, 16))
        self.drop_card.pack_propagate(False)

        lbl1 = ctk.CTkLabel(self.drop_card, text="+  화질을 높일 이미지 파일 추가하기 (클릭 또는 드래그 앤 드롭)", font=FONT_CARD_TITLE, text_color=TEXT_MAIN)
        lbl1.pack(pady=(22, 4))
        lbl2 = ctk.CTkLabel(self.drop_card, text="여러 폴더의 이미지들을 나눠서 추가할 수 있으며, 아래 배지를 누르면 개별 취소할 수 있습니다", font=FONT_DEFAULT, text_color=TEXT_SUB)
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

        up_left = ctk.CTkFrame(up_grid, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(up_left, text="AI UPSCALE ENGINE", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(up_left, text="AI 처리 모델", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 12))

        engine_row = ctk.CTkFrame(up_left, fg_color="transparent")
        engine_row.pack(fill="x", padx=18, pady=(0, 16))
        engine_row.grid_columnconfigure((0, 1), weight=1, uniform="up_engine")

        for idx, e_name in enumerate(["기본 선명화 (빠름)", "고화질 복원 (정밀)"]):
            btn = ctk.CTkButton(
                engine_row, text=e_name, height=36, corner_radius=6,
                font=FONT_DEFAULT_BOLD,
                command=lambda e=e_name: self.set_engine(e)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.engine_btns[e_name] = btn
            ToolTip(btn, "가벼운 알고리즘으로 빠르게 해상도를 높입니다." if e_name == "기본 선명화 (빠름)" else "딥러닝 기반으로 픽셀을 정교하게 재창조합니다.")

        ctk.CTkLabel(up_left, text="이미지 특성", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", padx=18, pady=(0, 6))
        
        type_row = ctk.CTkFrame(up_left, fg_color="transparent")
        type_row.pack(fill="x", padx=18, pady=(0, 18))
        type_row.grid_columnconfigure((0, 1), weight=1, uniform="up_type")

        for idx, t_name in enumerate(["사진", "일러스트"]):
            btn = ctk.CTkButton(
                type_row, text=t_name, height=34, corner_radius=6,
                font=FONT_SMALL_BOLD,
                command=lambda t=t_name: self.set_type(t)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.type_btns[t_name] = btn
            ToolTip(btn, "풍경, 인물 등 자연스러운 질감 표현에 최적화됩니다." if t_name == "사진" else "선이 뚜렷한 2D 그래픽에 최적화됩니다.")

        up_right = ctk.CTkFrame(up_grid, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        up_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(up_right, text="RESOLUTION & DETAIL", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(up_right, text="해상도 확대", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 12))

        scale_row = ctk.CTkFrame(up_right, fg_color="transparent")
        scale_row.pack(fill="x", padx=18, pady=(0, 16))
        scale_row.grid_columnconfigure((0, 1), weight=1, uniform="up_scale")

        for idx, s_name in enumerate(["2x", "4x"]):
            btn = ctk.CTkButton(
                scale_row, text=s_name, height=36, corner_radius=6,
                font=FONT_DEFAULT_BOLD,
                command=lambda s=s_name: self.set_scale(s)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.scale_btns[s_name] = btn
            ToolTip(btn, f"원본 해상도의 가로/세로를 각각 {s_name.split('x')[0]}배로 확대합니다.")

        ctk.CTkLabel(up_right, text="내보내기 설정", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", padx=18, pady=(0, 6))

        self.denoise_sw = ctk.CTkSwitch(
            up_right, text="압축 노이즈 감소", font=FONT_DEFAULT, 
            text_color=TEXT_MAIN, progress_color=ACCENT
        )
        self.denoise_sw.select()
        self.denoise_sw.pack(anchor="w", padx=18, pady=4)
        ToolTip(self.denoise_sw, "인터넷에서 다운로드한 이미지 특유의 자글자글한 압축 노이즈(블록 현상)를 매끄럽게 폅니다.")

        self.sharpen_sw = ctk.CTkSwitch(
            up_right, text="윤곽선 선명하게", font=FONT_DEFAULT, 
            text_color=TEXT_MAIN, progress_color=ACCENT
        )
        self.sharpen_sw.select()
        self.sharpen_sw.pack(anchor="w", padx=18, pady=(4, 16))
        ToolTip(self.sharpen_sw, "뿌옇게 흐려진 경계선을 더욱 또렷하고 선명하게 강조합니다.")

        self.bottom_action_box = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_action_box.pack(fill="x", side="bottom")
        self.bottom_action_box.grid_columnconfigure(0, weight=1)
        self.bottom_action_box.grid_columnconfigure(1, weight=2)

        self.up_preview_btn = ctk.CTkButton(
            self.bottom_action_box, text="결과 미리보기", height=48, corner_radius=10,
            font=FONT_CARD_TITLE, fg_color=BG_CARD, hover_color=BORDER_COLOR,
            text_color=TEXT_MAIN, border_width=1, border_color=BORDER_COLOR,
            command=lambda: self.start_upscale(True)
        )
        self.up_preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.up_run_btn = ctk.CTkButton(
            self.bottom_action_box, text="업스케일링 시작", height=48, corner_radius=10,
            font=FONT_CARD_TITLE, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#FFFFFF", command=lambda: self.start_upscale(False)
        )
        self.up_run_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.update_button_styles()

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
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

        for name, btn in self.scale_btns.items():
            if name == self.selected_scale:
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

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
            title="업스케일링할 이미지 추가 선택",
            filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("모든 파일", "*.*")]
        )
        if files:
            self.add_up_files(list(files))

    def start_upscale(self, open_preview=False):
        if not self.up_file_list:
            return self.show_file_card_warning("! 먼저 작업할 이미지 파일을 선택해주세요")
            
        self.app.engine_dot.configure(text="● 업스케일 연산 중...", text_color=WARN_COLOR)
        file_names = [os.path.basename(p) for p in self.up_file_list]
        self.app.floating_prog.start(file_names)

        def worker():
            preview_items = []
            last_dir = ""
            try:
                for idx, fpath in enumerate(self.up_file_list, start=1):
                    def cb(msg, ratio, i=idx):
                        self.after(0, lambda: self.app.floating_prog.update_state(i, len(self.up_file_list), ratio))
                        
                    orig_pil = Image.open(fpath).convert("RGB")
                    
                    target_engine = "고속 선명화" if self.selected_engine == "기본 선명화 (빠름)" else "정밀 AI 복원"
                    target_type = "일러스트 / 그래픽" if self.selected_type == "일러스트" else "실사 사진"
                    
                    res_pil = engine_upscale.process_upscale_to_memory(
                        image_path=fpath, engine=target_engine, img_type=target_type,
                        scale=self.selected_scale, denoise=bool(self.denoise_sw.get()), 
                        sharpen=bool(self.sharpen_sw.get()), progress_callback=cb
                    )
                    
                    if open_preview:
                        preview_items.append({"path": fpath, "orig_img": orig_pil, "res_img": res_pil})
                    else:
                        last_dir, _ = engine_upscale.save_upscaled_image(res_pil, fpath, self.app.settings.get("custom_out_dir", ""))
                        
                self.after(0, lambda: self.on_complete(preview_items, last_dir))
            except Exception as e:
                self.after(0, lambda err=str(e): messagebox.showerror("오류", err))
                
        threading.Thread(target=worker, daemon=True).start()

    def on_complete(self, preview_items, last_dir):
        self.app.floating_prog.stop()
        self.app.engine_dot.configure(text="● Modular Engine Ready", text_color=SUCCESS_COLOR)
        if preview_items:
            UpPreviewWindow(self, preview_items)
        else:
            messagebox.showinfo("완료", "업스케일링 및 저장이 완료되었습니다.")
            if self.app.settings.get("auto_open_folder", True) and last_dir: os.startfile(last_dir)