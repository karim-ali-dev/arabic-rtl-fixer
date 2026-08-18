#!/usr/bin/env python3
"""
Arabic RTL Fixer for Affinity Designer/Photo/Publisher
Professional lightweight tool for fixing Arabic text.
"""

import json
import os
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox
from pathlib import Path

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
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
    "window_x": None, "window_y": None,
    "window_w": 500, "window_h": 680,
    "theme": "dark", "opacity": 1.0,
    "do_reshape": True, "do_reverse": True, "do_reverse_chars": False,
    "input_font_size": 16, "output_font_size": 16,
    "auto_copy": True,
}

# Affinity-style colors
THEMES = {
    "dark": {
        "bg": "#2C2C2C", "panel": "#363636", "panel_dark": "#1E1E1E",
        "text": "#E0E0E0", "dim": "#888888", "dimmer": "#555555",
        "accent": "#0099E5", "accent2": "#533483",
        "green": "#28C840", "red": "#FF5F57",
        "border": "#444444", "input_bg": "#2A2A2A", "output_bg": "#252525",
        "btn_hover": "#404040",
    },
    "light": {
        "bg": "#F5F5F5", "panel": "#FFFFFF", "panel_dark": "#E8E8E8",
        "text": "#1A1A1A", "dim": "#666666", "dimmer": "#999999",
        "accent": "#0077CC", "accent2": "#6B3FA0",
        "green": "#1A8F30", "red": "#E04040",
        "border": "#D0D0D0", "input_bg": "#FFFFFF", "output_bg": "#F0F0F0",
        "btn_hover": "#E0E0E0",
    },
}


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults = DEFAULT_CONFIG.copy()
            defaults.update(saved)
            return defaults
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
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
            json.dump(history[-50:], f, ensure_ascii=False)
    except Exception:
        pass


def is_arabic(ch):
    cp = ord(ch)
    return (0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFDFF or
            0xFE70 <= cp <= 0xFEFF or 0x0750 <= cp <= 0x077F)


def reshape_arabic(text):
    if HAS_LIBS:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            pass
    return text


def reverse_words(text):
    words = text.split(" ")
    ai, aw = [], []
    for i, w in enumerate(words):
        if any(is_arabic(c) for c in w):
            ai.append(i)
            aw.append(w)
    aw.reverse()
    for k, idx in enumerate(ai):
        words[idx] = aw[k]
    return " ".join(words)


def process_text(text, reshape=True, reverse=True, reverse_chars=False):
    result = text
    if reshape:
        result = "\n".join(reshape_arabic(line) for line in result.split("\n"))
    if reverse:
        result = "\n".join(reverse_words(line) for line in result.split("\n"))
    if reverse_chars:
        result = "\n".join(line[::-1] for line in result.split("\n"))
    return result


class ArabicFixerApp:
    def __init__(self):
        self.cfg = load_config()
        self.history = load_history()
        self.theme = THEMES[self.cfg.get("theme", "dark")]
        self.processing = False

        self.root = tk.Tk()
        self.root.title("Arabic RTL Fixer")
        self.root.configure(bg=self.theme["bg"])
        self.root.minsize(420, 550)

        x = self.cfg.get("window_x")
        y = self.cfg.get("window_y")
        w = self.cfg.get("window_w", 500)
        h = self.cfg.get("window_h", 680)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        if x is not None and y is not None:
            if x < 0 or x > screen_w - 100 or y < 0 or y > screen_h - 100:
                x = max(0, (screen_w - w) // 2)
                y = max(0, (screen_h - h) // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        else:
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", self.cfg.get("opacity", 1.0))
        except Exception:
            pass

        self._setup_fonts()
        self._build_ui()
        self._apply_theme()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Control-Shift-C>", lambda e: self._copy_result())
        self.root.bind("<Control-Shift-c>", lambda e: self._copy_result())
        self.root.bind("<Control-l>", lambda e: self._clear_all())
        self.root.bind("<Control-L>", lambda e: self._clear_all())
        self.root.bind("<Control-t>", lambda e: self._toggle_theme())
        self.root.bind("<Control-T>", lambda e: self._toggle_theme())

        self._debounce_id = None
        self.input_text.bind("<<Modified>>", self._on_text_change)

        self.root.mainloop()

    def _setup_fonts(self):
        families = ["Segoe UI", "Tahoma", "Arial"]
        self.ui_font = ("Segoe UI", 10)
        self.ui_font_bold = ("Segoe UI", 10, "bold")
        self.title_font = ("Segoe UI", 12, "bold")
        self.accent_font = ("Segoe UI", 9)

        try:
            test = tkfont.Font(family="Segoe UI", size=10)
            if test.actual()["family"] != "Segoe UI":
                for f in families:
                    test = tkfont.Font(family=f, size=10)
                    if test.actual()["family"] == f:
                        self.ui_font = (f, 10)
                        self.ui_font_bold = (f, 10, "bold")
                        self.title_font = (f, 12, "bold")
                        self.accent_font = (f, 9)
                        break
        except Exception:
            pass

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)

        self._build_toolbar()
        self._build_options()
        self._build_input_section()
        self._build_process_button()
        self._build_output_section()
        self._build_buttons()
        self._build_statusbar()

    def _build_toolbar(self):
        self.toolbar = tk.Frame(self.root, height=40)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.toolbar.grid_propagate(False)

        self.title_label = tk.Label(
            self.toolbar, text="  Arabic RTL Fixer",
            font=self.title_font, anchor="w"
        )
        self.title_label.pack(side="left", fill="y")

        btn_frame = tk.Frame(self.toolbar)
        btn_frame.pack(side="right", padx=10)

        self.pin_btn = tk.Button(
            btn_frame, text="Pin", font=self.accent_font,
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="right", padx=2)

        self.theme_btn = tk.Button(
            btn_frame, text="Theme", font=self.accent_font,
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right", padx=2)

    def _build_options(self):
        self.options_frame = tk.Frame(self.root)
        self.options_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(8, 0))

        self.var_reshape = tk.BooleanVar(value=self.cfg.get("do_reshape", True))
        self.var_reverse = tk.BooleanVar(value=self.cfg.get("do_reverse", True))
        self.var_reverse_chars = tk.BooleanVar(value=self.cfg.get("do_reverse_chars", False))

        for var, text in [
            (self.var_reshape, "Reshape"),
            (self.var_reverse, "Reverse Words"),
            (self.var_reverse_chars, "Reverse Chars"),
        ]:
            cb = tk.Checkbutton(
                self.options_frame, text=text, variable=var,
                font=self.ui_font, relief="flat", bd=0,
                command=self._on_option_change
            )
            cb.pack(side="right", padx=(8, 0))

    def _build_input_section(self):
        frame = tk.Frame(self.root)
        frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(10, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self.input_label = tk.Label(
            frame, text="INPUT", font=self.ui_font_bold, anchor="w"
        )
        self.input_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.input_text = tk.Text(
            frame, height=7, width=45,
            font=("Segoe UI", self.cfg.get("input_font_size", 16)),
            wrap="word", undo=True, padx=12, pady=10,
            relief="flat", bd=0, insertbackground=self.theme["accent"]
        )
        self.input_text.grid(row=1, column=0, sticky="nsew")
        self.input_text.tag_configure("rtl", justify="right")

    def _build_process_button(self):
        self.process_btn = tk.Button(
            self.root, text="PROCESS", font=self.ui_font_bold,
            relief="flat", bd=0, padx=20, pady=6, cursor="hand2",
            command=self._process
        )
        self.process_btn.grid(row=3, column=0, pady=(10, 0))

    def _build_output_section(self):
        frame = tk.Frame(self.root)
        frame.grid(row=4, column=0, sticky="nsew", padx=15, pady=(10, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(4, weight=1)

        self.output_label = tk.Label(
            frame, text="OUTPUT", font=self.ui_font_bold, anchor="w"
        )
        self.output_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.output_text = tk.Text(
            frame, height=7, width=45,
            font=("Segoe UI", self.cfg.get("output_font_size", 16)),
            wrap="word", padx=12, pady=10,
            state="disabled", relief="flat", bd=0,
            insertbackground=self.theme["green"]
        )
        self.output_text.grid(row=1, column=0, sticky="nsew")
        self.output_text.tag_configure("rtl", justify="right")

    def _build_buttons(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=5, column=0, sticky="ew", padx=15, pady=(10, 0))

        self.copy_btn = tk.Button(
            btn_frame, text="COPY", font=self.ui_font_bold,
            relief="flat", bd=0, padx=16, pady=6, cursor="hand2",
            command=self._copy_result
        )
        self.copy_btn.pack(side="right", padx=(4, 0))

        self.export_btn = tk.Button(
            btn_frame, text="EXPORT", font=self.ui_font,
            relief="flat", bd=0, padx=16, pady=6, cursor="hand2",
            command=self._export
        )
        self.export_btn.pack(side="right", padx=(4, 0))

        self.clear_btn = tk.Button(
            btn_frame, text="CLEAR", font=self.ui_font,
            relief="flat", bd=0, padx=16, pady=6, cursor="hand2",
            command=self._clear_all
        )
        self.clear_btn.pack(side="right")

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self.root, height=28)
        self.statusbar.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.statusbar.grid_propagate(False)

        self.status_label = tk.Label(
            self.statusbar, text="Ready",
            font=self.accent_font, anchor="w", padx=15
        )
        self.status_label.pack(side="left", fill="y")

        self.count_label = tk.Label(
            self.statusbar, text="",
            font=self.accent_font, anchor="e", padx=15
        )
        self.count_label.pack(side="right", fill="y")

    def _apply_theme(self):
        t = self.theme
        self.root.configure(bg=t["bg"])

        for widget in [self.toolbar, self.options_frame]:
            widget.configure(bg=t["bg"])

        self.title_label.configure(bg=t["bg"], fg=t["text"])
        self.pin_btn.configure(bg=t["panel"], fg=t["text"], activebackground=t["btn_hover"], activeforeground=t["text"])
        self.theme_btn.configure(bg=t["panel"], fg=t["text"], activebackground=t["btn_hover"], activeforeground=t["text"])

        for var_name in ["input_label", "output_label"]:
            getattr(self, var_name).configure(bg=t["bg"], fg=t["text"])

        self.input_text.configure(
            bg=t["input_bg"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent"], selectforeground="#FFFFFF"
        )
        self.output_text.configure(
            bg=t["output_bg"], fg=t["text"], insertbackground=t["green"],
            selectbackground=t["green"], selectforeground="#FFFFFF"
        )

        self.process_btn.configure(
            bg=t["accent"], fg="#FFFFFF",
            activebackground="#0088CC", activeforeground="#FFFFFF"
        )
        self.copy_btn.configure(
            bg=t["accent2"], fg="#FFFFFF",
            activebackground="#6B4FA0", activeforeground="#FFFFFF"
        )
        self.export_btn.configure(
            bg=t["panel"], fg=t["text"],
            activebackground=t["btn_hover"], activeforeground=t["text"]
        )
        self.clear_btn.configure(
            bg=t["panel"], fg=t["dim"],
            activebackground=t["btn_hover"], activeforeground=t["text"]
        )

        self.statusbar.configure(bg=t["panel_dark"])
        self.status_label.configure(bg=t["panel_dark"], fg=t["dim"])
        self.count_label.configure(bg=t["panel_dark"], fg=t["dim"])

        for cb in self.options_frame.winfo_children():
            try:
                cb.configure(
                    bg=t["bg"], fg=t["text"],
                    selectcolor=t["panel"], activebackground=t["bg"],
                    activeforeground=t["text"]
                )
            except Exception:
                pass

    def _on_text_change(self, event=None):
        if self.processing:
            return
        self.input_text.edit_modified(False)
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(200, self._process)

    def _on_option_change(self):
        self.cfg["do_reshape"] = self.var_reshape.get()
        self.cfg["do_reverse"] = self.var_reverse.get()
        self.cfg["do_reverse_chars"] = self.var_reverse_chars.get()
        self._process()

    def _process(self):
        self.processing = True
        text = self.input_text.get("1.0", "end-1c")
        if not text.strip():
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            self.output_text.configure(state="disabled")
            self.count_label.configure(text="")
            self.processing = False
            return

        result = process_text(
            text,
            reshape=self.var_reshape.get(),
            reverse=self.var_reverse.get(),
            reverse_chars=self.var_reverse_chars.get()
        )

        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", result, "rtl")
        self.output_text.configure(state="disabled")

        words = len(text.split())
        chars = len(text.strip())
        self.count_label.configure(text=f"Words: {words}  |  Chars: {chars}")
        self.processing = False

    def _copy_result(self):
        text = self.output_text.get("1.0", "end-1c")
        if not text.strip():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        if self.history and self.history[-1].get("text") != text:
            from datetime import datetime
            self.history.append({
                "text": text,
                "time": datetime.now().isoformat()
            })
            save_history(self.history)

        self.status_label.configure(text="Copied!")
        self.root.after(1500, lambda: self.status_label.configure(text="Ready"))

    def _clear_all(self):
        self.input_text.delete("1.0", "end")
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self.count_label.configure(text="")
        self.status_label.configure(text="Ready")

    def _export(self):
        text = self.output_text.get("1.0", "end-1c")
        if not text.strip():
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="arabic_output.txt"
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            self.status_label.configure(text=f"Exported: {os.path.basename(filepath)}")

    def _toggle_theme(self):
        new_theme = "light" if self.cfg.get("theme") == "dark" else "dark"
        self.cfg["theme"] = new_theme
        self.theme = THEMES[new_theme]
        self._apply_theme()

    def _toggle_pin(self):
        current = self.root.attributes("-topmost")
        self.root.attributes("-topmost", not current)
        self.pin_btn.configure(text="Pin" if not current else "Unpin")

    def _on_close(self):
        try:
            geo = self.root.geometry()
            parts = geo.replace("x", "+").split("+")
            self.cfg["window_x"] = int(parts[2])
            self.cfg["window_y"] = int(parts[3])
            self.cfg["window_w"] = int(parts[0])
            self.cfg["window_h"] = int(parts[1])
        except Exception:
            pass
        save_config(self.cfg)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ArabicFixerApp(root)
    root.mainloop()


if __name__ == "__main__":
    ArabicFixerApp()
