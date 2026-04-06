#!/usr/bin/env python3
"""hba_convert_gui.py — GUI converter: ASCII .txt / .bas / .hba  ->  tokenized .HBA binary.
By Kayto, April 2026
Licensed under the MIT License. See LICENSE file for details.
"""

import importlib.util, os, sys, tkinter as tk
from tkinter import filedialog, ttk

# ---------------------------------------------------------------------------
# Load tokenizer from sibling file regardless of working directory
# ---------------------------------------------------------------------------
_here = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "hba_tok", os.path.join(_here, "hba_tokenize.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
tokenize_file = _mod.tokenize_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _output_path(src: str, out_dir: str) -> str:
    base = os.path.splitext(os.path.basename(src))[0]
    return os.path.join(out_dir, base + ".HBA")


def _convert(src: str, out_dir: str) -> tuple[bool, str]:
    try:
        text = open(src, encoding="ascii", errors="replace").read()
        binary = tokenize_file(text)
        out = _output_path(src, out_dir)
        with open(out, "wb") as f:
            f.write(binary)
        lines = sum(1 for ln in text.splitlines() if ln.strip()[:1].isdigit())
        return True, f"OK  {lines} lines -> {len(binary)} bytes -> {os.path.basename(out)}"
    except Exception as exc:
        return False, f"ERROR  {exc}"


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HBA Tokenizer")
        self.resizable(True, True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._files: list[str] = []
        self._out_dir = tk.StringVar(value=os.path.expanduser("~\\Desktop"))

        self._build_ui()
        self.minsize(560, 400)

    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Source files row ---
        fr_src = ttk.LabelFrame(self, text="Source files (.txt / .bas / .hba ASCII)")
        fr_src.grid(row=0, column=0, sticky="ew", **pad)
        fr_src.columnconfigure(0, weight=1)

        self._lbl_count = ttk.Label(fr_src, text="No files selected.")
        self._lbl_count.grid(row=0, column=0, sticky="w", padx=4, pady=2)

        btn_add = ttk.Button(fr_src, text="Add files...", command=self._add_files)
        btn_add.grid(row=0, column=1, padx=4, pady=2)

        btn_clear = ttk.Button(fr_src, text="Clear", command=self._clear_files)
        btn_clear.grid(row=0, column=2, padx=4, pady=2)

        # --- Output directory row ---
        fr_out = ttk.LabelFrame(self, text="Output directory")
        fr_out.grid(row=1, column=0, sticky="ew", **pad)
        fr_out.columnconfigure(0, weight=1)

        ttk.Entry(fr_out, textvariable=self._out_dir).grid(
            row=0, column=0, sticky="ew", padx=4, pady=2)
        ttk.Button(fr_out, text="Browse...", command=self._browse_out).grid(
            row=0, column=1, padx=4, pady=2)

        # --- Log ---
        fr_log = ttk.LabelFrame(self, text="Output")
        fr_log.grid(row=2, column=0, sticky="nsew", **pad)
        fr_log.columnconfigure(0, weight=1)
        fr_log.rowconfigure(0, weight=1)

        self._log = tk.Text(fr_log, state="disabled", wrap="none",
                            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
                            insertbackground="white")
        self._log.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        sb = ttk.Scrollbar(fr_log, command=self._log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._log["yscrollcommand"] = sb.set

        self._log.tag_config("ok",  foreground="#4ec94e")
        self._log.tag_config("err", foreground="#f44747")
        self._log.tag_config("hdr", foreground="#569cd6")

        # --- Convert button ---
        self._btn_go = ttk.Button(self, text="Convert", command=self._convert_all,
                                  style="Accent.TButton")
        self._btn_go.grid(row=3, column=0, pady=6)

    # ------------------------------------------------------------------
    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select source files",
            filetypes=[("BASIC source", "*.txt *.bas *.hba *.BAS *.HBA *.TXT"),
                       ("All files", "*.*")])
        for p in paths:
            if p not in self._files:
                self._files.append(p)
        self._update_count()

    def _clear_files(self):
        self._files.clear()
        self._update_count()

    def _browse_out(self):
        d = filedialog.askdirectory(title="Select output directory",
                                    initialdir=self._out_dir.get())
        if d:
            self._out_dir.set(d)

    def _update_count(self):
        n = len(self._files)
        self._lbl_count.config(text=f"{n} file{'s' if n != 1 else ''} selected." if n else "No files selected.")

    # ------------------------------------------------------------------
    def _log_line(self, text: str, tag: str = ""):
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _convert_all(self):
        if not self._files:
            self._log_line("No source files selected.", "err")
            return

        out_dir = self._out_dir.get().strip()
        if not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir)
            except OSError as e:
                self._log_line(f"Cannot create output dir: {e}", "err")
                return

        self._log_line(f"--- Converting {len(self._files)} file(s) -> {out_dir} ---", "hdr")
        ok = err = 0
        for src in self._files:
            success, msg = _convert(src, out_dir)
            self._log_line(f"  {os.path.basename(src)}: {msg}", "ok" if success else "err")
            if success:
                ok += 1
            else:
                err += 1

        self._log_line(f"--- Done: {ok} OK, {err} failed ---", "hdr")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
