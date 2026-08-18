#!/usr/bin/env python3
"""
Arabic Text Fixer for Affinity Designer/Photo/Publisher
A desktop tool for fixing Arabic RTL text for applications that don't support RTL natively.
"""

import json
import os
import sys
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox
from pathlib import Path

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_LIBS_AVAILABLE = True
except ImportError:
    ARABIC_LIBS_AVAILABLE = False

try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
HISTORY_FILE = BASE_DIR / "history.json"

DEFAULT_CONFIG = {
    "window_x": None,
    "window_y": None,
    "window_w": 480,
    "window_h": 700,
    "theme": "dark",
    "opacity": 1.0,
    "auto_copy": True,
    "do_reshape": True,
    "do_reverse": True,
    "do_reverse_chars": False,
    "input_font_size": 14,
    "output_font_size": 14,
    "history_visible": False,
}

MAX_HISTORY = 50

DARK_COLORS = {
    "bg": "#0d1117",
    "secondary_bg": "#161b22",
    "tertiary_bg": "#1c2333",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "text": "#e6edf3",
    "text_dim": "#8b949e",
    "border": "#30363d",
    "input_bg": "#0d1117",
    "output_bg": "#161b22",
    "button_bg": "#21262d",
    "button_hover": "#30363d",
    "entry_bg": "#0d1117",
    "entry_insert": "#e6edf3",
    "check_bg": "#161b22",
    "history_item_bg": "#1c2333",
    "history_hover": "#21262d",
}

LIGHT_COLORS = {
    "bg": "#f0f0f0",
    "secondary_bg": "#ffffff",
    "tertiary_bg": "#e8e8e8",
    "accent": "#d63384",
    "accent_hover": "#b02a6b",
    "text": "#1a1a1a",
    "text_dim": "#6c757d",
    "border": "#dee2e6",
    "input_bg": "#ffffff",
    "output_bg": "#f8f9fa",
    "button_bg": "#e9ecef",
    "button_hover": "#dee2e6",
    "entry_bg": "#ffffff",
    "entry_insert": "#1a1a1a",
    "check_bg": "#ffffff",
    "history_item_bg": "#f8f9fa",
    "history_hover": "#e9ecef",
}

FONT_PATH = r"C:\Users\karim\AppData\Local\Microsoft\Windows\Fonts\GraphicSchool-Regular.ttf"


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config = dict(DEFAULT_CONFIG)
            config.update({k: v for k, v in saved.items() if k in DEFAULT_CONFIG})
            return config
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-MAX_HISTORY:], f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def reshape_arabic(text):
    if not ARABIC_LIBS_AVAILABLE:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        display = get_display(reshaped)
        return display
    except Exception:
        return text


def reverse_words(text):
    return " ".join(reversed(text.split()))


def reverse_characters(text):
    return text[::-1]


def process_text(text, do_reshape=True, do_reverse=True, do_reverse_chars=False):
    if not text.strip():
        return ""
    result = text
    if do_reshape:
        result = reshape_arabic(result)
    if do_reverse_chars:
        result = reverse_characters(result)
    elif do_reverse:
        result = reverse_words(result)
    return result

class ArabicFixerApp:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.history = load_history()
        self.colors = DARK_COLORS if self.config["theme"] == "dark" else LIGHT_COLORS
        self.debounce_id = None
        self.history_collapsed = not self.config.get("history_visible", False)
        self._pinned = True

        self._setup_window()
        self._load_custom_font()
        self._build_ui()
        self._apply_theme()
        self._bind_shortcuts()
        self._restore_settings()
        self._update_output()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_window(self):
        self.root.title("Arabic Text Fixer")
        self.root.configure(bg=self.colors["bg"])
        self.root.minsize(380, 500)

        w = self.config.get("window_w", 480)
        h = self.config.get("window_h", 700)
        x = self.config.get("window_x")
        y = self.config.get("window_y")

        if x is not None and y is not None:
            try:
                self.root.geometry(f"{w}x{h}+{x}+{y}")
            except Exception:
                self.root.geometry(f"{w}x{h}")
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", self.config.get("opacity", 1.0))
        except Exception:
            pass

    def _load_custom_font(self):
        self.custom_font = None
        if os.path.exists(FONT_PATH):
            try:
                self.custom_font = tkfont.Font(
                    family="GraphicSchool",
                    size=self.config.get("input_font_size", 14),
                )
            except Exception:
                self.custom_font = None

    def _get_font(self, size_key="input_font_size"):
        size = self.config.get(size_key, 14)
        if self.custom_font:
            try:
                return self.custom_font.copy(size=size)
            except TypeError:
                return tkfont.Font(
                    family=self.custom_font.cget("family"),
                    size=size,
                )
        return ("Segoe UI", size)

    def _build_ui(self):
        self._build_title_bar()
        self._build_options_row()
        self._build_text_areas()
        self._build_buttons_row()
        self._build_status_bar()
        self._build_history_section()

    def _build_title_bar(self):
        self.title_frame = tk.Frame(self.root, height=44)
        self.title_frame.pack(fill="x", padx=0, pady=0)
        self.title_frame.pack_propagate(False)

        self.title_label = tk.Label(
            self.title_frame,
            text="Arabic Text Fixer",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        self.title_label.pack(side="left", padx=12, pady=8)

        btn_frame = tk.Frame(self.title_frame)
        btn_frame.pack(side="right", padx=8)

        self.theme_btn = tk.Button(
            btn_frame,
            text="\u263E",
            width=3,
            relief="flat",
            command=self._toggle_theme,
            font=("Segoe UI", 12),
        )
        self.theme_btn.pack(side="left", padx=2)

        self.pin_btn = tk.Button(
            btn_frame,
            text="\u2B50",
            width=3,
            relief="flat",
            command=self._toggle_pin,
            font=("Segoe UI", 12),
        )
        self.pin_btn.pack(side="left", padx=2)

    def _build_options_row(self):
        self.options_frame = tk.Frame(self.root)
        self.options_frame.pack(fill="x", padx=10, pady=(4, 2))

        self.reshape_var = tk.BooleanVar(value=self.config.get("do_reshape", True))
        self.reverse_var = tk.BooleanVar(value=self.config.get("do_reverse", True))
        self.reverse_chars_var = tk.BooleanVar(value=self.config.get("do_reverse_chars", False))
        self.auto_copy_var = tk.BooleanVar(value=self.config.get("auto_copy", True))

        cb_font = ("Segoe UI", 9)

        self.reshape_cb = tk.Checkbutton(
            self.options_frame, text="Reshape", variable=self.reshape_var,
            font=cb_font, command=self._on_option_change,
        )
        self.reshape_cb.pack(side="left", padx=(0, 6))

        self.reverse_cb = tk.Checkbutton(
            self.options_frame, text="Reverse Words", variable=self.reverse_var,
            font=cb_font, command=self._on_option_change,
        )
        self.reverse_cb.pack(side="left", padx=(0, 6))

        self.reverse_chars_cb = tk.Checkbutton(
            self.options_frame, text="Reverse Chars", variable=self.reverse_chars_var,
            font=cb_font, command=self._on_option_change,
        )
        self.reverse_chars_cb.pack(side="left", padx=(0, 6))

        self.auto_copy_cb = tk.Checkbutton(
            self.options_frame, text="Auto-Copy", variable=self.auto_copy_var,
            font=cb_font,
        )
        self.auto_copy_cb.pack(side="left", padx=(0, 6))

        op_frame = tk.Frame(self.options_frame)
        op_frame.pack(side="right")

        tk.Label(op_frame, text="Opacity", font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))

        self.opacity_var = tk.DoubleVar(value=self.config.get("opacity", 1.0))
        self.opacity_scale = tk.Scale(
            op_frame, from_=0.3, to=1.0, resolution=0.05, orient="horizontal",
            variable=self.opacity_var, showvalue=True, length=90,
            command=self._on_opacity_change, font=("Segoe UI", 8),
            highlightthickness=0, bd=0,
        )
        self.opacity_scale.pack(side="left")

    def _build_text_areas(self):
        size_frame = tk.Frame(self.root)
        size_frame.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(size_frame, text="Input Size", font=("Segoe UI", 8)).pack(side="left")
        self.input_size_var = tk.IntVar(value=self.config.get("input_font_size", 14))
        self.input_size_spin = tk.Spinbox(
            size_frame, from_=8, to=48, width=3, textvariable=self.input_size_var,
            command=self._on_font_size_change, font=("Segoe UI", 8),
        )
        self.input_size_spin.pack(side="left", padx=(2, 12))

        tk.Label(size_frame, text="Output Size", font=("Segoe UI", 8)).pack(side="left")
        self.output_size_var = tk.IntVar(value=self.config.get("output_font_size", 14))
        self.output_size_spin = tk.Spinbox(
            size_frame, from_=8, to=48, width=3, textvariable=self.output_size_var,
            command=self._on_font_size_change, font=("Segoe UI", 8),
        )
        self.output_size_spin.pack(side="left", padx=(2, 0))

        input_label_frame = tk.Frame(self.root)
        input_label_frame.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(input_label_frame, text="Input (Arabic):", font=("Segoe UI", 9, "bold")).pack(side="left")

        input_container = tk.Frame(self.root)
        input_container.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        self.input_text = tk.Text(
            input_container, wrap="word", undo=True,
            font=self._get_font("input_font_size"),
            padx=8, pady=8, spacing1=2, spacing2=1, spacing3=2,
            relief="flat", borderwidth=0,
            highlightthickness=1, highlightbackground=self.colors["border"],
        )
        self.input_text.pack(side="left", fill="both", expand=True)

        input_scroll = tk.Scrollbar(input_container, command=self.input_text.yview, width=8)
        input_scroll.pack(side="right", fill="y")
        self.input_text.configure(yscrollcommand=input_scroll.set)

        self.input_text.tag_configure("rtl", justify="right")
        self.input_text.insert("1.0", "")
        self.input_text.bind("<KeyRelease>", self._on_input_key)

        output_label_frame = tk.Frame(self.root)
        output_label_frame.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(output_label_frame, text="Output (Fixed):", font=("Segoe UI", 9, "bold")).pack(side="left")

        output_container = tk.Frame(self.root)
        output_container.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        self.output_text = tk.Text(
            output_container, wrap="word", undo=False, state="disabled",
            font=self._get_font("output_font_size"),
            padx=8, pady=8, spacing1=2, spacing2=1, spacing3=2,
            relief="flat", borderwidth=0,
            highlightthickness=1, highlightbackground=self.colors["border"],
        )
        self.output_text.pack(side="left", fill="both", expand=True)

        output_scroll = tk.Scrollbar(output_container, command=self.output_text.yview, width=8)
        output_scroll.pack(side="right", fill="y")
        self.output_text.configure(yscrollcommand=output_scroll.set)

        self.output_text.tag_configure("rtl", justify="right")

    def _build_buttons_row(self):
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(fill="x", padx=10, pady=(2, 4))

        self.copy_btn = tk.Button(
            self.btn_frame, text="Copy Result", font=("Segoe UI", 9, "bold"),
            relief="flat", command=self._copy_result, cursor="hand2", height=1,
        )
        self.copy_btn.pack(side="left", expand=True, fill="x", padx=(0, 4), ipady=2)

        self.export_btn = tk.Button(
            self.btn_frame, text="Export .txt", font=("Segoe UI", 9, "bold"),
            relief="flat", command=self._export_file, cursor="hand2", height=1,
        )
        self.export_btn.pack(side="left", expand=True, fill="x", padx=(0, 4), ipady=2)

        self.clear_btn = tk.Button(
            self.btn_frame, text="Clear", font=("Segoe UI", 9, "bold"),
            relief="flat", command=self._clear_all, cursor="hand2", height=1,
        )
        self.clear_btn.pack(side="left", expand=True, fill="x", ipady=2)

    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, height=22)
        self.status_frame.pack(fill="x", padx=0, pady=0)
        self.status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_frame, text="Ready | Words: 0 | Chars: 0",
            font=("Segoe UI", 8), anchor="w",
        )
        self.status_label.pack(side="left", padx=10)

        self.shortcut_label = tk.Label(
            self.status_frame,
            text="Ctrl+Shift+C: Copy | Ctrl+L: Clear | Ctrl+T: Theme",
            font=("Segoe UI", 7), anchor="e",
        )
        self.shortcut_label.pack(side="right", padx=10)

    def _build_history_section(self):
        self.history_outer = tk.Frame(self.root)

        self.history_toggle_frame = tk.Frame(self.history_outer)
        self.history_toggle_frame.pack(fill="x", padx=10, pady=(4, 0))

        self.history_arrow = "\u25BC"
        self.history_toggle_btn = tk.Button(
            self.history_toggle_frame,
            text=f" {self.history_arrow} History ({len(self.history)})",
            font=("Segoe UI", 9, "bold"), relief="flat", anchor="w",
            command=self._toggle_history, cursor="hand2",
        )
        self.history_toggle_btn.pack(side="left")

        self.history_clear_btn = tk.Button(
            self.history_toggle_frame, text="Clear History",
            font=("Segoe UI", 8), relief="flat", command=self._clear_history,
        )
        self.history_clear_btn.pack(side="right")

        self.history_container = tk.Frame(self.history_outer)

        self.history_canvas = tk.Canvas(
            self.history_container, highlightthickness=0, height=150,
        )
        self.history_scrollbar = tk.Scrollbar(
            self.history_container, orient="vertical",
            command=self.history_canvas.yview, width=8,
        )

        self.history_inner = tk.Frame(self.history_canvas)
        self.history_inner.bind(
            "<Configure>",
            lambda e: self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all")),
        )

        self.history_canvas_window = self.history_canvas.create_window(
            (0, 0), window=self.history_inner, anchor="nw",
        )
        self.history_canvas.configure(yscrollcommand=self.history_scrollbar.set)

        self.history_canvas.pack(side="left", fill="both", expand=True)
        self.history_scrollbar.pack(side="right", fill="y")

        self.history_canvas.bind("<Configure>", self._on_history_canvas_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        self._render_history()

        if not self.history_collapsed:
            self.history_outer.pack(fill="x", padx=0, pady=(0, 4))
            self.history_container.pack(fill="x", padx=10, pady=(2, 4), after=self.history_toggle_frame)

    def _on_history_canvas_configure(self, event):
        self.history_canvas.itemconfig(self.history_canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        try:
            if hasattr(self, "history_canvas"):
                self.history_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _render_history(self):
        for widget in self.history_inner.winfo_children():
            widget.destroy()

        if not self.history:
            tk.Label(
                self.history_inner, text="No history yet",
                font=("Segoe UI", 9), fg=self.colors["text_dim"],
            ).pack(pady=10)
            return

        for idx, item in enumerate(reversed(self.history)):
            entry_frame = tk.Frame(
                self.history_inner, bg=self.colors["history_item_bg"],
                padx=8, pady=6, cursor="hand2",
            )
            entry_frame.pack(fill="x", padx=4, pady=2)

            input_preview = item.get("input", "")[:60]
            output_preview = item.get("output", "")[:60]
            timestamp = item.get("time", "")

            in_text = f"IN:  {input_preview}"
            if len(item.get("input", "")) > 60:
                in_text += "..."

            out_text = f"OUT: {output_preview}"
            if len(item.get("output", "")) > 60:
                out_text += "..."

            input_label = tk.Label(
                entry_frame, text=in_text, font=("Segoe UI", 8), anchor="w",
                bg=self.colors["history_item_bg"], fg=self.colors["text"],
            )
            input_label.pack(fill="x")

            output_label = tk.Label(
                entry_frame, text=out_text, font=("Segoe UI", 8), anchor="w",
                bg=self.colors["history_item_bg"], fg=self.colors["accent"],
            )
            output_label.pack(fill="x")

            time_label = tk.Label(
                entry_frame, text=timestamp, font=("Segoe UI", 7), anchor="w",
                bg=self.colors["history_item_bg"], fg=self.colors["text_dim"],
            )
            time_label.pack(fill="x")

            original_idx = len(self.history) - 1 - idx
            for w in [entry_frame, input_label, output_label, time_label]:
                w.bind("<Button-1>", lambda e, i=original_idx: self._load_history_item(i))
                w.bind("<Enter>", lambda e, f=entry_frame: f.configure(bg=self.colors["history_hover"]))
                w.bind("<Leave>", lambda e, f=entry_frame, obg=self.colors["history_item_bg"]: f.configure(bg=obg))

    def _load_history_item(self, index):
        if 0 <= index < len(self.history):
            item = self.history[index]
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", item.get("input", ""))
            self._update_output()

    def _toggle_history(self):
        self.history_collapsed = not self.history_collapsed
        self.history_arrow = "\u25B2" if not self.history_collapsed else "\u25BC"
        count = len(self.history)
        self.history_toggle_btn.configure(text=f" {self.history_arrow} History ({count})")

        if self.history_collapsed:
            self.history_container.pack_forget()
        else:
            self.history_outer.pack(fill="x", padx=0, pady=(0, 4))
            self.history_container.pack(fill="x", padx=10, pady=(2, 4), after=self.history_toggle_frame)

        self.config["history_visible"] = not self.history_collapsed

    def _clear_history(self):
        self.history = []
        save_history(self.history)
        self._render_history()
        self._update_history_button_text()

    def _update_history_button_text(self):
        count = len(self.history)
        self.history_toggle_btn.configure(text=f" {self.history_arrow} History ({count})")

    def _add_to_history(self, input_text, output_text):
        if not input_text.strip():
            return
        entry = {
            "input": input_text,
            "output": output_text,
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }
        self.history.append(entry)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
        save_history(self.history)
        self._render_history()
        self._update_history_button_text()

    def _apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["bg"])

        self.title_frame.configure(bg=c["secondary_bg"])
        self.title_label.configure(bg=c["secondary_bg"], fg=c["text"])
        self.theme_btn.configure(bg=c["button_bg"], fg=c["text"], activebackground=c["button_hover"])
        self.pin_btn.configure(bg=c["button_bg"], fg=c["text"], activebackground=c["button_hover"])

        self.options_frame.configure(bg=c["bg"])
        for cb in [self.reshape_cb, self.reverse_cb, self.reverse_chars_cb, self.auto_copy_cb]:
            cb.configure(bg=c["bg"], fg=c["text"], selectcolor=c["check_bg"],
                         activebackground=c["bg"], activeforeground=c["text"])

        self.input_text.configure(
            bg=c["input_bg"], fg=c["text"], insertbackground=c["entry_insert"],
            selectbackground=c["accent"], selectforeground=c["text"],
            highlightbackground=c["border"], highlightcolor=c["accent"],
        )
        self.output_text.configure(
            bg=c["output_bg"], fg=c["text"],
            selectbackground=c["accent"], selectforeground=c["text"],
            highlightbackground=c["border"], highlightcolor=c["accent"],
        )

        self.copy_btn.configure(bg=c["accent"], fg="#ffffff", activebackground=c["accent_hover"])
        self.export_btn.configure(bg=c["button_bg"], fg=c["text"], activebackground=c["button_hover"])
        self.clear_btn.configure(bg=c["button_bg"], fg=c["text"], activebackground=c["button_hover"])

        self.status_frame.configure(bg=c["secondary_bg"])
        self.status_label.configure(bg=c["secondary_bg"], fg=c["text_dim"])
        self.shortcut_label.configure(bg=c["secondary_bg"], fg=c["text_dim"])

        self.history_outer.configure(bg=c["bg"])
        self.history_toggle_frame.configure(bg=c["bg"])
        self.history_toggle_btn.configure(bg=c["bg"], fg=c["text"], activebackground=c["bg"])
        self.history_clear_btn.configure(bg=c["bg"], fg=c["text_dim"], activebackground=c["bg"])
        self.history_container.configure(bg=c["bg"])
        self.history_canvas.configure(bg=c["bg"], highlightbackground=c["border"])
        self.history_inner.configure(bg=c["bg"])

        for child in self.history_inner.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=c["history_item_bg"])
                for label in child.winfo_children():
                    if isinstance(label, tk.Label):
                        current_fg = label.cget("fg")
                        if current_fg == self.colors.get("text"):
                            label.configure(bg=c["history_item_bg"], fg=c["text"])
                        elif current_fg == self.colors.get("accent"):
                            label.configure(bg=c["history_item_bg"], fg=c["accent"])
                        else:
                            label.configure(bg=c["history_item_bg"], fg=c["text_dim"])

    def _toggle_theme(self):
        if self.config["theme"] == "dark":
            self.config["theme"] = "light"
            self.colors = LIGHT_COLORS
        else:
            self.config["theme"] = "dark"
            self.colors = DARK_COLORS
        self._apply_theme()

    def _toggle_pin(self):
        current = self.root.attributes("-topmost")
        self.root.attributes("-topmost", not current)
        self._pinned = not current
        if not current:
            self.pin_btn.configure(bg=self.colors["accent"])
        else:
            self.pin_btn.configure(bg=self.colors["button_bg"])

    def _bind_shortcuts(self):
        self.root.bind("<Control-Shift-C>", lambda e: self._copy_result())
        self.root.bind("<Control-Shift-c>", lambda e: self._copy_result())
        self.root.bind("<Control-l>", lambda e: self._clear_all())
        self.root.bind("<Control-L>", lambda e: self._clear_all())
        self.root.bind("<Control-t>", lambda e: self._toggle_theme())
        self.root.bind("<Control-T>", lambda e: self._toggle_theme())
        self.root.bind("<Control-Shift-A>", lambda e: self._paste_to_active())
        self.root.bind("<Control-Shift-a>", lambda e: self._paste_to_active())

    def _restore_settings(self):
        self.reshape_var.set(self.config.get("do_reshape", True))
        self.reverse_var.set(self.config.get("do_reverse", True))
        self.reverse_chars_var.set(self.config.get("do_reverse_chars", False))
        self.auto_copy_var.set(self.config.get("auto_copy", True))
        self.input_size_var.set(self.config.get("input_font_size", 14))
        self.output_size_var.set(self.config.get("output_font_size", 14))
        self.opacity_var.set(self.config.get("opacity", 1.0))
        self._on_font_size_change()

    def _save_geometry(self):
        try:
            geo = self.root.geometry()
            parts = geo.replace("+", " ").replace("x", " ").split()
            self.config["window_w"] = int(parts[0])
            self.config["window_h"] = int(parts[1])
            self.config["window_x"] = int(parts[2])
            self.config["window_y"] = int(parts[3])
        except Exception:
            pass

    def _on_close(self):
        self._save_geometry()
        self.config["do_reshape"] = self.reshape_var.get()
        self.config["do_reverse"] = self.reverse_var.get()
        self.config["do_reverse_chars"] = self.reverse_chars_var.get()
        self.config["auto_copy"] = self.auto_copy_var.get()
        self.config["input_font_size"] = self.input_size_var.get()
        self.config["output_font_size"] = self.output_size_var.get()
        self.config["opacity"] = self.opacity_var.get()
        save_config(self.config)
        save_history(self.history)
        self.root.destroy()

    def _on_input_key(self, event=None):
        if self.debounce_id is not None:
            self.root.after_cancel(self.debounce_id)
        self.debounce_id = self.root.after(150, self._update_output)

    def _update_output(self):
        self.debounce_id = None
        text = self.input_text.get("1.0", "end-1c")
        do_reshape = self.reshape_var.get()
        do_reverse = self.reverse_var.get()
        do_reverse_chars = self.reverse_chars_var.get()

        result = process_text(text, do_reshape, do_reverse, do_reverse_chars)

        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", result)
        self.output_text.tag_add("rtl", "1.0", "end")
        self.output_text.configure(state="disabled")

        self.input_text.tag_add("rtl", "1.0", "end")

        input_words = len(text.split()) if text.strip() else 0
        input_chars = len(text.strip()) if text.strip() else 0
        output_words = len(result.split()) if result.strip() else 0
        output_chars = len(result.strip()) if result.strip() else 0
        self.status_label.configure(
            text=f"In: {input_words} words, {input_chars} chars | Out: {output_words} words, {output_chars} chars"
        )

        if self.auto_copy_var.get() and result.strip():
            self._copy_to_clipboard(result, silent=True)

        if text.strip() and result.strip():
            existing = [h["input"] for h in self.history]
            if text.strip() not in existing:
                self._add_to_history(text, result)

    def _on_option_change(self):
        self._update_output()

    def _on_opacity_change(self, value=None):
        try:
            val = float(self.opacity_var.get())
            self.root.attributes("-alpha", val)
            self.config["opacity"] = val
        except Exception:
            pass

    def _on_font_size_change(self):
        try:
            in_size = self.input_size_var.get()
            out_size = self.output_size_var.get()
            self.input_text.configure(font=self._get_font("input_font_size"))
            self.output_text.configure(font=self._get_font("output_font_size"))
            self.config["input_font_size"] = in_size
            self.config["output_font_size"] = out_size
        except Exception:
            pass

    def _copy_to_clipboard(self, text, silent=False):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            if not silent:
                original = self.status_label.cget("text")
                self.status_label.configure(text="Copied to clipboard!")
                self.root.after(2000, lambda: self.status_label.configure(text=original))
        except Exception as e:
            if not silent:
                messagebox.showerror("Copy Error", str(e))

    def _copy_result(self):
        result = self.output_text.get("1.0", "end-1c")
        if result.strip():
            self._copy_to_clipboard(result)
        else:
            self.status_label.configure(text="Nothing to copy!")

    def _export_file(self):
        result = self.output_text.get("1.0", "end-1c")
        if not result.strip():
            messagebox.showinfo("Export", "Nothing to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="arabic_output.txt",
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(result)
                self.status_label.configure(text=f"Exported to: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _clear_all(self):
        self.input_text.delete("1.0", "end")
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self.status_label.configure(text="Cleared | Words: 0 | Chars: 0")

    def _paste_to_active(self):
        result = self.output_text.get("1.0", "end-1c")
        if not result.strip():
            self.status_label.configure(text="Nothing to paste!")
            return
        self._copy_to_clipboard(result, silent=True)
        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "v")
            self.status_label.configure(text="Pasted to active window!")
        except ImportError:
            self.status_label.configure(text="pyautogui not installed - copied instead")
        except Exception as e:
            self.status_label.configure(text=f"Paste failed: {e}")


def main():
    root = tk.Tk()
    app = ArabicFixerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
