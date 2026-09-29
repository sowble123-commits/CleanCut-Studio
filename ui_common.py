# ui_common.py
import tkinter as tk
import customtkinter as ctk
from config import *

# ==========================================
# 마우스 호버 시 1초 뒤 나타나는 툴팁(말풍선)
# ==========================================
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

# ==========================================
# 우측 하단 플로팅 진행률 바 + 호버 대기열 현황판
# ==========================================
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
        if not self.is_active:
            return
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
            if idx >= len(self.queue_items):
                break
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
        if not self.is_active:
            return
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