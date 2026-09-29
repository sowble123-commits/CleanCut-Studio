import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from config import *

class ToolTip:
    def __init__(self, widget, text, delay=1000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.after_id = None

        if hasattr(self.widget, "_buttons_dict"):
            targets = list(self.widget._buttons_dict.values())
        else:
            targets = [self.widget]

        for t in targets:
            try:
                t.bind("<Enter>", self.schedule_show, add="+")
                t.bind("<Leave>", self.hide_tip, add="+")
                t.bind("<ButtonPress>", self.hide_tip, add="+")
            except NotImplementedError:
                pass

    def schedule_show(self, event=None):
        self.cancel_schedule()
        self.after_id = self.widget.after(self.delay, self.show_tip)

    def cancel_schedule(self):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show_tip(self):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        frame = tk.Frame(tw, background="#1E2230", highlightbackground=ACCENT, highlightthickness=1, bd=0)
        frame.pack()
        lbl = tk.Label(
            frame, text=self.text, justify="left", background="#1E2230",
            foreground="#F3F4F6", font=("맑은 고딕", 10), padx=10, pady=6
        )
        lbl.pack()

    def hide_tip(self, event=None):
        self.cancel_schedule()
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class FloatingProgressWidget:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.is_active = False
        self.is_hovered = False
        self.hide_job = None
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self.summary_text = "변환 준비 중..."
        self.pct = 0
        self.queue_items = []
        self.row_widgets = []

        self.capsule = ctk.CTkFrame(
            self.parent, width=265, height=56, corner_radius=12,
            fg_color=("#1E293B", "#1A1D29"), border_width=1, border_color=ACCENT
        )
        self.capsule.pack_propagate(False)

        top_row = ctk.CTkFrame(self.capsule, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(10, 4))
        self.lbl_summary = ctk.CTkLabel(top_row, text="⠋ 변환 중...", font=FONT_DEFAULT_BOLD, text_color="#F3F4F6")
        self.lbl_summary.pack(side="left")
        self.lbl_pct = ctk.CTkLabel(top_row, text="0%", font=FONT_DEFAULT_BOLD, text_color=ACCENT)
        self.lbl_pct.pack(side="right")

        self.pbar = ctk.CTkProgressBar(self.capsule, height=6, corner_radius=3, fg_color="#0F1117", progress_color=ACCENT)
        self.pbar.set(0)
        self.pbar.pack(fill="x", padx=14, pady=(0, 10))

        self.popup = ctk.CTkFrame(
            self.parent, width=265, corner_radius=12,
            fg_color=("#1E293B", "#141722"), border_width=1, border_color="#32384D"
        )
        ctk.CTkLabel(
            self.popup, text="작업 대기열 현황", font=FONT_SMALL_BOLD, text_color="#8A8F98"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.list_frame = ctk.CTkFrame(self.popup, fg_color="transparent")
        self.list_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.more_label = None

        for w in [self.capsule, top_row, self.lbl_summary, self.lbl_pct, self.pbar, self.popup, self.list_frame]:
            w.bind("<Enter>", self.on_enter, add="+")
            w.bind("<Leave>", self.on_leave, add="+")

    def _is_pointer_inside(self, widget):
        try:
            if not widget.winfo_ismapped():
                return False
            px, py = widget.winfo_pointerxy()
            wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
            ww, wh = widget.winfo_width(), widget.winfo_height()
            return (wx <= px <= wx + ww) and (wy <= py <= wy + wh)
        except Exception:
            return False

    def on_enter(self, event=None):
        if not self.is_active: return
        if self.hide_job:
            self.parent.after_cancel(self.hide_job)
            self.hide_job = None
        if not self.is_hovered:
            self.is_hovered = True
            self.update_popup_labels()
            self.popup.place(relx=1.0, rely=1.0, x=-20, y=-82, anchor="se")
            self.popup.lift()

    def on_leave(self, event=None):
        if self.hide_job:
            self.parent.after_cancel(self.hide_job)
        self.hide_job = self.parent.after(80, self._check_mouse_really_left)

    def _check_mouse_really_left(self):
        self.hide_job = None
        if self._is_pointer_inside(self.capsule) or self._is_pointer_inside(self.popup):
            return
        self.is_hovered = False
        self.popup.place_forget()

    def _build_popup_rows_once(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.row_widgets.clear()

        for item in self.queue_items[:8]:
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            lbl_left = ctk.CTkLabel(row, text="", font=FONT_SMALL, text_color="#8A8F98")
            lbl_left.pack(side="left")
            lbl_right = ctk.CTkLabel(row, text="", font=FONT_SMALL_BOLD, text_color="#8A8F98")
            lbl_right.pack(side="right")

            for w in (row, lbl_left, lbl_right):
                w.bind("<Enter>", self.on_enter, add="+")
                w.bind("<Leave>", self.on_leave, add="+")

            self.row_widgets.append((lbl_left, lbl_right))

        if len(self.queue_items) > 8:
            self.more_label = ctk.CTkLabel(
                self.list_frame, text=f"...외 {len(self.queue_items) - 8}개 파일",
                font=("맑은 고딕", 10), text_color="#8A8F98"
            )
            self.more_label.pack(anchor="e", pady=(2, 0))

    def update_popup_labels(self):
        sp = self.spinner_frames[self.spinner_idx % len(self.spinner_frames)]
        for idx, (lbl_left, lbl_right) in enumerate(self.row_widgets):
            if idx >= len(self.queue_items): break
            item = self.queue_items[idx]
            name_short = item["name"] if len(item["name"]) <= 18 else item["name"][:15] + "..."
            if item["status"] == "done":
                icon, col, right_txt = "✔", SUCCESS_COLOR, "완료"
            elif item["status"] == "proc":
                icon, col, right_txt = sp, "#F3F4F6", f"{item['pct']}%"
            else:
                icon, col, right_txt = "⏳", "#8A8F98", "대기 중"

            lbl_left.configure(text=f"{icon}  {name_short}", text_color=col)
            lbl_right.configure(text=right_txt, text_color=col)

    def start(self, file_names):
        self.queue_items = [{"name": fn, "status": "wait", "pct": 0} for fn in file_names]
        self._build_popup_rows_once()
        self.is_active = True
        self.pct = 2
        self.pbar.set(0.02)
        self.capsule.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        self.capsule.lift()
        self.animate()

    def update_state(self, current_idx, total, step_ratio):
        for i, item in enumerate(self.queue_items):
            if i < current_idx - 1:
                item["status"] = "done"
                item["pct"] = 100
            elif i == current_idx - 1:
                item["status"] = "proc"
                item["pct"] = int(step_ratio * 100)
            else:
                item["status"] = "wait"
                item["pct"] = 0

        overall = ((current_idx - 1) + step_ratio) / max(1, total)
        self.pct = int(overall * 100)
        self.summary_text = f"변환 진행 중 ({current_idx}/{total})"
        self.pbar.set(overall)
        if self.is_hovered:
            self.update_popup_labels()

    def animate(self):
        if not self.is_active: return
        sp = self.spinner_frames[self.spinner_idx % len(self.spinner_frames)]
        self.spinner_idx += 1
        self.lbl_summary.configure(text=f"{sp}  {self.summary_text}")
        self.lbl_pct.configure(text=f"{self.pct}%")
        if self.is_hovered:
            self.update_popup_labels()
        self.parent.after(100, self.animate)

    def stop(self):
        self.is_active = False
        self.is_hovered = False
        if self.hide_job:
            self.parent.after_cancel(self.hide_job)
            self.hide_job = None
        self.popup.place_forget()
        self.capsule.place_forget()


class InteractiveImageCanvas(tk.Canvas):
    def __init__(self, master, bg_color, draw_mode=False, **kwargs):
        super().__init__(master, bg=bg_color, highlightthickness=0, **kwargs)
        
        self.orig_img = None
        self.res_img = None
        self.tk_img = None
        
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.draw_mode = draw_mode
        self.pan_mode = False
        self.brush_size = 20
        self.brush_color = "#EF4444"
        self.on_draw_cb = None
        
        self.view_mode = "normal"
        self.split_ratio = 0.5
        self.is_sliding = False
        self.is_drawing = False
        self.is_space_pressed = False
        
        self.lines = []
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind("<ButtonPress-2>", self.start_pan_b2)
        self.bind("<B2-Motion>", self.do_pan_b2)
        self.bind("<Configure>", lambda e: self.redraw())

        self.bind("<ButtonPress-1>", self.on_b1_press)
        self.bind("<B1-Motion>", self.on_b1_motion)
        self.bind("<ButtonRelease-1>", self.on_b1_release)
        
        self.bind("<Motion>", self.on_mouse_motion)
        self.bind("<Leave>", self.on_mouse_leave)

        self.bind("<Enter>", lambda e: self.focus_set())
        self.bind("<KeyPress-space>", self.on_space_press)
        self.bind("<KeyRelease-space>", self.on_space_release)
        
        self.set_pan_mode(False)

    def clear_lines(self):
        self.lines.clear()
        self.delete("paint")

    def set_image(self, pil_img):
        self.orig_img = pil_img
        self.res_img = None
        self.view_mode = "normal"
        self.fit_to_screen()

    def set_comparison(self, orig_img, res_img, mode="split"):
        self.res_img = res_img
        if orig_img.size != res_img.size:
            self.orig_img = orig_img.resize(res_img.size, Image.Resampling.NEAREST)
        else:
            self.orig_img = orig_img
        self.view_mode = mode
        self.redraw()

    def set_view_mode(self, mode):
        self.view_mode = mode
        self.redraw()

    def set_pan_mode(self, is_pan):
        self.pan_mode = is_pan
        if is_pan:
            self.config(cursor="fleur")
            self.hide_brush_cursor()
        else:
            self.config(cursor="none" if self.draw_mode else "arrow")
            if self.draw_mode:
                self.draw_brush_cursor(self.last_mouse_x, self.last_mouse_y)

    def draw_brush_cursor(self, x, y):
        self.delete("brush_cursor")
        if not self.draw_mode or self.pan_mode: return
        r = (self.brush_size * self.scale) / 2
        self.create_oval(x-r, y-r, x+r, y+r, outline="#EF4444", width=2, tags="brush_cursor")

    def hide_brush_cursor(self):
        self.delete("brush_cursor")

    def on_mouse_leave(self, event):
        self.hide_brush_cursor()
        self.is_sliding = False
        self.is_drawing = False
        self.last_draw_x, self.last_draw_y = None, None

    def on_mouse_motion(self, event):
        self.last_mouse_x, self.last_mouse_y = event.x, event.y
        if self.draw_mode and not self.pan_mode:
            self.draw_brush_cursor(event.x, event.y)

    def on_space_press(self, event):
        if not self.is_space_pressed:
            self.is_space_pressed = True
            self.set_pan_mode(True)

    def on_space_release(self, event):
        self.is_space_pressed = False
        self.set_pan_mode(False)

    def on_b1_press(self, event):
        if self.view_mode == "split" and self.res_img:
            cw = self.winfo_width()
            sx = cw * self.split_ratio
            if abs(event.x - sx) < 25:
                self.is_sliding = True
                return
        
        if self.pan_mode:
            self.start_pan_b2(event)
            return
            
        if self.draw_mode and self.orig_img and self.view_mode in ["normal", "toggle_orig"]:
            self.is_drawing = True
            self.last_draw_x, self.last_draw_y = self.get_img_coords(event.x, event.y)
            self.last_draw_cx, self.last_draw_cy = event.x, event.y

    def on_b1_motion(self, event):
        self.last_mouse_x, self.last_mouse_y = event.x, event.y
        if self.draw_mode and not self.pan_mode:
            self.draw_brush_cursor(event.x, event.y)

        if self.is_sliding:
            cw = self.winfo_width()
            if cw > 0:
                self.split_ratio = max(0.0, min(1.0, event.x / cw))
                self.redraw()
            return
            
        if self.pan_mode:
            self.do_pan_b2(event)
            return
            
        # 수정됨: 마우스 왼쪽 버튼을 누르지 않은 상태라면(is_drawing이 False) 절대 선이 그려지지 않도록 확실하게 차단
        if self.draw_mode and self.is_drawing:
            ix, iy = self.get_img_coords(event.x, event.y)
            r = (self.brush_size * self.scale) / 2
            
            self.create_line(self.last_draw_cx, self.last_draw_cy, event.x, event.y, 
                             width=r*2, fill=self.brush_color, capstyle=tk.ROUND, smooth=True, tags="paint")
            
            self.lines.append((self.last_draw_x, self.last_draw_y, ix, iy, self.brush_size, self.brush_color))
            
            if self.on_draw_cb:
                self.on_draw_cb(self.last_draw_x, self.last_draw_y, ix, iy, self.brush_size)
                
            self.last_draw_x, self.last_draw_y = ix, iy
            self.last_draw_cx, self.last_draw_cy = event.x, event.y

    def on_b1_release(self, event):
        # 수정됨: 마우스 버튼을 떼는 순간 드래그 상태를 확실하게 해제하여 선이 끌려다니는 버그 원천 차단
        self.is_sliding = False
        self.is_drawing = False
        self.last_draw_x, self.last_draw_y = None, None

    def start_pan_b2(self, event):
        self.pan_start_x, self.pan_start_y = event.x, event.y

    def do_pan_b2(self, event):
        self.offset_x += (event.x - self.pan_start_x)
        self.offset_y += (event.y - self.pan_start_y)
        self.pan_start_x, self.pan_start_y = event.x, event.y
        self.redraw()

    def fit_to_screen(self):
        if not self.orig_img: return
        self.update_idletasks()
        cw, ch = self.winfo_width(), self.winfo_height()
        if cw <= 1: cw, ch = 400, 400
        
        active_img = self.res_img if (self.view_mode == "toggle_res" and self.res_img) else self.orig_img
        iw, ih = active_img.size
        
        self.scale = min(cw / iw, ch / ih) * 0.95
        self.offset_x = (cw - (iw * self.scale)) / 2
        self.offset_y = (ch - (ih * self.scale)) / 2
        self.redraw()

    def zoom(self, factor, cx=None, cy=None):
        if not self.orig_img: return
        if cx is None: cx = self.winfo_width() / 2
        if cy is None: cy = self.winfo_height() / 2
        
        new_scale = self.scale * factor
        
        cw, ch = self.winfo_width(), self.winfo_height()
        iw, ih = self.orig_img.size
        min_scale = min(cw / max(1, iw), ch / max(1, ih)) * 0.1 
        new_scale = max(min_scale, min(new_scale, 30.0))
        
        self.offset_x = cx - (cx - self.offset_x) * (new_scale / self.scale)
        self.offset_y = cy - (cy - self.offset_y) * (new_scale / self.scale)
        self.scale = new_scale
        self.redraw()
        if self.draw_mode:
            self.draw_brush_cursor(self.last_mouse_x, self.last_mouse_y)

    def zoom_in(self): self.zoom(1.2)
    def zoom_out(self): self.zoom(0.8)
    
    def zoom_1to1(self):
        if not self.orig_img: return
        active_img = self.res_img if (self.view_mode == "toggle_res" and self.res_img) else self.orig_img
        self.scale = 1.0
        self.offset_x = (self.winfo_width() - active_img.size[0]) / 2
        self.offset_y = (self.winfo_height() - active_img.size[1]) / 2
        self.redraw()
        if self.draw_mode:
            self.draw_brush_cursor(self.last_mouse_x, self.last_mouse_y)

    def on_mousewheel(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom(factor, event.x, event.y)

    def get_img_coords(self, cx, cy):
        return (cx - self.offset_x) / self.scale, (cy - self.offset_y) / self.scale

    def redraw(self):
        self.delete("img", "slider", "paint")
        if not self.orig_img: return
        
        cw, ch = self.winfo_width(), self.winfo_height()
        if cw <= 1 or ch <= 1: return
        
        active_img = self.orig_img
        if self.view_mode == "toggle_res" and self.res_img:
            active_img = self.res_img
            
        iw, ih = active_img.size
        
        left = max(0, int(-self.offset_x / self.scale))
        top = max(0, int(-self.offset_y / self.scale))
        right = min(iw, int((cw - self.offset_x) / self.scale) + 1)
        bottom = min(ih, int((ch - self.offset_y) / self.scale) + 1)
        
        if right <= left or bottom <= top: return
            
        new_w = int((right - left) * self.scale)
        new_h = int((bottom - top) * self.scale)
        if new_w <= 0 or new_h <= 0: return
        
        resample = Image.Resampling.NEAREST if self.scale >= 1.0 else Image.Resampling.LANCZOS
        draw_x, draw_y = int(max(0, self.offset_x)), int(max(0, self.offset_y))
        
        if self.view_mode != "split" or not self.res_img:
            cropped = active_img.crop((left, top, right, bottom))
            resized = cropped.resize((new_w, new_h), resample)
            self.tk_img = ImageTk.PhotoImage(resized)
            self.create_image(draw_x, draw_y, anchor="nw", image=self.tk_img, tags="img")
            
        else:
            c_orig = self.orig_img.crop((left, top, right, bottom))
            c_res = self.res_img.crop((left, top, right, bottom))
            r_orig = c_orig.resize((new_w, new_h), resample)
            r_res = c_res.resize((new_w, new_h), resample)
            
            split_x_canvas = int(cw * self.split_ratio)
            split_x_img = int(split_x_canvas - draw_x)
            
            if split_x_img <= 0:
                final_img = r_res
            elif split_x_img >= new_w:
                final_img = r_orig
            else:
                final_img = Image.new("RGBA", (new_w, new_h))
                final_img.paste(r_orig.crop((0, 0, split_x_img, new_h)), (0, 0))
                final_img.paste(r_res.crop((split_x_img, 0, new_w, new_h)), (split_x_img, 0))
                
            self.tk_img = ImageTk.PhotoImage(final_img)
            self.create_image(draw_x, draw_y, anchor="nw", image=self.tk_img, tags="img")
            
            self.create_line(split_x_canvas, 0, split_x_canvas, ch, fill="#FFFFFF", width=2, tags="slider")
            self.create_line(split_x_canvas, 0, split_x_canvas, ch, fill="#000000", width=1, dash=(4, 4), tags="slider")
            
            hy = ch / 2
            self.create_oval(split_x_canvas-14, hy-14, split_x_canvas+14, hy+14, fill="#FFFFFF", outline=ACCENT, width=3, tags="slider")
            self.create_line(split_x_canvas-5, hy-6, split_x_canvas-5, hy+6, fill=ACCENT, width=2, tags="slider")
            self.create_line(split_x_canvas+5, hy-6, split_x_canvas+5, hy+6, fill=ACCENT, width=2, tags="slider")
            
        self.tag_lower("img")
        
        if self.draw_mode:
            for line in self.lines:
                x1 = line[0] * self.scale + self.offset_x
                y1 = line[1] * self.scale + self.offset_y
                x2 = line[2] * self.scale + self.offset_x
                y2 = line[3] * self.scale + self.offset_y
                r = (line[4] * self.scale) / 2
                self.create_line(x1, y1, x2, y2, width=r*2, fill=line[5], capstyle=tk.ROUND, smooth=True, tags="paint")
            
            self.tag_raise("brush_cursor")