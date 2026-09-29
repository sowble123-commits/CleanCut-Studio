import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw
import customtkinter as ctk

from config import *
import engine_eraser
from ui_common import FloatingProgressWidget, InteractiveImageCanvas

class EraserWorkspaceWindow(ctk.CTkToplevel):
    def __init__(self, tab_eraser, file_path):
        super().__init__(tab_eraser.app)
        self.tab_eraser = tab_eraser
        self.app = tab_eraser.app
        self.current_image_path = file_path
        
        self.original_image = Image.open(file_path).convert("RGB")
        self.result_image = None
        self.mask_image = None
        self.mask_draw = None
        self.is_processing = False
        
        self.title("매직 지우개 작업 공간")
        self.geometry("900x700")
        self.configure(fg_color=BG_MAIN)
        
        self.floating_prog = FloatingProgressWidget(self)
        self.build_ui()
        
        self.canvas.set_image(self.original_image)
        self.reset_mask()

    def build_ui(self):
        top_bar = ctk.CTkFrame(self, height=54, fg_color=BG_SIDEBAR, border_width=1, border_color=BORDER_COLOR)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        tool_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        tool_row.pack(side="left", padx=22, pady=10)
        
        # [수정] 박스 안 박스(SegmentedButton)를 개별 버튼으로 분리
        self.btn_tool_brush = ctk.CTkButton(tool_row, text="브러쉬", width=60, height=28, corner_radius=6, fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, font=FONT_SMALL_BOLD, command=lambda: self.on_tool_change("브러쉬"))
        self.btn_tool_brush.pack(side="left", padx=(0, 4))
        self.btn_tool_pan = ctk.CTkButton(tool_row, text="화면 이동", width=60, height=28, corner_radius=6, fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.on_tool_change("화면 이동"))
        self.btn_tool_pan.pack(side="left", padx=(0, 16))
        
        ctk.CTkLabel(tool_row, text="브러쉬 두께", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(side="left", padx=(0, 8))
        self.brush_size_var = tk.IntVar(value=20)
        self.slider_brush = ctk.CTkSlider(tool_row, from_=5, to=60, width=120, button_color=ACCENT, progress_color=ACCENT, variable=self.brush_size_var)
        self.slider_brush.pack(side="left")

        act_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        act_row.pack(side="right", padx=22, pady=10)
        self.btn_reset = ctk.CTkButton(act_row, text="칠한 영역 초기화", width=110, height=32, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_DEFAULT_BOLD, command=self.reset_mask)
        self.btn_reset.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=22, pady=(18, 0))
        
        zoom_bar = ctk.CTkFrame(body, fg_color="transparent")
        zoom_bar.pack(fill="x", pady=(0, 10))
        
        # [수정] 박스 안 박스(SegmentedButton)를 개별 버튼으로 분리
        self.btn_view_res = ctk.CTkButton(zoom_bar, text="결과물", width=60, height=28, corner_radius=6, fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("toggle_res"))
        self.btn_view_res.pack(side="left", padx=(0, 4))
        self.btn_view_res.configure(state="disabled")
        
        self.btn_view_orig = ctk.CTkButton(zoom_bar, text="원본", width=60, height=28, corner_radius=6, fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER, font=FONT_SMALL_BOLD, command=lambda: self.on_view_change("toggle_orig"))
        self.btn_view_orig.pack(side="left")
        self.btn_view_orig.configure(state="disabled")
        
        ctk.CTkLabel(zoom_bar, text=" Spacebar 누른 채로 드래그 시 화면 이동", font=FONT_SMALL, text_color=TEXT_SUB).pack(side="left", padx=16)
        
        ctk.CTkButton(zoom_bar, text="1:1", width=50, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, font=FONT_SMALL_BOLD, command=lambda: self.canvas.zoom_1to1()).pack(side="right", padx=2)
        ctk.CTkButton(zoom_bar, text="맞춤", width=50, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, font=FONT_SMALL_BOLD, command=lambda: self.canvas.fit_to_screen()).pack(side="right", padx=2)
        ctk.CTkButton(zoom_bar, text="-", width=40, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, font=FONT_SMALL_BOLD, command=lambda: self.canvas.zoom_out()).pack(side="right", padx=2)
        ctk.CTkButton(zoom_bar, text="+", width=40, height=28, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_MAIN, font=FONT_SMALL_BOLD, command=lambda: self.canvas.zoom_in()).pack(side="right", padx=2)

        bg_col = BG_INNER[1] if self.app.settings.get("theme") == "dark" else BG_INNER[0]
        self.canvas = InteractiveImageCanvas(body, bg_color=bg_col, draw_mode=True)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.on_draw_cb = self.on_canvas_draw 

        # [수정] 위젯 렌더링 후 맞춤 동기화
        self.after(100, lambda: self.canvas.fit_to_screen())

        bot_bar = ctk.CTkFrame(self, fg_color="transparent")
        bot_bar.pack(fill="x", padx=22, pady=18)
        
        self.btn_run = ctk.CTkButton(bot_bar, text="칠한 영역 지우기 시작", height=46, corner_radius=10, font=FONT_CARD_TITLE, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.run_eraser)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 6))
        
        self.btn_save = ctk.CTkButton(bot_bar, text="결과물 저장하기", width=160, height=46, corner_radius=10, font=FONT_CARD_TITLE, fg_color="#262936", hover_color="#323646", command=self.save_result)
        self.btn_save.pack(side="right", padx=(6, 0))
        self.btn_save.configure(state="disabled")

    def on_tool_change(self, tool_name):
        is_pan = (tool_name == "화면 이동")
        self.canvas.set_pan_mode(is_pan)
        if is_pan:
            self.btn_tool_pan.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
            self.btn_tool_brush.configure(fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER)
        else:
            self.btn_tool_brush.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
            self.btn_tool_pan.configure(fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER)

    def on_view_change(self, mode):
        self.canvas.set_view_mode(mode)
        if mode == "toggle_res":
            self.btn_view_res.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
            self.btn_view_orig.configure(fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER)
        else:
            self.btn_view_orig.configure(fg_color=ACCENT, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
            self.btn_view_res.configure(fg_color="transparent", text_color=TEXT_MAIN, hover_color=BG_INNER)

    def on_canvas_draw(self, x1, y1, x2, y2, brush_size):
        if self.mask_draw:
            self.mask_draw.line([x1, y1, x2, y2], fill=255, width=int(self.brush_size_var.get()))

    def reset_mask(self):
        if not self.original_image: return
        self.canvas.delete("paint")
        w, h = self.original_image.size
        self.mask_image = Image.new("L", (w, h), 0)
        self.mask_draw = ImageDraw.Draw(self.mask_image)
        self.btn_save.configure(state="disabled")
        
        self.btn_view_res.configure(state="disabled", fg_color="transparent", text_color=TEXT_MAIN)
        self.btn_view_orig.configure(state="disabled", fg_color=ACCENT, text_color="#FFFFFF")
        
        self.canvas.set_image(self.original_image)

    def run_eraser(self):
        if self.is_processing or not self.current_image_path: return
        if not self.mask_image.getbbox():
            messagebox.showwarning("안내", "지울 영역을 먼저 마우스로 칠해주세요.", parent=self)
            return

        self.is_processing = True
        self.btn_run.configure(state="disabled", text="복원 연산 중...")
        self.floating_prog.start([os.path.basename(self.current_image_path)])

        def worker():
            try:
                def step_cb(msg, ratio):
                    self.after(0, lambda: self.floating_prog.update_state(1, 1, ratio))

                res_pil = engine_eraser.process_eraser_to_memory(
                    image_path=self.current_image_path, mask_image=self.mask_image, progress_callback=step_cb
                )
                self.after(0, lambda: self.on_process_complete(res_pil))
            except Exception as e:
                self.after(0, lambda err=str(e): self.on_process_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def on_process_complete(self, result_pil):
        self.is_processing = False
        self.result_image = result_pil
        self.floating_prog.stop()
        self.btn_run.configure(state="normal", text="칠한 영역 지우기 시작")
        self.btn_save.configure(state="normal", fg_color=ACCENT, hover_color=ACCENT_HOVER)
        
        self.canvas.set_comparison(self.original_image, self.result_image, mode="toggle_res")
        
        self.btn_view_res.configure(state="normal")
        self.btn_view_orig.configure(state="normal")
        self.on_view_change("toggle_res")
        
        self.canvas.delete("paint")
        w, h = self.original_image.size
        self.mask_image = Image.new("L", (w, h), 0)
        self.mask_draw = ImageDraw.Draw(self.mask_image)

    def on_process_error(self, err_msg):
        self.is_processing = False
        self.floating_prog.stop()
        self.btn_run.configure(state="normal", text="칠한 영역 지우기 시작")
        messagebox.showerror("오류 발생", err_msg, parent=self)

    def save_result(self):
        if not self.result_image or self.is_processing: return
        if hasattr(self.app, 'sync_settings_from_ui'): self.app.sync_settings_from_ui()
            
        out_dir, saved_files = engine_eraser.save_erased_image(
            pil_image=self.result_image,
            original_path=self.current_image_path,
            custom_out_dir=self.app.settings.get("custom_out_dir", ""),
            filename_suffix=self.app.settings.get("filename_suffix", "_erased")
        )
        
        messagebox.showinfo("저장 완료", f"이미지가 복원되어 저장되었습니다!\n\n경로:\n{saved_files[0]}", parent=self)
        if self.app.settings.get("auto_open_folder", True) and out_dir: os.startfile(out_dir)

class TabEraser(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="매직 지우개", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="지우고 싶은 글씨나 로고 위를 마우스로 칠하면 주변 배경에 맞춰 자연스럽게 복원합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        card = ctk.CTkFrame(self, height=180, corner_radius=12, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(20, 16))
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="넓은 화면에서 이미지를 정밀하게 복원해보세요", font=("맑은 고딕", 15, "bold"), text_color=TEXT_MAIN).pack(pady=(45, 10))
        
        ctk.CTkButton(
            card, text="매직 지우개 작업창 열기", height=42, width=240, corner_radius=8,
            font=FONT_DEFAULT_BOLD, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.open_workspace
        ).pack()

    def open_workspace(self):
        file_path = filedialog.askopenfilename(title="지우개를 사용할 이미지 선택", filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp")])
        if file_path:
            EraserWorkspaceWindow(self, file_path)