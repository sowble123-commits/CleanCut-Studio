import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw
import customtkinter as ctk

from config import *
from ui_common import ToolTip, FloatingProgressWidget, InteractiveImageCanvas
import engine_bg

def create_checkerboard_preview(pil_rgba, box_size=(380, 360)):
    bw, bh = box_size
    w, h = pil_rgba.size
    scale = min(bw / max(1, w), bh / max(1, h))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = pil_rgba.resize((nw, nh), Image.Resampling.LANCZOS)

    checker = Image.new("RGBA", (nw, nh), (255, 255, 255, 255))
    draw = ImageDraw.Draw(checker)
    step = 12
    for y in range(0, nh, step):
        for x in range(0, nw, step):
            if (x // step + y // step) % 2 == 1:
                draw.rectangle([x, y, min(x + step, nw), min(y + step, nh)], fill=(220, 224, 232, 255))

    checker.alpha_composite(resized)
    return checker, (nw, nh)


class FileListModal(ctk.CTkToplevel):
    def __init__(self, tab_bg):
        super().__init__(tab_bg.app)
        self.tab_bg = tab_bg
        self.app = tab_bg.app
        self.title("현재 선택된 파일 관리")
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

        count = len(self.tab_bg.bg_file_list)
        self.lbl_title.configure(text=f"선택된 이미지 목록 ({count}개)")

        if count == 0:
            ctk.CTkLabel(
                self.scroll_box, text="선택된 파일이 없습니다.",
                font=FONT_DEFAULT, text_color=TEXT_SUB
            ).pack(pady=80)
            return

        for idx, fpath in enumerate(self.tab_bg.bg_file_list):
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
        if path_to_remove in self.tab_bg.bg_file_list:
            self.tab_bg.bg_file_list.remove(path_to_remove)
            self.tab_bg.refresh_file_badge()
            self.render_list()

    def clear_all(self):
        self.tab_bg.bg_file_list.clear()
        self.tab_bg.refresh_file_badge()
        self.destroy()

    def add_more_files(self):
        self.tab_bg.select_bg_files()
        self.render_list()


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, tab_bg, items_data, active_formats):
        super().__init__(tab_bg.app)
        self.tab_bg = tab_bg
        self.app = tab_bg.app
        self.items = items_data
        self.active_formats = active_formats
        self.current_idx = 0
        self.is_reprocessing = False
        self.warn_timer = None
        self._is_updating_ui = False
        self.current_view_mode = "toggle_res"

        self.title("변환 결과 미리보기 및 개별 수정")
        self.geometry("1000x720")
        self.resizable(True, True)
        self.configure(fg_color=BG_MAIN)
        
        self.floating_prog = FloatingProgressWidget(self)
        self.build_ui()
        self.load_current_item_to_ui()

    def shake_window(self):
        x = self.winfo_x()
        y = self.winfo_y()
        offsets = [-10, 10, -8, 8, -5, 5, -2, 2, 0]
        for i, dx in enumerate(offsets):
            self.after(i * 28, lambda new_x=x + dx: self.geometry(f"+{new_x}+{y}"))

    def build_ui(self):
        top_bar = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color=BG_SIDEBAR, border_width=1, border_color=BORDER_COLOR)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        title_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_row.pack(side="left", padx=22)
        self.lbl_filename = ctk.CTkLabel(title_row, text="", font=("맑은 고딕", 15, "bold"), text_color=TEXT_MAIN)
        self.lbl_filename.pack(side="left")
        self.lbl_saved_badge = ctk.CTkLabel(
            title_row, text=" ● 저장됨 ", font=FONT_SMALL_BOLD,
            text_color=SUCCESS_COLOR, fg_color=("#DCFCE7", "#132A22"), corner_radius=6
        )

        btn_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_row.pack(side="right", padx=22)
        self.btn_delete = ctk.CTkButton(
            btn_row, text="삭제", width=68, height=32, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=ERROR_COLOR,
            text_color=ERROR_COLOR, hover_color=("#FEE2E2", "#2A1519"),
            font=FONT_DEFAULT_BOLD, command=self.delete_current_item
        )
        self.btn_delete.pack(side="right", padx=(8, 0))

        self.btn_save_one = ctk.CTkButton(
            btn_row, text="개별 저장", width=88, height=32, corner_radius=6,
            fg_color=("#E2E8F0", "#262936"), hover_color=("#CBD5E1", "#323646"),
            text_color=TEXT_MAIN, font=FONT_DEFAULT_BOLD, command=self.save_current_item
        )
        self.btn_save_one.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=22, pady=18)
        
        right_card = ctk.CTkFrame(body, width=320, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        right_card.pack(side="right", fill="y", padx=(10, 0))
        right_card.pack_propagate(False)

        left_card = ctk.CTkFrame(body, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        nav_bar = ctk.CTkFrame(left_card, fg_color="transparent")
        nav_bar.pack(fill="x", padx=10, pady=(12, 4))
        
        self.btn_prev = ctk.CTkButton(nav_bar, text="◀ 이전", width=60, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=self.prev_item)
        self.btn_prev.pack(side="left", padx=2)
        
        self.lbl_page = ctk.CTkLabel(nav_bar, text="1 / 1", font=FONT_DEFAULT_BOLD, text_color=TEXT_MAIN, width=40)
        self.lbl_page.pack(side="left", padx=4)
        
        self.btn_next = ctk.CTkButton(nav_bar, text="다음 ▶", width=60, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=self.next_item)
        self.btn_next.pack(side="left", padx=(2, 16))

        ctk.CTkLabel(nav_bar, text="Spacebar 누른 채 드래그 시 화면 이동", font=FONT_SMALL, text_color=TEXT_SUB).pack(side="left")

        ctk.CTkButton(nav_bar, text="1:1", width=44, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.canvas.zoom_1to1()).pack(side="right", padx=2)
        ctk.CTkButton(nav_bar, text="맞춤", width=44, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.canvas.fit_to_screen()).pack(side="right", padx=2)
        ctk.CTkButton(nav_bar, text="-", width=36, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.canvas.zoom_out()).pack(side="right", padx=2)
        ctk.CTkButton(nav_bar, text="+", width=36, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.canvas.zoom_in()).pack(side="right", padx=2)

        self.preview_box = ctk.CTkFrame(left_card, corner_radius=8, fg_color=BG_INNER)
        self.preview_box.pack(padx=16, pady=(10, 16), fill="both", expand=True)

        bg_col = BG_INNER[1] if self.app.settings.get("theme") == "dark" else BG_INNER[0]
        self.canvas = InteractiveImageCanvas(self.preview_box, bg_color=bg_col, draw_mode=False)
        self.canvas.pack(fill="both", expand=True)

        opt_header = ctk.CTkFrame(right_card, fg_color="transparent")
        opt_header.pack(fill="x", padx=18, pady=(16, 6))
        ctk.CTkLabel(opt_header, text="작업 모드", font=("맑은 고딕", 13, "bold"), text_color=TEXT_MAIN).pack(side="left")

        self.btn_reset_opt = ctk.CTkButton(
            opt_header, text="↺ 원래대로", width=72, height=24, corner_radius=6,
            fg_color="transparent", text_color=ACCENT, hover_color=BG_INNER,
            font=FONT_SMALL_BOLD, command=self.reset_current_pending
        )

        mode_row = ctk.CTkFrame(right_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=18, pady=(0, 12))
        mode_row.grid_columnconfigure((0, 1), weight=1, uniform="mode_preview")

        self.mode_btns = {}
        for idx, m_name in enumerate(["단색 배경", "일반 사진"]):
            b = ctk.CTkButton(
                mode_row, text=m_name, height=34, width=10, corner_radius=6,
                font=FONT_DEFAULT_BOLD,
                command=lambda m=m_name: self.on_change_mode(m)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            b.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.mode_btns[m_name] = b

        self.strength_section = ctk.CTkFrame(right_card, fg_color="transparent")
        ctk.CTkLabel(self.strength_section, text="허용치 (단색 배경용)", font=("맑은 고딕", 13, "bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 6))
        str_row = ctk.CTkFrame(self.strength_section, fg_color="transparent")
        str_row.pack(fill="x", pady=(0, 12))
        str_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="str_preview")

        self.str_btns = {}
        for idx, s_name in enumerate(["낮음", "기본", "높음"]):
            btn = ctk.CTkButton(
                str_row, text=s_name, height=32, width=10, corner_radius=6,
                font=FONT_SMALL_BOLD,
                command=lambda s=s_name: self.on_change_strength(s)
            )
            if idx == 0: padx = (0, 4)
            elif idx == 1: padx = (2, 2)
            else: padx = (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.str_btns[s_name] = btn

        self.trim_section = ctk.CTkFrame(right_card, fg_color="transparent")
        self.trim_section.pack(fill="x", padx=18, pady=(2, 8))
        ctk.CTkLabel(self.trim_section, text="내보내기 설정", font=("맑은 고딕", 13, "bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 6))

        self.sw_crop = ctk.CTkSwitch(
            self.trim_section, text="빈 여백 자동 자르기", font=FONT_DEFAULT,
            text_color=TEXT_MAIN, progress_color=ACCENT, command=self.on_change_trim
        )
        self.sw_crop.pack(anchor="w", pady=4)

        self.sw_square = ctk.CTkSwitch(
            self.trim_section, text="1:1 정사각형 맞춤", font=FONT_DEFAULT,
            text_color=TEXT_MAIN, progress_color=ACCENT, command=self.on_change_trim
        )
        self.sw_square.pack(anchor="w", pady=4)

        bottom_act = ctk.CTkFrame(right_card, fg_color="transparent")
        bottom_act.pack(side="bottom", fill="x", padx=18, pady=16)

        view_row = ctk.CTkFrame(bottom_act, fg_color="transparent")
        view_row.pack(fill="x", pady=(0, 16))
        
        self.btn_view_res = ctk.CTkButton(view_row, text="결과물 보기", height=32, corner_radius=6, fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("toggle_res"))
        self.btn_view_res.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.btn_view_orig = ctk.CTkButton(view_row, text="원본 보기", height=32, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("toggle_orig"))
        self.btn_view_orig.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.lbl_warn = ctk.CTkLabel(bottom_act, text="", font=FONT_SMALL_BOLD, text_color=ERROR_COLOR)
        self.lbl_warn.pack(anchor="w", pady=(0, 4))

        self.btn_apply = ctk.CTkButton(
            bottom_act, text="변경사항 적용", height=40, corner_radius=8,
            fg_color=("#E2E8F0", "#262936"), hover_color=("#CBD5E1", "#323646"),
            text_color=TEXT_MAIN, border_width=1, border_color=BORDER_COLOR,
            font=("맑은 고딕", 13, "bold"), command=self.apply_pending_changes
        )
        self.btn_apply.pack(fill="x", pady=(0, 8))

        self.btn_save_all = ctk.CTkButton(
            bottom_act, text="전체 저장", height=44, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=FONT_CARD_TITLE, command=self.save_all_items
        )
        self.btn_save_all.pack(fill="x")

    def on_view_change(self, mode):
        self.current_view_mode = mode
        if mode == "toggle_res":
            self.btn_view_res.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            self.btn_view_orig.configure(fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER, border_width=1, border_color=BORDER_COLOR)
        else:
            self.btn_view_orig.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            self.btn_view_res.configure(fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER, border_width=1, border_color=BORDER_COLOR)
        self.canvas.set_view_mode(mode)

    def load_current_item_to_ui(self):
        if not self.items:
            self.destroy()
            return

        self.current_idx = max(0, min(self.current_idx, len(self.items) - 1))
        item = self.items[self.current_idx]

        fname = os.path.basename(item["path"])
        self.lbl_filename.configure(text=fname)
        if item["saved"]:
            self.lbl_saved_badge.pack(side="left", padx=(10, 0), ipadx=6, ipady=1)
        else:
            self.lbl_saved_badge.pack_forget()

        self.lbl_page.configure(text=f"{self.current_idx + 1} / {len(self.items)}")

        img_to_show = item.get("raw_pil_img", item["pil_img"])
        pend_cfg = item["pending"]
        
        img_to_show = engine_bg.apply_trimming(
            img_to_show,
            auto_crop=pend_cfg.get("auto_crop", False),
            make_square=pend_cfg.get("make_square", False)
        )

        checker_img, sz = create_checkerboard_preview(img_to_show, box_size=(1000, 1000))
        
        self.canvas.set_comparison(item["orig_img"], checker_img, mode="toggle_res")
        self.on_view_change("toggle_res")
        
        self.after(100, lambda: self.canvas.fit_to_screen())

        self.refresh_right_controls()

    def refresh_right_controls(self):
        self._is_updating_ui = True
        item = self.items[self.current_idx]
        app_cfg = item["applied"]
        pend_cfg = item["pending"]
        is_modified = (app_cfg != pend_cfg)

        if is_modified:
            self.btn_reset_opt.pack(side="right")
        else:
            self.btn_reset_opt.pack_forget()

        for m_name, btn in self.mode_btns.items():
            label_txt = f"● {m_name}" if app_cfg["mode"] == m_name else m_name
            if pend_cfg["mode"] == m_name:
                btn.configure(text=label_txt, fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(text=label_txt, fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

        if pend_cfg["mode"] == "단색 배경":
            self.strength_section.pack(fill="x", padx=18, before=self.trim_section)
            for s_name, btn in self.str_btns.items():
                label_txt = f"● {s_name}" if (app_cfg["mode"] == "단색 배경" and app_cfg["strength"] == s_name) else s_name
                if pend_cfg["strength"] == s_name:
                    btn.configure(text=label_txt, fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
                else:
                    btn.configure(text=label_txt, fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)
        else:
            self.strength_section.pack_forget()

        crop_txt = "빈 여백 자동 자르기 (● 적용됨)" if app_cfg["auto_crop"] else "빈 여백 자동 자르기"
        sq_txt = "1:1 정사각형 맞춤 (● 적용됨)" if app_cfg["make_square"] else "1:1 정사각형 맞춤"
        self.sw_crop.configure(text=crop_txt)
        self.sw_square.configure(text=sq_txt)

        if pend_cfg["auto_crop"] != bool(self.sw_crop.get()):
            if pend_cfg["auto_crop"]:
                self.sw_crop.select()
            else:
                self.sw_crop.deselect()

        if pend_cfg["make_square"] != bool(self.sw_square.get()):
            if pend_cfg["make_square"]:
                self.sw_square.select()
            else:
                self.sw_square.deselect()

        changed_count = sum(1 for it in self.items if it["applied"] != it["pending"])
        if changed_count > 0:
            self.btn_apply.configure(
                text=f"변경사항 적용 ({changed_count}장)",
                border_color=ACCENT, border_width=2
            )
        else:
            self.btn_apply.configure(
                text="변경사항 적용",
                border_color=BORDER_COLOR, border_width=1
            )
        self._is_updating_ui = False

    def clear_warning(self):
        if self.warn_timer:
            self.after_cancel(self.warn_timer)
            self.warn_timer = None
        self.lbl_warn.configure(text="")
        
        changed_count = sum(1 for it in self.items if it["applied"] != it["pending"])
        if changed_count > 0:
            self.btn_apply.configure(border_color=ACCENT, border_width=2)
        else:
            self.btn_apply.configure(border_color=BORDER_COLOR, border_width=1)

    def show_duplicate_warning(self, msg):
        self.shake_window()
        self.lbl_warn.configure(text=msg)
        self.btn_apply.configure(border_color=ERROR_COLOR, border_width=2)
        if self.warn_timer:
            self.after_cancel(self.warn_timer)
        self.warn_timer = self.after(2200, self.clear_warning)

    def on_change_mode(self, new_mode):
        self.clear_warning()
        self.items[self.current_idx]["pending"]["mode"] = new_mode
        self.refresh_right_controls()

    def on_change_strength(self, new_str):
        self.clear_warning()
        self.items[self.current_idx]["pending"]["strength"] = new_str
        self.refresh_right_controls()

    def on_change_trim(self):
        if getattr(self, '_is_updating_ui', False):
            return
        
        self.items[self.current_idx]["pending"]["auto_crop"] = bool(self.sw_crop.get())
        self.items[self.current_idx]["pending"]["make_square"] = bool(self.sw_square.get())
        
        self.clear_warning()
        self.load_current_item_to_ui()

    def reset_current_pending(self):
        self.clear_warning()
        item = self.items[self.current_idx]
        item["pending"] = dict(item["applied"])
        self.load_current_item_to_ui()

    def prev_item(self):
        if len(self.items) > 1:
            self.current_idx = (self.current_idx - 1) % len(self.items)
            self.load_current_item_to_ui()

    def next_item(self):
        if len(self.items) > 1:
            self.current_idx = (self.current_idx + 1) % len(self.items)
            self.load_current_item_to_ui()

    def apply_pending_changes(self):
        if self.is_reprocessing:
            return

        target_indices = [i for i, it in enumerate(self.items) if it["applied"] != it["pending"]]
        if not target_indices:
            self.show_duplicate_warning("! 변경된 설정이 없습니다 (현재 화면과 동일한 설정입니다)")
            return

        self.is_reprocessing = True
        target_names = [os.path.basename(self.items[i]["path"]) for i in target_indices]
        self.floating_prog.start(target_names)

        tasks = [(i, dict(self.items[i]["pending"])) for i in target_indices]

        def worker():
            total = len(tasks)
            try:
                for step_num, (item_idx, cfg) in enumerate(tasks, start=1):
                    item = self.items[item_idx]
                    app_cfg = item["applied"]
                    
                    needs_heavy_processing = (cfg["mode"] != app_cfg["mode"] or cfg["strength"] != app_cfg["strength"])
                    
                    def cb(msg, r, sn=step_num):
                        self.after(0, lambda: self.floating_prog.update_state(sn, total, r))
                        
                    engine_strength_map = {"낮음": "낮음", "기본": "표준", "높음": "높음"}
                    target_strength = engine_strength_map.get(cfg["strength"], "표준")

                    if needs_heavy_processing:
                        new_pil = engine_bg.process_image_to_memory(
                            image_path=item["path"],
                            mode=cfg["mode"],
                            strength=target_strength,
                            auto_crop=False, 
                            make_square=False,
                            progress_callback=cb
                        )
                        item["raw_pil_img"] = new_pil
                        final_pil = engine_bg.apply_trimming(new_pil, auto_crop=cfg["auto_crop"], make_square=cfg["make_square"])
                    else:
                        cb("다듬기 설정 적용 중...", 0.5)
                        base_img = item.get("raw_pil_img", item["pil_img"])
                        final_pil = engine_bg.apply_trimming(base_img, auto_crop=cfg["auto_crop"], make_square=cfg["make_square"])
                        cb("다듬기 완료", 1.0)

                    def apply_one(idx=item_idx, pil_res=final_pil, c=cfg):
                        if idx < len(self.items):
                            self.items[idx]["pil_img"] = pil_res
                            self.items[idx]["applied"] = dict(c)
                            self.items[idx]["pending"] = dict(c)
                            self.items[idx]["saved"] = False
                            if self.current_idx == idx:
                                self.load_current_item_to_ui()
                            else:
                                self.refresh_right_controls()

                    self.after(0, apply_one)

                self.after(0, self.on_reprocess_done)
            except Exception as e:
                self.after(0, lambda err=str(e): self.on_reprocess_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def on_reprocess_done(self):
        self.is_reprocessing = False
        self.floating_prog.stop()
        self.load_current_item_to_ui()

    def on_reprocess_error(self, err_msg):
        self.is_reprocessing = False
        self.floating_prog.stop()
        messagebox.showerror("재변환 오류", err_msg, parent=self)

    def delete_current_item(self):
        if self.is_reprocessing or not self.items:
            return
        del self.items[self.current_idx]
        if not self.items:
            self.destroy()
            return
        if self.current_idx >= len(self.items):
            self.current_idx = len(self.items) - 1
        self.load_current_item_to_ui()

    def save_current_item(self):
        if not self.items:
            return
        item = self.items[self.current_idx]
        if hasattr(self.app, 'sync_settings_from_ui'):
            self.app.sync_settings_from_ui()
        out_dir, _ = engine_bg.save_processed_image(
            pil_image=item["pil_img"],
            original_path=item["path"],
            formats=self.active_formats,
            custom_out_dir=self.app.settings.get("custom_out_dir", ""),
            filename_suffix=self.app.settings.get("filename_suffix", "_cut")
        )
        item["saved"] = True
        self.load_current_item_to_ui()

    def save_all_items(self):
        if self.is_reprocessing or not self.items:
            return
        unsaved = [it for it in self.items if not it["saved"]]
        targets = unsaved if unsaved else self.items

        if hasattr(self.app, 'sync_settings_from_ui'):
            self.app.sync_settings_from_ui()

        last_out_dir = ""
        for it in targets:
            out_dir, _ = engine_bg.save_processed_image(
                pil_image=it["pil_img"],
                original_path=it["path"],
                formats=self.active_formats,
                custom_out_dir=self.app.settings.get("custom_out_dir", ""),
                filename_suffix=self.app.settings.get("filename_suffix", "_cut")
            )
            it["saved"] = True
            last_out_dir = out_dir

        self.load_current_item_to_ui()
        messagebox.showinfo(
            "저장 완료",
            f"총 {len(targets)}장의 이미지가 저장되었습니다!\n\n저장 폴더:\n{last_out_dir}",
            parent=self
        )
        if self.app.settings.get("auto_open_folder", True) and last_out_dir and os.path.exists(last_out_dir):
            os.startfile(last_out_dir)
        self.destroy()


class TabBackground(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        self.bg_file_list = []
        self.selected_mode = "단색 배경"
        self.selected_strength = "기본"
        self.main_mode_btns = {}
        self.main_str_btns = {}
        self.selected_formats = {"PNG": False, "WEBP": False, "ICO": False, "JPG": False}
        self.format_buttons = {}
        self.is_processing = False
        self.file_warn_timer = None
        self.preview_window = None

        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="배경 지우기", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="단색 배경 또는 일반 사진 모드로 여러 이미지의 배경을 깔끔하게 지웁니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        self.drop_card = ctk.CTkFrame(self, height=130, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR, cursor="hand2")
        self.drop_card.pack(fill="x", pady=(0, 16))
        self.drop_card.pack_propagate(False)

        lbl1 = ctk.CTkLabel(self.drop_card, text="+  작업할 이미지 파일 추가하기 (클릭 또는 드래그 앤 드롭)", font=("맑은 고딕", 15, "bold"), text_color=TEXT_MAIN)
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
            widget.bind("<Button-1>", lambda e: self.select_bg_files())

        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 14))
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        self.card_left = ctk.CTkFrame(grid_frame, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.card_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(self.card_left, text="PROCESSING ENGINE", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        lbl_mode_title = ctk.CTkLabel(self.card_left, text="작업 모드", font=FONT_CARD_TITLE, text_color=TEXT_MAIN)
        lbl_mode_title.pack(anchor="w", padx=18, pady=(0, 10))

        mode_btn_row = ctk.CTkFrame(self.card_left, fg_color="transparent")
        mode_btn_row.pack(fill="x", padx=18, pady=(0, 12))
        mode_btn_row.grid_columnconfigure((0, 1), weight=1, uniform="mode_main")

        for idx, m_name in enumerate(["단색 배경", "일반 사진"]):
            btn = ctk.CTkButton(
                mode_btn_row, text=m_name, height=34, width=10, corner_radius=6,
                font=FONT_DEFAULT_BOLD,
                command=lambda m=m_name: self.on_main_mode_change(m)
            )
            padx = (0, 4) if idx == 0 else (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.main_mode_btns[m_name] = btn
            
            if m_name == "단색 배경":
                ToolTip(btn, "흰색 등 단색 배경의 로고·아이콘을 빠르게 지웁니다.")
            else:
                ToolTip(btn, "배경이 복잡한 인물·상품 사진을 정밀하게 오려냅니다.")

        self.strength_container = ctk.CTkFrame(self.card_left, height=75, fg_color="transparent")
        self.strength_container.pack(fill="x", padx=18, pady=(0, 16))
        self.strength_container.pack_propagate(False)

        self.main_strength_box = ctk.CTkFrame(self.strength_container, fg_color="transparent")
        self.main_strength_box.pack(fill="both", expand=True)

        ctk.CTkLabel(self.main_strength_box, text="허용치 (단색 배경용)", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(0, 6))

        str_btn_row = ctk.CTkFrame(self.main_strength_box, fg_color="transparent")
        str_btn_row.pack(fill="x")
        str_btn_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="str_main")

        self.main_str_btns = {}
        for idx, s_name in enumerate(["낮음", "기본", "높음"]):
            btn = ctk.CTkButton(
                str_btn_row, text=s_name, height=32, width=10, corner_radius=6,
                font=FONT_SMALL_BOLD,
                command=lambda s=s_name: self.on_main_strength_change(s)
            )
            if idx == 0: padx = (0, 4)
            elif idx == 1: padx = (2, 2)
            else: padx = (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.main_str_btns[s_name] = btn
            
            if s_name == "낮음":
                ToolTip(btn, "배경색과 완전히 같은 색만 조심스럽게 지웁니다.")
            elif s_name == "기본":
                ToolTip(btn, "일반적인 로고·아이콘에 가장 알맞은 기본 설정입니다.")
            else:
                ToolTip(btn, "테두리에 남은 흐릿한 그림자나 얼룩까지 넓게 지웁니다.")

        self.update_main_left_buttons()

        self.card_right = ctk.CTkFrame(grid_frame, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.card_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(self.card_right, text="OUTPUT & EXPORT", font=("맑은 고딕", 10, "bold"), text_color=ACCENT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(self.card_right, text="내보내기 설정", font=FONT_CARD_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(0, 8))

        self.crop_sw = ctk.CTkSwitch(self.card_right, text="빈 여백 자동 자르기", font=FONT_DEFAULT, text_color=TEXT_MAIN, progress_color=ACCENT)
        self.crop_sw.pack(anchor="w", padx=18, pady=4)
        ToolTip(self.crop_sw, "투명해진 바깥의 빈 공간을 잘라내고, 가운데 피사체 크기에 딱 맞게 맞춥니다.")

        self.square_sw = ctk.CTkSwitch(self.card_right, text="1:1 정사각형 맞춤", font=FONT_DEFAULT, text_color=TEXT_MAIN, progress_color=ACCENT)
        self.square_sw.pack(anchor="w", padx=18, pady=4)
        ToolTip(self.square_sw, "이미지가 찌그러지지 않게 상하 또는 좌우 여백을 보태어 반듯한 정사각형으로 만듭니다.")

        self.fmt_label = ctk.CTkLabel(self.card_right, text="저장 형식 (1개 이상 선택 필수)", font=FONT_DEFAULT, text_color=TEXT_SUB)
        self.fmt_label.pack(anchor="w", padx=18, pady=(8, 6))

        fmt_box = ctk.CTkFrame(self.card_right, fg_color="transparent")
        fmt_box.pack(fill="x", padx=18, pady=(0, 16))
        fmt_box.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="fmt_main")
        
        for idx, fmt in enumerate(["PNG", "WEBP", "ICO", "JPG"]):
            btn = ctk.CTkButton(
                fmt_box, text=fmt, height=30, width=10, corner_radius=6, font=FONT_SMALL_BOLD,
                command=lambda f=fmt: self.toggle_format(f)
            )
            if idx == 0: padx = (0, 4)
            elif idx == 1: padx = (2, 2)
            elif idx == 2: padx = (2, 2)
            else: padx = (4, 0)
            btn.grid(row=0, column=idx, sticky="ew", padx=padx)
            self.format_buttons[fmt] = btn
        self.update_format_buttons()

        self.bottom_action_box = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_action_box.pack(fill="x", side="bottom")
        self.bottom_action_box.grid_columnconfigure(0, weight=1)
        self.bottom_action_box.grid_columnconfigure(1, weight=2)

        self.bg_preview_btn = ctk.CTkButton(
            self.bottom_action_box, text="결과 미리보기", height=48, corner_radius=10,
            font=FONT_CARD_TITLE, fg_color=BG_CARD, hover_color=BORDER_COLOR,
            text_color=TEXT_MAIN, border_width=1, border_color=BORDER_COLOR,
            command=lambda: self.start_bg_process(open_preview=True)
        )
        self.bg_preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.bg_run_btn = ctk.CTkButton(
            self.bottom_action_box, text="일괄 배경 제거 및 변환 시작", height=48, corner_radius=10,
            font=("맑은 고딕", 15, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#FFFFFF", command=lambda: self.start_bg_process(open_preview=False)
        )
        self.bg_run_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def on_main_mode_change(self, selected_mode):
        if self.is_processing:
            return
        self.selected_mode = selected_mode
        if selected_mode == "단색 배경":
            self.main_strength_box.pack(fill="both", expand=True)
        else:
            self.main_strength_box.pack_forget()
        self.update_main_left_buttons()

    def on_main_strength_change(self, selected_str):
        if self.is_processing:
            return
        self.selected_strength = selected_str
        self.update_main_left_buttons()

    def update_main_left_buttons(self):
        for m_name, btn in self.main_mode_btns.items():
            if self.selected_mode == m_name:
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

        for s_name, btn in self.main_str_btns.items():
            if self.selected_strength == s_name:
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                btn.configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)

    def refresh_file_badge(self):
        if self.file_warn_timer:
            self.after_cancel(self.file_warn_timer)
            self.file_warn_timer = None
        self.drop_card.configure(border_color=BORDER_COLOR, border_width=1)
        count = len(self.bg_file_list)
        if count > 0:
            self.file_badge.configure(
                text=f" 현재 선택된 파일: {count}개 (클릭하여 관리/취소) ",
                text_color=SUCCESS_COLOR
            )
        else:
            self.file_badge.configure(
                text=" 현재 선택된 파일: 0개 ",
                text_color=ACCENT
            )

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

    def add_bg_files(self, raw_paths):
        if self.is_processing or not raw_paths:
            return

        valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".ico")
        existing_norm = {os.path.normcase(os.path.abspath(p)) for p in self.bg_file_list}

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
                                self.bg_file_list.append(full_p)
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
                    self.bg_file_list.append(p)
                    existing_norm.add(norm_p)
                    added_count += 1

        if dup_count > 0 or invalid_count > 0:
            if added_count > 0:
                parts = []
                if dup_count > 0: parts.append(f"중복 {dup_count}개")
                if invalid_count > 0: parts.append(f"미지원 {invalid_count}개")
                msg = f"✅ {added_count}개 추가 (" + ", ".join(parts) + " 제외)"
                self.show_soft_warning(msg)
            else:
                if invalid_count > 0 and dup_count == 0:
                    self.show_file_card_warning("! 지원하지 않는 파일 형식입니다 (PNG, JPG, WEBP, BMP, ICO 지원)")
                else:
                    self.show_file_card_warning(f"! 이미 추가된 중복 파일입니다 ({dup_count}개)")
        else:
            self.refresh_file_badge()

    def on_drop_files(self, dropped_items):
        if self.is_processing or self.app.current_page_name != "bg":
            return
        decoded = []
        for item in dropped_items:
            if isinstance(item, bytes):
                try:
                    decoded.append(item.decode("mbcs"))
                except Exception:
                    decoded.append(item.decode("utf-8", errors="ignore"))
            else:
                decoded.append(str(item))
        self.add_bg_files(decoded)

    def on_click_file_badge(self):
        if self.is_processing:
            return
        if not self.bg_file_list:
            self.select_bg_files()
        else:
            FileListModal(self)

    def select_bg_files(self):
        if self.is_processing:
            return
        files = filedialog.askopenfilenames(
            title="배경을 제거할 이미지 추가 선택",
            filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.ico"), ("모든 파일", "*.*")]
        )
        if files:
            self.add_bg_files(list(files))

    def start_bg_process(self, open_preview=False):
        if self.is_processing:
            return

        if open_preview and self.preview_window is not None and self.preview_window.winfo_exists():
            ans = messagebox.askyesno(
                "미리보기 창 열림",
                "이미 열려있는 미리보기 창이 있습니다.\n기존 작업 내역을 무시하고 새로 변환하시겠습니까?"
            )
            if not ans:
                self.preview_window.deiconify()
                self.preview_window.lift()
                self.preview_window.focus_force()
                return
            else:
                self.preview_window.destroy()
                self.preview_window = None

        active_formats = [fmt for fmt, selected in self.selected_formats.items() if selected]
        has_error = False

        if not self.bg_file_list:
            self.drop_card.configure(border_color=ERROR_COLOR, border_width=2)
            self.file_badge.configure(text=" ! 먼저 작업할 이미지 파일을 선택해주세요 ", text_color=ERROR_COLOR)
            has_error = True

        if not active_formats:
            self.card_right.configure(border_color=ERROR_COLOR, border_width=2)
            self.fmt_label.configure(text="! 저장할 형식(확장자)을 1개 이상 선택해주세요", text_color=ERROR_COLOR, font=("맑은 고딕", 12, "bold"))
            for btn in self.format_buttons.values():
                btn.configure(border_color=ERROR_COLOR)
            has_error = True

        if has_error:
            self.app.shake_window()
            return

        if hasattr(self.app, 'sync_settings_from_ui'):
            self.app.sync_settings_from_ui()
        self.app.save_settings()

        mode = self.selected_mode
        strength = self.selected_strength
        auto_crop = bool(self.crop_sw.get())
        make_square = bool(self.square_sw.get())

        self.is_processing = True
        file_names = [os.path.basename(p) for p in self.bg_file_list]
        self.app.floating_prog.start(file_names)

        self.app.engine_dot.configure(text="● AI 엔진 연산 중 (화면 멈춤 정상)...", text_color=WARN_COLOR)
        self.bg_preview_btn.configure(state="disabled")
        self.bg_run_btn.configure(state="disabled", text="AI 연산 진행 중 (화면 멈춤 정상)...")

        def worker():
            total = len(self.bg_file_list)
            preview_items = []
            last_out_dir = ""
            try:
                for idx, fpath in enumerate(self.bg_file_list, start=1):
                    def step_cb(msg, ratio, i=idx):
                        self.after(0, lambda: self.app.floating_prog.update_state(i, total, ratio))

                    engine_strength_map = {"낮음": "낮음", "기본": "표준", "높음": "높음"}
                    target_strength = engine_strength_map.get(strength, "표준")

                    if open_preview:
                        orig_pil = Image.open(fpath).convert("RGBA")
                        raw_pil = engine_bg.process_image_to_memory(
                            image_path=fpath,
                            mode=mode,
                            strength=target_strength,
                            auto_crop=False, 
                            make_square=False,
                            progress_callback=step_cb
                        )
                        
                        final_pil = engine_bg.apply_trimming(raw_pil, auto_crop=auto_crop, make_square=make_square)

                        init_cfg = {
                            "mode": mode,
                            "strength": strength,
                            "auto_crop": auto_crop,
                            "make_square": make_square
                        }
                        preview_items.append({
                            "path": fpath,
                            "orig_img": orig_pil,       
                            "pil_img": final_pil,       
                            "raw_pil_img": raw_pil,     
                            "applied": dict(init_cfg),
                            "pending": dict(init_cfg),
                            "saved": False
                        })
                    else:
                        out_dir, _ = engine_bg.remove_background_single(
                            image_path=fpath,
                            mode=mode,
                            strength=target_strength,
                            auto_crop=auto_crop,
                            make_square=make_square,
                            formats=active_formats,
                            progress_callback=step_cb,
                            custom_out_dir=self.app.settings.get("custom_out_dir", ""),
                            filename_suffix=self.app.settings.get("filename_suffix", "_cut")
                        )
                        last_out_dir = out_dir

                if open_preview:
                    self.after(0, lambda: self.on_preview_ready(preview_items, active_formats))
                else:
                    self.after(0, lambda: self.on_bg_complete(total, last_out_dir))
            except Exception as err:
                self.after(0, lambda e=err: self.on_bg_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def on_preview_ready(self, preview_items, active_formats):
        self.is_processing = False
        self.app.floating_prog.stop()
        self.app.engine_dot.configure(text="● Modular Engine Ready", text_color=SUCCESS_COLOR)
        self.bg_preview_btn.configure(state="normal")
        self.bg_run_btn.configure(state="normal", text="일괄 배경 제거 및 변환 시작")

        self.preview_window = PreviewWindow(self, preview_items, active_formats)

    def on_bg_complete(self, total, out_dir):
        self.is_processing = False
        self.app.floating_prog.stop()
        self.app.engine_dot.configure(text="● Modular Engine Ready", text_color=SUCCESS_COLOR)
        self.bg_preview_btn.configure(state="normal")
        self.bg_run_btn.configure(state="normal", text="일괄 배경 제거 및 변환 시작")

        messagebox.showinfo(
            "변환 완료",
            f"총 {total}장의 이미지 처리가 완료되었습니다!\n\n저장 폴더:\n{out_dir}"
        )
        if self.app.settings.get("auto_open_folder", True) and out_dir and os.path.exists(out_dir):
            os.startfile(out_dir)

    def on_bg_error(self, err_msg):
        self.is_processing = False
        self.app.floating_prog.stop()
        self.app.engine_dot.configure(text="● Engine Error", text_color=ERROR_COLOR)
        self.bg_preview_btn.configure(state="normal")
        self.bg_run_btn.configure(state="normal", text="일괄 배경 제거 및 변환 시작")
        messagebox.showerror("오류 발생", err_msg)

    def toggle_format(self, fmt):
        if self.is_processing:
            return
        self.selected_formats[fmt] = not self.selected_formats[fmt]
        if any(self.selected_formats.values()):
            self.card_right.configure(border_color=BORDER_COLOR, border_width=1)
            self.fmt_label.configure(text="저장 형식 (중복 선택 가능)", text_color=TEXT_SUB, font=FONT_DEFAULT)
        self.update_format_buttons()

    def update_format_buttons(self):
        for fmt, is_selected in self.selected_formats.items():
            if is_selected:
                self.format_buttons[fmt].configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, border_width=0)
            else:
                self.format_buttons[fmt].configure(fg_color=BG_INNER, text_color=TEXT_SUB, hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR)