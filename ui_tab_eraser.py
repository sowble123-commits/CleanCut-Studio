import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import customtkinter as ctk

from config import *
import engine_eraser

class TabEraser(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # 상태 관리 변수
        self.current_image_path = None
        self.original_image = None
        self.display_image = None
        self.mask_image = None
        self.mask_draw = None
        self.is_processing = False
        
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="매직 지우개 (텍스트 / 마크 복원)", font=FONT_MAIN_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="지우고 싶은 글씨나 로고 위를 마우스로 칠하면 주변 배경에 맞춰 자연스럽게 복원합니다.", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(anchor="w", pady=(2, 0))

        ctrl_bar = ctk.CTkFrame(self, height=48, corner_radius=10, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        ctrl_bar.pack(fill="x", pady=(0, 12))

        # [기능 연결] 이미지 열기 버튼
        self.btn_open = ctk.CTkButton(ctrl_bar, text="이미지 열기", width=95, height=32, corner_radius=6, fg_color="#262936", hover_color="#323646", font=FONT_DEFAULT_BOLD, command=self.load_image)
        self.btn_open.pack(side="left", padx=12, pady=8)
        
        ctk.CTkLabel(ctrl_bar, text="브러시 두께", font=FONT_DEFAULT, text_color=TEXT_SUB).pack(side="left", padx=(12, 6))
        
        # [기능 연결] 슬라이더 변수 연동
        self.brush_size_var = tk.IntVar(value=20)
        self.slider_brush = ctk.CTkSlider(ctrl_bar, from_=5, to=60, width=150, button_color=ACCENT, progress_color=ACCENT, variable=self.brush_size_var)
        self.slider_brush.pack(side="left", padx=4)
        
        # [기능 연결] 초기화 버튼
        self.btn_reset = ctk.CTkButton(ctrl_bar, text="칠한 영역 초기화", width=110, height=32, corner_radius=6, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, hover_color="#262936", text_color=TEXT_MAIN, font=FONT_DEFAULT, command=self.reset_mask)
        self.btn_reset.pack(side="right", padx=12, pady=8)

        # [기능 연결] 캔버스 영역 구현
        self.canvas_card = ctk.CTkFrame(self, corner_radius=12, fg_color=BG_INNER, border_width=1, border_color=BORDER_COLOR)
        self.canvas_card.pack(fill="both", expand=True, pady=(0, 14))
        
        self.canvas = tk.Canvas(self.canvas_card, bg=BG_INNER[1] if self.app.settings.get("theme") == "dark" else BG_INNER[0], highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 마우스 드래그 이벤트 바인딩
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.reset_paint_coord)
        self.last_x, self.last_y = None, None

        bot_bar = ctk.CTkFrame(self, fg_color="transparent")
        bot_bar.pack(fill="x", side="bottom")
        
        # [기능 연결] 실행 및 저장 버튼
        self.btn_run = ctk.CTkButton(bot_bar, text="칠한 영역 흔적 없이 지우기", height=46, corner_radius=10, font=FONT_CARD_TITLE, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.run_eraser)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 6))
        
        self.btn_save = ctk.CTkButton(bot_bar, text="결과물 저장하기", width=160, height=46, corner_radius=10, font=FONT_CARD_TITLE, fg_color="#262936", hover_color="#323646", command=self.save_result)
        self.btn_save.pack(side="right", padx=(6, 0))
        self.btn_save.configure(state="disabled") # 초기엔 비활성화

    # --- 이미지 로드 및 캔버스 제어 ---
    def load_image(self):
        if self.is_processing: return
        file_path = filedialog.askopenfilename(title="지우개를 사용할 이미지 선택", filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp")])
        if not file_path: return
        
        self.current_image_path = file_path
        self.original_image = Image.open(file_path).convert("RGB")
        self.result_image = None
        self.btn_save.configure(state="disabled")
        
        self.draw_image_on_canvas()
        self.reset_mask()

    def draw_image_on_canvas(self):
        self.canvas.update()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1 or ch <= 1: 
            cw, ch = 800, 400 # 안전 보장값
            
        iw, ih = self.original_image.size
        scale = min(cw / iw, ch / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)
        
        # 표시용 이미지 리사이즈
        self.display_image = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        
        # 캔버스 중앙 정렬 계산
        self.img_x = (cw - new_w) // 2
        self.img_y = (ch - new_h) // 2
        
        self.canvas.delete("all")
        self.canvas.create_image(self.img_x, self.img_y, anchor="nw", image=self.tk_image)
        
        # 연산용 내부 마스크 이미지 생성 (표시용 이미지와 동일한 크기)
        self.mask_image = Image.new("L", (new_w, new_h), 0)
        self.mask_draw = ImageDraw.Draw(self.mask_image)

    def paint(self, event):
        if not self.display_image: return
        
        # 마우스 좌표가 이미지 영역 안인지 확인 후 보정
        x = event.x - self.img_x
        y = event.y - self.img_y
        w, h = self.display_image.size
        
        if 0 <= x <= w and 0 <= y <= h:
            r = self.brush_size_var.get() // 2
            # 캔버스에 붉은색 반투명(stipple 효과가 한계이나 윤곽선으로 시각화) 브러시 그리기
            if self.last_x and self.last_y:
                self.canvas.create_line(self.last_x + self.img_x, self.last_y + self.img_y, event.x, event.y, 
                                        width=r*2, fill="#EF4444", capstyle=tk.ROUND, smooth=True, tags="paint")
                self.mask_draw.line([self.last_x, self.last_y, x, y], fill=255, width=r*2)
            
            self.last_x, self.last_y = x, y

    def reset_paint_coord(self, event):
        self.last_x, self.last_y = None, None

    def reset_mask(self):
        if not self.display_image: return
        self.canvas.delete("paint")
        w, h = self.display_image.size
        self.mask_image = Image.new("L", (w, h), 0)
        self.mask_draw = ImageDraw.Draw(self.mask_image)
        self.btn_save.configure(state="disabled")

    # --- 엔진 연동 ---
    def run_eraser(self):
        if self.is_processing or not self.current_image_path:
            return
            
        # 마스크에 칠한 흔적이 있는지 확인 (모두 0인지)
        if not self.mask_image.getbbox():
            messagebox.showwarning("안내", "지울 영역을 먼저 마우스로 칠해주세요.", parent=self)
            return

        self.is_processing = True
        self.app.engine_dot.configure(text="● AI 엔진 연산 중...", text_color=WARN_COLOR)
        self.btn_run.configure(state="disabled", text="복원 연산 중...")
        
        # 마스크 이미지를 원본 해상도로 확대 (Inpainting 엔진에 전달하기 위함)
        original_mask = self.mask_image.resize(self.original_image.size, Image.Resampling.NEAREST)
        
        self.app.floating_prog.start([os.path.basename(self.current_image_path)])

        def worker():
            try:
                def step_cb(msg, ratio):
                    self.after(0, lambda: self.app.floating_prog.update_state(1, 1, ratio))

                # 새로 생성한 엔진 모듈 호출
                res_pil = engine_eraser.process_eraser_to_memory(
                    image_path=self.current_image_path,
                    mask_image=original_mask,
                    progress_callback=step_cb
                )
                self.after(0, lambda: self.on_process_complete(res_pil))
            except Exception as e:
                self.after(0, lambda err=str(e): self.on_process_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def on_process_complete(self, result_pil):
        self.is_processing = False
        self.result_image = result_pil
        self.app.floating_prog.stop()
        self.app.engine_dot.configure(text="● Modular Engine Ready", text_color=SUCCESS_COLOR)
        self.btn_run.configure(state="normal", text="칠한 영역 흔적 없이 지우기")
        self.btn_save.configure(state="normal", fg_color=ACCENT, hover_color=ACCENT_HOVER)
        
        # 캔버스에 결과 이미지 업데이트
        cw, ch = self.display_image.size
        self.display_image = self.result_image.resize((cw, ch), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.delete("all")
        self.canvas.create_image(self.img_x, self.img_y, anchor="nw", image=self.tk_image)
        
        # 마스크 초기화 (새로 그릴 수 있게)
        self.mask_image = Image.new("L", (cw, ch), 0)
        self.mask_draw = ImageDraw.Draw(self.mask_image)

    def on_process_error(self, err_msg):
        self.is_processing = False
        self.app.floating_prog.stop()
        self.app.engine_dot.configure(text="● Engine Error", text_color=ERROR_COLOR)
        self.btn_run.configure(state="normal", text="칠한 영역 흔적 없이 지우기")
        messagebox.showerror("오류 발생", err_msg)

    def save_result(self):
        if not self.result_image or self.is_processing: return
        
        if hasattr(self.app, 'sync_settings_from_ui'):
            self.app.sync_settings_from_ui()
            
        out_dir, saved_files = engine_eraser.save_erased_image(
            pil_image=self.result_image,
            original_path=self.current_image_path,
            custom_out_dir=self.app.settings.get("custom_out_dir", ""),
            filename_suffix=self.app.settings.get("filename_suffix", "_erased")
        )
        
        messagebox.showinfo("저장 완료", f"이미지가 복원되어 저장되었습니다!\n\n경로:\n{saved_files[0]}")
        if self.app.settings.get("auto_open_folder", True) and out_dir:
            os.startfile(out_dir)