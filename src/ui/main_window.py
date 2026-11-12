"""Pixelroom-inspired Tkinter interface for the OpenCV image editor.

This module keeps OpenCV logic in ``core`` and renders the dark desktop
workspace from the supplied visual reference: brand bar, project breadcrumb,
tool rail, comparison canvas, contextual inspector and status footer.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np

from core.image_loader import load_image, save_image
from core.processor import ImageProcessor
from utils.helpers import fit_image


class ImageEditorApp(tk.Tk):
    """OpenCV editor using a Pixelroom-like dark desktop UI."""

    APP_BG = "#0d1011"
    TOP_BG = "#181d20"
    PANEL_BG = "#13181a"
    PANEL_ALT = "#191f22"
    PANEL_HOVER = "#242c2f"
    BORDER = "#293135"
    BORDER_SOFT = "#20282b"
    TEXT = "#f1f4f2"
    MUTED = "#8e989e"
    DIM = "#687278"
    ACCENT = "#c4f36a"
    ACCENT_DARK = "#17200d"
    CANVAS_BG = "#0b0f10"

    def __init__(self) -> None:
        super().__init__()
        self.title("pixelroom - Trình chỉnh ảnh")
        self.geometry("1440x900+80+40")
        self.minsize(1100, 700)
        self.configure(bg=self.APP_BG)
        self.overrideredirect(True)

        # Image/session state.
        self.original: np.ndarray | None = None
        self.current: np.ndarray | None = None
        self.file_path: str | None = None
        self.history: list[str] = []
        self.inspector_tool = "welcome"
        self.active_tool: str | None = None
        self.compare_mode = True
        self.preview_scale = 1.0
        self.preview_origin = (0, 0)
        self.crop_start: tuple[int, int] | None = None
        self.crop_selection: tuple[int, int, int, int] | None = None
        self.resize_dragging = False
        self.resize_target: tuple[int, int] | None = None
        self._refresh_job: str | None = None
        self._resize_input_updating = False
        self._drag_offset: tuple[int, int] | None = None
        self._maximized = False
        self._normal_geometry = ""

        # Tk state exposed by the UI.
        self.file_name_var = tk.StringVar(value="Chưa có ảnh")
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.tip_var = tk.StringVar(value="Mở một ảnh để bắt đầu chỉnh sửa.")
        self.meta_var = tk.StringVar(value="—")
        self.low_var = tk.IntVar(value=80)
        self.high_var = tk.IntVar(value=160)
        self.gamma_var = tk.DoubleVar(value=0.70)
        self.gamma_text_var = tk.StringVar(value="0.70")
        self.log_coefficient_var = tk.DoubleVar(value=45.99)
        self.log_coefficient_text_var = tk.StringVar(value="45.99")
        self.crop_x_var = tk.StringVar(value="0")
        self.crop_y_var = tk.StringVar(value="0")
        self.crop_width_var = tk.StringVar(value="0")
        self.crop_height_var = tk.StringVar(value="0")
        self.resize_width_var = tk.StringVar(value="0")
        self.resize_height_var = tk.StringVar(value="0")
        self.keep_ratio_var = tk.BooleanVar(value=True)
        self.gamma_var.trace_add("write", self._update_gamma_text)
        self.log_coefficient_var.trace_add("write", self._update_log_coefficient_text)

        self._build_ui()
        self.bind("<Alt-F4>", lambda _event: self.destroy())
        self.bind("<Escape>", self._cancel_direct_tool)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        """Construct the top bars, three-column workspace and footer."""
        self._build_top_bar()
        self._build_project_bar()
        main = tk.Frame(self, bg=self.APP_BG)
        main.pack(fill="both", expand=True)

        self.left_panel = tk.Frame(main, bg=self.PANEL_BG, width=264,
                                   highlightbackground=self.BORDER_SOFT, highlightthickness=1)
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)
        self.workspace = tk.Frame(main, bg=self.APP_BG)
        self.workspace.pack(side="left", fill="both", expand=True)
        self.right_panel = tk.Frame(main, bg=self.PANEL_BG, width=288,
                                    highlightbackground=self.BORDER_SOFT, highlightthickness=1)
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False)

        self._build_tool_rail()
        self._build_workspace()
        self.inspector = tk.Frame(self.right_panel, bg=self.PANEL_BG)
        self.inspector.pack(fill="both", expand=True, padx=20, pady=20)
        self._show_inspector("welcome")
        self._build_status_bar()

    def _build_top_bar(self) -> None:
        """Build the 64px brand/navigation bar visible in the reference."""
        bar = tk.Frame(self, bg=self.TOP_BG, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        bar.bind("<ButtonPress-1>", self._start_window_drag)
        bar.bind("<B1-Motion>", self._drag_window)
        bar.bind("<Double-Button-1>", lambda _event: self._toggle_maximize())

        mark = tk.Canvas(bar, width=36, height=36, bg=self.TOP_BG, highlightthickness=0)
        mark.place(x=28, y=14)
        self._round_rect(mark, 1, 1, 35, 35, 8, fill=self.ACCENT, outline=self.ACCENT)
        mark.create_text(18, 19, text="p", fill=self.ACCENT_DARK, font=("Segoe UI", 24, "bold"))
        tk.Label(bar, text="pixelroom", bg=self.TOP_BG, fg=self.TEXT,
                 font=("Segoe UI Semibold", 21)).place(x=79, y=17)
        tk.Label(bar, text="TRÌNH CHỈNH ẢNH", bg=self.TOP_BG, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).place(x=278, y=27)

        self._nav_label(bar, "Tệp", 526, self._show_file_menu)
        self._nav_label(bar, "Chỉnh sửa", 591, lambda _event: self._show_inspector("gamma"))
        self._nav_label(bar, "Hiển thị", 711, lambda _event: self._toggle_compare())
        self._nav_label(bar, "Trợ giúp", 825, lambda _event: self._show_help())

        controls = tk.Frame(bar, bg=self.TOP_BG)
        controls.place(relx=1.0, x=-112, y=0, width=112, height=64)
        self._title_button(controls, "−", self.iconify).pack(side="left", fill="y", expand=True)
        self._title_button(controls, "□", self._toggle_maximize).pack(side="left", fill="y", expand=True)
        self._title_button(controls, "×", self.destroy, close=True).pack(side="left", fill="y", expand=True)

    def _build_project_bar(self) -> None:
        """Create the project breadcrumb/status band below global navigation."""
        bar = tk.Frame(self, bg=self.APP_BG, height=104,
                       highlightbackground=self.BORDER_SOFT, highlightthickness=1)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="Dự án của tôi  /", bg=self.APP_BG, fg=self.MUTED,
                 font=("Segoe UI", 11)).place(x=29, y=35)
        tk.Label(bar, textvariable=self.file_name_var, bg=self.APP_BG, fg=self.TEXT,
                 font=("Segoe UI Semibold", 11)).place(x=169, y=35)
        tk.Label(bar, text="●", bg=self.APP_BG, fg=self.ACCENT,
                 font=("Segoe UI", 10)).place(x=341, y=35)
        tk.Label(bar, text="Đã chỉnh sửa", bg=self.APP_BG, fg=self.MUTED,
                 font=("Segoe UI", 10)).place(x=360, y=36)

    def _build_tool_rail(self) -> None:
        """Build the always-accessible image tools and compact history card."""
        actions = tk.Frame(self.left_panel, bg=self.PANEL_BG)
        actions.pack(fill="x", padx=16, pady=(18, 14))
        self._button(actions, "Mở ảnh", self.open_image, "accent").pack(fill="x", pady=(0, 8))
        action_row = tk.Frame(actions, bg=self.PANEL_BG)
        action_row.pack(fill="x")
        self._button(action_row, "Đặt lại", self.reset, "subtle").pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._button(action_row, "Lưu ảnh ↗", self.save_image, "subtle").pack(side="left", fill="x", expand=True, padx=(4, 0))

        self._section_label(self.left_panel, "CÔNG CỤ CHỈNH ẢNH").pack(fill="x", padx=20, pady=(6, 8))
        self.tool_list = tk.Frame(self.left_panel, bg=self.PANEL_BG)
        self.tool_list.pack(fill="x", padx=10)
        self.tool_buttons: dict[str, tk.Button] = {}
        specs = [
            ("gray", "◐", "Ảnh xám", self.grayscale),
            ("canny", "⌁", "Phát hiện biên", lambda: self._show_inspector("canny")),
            ("crop", "⌗", "Cắt ảnh", lambda: self._show_inspector("crop")),
            ("resize", "↔", "Đổi kích thước", lambda: self._show_inspector("resize")),
            ("negative", "◑", "Ảnh âm bản", self.negative),
            ("log", "ln", "Biến đổi Logarit", lambda: self._show_inspector("log")),
            ("gamma", "γ", "Hiệu chỉnh Gamma", lambda: self._show_inspector("gamma")),
        ]
        for key, icon, title, command in specs:
            button = self._tool_button(self.tool_list, icon, title, command)
            button.pack(fill="x", pady=2)
            self.tool_buttons[key] = button

        card = tk.Frame(self.left_panel, bg=self.PANEL_BG, highlightbackground=self.BORDER_SOFT, highlightthickness=1)
        card.pack(side="bottom", fill="x", padx=16, pady=16)
        self._section_label(card, "LỊCH SỬ CHỈNH SỬA").pack(anchor="w", padx=10, pady=(12, 5))
        self.history_list = tk.Frame(card, bg=self.PANEL_BG)
        self.history_list.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(card, text="Mọi thay đổi đều có thể đặt lại.\nẢnh gốc luôn được giữ nguyên.",
                 justify="left", bg=self.PANEL_BG, fg=self.DIM, font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 12))
        self._refresh_history()

    def _build_workspace(self) -> None:
        """Build comparison controls plus original/current image cards."""
        toolbar = tk.Frame(self.workspace, bg=self.APP_BG, height=60)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        self.compare_button = self._button(toolbar, "So sánh song song", self._toggle_compare, "subtle")
        self.compare_button.place(x=24, y=16, width=142, height=30)
        tk.Label(toolbar, text="−     50%     +", bg=self.APP_BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).place(relx=1.0, x=-220, y=24)
        self._button(toolbar, "Vừa khung", self.refresh_views, "subtle").place(relx=1.0, x=-104, y=16, width=80, height=30)

        self.comparison_host = tk.Frame(self.workspace, bg=self.APP_BG)
        self.comparison_host.pack(fill="both", expand=True, padx=22, pady=(0, 20))
        self.original_holder, self.original_canvas, self.original_caption = self._image_pane(self.comparison_host, "ẢNH GỐC")
        self.preview_holder, self.preview_canvas, self.preview_caption = self._image_pane(self.comparison_host, "KẾT QUẢ")
        self.preview_canvas.bind("<ButtonPress-1>", self._interaction_begin)
        self.preview_canvas.bind("<B1-Motion>", self._interaction_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._interaction_end)
        self.comparison_host.bind("<Configure>", self._queue_refresh)
        self._arrange_panes()

    def _build_status_bar(self) -> None:
        """Create the restrained bottom operational footer from the PDF."""
        footer = tk.Frame(self, bg=self.TOP_BG, height=36,
                          highlightbackground=self.BORDER_SOFT, highlightthickness=1)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(footer, textvariable=self.status_var, bg=self.TOP_BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).place(x=18, y=9)
        tk.Label(footer, textvariable=self.meta_var, bg=self.TOP_BG, fg=self.DIM,
                 font=("Segoe UI", 9)).place(x=156, y=9)
        tk.Label(footer, textvariable=self.tip_var, bg=self.TOP_BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).place(relx=0.5, y=9, anchor="n")
        tk.Label(footer, text="OpenCV  /  Desktop editor", bg=self.TOP_BG, fg=self.DIM,
                 font=("Segoe UI", 8)).place(relx=1.0, x=-18, y=10, anchor="ne")

    # ----------------------------------------------------------- components
    def _round_rect(self, canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: object) -> None:
        """Draw a simple smoothed rounded rectangle without image assets."""
        points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
                  x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
                  x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
        canvas.create_polygon(points, smooth=True, **kwargs)

    def _nav_label(self, parent: tk.Widget, text: str, x: int, command: object) -> None:
        """Create header navigation with quiet hover feedback."""
        label = tk.Label(parent, text=text, bg=self.TOP_BG, fg=self.MUTED,
                         cursor="hand2", font=("Segoe UI", 11))
        label.place(x=x, y=23)
        label.bind("<Enter>", lambda _event: label.configure(fg=self.TEXT))
        label.bind("<Leave>", lambda _event: label.configure(fg=self.MUTED))
        label.bind("<Button-1>", command)  # type: ignore[arg-type]

    def _title_button(self, parent: tk.Widget, text: str, command: object, close: bool = False) -> tk.Button:
        """Return one frameless minimize/maximize/close control."""
        return tk.Button(parent, text=text, command=command, bd=0, relief="flat",
                         bg=self.TOP_BG, fg=self.MUTED, activeforeground=self.TEXT,
                         activebackground="#9e2f2f" if close else self.PANEL_HOVER,
                         font=("Segoe UI", 15), cursor="hand2")

    def _button(self, parent: tk.Widget, text: str, command: object, variant: str = "primary") -> tk.Button:
        """Create reusable dark, subtle, or lime-accent action buttons."""
        if variant == "accent":
            bg, fg, active_bg, active_fg = self.ACCENT, self.ACCENT_DARK, "#d5fb8b", self.ACCENT_DARK
        elif variant == "subtle":
            bg, fg, active_bg, active_fg = self.PANEL_ALT, self.MUTED, self.PANEL_HOVER, self.TEXT
        else:
            bg, fg, active_bg, active_fg = self.PANEL_ALT, self.TEXT, self.PANEL_HOVER, self.TEXT
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=active_bg, activeforeground=active_fg,
                         bd=0, relief="flat", highlightthickness=0, cursor="hand2",
                         font=("Segoe UI Semibold", 9), padx=10, pady=6)

    def _tool_button(self, parent: tk.Widget, icon: str, text: str, command: object) -> tk.Button:
        """Build a reference-style tool rail row with a compact glyph."""
        button = tk.Button(parent, text=f" {icon:<3}  {text}", command=command, anchor="w",
                           bg=self.PANEL_BG, fg=self.MUTED, activebackground=self.PANEL_HOVER,
                           activeforeground=self.TEXT, bd=0, relief="flat", highlightthickness=0,
                           cursor="hand2", font=("Segoe UI", 10), padx=9, pady=8)
        button.bind("<Enter>", lambda _event: button.configure(bg=self.PANEL_HOVER, fg=self.TEXT))
        button.bind("<Leave>", lambda _event: self._refresh_tool_buttons())
        return button

    def _section_label(self, parent: tk.Widget, text: str) -> tk.Label:
        """Return the small uppercase section label used throughout the UI."""
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=self.DIM,
                        anchor="w", font=("Segoe UI", 8, "bold"))

    def _image_pane(self, parent: tk.Widget, title: str) -> tuple[tk.Frame, tk.Canvas, tk.Label]:
        """Create one labelled image viewport for original or edited content."""
        holder = tk.Frame(parent, bg=self.APP_BG)
        head = tk.Frame(holder, bg=self.APP_BG, height=30)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text=title, bg=self.APP_BG, fg=self.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(side="left", pady=(7, 0))
        caption = tk.Label(head, text="", bg=self.APP_BG, fg=self.DIM, font=("Segoe UI", 8))
        caption.pack(side="right", pady=(7, 0))
        canvas = tk.Canvas(holder, bg=self.CANVAS_BG, bd=0,
                           highlightbackground=self.BORDER_SOFT, highlightthickness=1,
                           cursor="crosshair")
        canvas.pack(fill="both", expand=True)
        return holder, canvas, caption

    # ---------------------------------------------------------- window/nav
    def _start_window_drag(self, event: tk.Event) -> None:
        """Begin moving the frameless window from unused titlebar space."""
        if not self._maximized:
            self._drag_offset = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _drag_window(self, event: tk.Event) -> None:
        """Move the custom titlebar window while pointer is dragged."""
        if self._drag_offset is None or self._maximized:
            return
        self.geometry(f"+{event.x_root - self._drag_offset[0]}+{event.y_root - self._drag_offset[1]}")

    def _toggle_maximize(self) -> None:
        """Toggle native maximize while retaining custom Pixelroom chrome."""
        if self._maximized:
            self.state("normal")
            if self._normal_geometry:
                self.geometry(self._normal_geometry)
        else:
            self._normal_geometry = self.geometry()
            self.state("zoomed")
        self._maximized = not self._maximized

    def _show_file_menu(self, event: tk.Event) -> None:
        """Show a styled File menu at the header navigation point."""
        menu = tk.Menu(self, tearoff=0, bg=self.PANEL_ALT, fg=self.TEXT,
                       activebackground=self.PANEL_HOVER, activeforeground=self.TEXT,
                       bd=0, font=("Segoe UI", 10))
        menu.add_command(label="Mở ảnh", command=self.open_image)
        menu.add_command(label="Lưu ảnh", command=self.save_image)
        menu.add_separator()
        menu.add_command(label="Đặt lại ảnh gốc", command=self.reset)
        menu.tk_popup(event.x_root, event.y_root + 22)

    def _show_help(self) -> None:
        """Explain the editor's layout in a compact help dialog."""
        messagebox.showinfo("pixelroom", "Mở ảnh, chọn công cụ bên trái và áp dụng thiết lập trong bảng bên phải.\n\nẢnh gốc luôn được giữ nguyên.")

    def _toggle_compare(self) -> None:
        """Switch between side-by-side and result-only workspace modes."""
        self.compare_mode = not self.compare_mode
        self.compare_button.configure(text="So sánh song song" if self.compare_mode else "Chỉ xem kết quả")
        self._arrange_panes()
        self.refresh_views()

    def _arrange_panes(self) -> None:
        """Pack original and result cards in the requested comparison layout."""
        self.original_holder.pack_forget()
        self.preview_holder.pack_forget()
        if self.compare_mode:
            self.original_holder.pack(side="left", fill="both", expand=True, padx=(0, 7))
            self.preview_holder.pack(side="left", fill="both", expand=True, padx=(7, 0))
        else:
            self.preview_holder.pack(fill="both", expand=True)

    # -------------------------------------------------------- inspector UI
    def _show_inspector(self, tool: str) -> None:
        """Replace the contextual right panel without hiding any legacy tool."""
        if tool != "welcome" and not self._require_image(silent=True):
            self.open_image()
            return
        self._cancel_direct_tool(redraw=False, keep_selection=True)
        self.inspector_tool = tool
        for child in self.inspector.winfo_children():
            child.destroy()
        if tool == "welcome":
            self._build_welcome_inspector()
        elif tool == "gamma":
            self._build_gamma_inspector()
        elif tool == "log":
            self._build_logarithmic_inspector()
        elif tool == "canny":
            self._build_canny_inspector()
        elif tool == "crop":
            self._build_crop_inspector()
        elif tool == "resize":
            self._build_resize_inspector()
        else:
            self._build_info_inspector(tool)
        self._refresh_tool_buttons()
        self.refresh_views()

    def _inspector_heading(self, eyebrow: str, title: str, description: str) -> None:
        """Place the reference's eyebrow/title/description hierarchy."""
        self._section_label(self.inspector, eyebrow).pack(anchor="w")
        tk.Label(self.inspector, text=title, bg=self.PANEL_BG, fg=self.TEXT,
                 font=("Segoe UI Semibold", 16), anchor="w").pack(anchor="w", pady=(6, 5))
        tk.Label(self.inspector, text=description, bg=self.PANEL_BG, fg=self.MUTED,
                 justify="left", wraplength=242, font=("Segoe UI", 9), anchor="w").pack(anchor="w", pady=(0, 18))

    def _build_welcome_inspector(self) -> None:
        """Show the empty state used in the visual reference."""
        tk.Frame(self.inspector, bg=self.PANEL_BG, height=80).pack(fill="x")
        tk.Label(self.inspector, text="Từng chi tiết,\nđúng ý bạn.", bg=self.PANEL_BG,
                 fg=self.TEXT, justify="left", font=("Segoe UI Semibold", 19)).pack(anchor="w")
        tk.Label(self.inspector, text="Giữ ảnh gốc bên cạnh.\nNhìn rõ mọi thay đổi.", bg=self.PANEL_BG,
                 fg=self.MUTED, justify="left", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 24))
        self._button(self.inspector, "Mở ảnh", self.open_image, "accent").pack(fill="x")

    def _build_info_inspector(self, title: str) -> None:
        """Show a simple completion panel after a one-click action."""
        self._inspector_heading("CÔNG CỤ CHỈNH ẢNH", title, "Thao tác đã được áp dụng lên bản xem trước.")
        self._button(self.inspector, "Đặt lại ảnh gốc", self.reset, "subtle").pack(fill="x")

    def _build_gamma_inspector(self) -> None:
        """Build the light-and-tone Gamma control panel."""
        self._inspector_heading("ÁNH SÁNG & SẮC ĐỘ", "Hiệu chỉnh Gamma", "Cân chỉnh sáng tối, giữ lại chi tiết.")
        self._field_caption("Giá trị Gamma", self.gamma_text_var)
        self._scale(self.inspector, self.gamma_var, 0.10, 2.00, self._update_gamma_text).pack(fill="x", pady=(2, 0))
        ends = tk.Frame(self.inspector, bg=self.PANEL_BG)
        ends.pack(fill="x", pady=(0, 13))
        tk.Label(ends, text="0.10", bg=self.PANEL_BG, fg=self.DIM, font=("Segoe UI", 8)).pack(side="left")
        tk.Label(ends, text="2.00", bg=self.PANEL_BG, fg=self.DIM, font=("Segoe UI", 8)).pack(side="right")
        presets = tk.Frame(self.inspector, bg=self.PANEL_BG)
        presets.pack(fill="x", pady=(0, 18))
        for value in (0.50, 0.70, 1.00, 1.50):
            self._button(presets, f"{value:.2f}", lambda v=value: self.gamma_var.set(v), "subtle").pack(side="left", expand=True, fill="x", padx=2)
        self._callout("Điều chỉnh sắc độ", "Gamma < 1 làm tối ảnh; Gamma > 1 làm sáng ảnh.")
        self._button(self.inspector, "Áp dụng Gamma", self.gamma, "accent").pack(fill="x", pady=(20, 7))
        self._button(self.inspector, "Khôi phục giá trị mặc định", lambda: self.gamma_var.set(0.70), "subtle").pack(fill="x")

    def _build_logarithmic_inspector(self) -> None:
        """Build adjustable controls for Logarithmic Transformation strength."""
        self._inspector_heading("ÁNH SÁNG & SẮC ĐỘ", "Biến đổi Logarit", "Tăng chi tiết vùng tối bằng công thức c × log(1 + pixel).")
        self._field_caption("Hệ số c", self.log_coefficient_text_var)
        self._scale(self.inspector, self.log_coefficient_var, 1.00, 60.00,
                    self._update_log_coefficient_text).pack(fill="x", pady=(2, 0))
        ends = tk.Frame(self.inspector, bg=self.PANEL_BG)
        ends.pack(fill="x", pady=(0, 13))
        tk.Label(ends, text="1.00", bg=self.PANEL_BG, fg=self.DIM, font=("Segoe UI", 8)).pack(side="left")
        tk.Label(ends, text="60.00", bg=self.PANEL_BG, fg=self.DIM, font=("Segoe UI", 8)).pack(side="right")
        presets = tk.Frame(self.inspector, bg=self.PANEL_BG)
        presets.pack(fill="x", pady=(0, 18))
        for value in (25.00, 35.00, 45.99, 55.00):
            label = "Mặc định" if value == 45.99 else f"{value:.0f}"
            self._button(presets, label, lambda v=value: self.log_coefficient_var.set(v), "subtle").pack(side="left", expand=True, fill="x", padx=2)
        self._callout("Hiệu ứng", "c nhỏ cho kết quả tối hơn. c lớn làm sáng và có thể bão hòa vùng sáng.")
        self._button(self.inspector, "Áp dụng Logarit", self.logarithmic, "accent").pack(fill="x", pady=(20, 7))
        self._button(self.inspector, "Khôi phục giá trị mặc định", lambda: self.log_coefficient_var.set(45.99), "subtle").pack(fill="x")

    def _build_canny_inspector(self) -> None:
        """Build Canny threshold sliders and quick presets."""
        self._inspector_heading("PHÁT HIỆN BIÊN", "Canny", "Tách các đường nét khỏi hình ảnh.")
        self._field_caption("Ngưỡng dưới · Threshold 1", self.low_var)
        self._scale(self.inspector, self.low_var, 0, 255).pack(fill="x", pady=(2, 12))
        self._field_caption("Ngưỡng trên · Threshold 2", self.high_var)
        self._scale(self.inspector, self.high_var, 0, 255).pack(fill="x", pady=(2, 14))
        self._section_label(self.inspector, "THIẾT LẬP NHANH").pack(anchor="w", pady=(0, 6))
        presets = tk.Frame(self.inspector, bg=self.PANEL_BG)
        presets.pack(fill="x", pady=(0, 16))
        for text, values in (("Chi tiết", (45, 110)), ("Cân bằng", (80, 160)), ("Rõ nét", (120, 220))):
            self._button(presets, text, lambda v=values: self._set_canny_preset(*v), "subtle").pack(side="left", expand=True, fill="x", padx=2)
        self._callout("Lưu ý", "Ngưỡng dưới không vượt ngưỡng trên. Ảnh được chuyển xám trước khi xử lý.")
        self._button(self.inspector, "Áp dụng Canny", self.canny, "accent").pack(fill="x", pady=(20, 7))
        self._button(self.inspector, "Khôi phục giá trị mặc định", lambda: self._set_canny_preset(80, 160), "subtle").pack(fill="x")

    def _build_crop_inspector(self) -> None:
        """Build coordinate crop controls and direct selection button."""
        self._sync_dimension_fields()
        self._inspector_heading("BỐ CỤC & KÍCH THƯỚC", "Cắt ảnh", "Chọn chính xác vùng ảnh cần giữ.")
        self._two_fields("Tọa độ X", self.crop_x_var, "Tọa độ Y", self.crop_y_var)
        self._two_fields("Chiều rộng (px)", self.crop_width_var, "Chiều cao (px)", self.crop_height_var, (10, 0))
        self._button(self.inspector, "Chọn vùng trên ảnh", lambda: self._activate_direct_tool("crop"), "subtle").pack(fill="x", pady=(18, 7))
        self._button(self.inspector, "Áp dụng cắt ảnh", self.apply_crop, "accent").pack(fill="x")
        self._callout("Mẹo", "Kéo trực tiếp trên ảnh kết quả. Vùng ngoài khung sẽ bị loại bỏ khi bạn áp dụng.")

    def _build_resize_inspector(self) -> None:
        """Build resize fields, ratio lock and direct-resize activation."""
        self._sync_dimension_fields()
        self._inspector_heading("BỐ CỤC & KÍCH THƯỚC", "Đổi kích thước", "Thiết lập kích thước chính xác hoặc kéo tay nắm trên ảnh.")
        width_entry, height_entry = self._two_fields("Chiều rộng (px)", self.resize_width_var, "Chiều cao (px)", self.resize_height_var)
        width_entry.bind("<KeyRelease>", lambda _event: self._sync_resize_from_width())
        height_entry.bind("<KeyRelease>", lambda _event: self._sync_resize_from_height())
        tk.Checkbutton(self.inspector, text="Giữ nguyên tỷ lệ khung hình", variable=self.keep_ratio_var,
                       bg=self.PANEL_BG, fg=self.MUTED, selectcolor=self.PANEL_ALT,
                       activebackground=self.PANEL_BG, activeforeground=self.TEXT,
                       font=("Segoe UI", 9), bd=0, highlightthickness=0).pack(anchor="w", pady=(12, 14))
        self._button(self.inspector, "Kéo tay nắm trên ảnh", lambda: self._activate_direct_tool("resize"), "subtle").pack(fill="x", pady=(0, 7))
        self._button(self.inspector, "Áp dụng kích thước", self.apply_resize, "accent").pack(fill="x")
        self._callout("Nội suy", "INTER_AREA khi thu nhỏ, INTER_CUBIC khi phóng to.")

    def _field_caption(self, text: str, variable: tk.Variable) -> None:
        """Add one label/value row above a slider."""
        row = tk.Frame(self.inspector, bg=self.PANEL_BG)
        row.pack(fill="x", pady=(0, 4))
        tk.Label(row, text=text, bg=self.PANEL_BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row, textvariable=variable, bg=self.PANEL_ALT, fg=self.TEXT,
                 padx=7, pady=2, font=("Segoe UI Semibold", 9)).pack(side="right")

    def _two_fields(self, label1: str, var1: tk.StringVar, label2: str, var2: tk.StringVar,
                    pady: tuple[int, int] = (0, 0)) -> tuple[tk.Entry, tk.Entry]:
        """Place two dark input fields beside each other."""
        row = tk.Frame(self.inspector, bg=self.PANEL_BG)
        row.pack(fill="x", pady=pady)
        left, right = tk.Frame(row, bg=self.PANEL_BG), tk.Frame(row, bg=self.PANEL_BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        right.pack(side="left", fill="x", expand=True, padx=(5, 0))
        tk.Label(left, text=label1, bg=self.PANEL_BG, fg=self.MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        tk.Label(right, text=label2, bg=self.PANEL_BG, fg=self.MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        entry1, entry2 = self._entry(left, var1), self._entry(right, var2)
        entry1.pack(fill="x"); entry2.pack(fill="x")
        return entry1, entry2

    def _entry(self, parent: tk.Widget, variable: tk.StringVar) -> tk.Entry:
        """Return a compact dark numeric entry field."""
        return tk.Entry(parent, textvariable=variable, bg=self.PANEL_ALT, fg=self.TEXT,
                        insertbackground=self.ACCENT, relief="flat", bd=0,
                        highlightthickness=1, highlightbackground=self.BORDER,
                        highlightcolor=self.ACCENT, font=("Segoe UI", 10), justify="center")

    def _scale(self, parent: tk.Widget, variable: tk.Variable, start: float, end: float,
               command: object | None = None) -> tk.Scale:
        """Return a dark horizontal slider with an accent active thumb."""
        resolution = 0.01 if isinstance(variable, tk.DoubleVar) else 1
        return tk.Scale(parent, from_=start, to=end, variable=variable, orient="horizontal",
                        showvalue=False, resolution=resolution, command=command,
                        bg=self.PANEL_BG, fg=self.MUTED, troughcolor="#2c3538",
                        activebackground=self.ACCENT, highlightthickness=0, bd=0,
                        sliderrelief="flat", length=240)

    def _callout(self, title: str, text: str) -> None:
        """Add reference-style muted guidance to an inspector."""
        card = tk.Frame(self.inspector, bg=self.PANEL_ALT, padx=10, pady=9)
        card.pack(fill="x", pady=(18, 0))
        tk.Label(card, text=title, bg=self.PANEL_ALT, fg=self.ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(card, text=text, bg=self.PANEL_ALT, fg=self.MUTED, wraplength=220,
                 justify="left", font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))

    # ------------------------------------------------------- image actions
    def _require_image(self, silent: bool = False) -> bool:
        """Verify image availability before executing an operation."""
        if self.current is not None:
            return True
        if not silent:
            messagebox.showinfo("pixelroom", "Hãy mở một ảnh JPG hoặc PNG trước.")
        return False

    def open_image(self) -> None:
        """Load a JPG/PNG, retain an immutable original, and update UI metadata."""
        path = filedialog.askopenfilename(title="Mở ảnh", filetypes=[("Ảnh", "*.jpg *.jpeg *.png"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            self.original = load_image(path)
            self.current = self.original.copy()
            self.file_path = path
            self.file_name_var.set(Path(path).name)
            self.history = ["Mở ảnh gốc"]
            self.status_var.set("Sẵn sàng")
            self.tip_var.set("Xem trước trực tiếp · Ảnh gốc không thay đổi")
            self._sync_dimension_fields(force=True)
            self._refresh_history()
            self._show_inspector("gamma")
            self.refresh_views()
        except Exception as exc:
            messagebox.showerror("Không thể mở ảnh", str(exc))

    def save_image(self) -> None:
        """Save the current preview while preserving the source image."""
        if not self._require_image():
            return
        base = Path(self.file_path).stem if self.file_path else "pixelroom_edited"
        path = filedialog.asksaveasfilename(title="Lưu ảnh", initialfile=f"{base}_edited.png",
                                            defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])
        if not path:
            return
        try:
            save_image(path, self.current)
            self.status_var.set("Đã lưu ảnh")
            self.tip_var.set("Lưu thành bản sao mới, không ghi đè ảnh gốc.")
        except Exception as exc:
            messagebox.showerror("Không thể lưu ảnh", str(exc))

    def reset(self) -> None:
        """Restore the editable preview from the stored original image."""
        if self.original is None:
            return
        self.current = self.original.copy()
        self.history = ["Mở ảnh gốc"]
        self._cancel_direct_tool(redraw=False)
        self._sync_dimension_fields(force=True)
        self._refresh_history()
        self.status_var.set("Đã đặt lại ảnh gốc")
        self.tip_var.set("Ảnh gốc luôn được giữ nguyên.")
        self.refresh_views()

    def _apply(self, name: str, action: object) -> None:
        """Execute a pure processor action, update history, then redraw."""
        if not self._require_image():
            return
        self._cancel_direct_tool(redraw=False)
        try:
            self.current = action(self.current)  # type: ignore[operator]
            self._record_history(name)
            self.status_var.set("Đã chỉnh sửa")
            self.tip_var.set("Xem trước trực tiếp · Ảnh gốc không thay đổi")
            self._sync_dimension_fields(force=True)
            self.refresh_views()
        except Exception as exc:
            messagebox.showerror("Không thể xử lý", str(exc))

    def grayscale(self) -> None:
        """Apply grayscale conversion."""
        self._apply("Ảnh xám", ImageProcessor.grayscale)
        self._show_inspector("Ảnh xám")

    def negative(self) -> None:
        """Apply the safe photographic negative operation."""
        self._apply("Ảnh âm bản", ImageProcessor.negative)
        self._show_inspector("Ảnh âm bản")

    def logarithmic(self) -> None:
        """Apply logarithmic enhancement using the selected coefficient."""
        coefficient = self.log_coefficient_var.get()
        self._apply(f"Biến đổi Logarit · c={coefficient:.2f}",
                    lambda image: ImageProcessor.logarithmic(image, coefficient))
        self._show_inspector("log")

    def canny(self) -> None:
        """Apply Canny with inspector-defined lower and upper thresholds."""
        self._apply("Phát hiện biên Canny", lambda image: ImageProcessor.canny(image, self.low_var.get(), self.high_var.get()))
        self._show_inspector("canny")

    def gamma(self) -> None:
        """Apply gamma correction using the inspector slider value."""
        self._apply(f"Gamma · {self.gamma_var.get():.2f}", lambda image: ImageProcessor.gamma(image, self.gamma_var.get()))
        self._show_inspector("gamma")

    def apply_crop(self) -> None:
        """Crop from input coordinates or a direct canvas selection."""
        try:
            values = tuple(int(var.get()) for var in (self.crop_x_var, self.crop_y_var, self.crop_width_var, self.crop_height_var))
        except ValueError:
            messagebox.showerror("Cắt ảnh", "Tọa độ và kích thước phải là số nguyên.")
            return
        self._apply("Cắt ảnh", lambda image: ImageProcessor.crop(image, *values))
        self._show_inspector("crop")

    def apply_resize(self) -> None:
        """Resize to the inspector's width and height fields."""
        try:
            width, height = int(self.resize_width_var.get()), int(self.resize_height_var.get())
        except ValueError:
            messagebox.showerror("Đổi kích thước", "Chiều rộng và chiều cao phải là số nguyên.")
            return
        self._apply("Đổi kích thước", lambda image: ImageProcessor.resize(image, width, height))
        self._show_inspector("resize")

    # -------------------------------------------------- direct manipulation
    def _activate_direct_tool(self, tool: str) -> None:
        """Turn on crop selection or resize-handle interaction in preview."""
        if not self._require_image():
            return
        self.active_tool = tool
        if tool == "crop":
            self.crop_selection = None
            self.preview_canvas.configure(cursor="crosshair")
            self.status_var.set("Chế độ cắt")
            self.tip_var.set("Kéo trên ảnh kết quả để chọn vùng cần giữ.")
        else:
            self.resize_target = None
            self.preview_canvas.configure(cursor="sizing")
            self.status_var.set("Chế độ đổi kích thước")
            self.tip_var.set("Kéo tay nắm xanh ở góc dưới-phải của ảnh kết quả.")
        self.refresh_views()

    def _cancel_direct_tool(self, _event: object | None = None, redraw: bool = True, keep_selection: bool = False) -> None:
        """Leave interactive mode, optionally retaining an unfinished selection."""
        self.active_tool = None
        self.crop_start = None
        self.resize_dragging = False
        if not keep_selection:
            self.crop_selection = None
            self.resize_target = None
        if hasattr(self, "preview_canvas"):
            self.preview_canvas.configure(cursor="crosshair")
        if redraw:
            self.refresh_views()

    def _interaction_begin(self, event: tk.Event) -> None:
        """Start a direct crop/resize interaction when its mode is active."""
        if self.active_tool == "crop":
            point = self._inside_preview(event)
            if point is not None:
                self.crop_start = point
                self.crop_selection = None
                self.refresh_views()
        elif self.active_tool == "resize":
            self._resize_begin(event)

    def _interaction_drag(self, event: tk.Event) -> None:
        """Keep direct crop or resize visual overlays current while dragging."""
        if self.active_tool == "crop":
            point = self._inside_preview(event)
            if point is not None and self.crop_start is not None:
                x1, y1 = self.crop_start
                x2, y2 = point
                self.crop_selection = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                self._draw_crop_overlay()
        elif self.active_tool == "resize":
            self._resize_drag(event)

    def _interaction_end(self, event: tk.Event) -> None:
        """Transfer direct selection dimensions into inspector fields on release."""
        if self.active_tool == "crop":
            point = self._inside_preview(event)
            if point is not None and self.crop_start is not None:
                x1, y1 = self.crop_start
                x2, y2 = point
                x, y, width, height = min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
                if width > 2 and height > 2:
                    self.crop_selection = (x, y, width, height)
                    self.crop_x_var.set(str(x)); self.crop_y_var.set(str(y))
                    self.crop_width_var.set(str(width)); self.crop_height_var.set(str(height))
                    self.status_var.set("Đã chọn vùng cắt")
                    self.tip_var.set("Nhấn Áp dụng cắt ảnh để xác nhận.")
            self.active_tool = None
            self.crop_start = None
            self.preview_canvas.configure(cursor="crosshair")
            self.refresh_views()
        elif self.active_tool == "resize":
            self._resize_end(event)

    def _resize_begin(self, event: tk.Event) -> None:
        """Start resize only if the visible lower-right handle is grabbed."""
        if self.current is None:
            return
        height, width = self.current.shape[:2]
        right = self.preview_origin[0] + width * self.preview_scale
        bottom = self.preview_origin[1] + height * self.preview_scale
        if abs(event.x - right) > 20 or abs(event.y - bottom) > 20:
            self.tip_var.set("Hãy kéo ô vuông xanh ở góc dưới-phải của ảnh.")
            return
        self.resize_dragging = True
        self.resize_target = (width, height)

    def _resize_drag(self, event: tk.Event) -> None:
        """Map resize handle canvas location to image dimensions."""
        if not self.resize_dragging or self.current is None:
            return
        origin_x, origin_y = self.preview_origin
        width = max(1, round((event.x - origin_x) / self.preview_scale))
        height = max(1, round((event.y - origin_y) / self.preview_scale))
        self.resize_target = (width, height)
        self._draw_resize_overlay(self.resize_target)
        self.status_var.set(f"Kích thước mới: {width} × {height}px")

    def _resize_end(self, _event: tk.Event) -> None:
        """Populate resize input fields after the drag handle is released."""
        if not self.resize_dragging or self.resize_target is None:
            return
        width, height = self.resize_target
        self.resize_dragging = False
        self.active_tool = None
        self.resize_width_var.set(str(width)); self.resize_height_var.set(str(height))
        self.preview_canvas.configure(cursor="crosshair")
        self.status_var.set("Đã chọn kích thước")
        self.tip_var.set("Nhấn Áp dụng kích thước để xác nhận.")
        self.refresh_views()

    # ----------------------------------------------------- preview drawing
    def _queue_refresh(self, _event: tk.Event | None = None) -> None:
        """Coalesce layout resizes before drawing canvas previews again."""
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after_idle(self.refresh_views)

    def refresh_views(self) -> None:
        """Draw original/current arrays with OpenCV BGR-to-RGB conversion helper."""
        self._refresh_job = None
        if not self.winfo_exists():
            return
        self._draw_image(self.original_canvas, self.original, False)
        self._draw_image(self.preview_canvas, self.current, True)
        self._update_image_captions()

    def _draw_image(self, canvas: tk.Canvas, image: np.ndarray | None, is_preview: bool) -> None:
        """Fit an image into a canvas and preserve the Tk PhotoImage reference."""
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        if image is None:
            if is_preview:
                canvas.create_text(width // 2, height // 2 - 13, text="Từng chi tiết, đúng ý bạn.", fill=self.TEXT,
                                   font=("Segoe UI Semibold", 15))
                canvas.create_text(width // 2, height // 2 + 16, text="Mở một ảnh để bắt đầu chỉnh sửa.", fill=self.DIM,
                                   font=("Segoe UI", 10))
            else:
                canvas.create_text(width // 2, height // 2, text="Ảnh gốc", fill=self.DIM, font=("Segoe UI", 11))
            return
        available_w, available_h = max(width - 32, 1), max(height - 32, 1)
        if is_preview and self.active_tool == "resize":
            available_w = max(int(available_w * 0.72), 1)
            available_h = max(int(available_h * 0.72), 1)
        photo, scale = fit_image(image, available_w, available_h)
        x, y = (width - photo.width()) // 2, (height - photo.height()) // 2
        canvas.create_image(x, y, image=photo, anchor="nw")
        canvas.image = photo
        if is_preview:
            self.preview_scale, self.preview_origin = scale, (x, y)
            if self.crop_selection is not None and (self.active_tool == "crop" or self.inspector_tool == "crop"):
                self._draw_crop_overlay()
            elif self.active_tool == "resize" or (self.resize_target is not None and self.inspector_tool == "resize"):
                self._draw_resize_overlay(self.resize_target)

    def _inside_preview(self, event: tk.Event) -> tuple[int, int] | None:
        """Translate a preview canvas event into a current-image pixel coordinate."""
        if self.current is None:
            return None
        x, y = event.x - self.preview_origin[0], event.y - self.preview_origin[1]
        height, width = self.current.shape[:2]
        if 0 <= x < width * self.preview_scale and 0 <= y < height * self.preview_scale:
            return int(x / self.preview_scale), int(y / self.preview_scale)
        return None

    def _draw_crop_overlay(self) -> None:
        """Display the selected crop rectangle in lime on the result canvas."""
        if self.crop_selection is None:
            return
        x, y, width, height = self.crop_selection
        ox, oy, scale = self.preview_origin[0], self.preview_origin[1], self.preview_scale
        left, top = ox + x * scale, oy + y * scale
        right, bottom = left + width * scale, top + height * scale
        canvas = self.preview_canvas
        canvas.delete("tool_overlay")
        canvas.create_rectangle(left, top, right, bottom, outline=self.ACCENT, width=2, tags="tool_overlay")
        canvas.create_text(left + 7, top + 7, text=f"{width} × {height}", anchor="nw", fill=self.ACCENT,
                           font=("Segoe UI", 8, "bold"), tags="tool_overlay")

    def _draw_resize_overlay(self, target: tuple[int, int] | None = None) -> None:
        """Display resize bounds and a lower-right drag handle on preview."""
        if self.current is None:
            return
        if target is None:
            height, width = self.current.shape[:2]
        else:
            width, height = target
        ox, oy = self.preview_origin
        right, bottom = ox + width * self.preview_scale, oy + height * self.preview_scale
        canvas = self.preview_canvas
        canvas.delete("tool_overlay")
        canvas.create_rectangle(ox, oy, right, bottom, outline=self.ACCENT, width=2, dash=(5, 3), tags="tool_overlay")
        canvas.create_rectangle(right - 7, bottom - 7, right + 7, bottom + 7, fill=self.ACCENT,
                                outline=self.TEXT, tags="tool_overlay")
        canvas.create_text(ox + 7, oy + 7, text=f"{width} × {height} px", anchor="nw", fill=self.ACCENT,
                           font=("Segoe UI", 8, "bold"), tags="tool_overlay")

    # ------------------------------------------------------------ helpers
    def _update_gamma_text(self, *_args: object) -> None:
        """Synchronise Gamma's label and slider value."""
        try:
            self.gamma_text_var.set(f"{self.gamma_var.get():.2f}")
        except tk.TclError:
            pass

    def _update_log_coefficient_text(self, *_args: object) -> None:
        """Synchronise the visible Logarithmic coefficient with its slider."""
        try:
            self.log_coefficient_text_var.set(f"{self.log_coefficient_var.get():.2f}")
        except tk.TclError:
            pass

    def _set_canny_preset(self, low: int, high: int) -> None:
        """Load paired Canny threshold preset values."""
        self.low_var.set(low); self.high_var.set(high)

    def _sync_dimension_fields(self, force: bool = False) -> None:
        """Populate crop/resize fields from active image dimensions when needed."""
        if self.current is None:
            return
        height, width = self.current.shape[:2]
        if force or self.crop_selection is None:
            self.crop_x_var.set("0"); self.crop_y_var.set("0")
            self.crop_width_var.set(str(width)); self.crop_height_var.set(str(height))
        if force or self.resize_target is None:
            self.resize_width_var.set(str(width)); self.resize_height_var.set(str(height))

    def _sync_resize_from_width(self) -> None:
        """Update height while typing width when aspect ratio lock is on."""
        if self._resize_input_updating or not self.keep_ratio_var.get() or self.current is None:
            return
        try:
            new_width = int(self.resize_width_var.get())
            old_height, old_width = self.current.shape[:2]
            new_height = max(1, round(new_width * old_height / old_width))
        except ValueError:
            return
        self._resize_input_updating = True
        self.resize_height_var.set(str(new_height))
        self._resize_input_updating = False

    def _sync_resize_from_height(self) -> None:
        """Update width while typing height when aspect ratio lock is on."""
        if self._resize_input_updating or not self.keep_ratio_var.get() or self.current is None:
            return
        try:
            new_height = int(self.resize_height_var.get())
            old_height, old_width = self.current.shape[:2]
            new_width = max(1, round(new_height * old_width / old_height))
        except ValueError:
            return
        self._resize_input_updating = True
        self.resize_width_var.set(str(new_width))
        self._resize_input_updating = False

    def _record_history(self, name: str) -> None:
        """Add an operation to the bounded left-side edit history."""
        self.history.append(name)
        self.history = self.history[-5:]
        self._refresh_history()

    def _refresh_history(self) -> None:
        """Refresh visible history rows without allowing tool loss by overflow."""
        if not hasattr(self, "history_list"):
            return
        for child in self.history_list.winfo_children():
            child.destroy()
        entries = list(reversed(self.history[-3:])) or ["Chưa có chỉnh sửa"]
        for index, name in enumerate(entries, start=1):
            row = tk.Frame(self.history_list, bg=self.PANEL_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{index:02d}", width=3, bg=self.PANEL_ALT, fg=self.ACCENT,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(row, text=name, bg=self.PANEL_BG, fg=self.MUTED, anchor="w",
                     font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(7, 0))

    def _refresh_tool_buttons(self) -> None:
        """Highlight the tool associated with the active inspector panel."""
        if not hasattr(self, "tool_buttons"):
            return
        active = self.inspector_tool if self.inspector_tool in {"canny", "crop", "resize", "gamma", "log"} else None
        for key, button in self.tool_buttons.items():
            selected = key == active
            button.configure(bg=self.PANEL_HOVER if selected else self.PANEL_BG,
                             fg=self.ACCENT if selected else self.MUTED)

    def _update_image_captions(self) -> None:
        """Expose dimensions and colour metadata beside image views and footer."""
        def dims(image: np.ndarray | None) -> str:
            if image is None:
                return ""
            height, width = image.shape[:2]
            return f"{width} × {height}"

        self.original_caption.configure(text=dims(self.original))
        self.preview_caption.configure(text=dims(self.current))
        if self.current is None:
            self.meta_var.set("—")
        else:
            height, width = self.current.shape[:2]
            channel_text = "1 kênh" if self.current.ndim == 2 else "RGB · 8 bit"
            self.meta_var.set(f"{width} × {height} px   {channel_text}")
