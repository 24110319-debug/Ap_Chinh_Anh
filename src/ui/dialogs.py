"""Small parameter dialogs used by the main editor window."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class CropDialog(tk.Toplevel):
    """Modal dialog for entering crop coordinates in original-image pixels."""
    def __init__(self, parent: tk.Misc, image_size: tuple[int, int]) -> None:
        super().__init__(parent)
        self.title("Cắt ảnh theo tọa độ")
        self.resizable(False, False)
        self.result: tuple[int, int, int, int] | None = None
        w, h = image_size
        self.vars = [tk.StringVar(value=value) for value in ("0", "0", str(w), str(h))]
        ttk.Label(self, text=f"Kích thước hiện tại: {w} × {h}px").grid(row=0, column=0, columnspan=2, padx=18, pady=(16, 10))
        for row, label in enumerate(("X", "Y", "Rộng", "Cao"), start=1):
            ttk.Label(self, text=f"{label} (px)").grid(row=row, column=0, padx=(18, 8), pady=4, sticky="w")
            ttk.Entry(self, textvariable=self.vars[row - 1], width=16).grid(row=row, column=1, padx=(0, 18), pady=4)
        buttons = ttk.Frame(self); buttons.grid(row=5, column=0, columnspan=2, pady=16)
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="Cắt", command=self._accept).pack(side="right", padx=4)
        self.transient(parent); self.grab_set()

    def _accept(self) -> None:
        try:
            self.result = tuple(int(v.get()) for v in self.vars)  # type: ignore[assignment]
        except ValueError:
            return
        self.destroy()


class ResizeDialog(tk.Toplevel):
    """Modal dialog with optional aspect-ratio locking for resize operations."""
    def __init__(self, parent: tk.Misc, image_size: tuple[int, int]) -> None:
        super().__init__(parent)
        self.title("Thay đổi kích thước")
        self.resizable(False, False)
        self.result: tuple[int, int] | None = None
        self.original_w, self.original_h = image_size
        self.width_var, self.height_var = tk.StringVar(value=str(image_size[0])), tk.StringVar(value=str(image_size[1]))
        self.lock_var = tk.BooleanVar(value=True)
        self._updating = False
        for row, (label, var) in enumerate((("Chiều rộng (px)", self.width_var), ("Chiều cao (px)", self.height_var))):
            ttk.Label(self, text=label).grid(row=row, column=0, padx=(18, 8), pady=(16 if row == 0 else 5, 5), sticky="w")
            ttk.Entry(self, textvariable=var, width=16).grid(row=row, column=1, padx=(0, 18), pady=(16 if row == 0 else 5, 5))
        ttk.Checkbutton(self, text="Giữ nguyên tỷ lệ", variable=self.lock_var).grid(row=2, column=0, columnspan=2, padx=18, pady=8, sticky="w")
        buttons = ttk.Frame(self); buttons.grid(row=3, column=0, columnspan=2, pady=(4, 16))
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="Áp dụng", command=self._accept).pack(side="right", padx=4)
        self.width_var.trace_add("write", self._sync_height)
        self.height_var.trace_add("write", self._sync_width)
        self.transient(parent); self.grab_set()

    def _sync_height(self, *_: object) -> None:
        if self._updating or not self.lock_var.get(): return
        try: new_h = round(int(self.width_var.get()) * self.original_h / self.original_w)
        except ValueError: return
        self._updating = True; self.height_var.set(str(new_h)); self._updating = False

    def _sync_width(self, *_: object) -> None:
        """Update width when the user edits height with ratio locking enabled."""
        if self._updating or not self.lock_var.get(): return
        try: new_w = round(int(self.height_var.get()) * self.original_w / self.original_h)
        except ValueError: return
        self._updating = True; self.width_var.set(str(new_w)); self._updating = False

    def _accept(self) -> None:
        try: self.result = (int(self.width_var.get()), int(self.height_var.get()))
        except ValueError: return
        self.destroy()

