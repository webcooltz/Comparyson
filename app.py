"""Comparyson - compare two directories and inspect file differences side by side.

Usage:  python app.py [DIR1 DIR2]
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import core

APP_NAME = "Comparyson"

LIGHT = {
    "bg": "#f4f5f7", "card": "#ffffff", "border": "#dfe2e8", "fg": "#1c2330",
    "muted": "#6b7486", "accent": "#4f46e5", "accent_fg": "#ffffff",
    "accent_hover": "#4338ca", "hover": "#eceef3", "select": "#e0e7ff",
    "editor": "#ffffff", "gutter": "#f4f5f7", "gutter_fg": "#9aa3b2",
    "del_bg": "#ffe3e3", "add_bg": "#ddf7e3", "chg_bg": "#fff4d1",
    "del_in": "#ffb3b3", "add_in": "#a6e8b8", "chg_in": "#ffd966",
    "pad": "#eef0f4",
    "same": "#6b7486", "modified": "#b7791f", "left_only": "#c53030", "right_only": "#2f855a",
}
DARK = {
    "bg": "#14171d", "card": "#1c2029", "border": "#2c3240", "fg": "#e6e9ef",
    "muted": "#8b94a7", "accent": "#7c83ff", "accent_fg": "#0f1117",
    "accent_hover": "#9aa0ff", "hover": "#262b37", "select": "#2d3354",
    "editor": "#171a22", "gutter": "#1c2029", "gutter_fg": "#5d667a",
    "del_bg": "#3a2024", "add_bg": "#1b3326", "chg_bg": "#3a3220",
    "del_in": "#6b2a30", "add_in": "#2a5a3c", "chg_in": "#6b5a22",
    "pad": "#1d212b",
    "same": "#8b94a7", "modified": "#f6c453", "left_only": "#ff8a8a", "right_only": "#6fdc9a",
}

STATUS_LABEL = {
    core.SAME: "Identical", core.MODIFIED: "Modified",
    core.LEFT_ONLY: "Only in 1", core.RIGHT_ONLY: "Only in 2",
}
FILTER_NAMES = {
    core.MODIFIED: "Modified", core.LEFT_ONLY: "Only in 1",
    core.RIGHT_ONLY: "Only in 2", core.SAME: "Identical",
}


def pick_font(root, candidates, fallback):
    available = set(tkfont.families(root))
    return next((f for f in candidates if f in available), fallback)


class App:
    def __init__(self, root):
        self.root = root
        self.colors = LIGHT
        self.dark = False
        self.entries = []
        self.rows = []
        self.hunks = []
        self.hunk_idx = -1
        self.current = None
        self.scan_queue = queue.Queue()
        self._syncing = False

        self.ui_font = pick_font(root, ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text",
                                        "Helvetica Neue", "Ubuntu", "DejaVu Sans"), "TkDefaultFont")
        self.mono_font = pick_font(root, ("Cascadia Mono", "Consolas", "Menlo",
                                          "DejaVu Sans Mono", "Courier New"), "TkFixedFont")

        root.title(APP_NAME)
        root.geometry("1280x780")
        root.minsize(900, 560)

        self.left_var = tk.StringVar()
        self.right_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.filter_vars = {s: tk.BooleanVar(value=True) for s in FILTER_NAMES}

        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self._build()
        self.apply_theme()

        self.search_var.trace_add("write", lambda *_: self.refresh_tree())
        root.bind("<F5>", lambda e: self.compare())
        root.bind("<Control-Down>", lambda e: self.goto_hunk(1))
        root.bind("<Control-Up>", lambda e: self.goto_hunk(-1))
        root.after(100, self._poll_scan)

    # ------------------------------------------------------------------ layout

    def _build(self):
        root = self.root
        self.outer = ttk.Frame(root, style="App.TFrame", padding=16)
        self.outer.pack(fill="both", expand=True)

        header = ttk.Frame(self.outer, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Directory comparison", style="Subtitle.TLabel").pack(
            side="left", padx=(12, 0), pady=(6, 0))
        self.theme_btn = ttk.Button(header, text="Dark mode", style="Ghost.TButton",
                                    command=self.toggle_theme)
        self.theme_btn.pack(side="right")

        # directory pickers
        card = ttk.Frame(self.outer, style="Card.TFrame", padding=14)
        card.pack(fill="x", pady=(14, 12))
        card.columnconfigure(1, weight=1)
        for row, (label, var) in enumerate((("Directory 1", self.left_var),
                                            ("Directory 2", self.right_var))):
            ttk.Label(card, text=label, style="Card.TLabel").grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4)
            entry = ttk.Entry(card, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=4, ipady=3)
            entry.bind("<Return>", lambda e: self.compare())
            ttk.Button(card, text="Browse...", command=lambda v=var: self.browse(v)).grid(
                row=row, column=2, padx=(8, 0), pady=4)
        actions = ttk.Frame(card, style="Plain.TFrame")
        actions.grid(row=0, column=3, rowspan=2, padx=(16, 0))
        self.compare_btn = ttk.Button(actions, text="Compare", style="Accent.TButton",
                                      command=self.compare)
        self.compare_btn.pack(fill="x")
        ttk.Button(actions, text="Swap", command=self.swap).pack(fill="x", pady=(6, 0))

        # main split
        self.paned = ttk.PanedWindow(self.outer, orient="horizontal")
        self.paned.pack(fill="both", expand=True)
        self._build_sidebar()
        self._build_viewer()

        self.status_var = tk.StringVar(value="Choose two directories to compare.")
        ttk.Label(self.outer, textvariable=self.status_var, style="Status.TLabel").pack(
            fill="x", pady=(10, 0))

    def _build_sidebar(self):
        side = ttk.Frame(self.paned, style="Card.TFrame", padding=10)
        self.paned.add(side, weight=0)

        search = ttk.Entry(side, textvariable=self.search_var)
        search.pack(fill="x", ipady=3)
        self._placeholder(search, self.search_var, "Filter files...")

        chips = ttk.Frame(side, style="Plain.TFrame")
        chips.pack(fill="x", pady=(8, 8))
        self.chip_buttons = {}
        for i, status in enumerate(FILTER_NAMES):
            cb = ttk.Checkbutton(chips, text=FILTER_NAMES[status], variable=self.filter_vars[status],
                                 command=self.refresh_tree, style="Chip.TCheckbutton")
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 10), pady=1)
            self.chip_buttons[status] = cb

        tree_wrap = ttk.Frame(side, style="Plain.TFrame")
        tree_wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_wrap, columns=("status",), selectmode="browse",
                                 style="Files.Treeview")
        self.tree.heading("#0", text="File", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")
        self.tree.column("#0", width=230, minwidth=120)
        self.tree.column("status", width=80, minwidth=70, stretch=False)
        sb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.paned.pane(side, weight=0)
        side.configure(width=340)

    def _placeholder(self, entry, var, text):
        """Show muted hint text in an empty entry (the var stays empty)."""
        def show(_e=None):
            if not var.get() and str(entry.focus_get()) != str(entry):
                entry.configure(style="Hint.TEntry")
                entry.delete(0, "end")
                entry.insert(0, text)
                self._hinted = True

        def hide(_e=None):
            if getattr(self, "_hinted", False):
                self._hinted = False
                entry.delete(0, "end")
                entry.configure(style="TEntry")

        entry.configure(textvariable="")
        entry.bind("<FocusIn>", hide)
        entry.bind("<FocusOut>", lambda e: (var.set(entry.get()), show()))
        entry.bind("<KeyRelease>", lambda e: var.set(entry.get()))
        self._show_hint = show
        show()

    def _build_viewer(self):
        view = ttk.Frame(self.paned, style="Card.TFrame", padding=10)
        self.paned.add(view, weight=1)

        bar = ttk.Frame(view, style="Plain.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        self.file_title = ttk.Label(bar, text="No file selected", style="FileTitle.TLabel")
        self.file_title.pack(side="left")
        self.badge = tk.Label(bar, text="", font=(self.ui_font, 9, "bold"), padx=8, pady=1)
        self.badge.pack(side="left", padx=10)
        nav = ttk.Frame(bar, style="Plain.TFrame")
        nav.pack(side="right")
        self.hunk_label = ttk.Label(nav, text="", style="Muted.TLabel")
        self.hunk_label.pack(side="left", padx=(0, 8))
        self.prev_btn = ttk.Button(nav, text="Prev", width=6, command=lambda: self.goto_hunk(-1))
        self.next_btn = ttk.Button(nav, text="Next", width=6, command=lambda: self.goto_hunk(1))
        self.prev_btn.pack(side="left")
        self.next_btn.pack(side="left", padx=(4, 0))

        self.body = ttk.Frame(view, style="Plain.TFrame")
        self.body.pack(fill="both", expand=True)
        self.body.columnconfigure(1, weight=1)
        self.body.columnconfigure(4, weight=1)
        self.body.rowconfigure(1, weight=1)

        self.head_left = ttk.Label(self.body, text="Directory 1", style="PaneHead.TLabel")
        self.head_right = ttk.Label(self.body, text="Directory 2", style="PaneHead.TLabel")
        self.head_left.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.head_right.grid(row=0, column=3, columnspan=2, sticky="ew")

        mono = (self.mono_font, 10)
        self.gut_l = tk.Text(self.body, width=5, font=mono, wrap="none", borderwidth=0,
                             highlightthickness=0, padx=6, cursor="arrow", takefocus=0)
        self.txt_l = tk.Text(self.body, font=mono, wrap="none", borderwidth=0,
                             highlightthickness=0, padx=8, undo=False)
        self.gut_r = tk.Text(self.body, width=5, font=mono, wrap="none", borderwidth=0,
                             highlightthickness=0, padx=6, cursor="arrow", takefocus=0)
        self.txt_r = tk.Text(self.body, font=mono, wrap="none", borderwidth=0,
                             highlightthickness=0, padx=8, undo=False)
        self.gut_l.grid(row=1, column=0, sticky="ns")
        self.txt_l.grid(row=1, column=1, sticky="nsew")
        self.divider = tk.Frame(self.body, width=1)
        self.divider.grid(row=1, column=2, sticky="ns")
        self.gut_r.grid(row=1, column=3, sticky="ns")
        self.txt_r.grid(row=1, column=4, sticky="nsew")

        self.vbar = ttk.Scrollbar(self.body, orient="vertical", command=self._yview)
        self.vbar.grid(row=1, column=5, sticky="ns")
        self.hbar_l = ttk.Scrollbar(self.body, orient="horizontal", command=self.txt_l.xview)
        self.hbar_r = ttk.Scrollbar(self.body, orient="horizontal", command=self.txt_r.xview)
        self.hbar_l.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.hbar_r.grid(row=2, column=3, columnspan=2, sticky="ew")
        self.txt_l.configure(xscrollcommand=self.hbar_l.set, yscrollcommand=self._on_yscroll)
        self.txt_r.configure(xscrollcommand=self.hbar_r.set, yscrollcommand=self._on_yscroll)
        self.gut_l.configure(yscrollcommand=self._on_yscroll)
        self.gut_r.configure(yscrollcommand=self._on_yscroll)

        self.panes = (self.gut_l, self.txt_l, self.gut_r, self.txt_r)
        tab_w = tkfont.Font(font=mono).measure("    ")
        for w in self.panes:
            w.configure(tabs=(tab_w,))
            w.bind("<MouseWheel>", self._on_wheel)
            w.bind("<Button-4>", lambda e: self._scroll_lines(-3))
            w.bind("<Button-5>", lambda e: self._scroll_lines(3))
        for w in (self.txt_l, self.txt_r):
            w.bind("<Button-1>", lambda e: e.widget.focus_set())
            w.bind("<Key>", self._block_edit)
            w.bind("<<Paste>>", lambda e: "break")
            w.bind("<<Cut>>", lambda e: "break")
        for w in (self.gut_l, self.gut_r):
            w.bind("<Button-1>", lambda e: "break")
            w.bind("<B1-Motion>", lambda e: "break")

        self.message = tk.Label(self.body, text="Select a file to see its differences",
                                font=(self.ui_font, 11))
        self.message.place(relx=0, rely=0, relwidth=1, relheight=1)

    # ------------------------------------------------------------------- theme

    def apply_theme(self):
        c = self.colors
        s = self.style
        ui = self.ui_font
        self.root.configure(bg=c["bg"])
        s.configure(".", font=(ui, 10), background=c["bg"], foreground=c["fg"],
                    bordercolor=c["border"], focuscolor=c["card"])
        s.configure("App.TFrame", background=c["bg"])
        s.configure("Plain.TFrame", background=c["card"])
        s.configure("Card.TFrame", background=c["card"], bordercolor=c["border"], relief="solid",
                    borderwidth=1)
        s.configure("TLabel", background=c["bg"], foreground=c["fg"])
        s.configure("Title.TLabel", font=(ui, 20, "bold"), background=c["bg"])
        s.configure("Subtitle.TLabel", foreground=c["muted"], background=c["bg"])
        s.configure("Card.TLabel", background=c["card"], foreground=c["muted"])
        s.configure("Muted.TLabel", background=c["card"], foreground=c["muted"])
        s.configure("Hint.TLabel", background=c["card"], foreground=c["muted"])
        s.configure("Status.TLabel", background=c["bg"], foreground=c["muted"])
        s.configure("FileTitle.TLabel", font=(ui, 12, "bold"), background=c["card"])
        s.configure("PaneHead.TLabel", background=c["card"], foreground=c["muted"],
                    font=(ui, 9, "bold"), padding=(8, 0, 0, 6))

        s.configure("TButton", background=c["card"], foreground=c["fg"], bordercolor=c["border"],
                    padding=(14, 6), relief="flat", borderwidth=1,
                    lightcolor=c["border"], darkcolor=c["border"])
        s.map("TButton", background=[("active", c["hover"]), ("disabled", c["card"])],
              foreground=[("disabled", c["muted"])])
        s.configure("Accent.TButton", background=c["accent"], foreground=c["accent_fg"],
                    bordercolor=c["accent"], lightcolor=c["accent"], darkcolor=c["accent"],
                    padding=(18, 8), font=(ui, 10, "bold"))
        s.map("Accent.TButton", background=[("active", c["accent_hover"]),
                                            ("disabled", c["border"])],
              bordercolor=[("active", c["accent_hover"])],
              lightcolor=[("active", c["accent_hover"])],
              darkcolor=[("active", c["accent_hover"])])
        s.configure("Ghost.TButton", background=c["bg"], bordercolor=c["bg"], lightcolor=c["bg"],
                    darkcolor=c["bg"], foreground=c["muted"])
        s.map("Ghost.TButton", background=[("active", c["hover"])],
              bordercolor=[("active", c["hover"])])

        s.configure("TEntry", fieldbackground=c["editor"], foreground=c["fg"],
                    bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"],
                    insertcolor=c["fg"], padding=(6, 2))
        s.configure("Hint.TEntry", foreground=c["muted"])
        s.map("TEntry", bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["accent"])],
              darkcolor=[("focus", c["accent"])])

        s.configure("Chip.TCheckbutton", background=c["card"], foreground=c["fg"])
        s.map("Chip.TCheckbutton", background=[("active", c["card"])],
              indicatorcolor=[("selected", c["accent"]), ("!selected", c["editor"])])

        s.configure("Files.Treeview", background=c["card"], fieldbackground=c["card"],
                    foreground=c["fg"], rowheight=28, borderwidth=0, bordercolor=c["card"],
                    lightcolor=c["card"], darkcolor=c["card"])
        s.map("Files.Treeview", background=[("selected", c["select"])],
              foreground=[("selected", c["fg"])])
        s.configure("Treeview.Heading", background=c["card"], foreground=c["muted"],
                    relief="flat", font=(ui, 9, "bold"), padding=(6, 4))
        s.map("Treeview.Heading", background=[("active", c["card"])])
        for status in STATUS_LABEL:
            self.tree.tag_configure(status, foreground=c[status])
        self.tree.tag_configure("dir", foreground=c["muted"])

        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar", background=c["border"], troughcolor=c["card"],
                        bordercolor=c["card"], arrowcolor=c["muted"], gripcount=0,
                        lightcolor=c["border"], darkcolor=c["border"])
            s.map(f"{orient}.TScrollbar", background=[("active", c["muted"])])
        s.configure("TPanedwindow", background=c["bg"])
        s.configure("Sash", sashthickness=10, background=c["bg"])

        for w in (self.txt_l, self.txt_r):
            w.configure(bg=c["editor"], fg=c["fg"], insertbackground=c["fg"],
                        selectbackground=c["select"], selectforeground=c["fg"],
                        inactiveselectbackground=c["select"])
        for w in (self.gut_l, self.gut_r):
            w.configure(bg=c["gutter"], fg=c["gutter_fg"], selectbackground=c["gutter"])
        self.divider.configure(bg=c["border"])
        self.message.configure(bg=c["editor"], fg=c["muted"])
        self._configure_tags()
        if self.current:
            self._set_badge(self.current.status)
        self.theme_btn.configure(text="Light mode" if self.dark else "Dark mode")

    def _configure_tags(self):
        c = self.colors
        for w, row_bg in ((self.txt_l, c["del_bg"]), (self.txt_r, c["add_bg"])):
            w.tag_configure("row", background=row_bg)
            w.tag_configure("chg", background=c["chg_bg"])
            w.tag_configure("pad", background=c["pad"])
        for w in (self.gut_l, self.gut_r):
            w.tag_configure("row", background=c["chg_bg"])
            w.tag_configure("pad", background=c["pad"])
        for w in (self.txt_l, self.txt_r):
            w.tag_configure("chg_in", background=c["chg_in"])
            w.tag_raise("chg_in")
            w.tag_raise("sel")

    def toggle_theme(self):
        self.dark = not self.dark
        self.colors = DARK if self.dark else LIGHT
        self.apply_theme()

    # -------------------------------------------------------------- scrolling

    def _yview(self, *args):
        for w in self.panes:
            w.yview(*args)

    def _on_yscroll(self, first, last):
        self.vbar.set(first, last)
        if self._syncing:
            return
        self._syncing = True
        try:
            for w in self.panes:
                w.yview_moveto(first)
        finally:
            self._syncing = False

    def _on_wheel(self, event):
        step = -1 if event.delta > 0 else 1
        self._scroll_lines(step * 3)
        return "break"

    def _scroll_lines(self, n):
        self.txt_l.yview_scroll(n, "units")
        return "break"

    @staticmethod
    def _block_edit(event):
        ctrl = event.state & 0x4
        if ctrl and event.keysym.lower() in ("c", "a"):
            if event.keysym.lower() == "a":
                event.widget.tag_add("sel", "1.0", "end")
                return "break"
            return None
        if event.keysym in ("Up", "Down", "Left", "Right", "Prior", "Next", "Home", "End"):
            return None
        return "break"

    # ------------------------------------------------------------------ actions

    def browse(self, var):
        start = var.get() if os.path.isdir(var.get()) else os.path.expanduser("~")
        chosen = filedialog.askdirectory(initialdir=start, mustexist=True)
        if chosen:
            var.set(os.path.normpath(chosen))

    def swap(self):
        a, b = self.left_var.get(), self.right_var.get()
        self.left_var.set(b)
        self.right_var.set(a)
        if a and b:
            self.compare()

    def compare(self):
        left = self.left_var.get().strip().strip('"')
        right = self.right_var.get().strip().strip('"')
        if not left or not right:
            messagebox.showinfo(APP_NAME, "Choose both directories first.")
            return
        for label, path in (("Directory 1", left), ("Directory 2", right)):
            if not os.path.isdir(path):
                messagebox.showerror(APP_NAME, f"{label} is not a valid directory:\n{path}")
                return
        if os.path.normcase(os.path.realpath(left)) == os.path.normcase(os.path.realpath(right)):
            messagebox.showwarning("Invalid selection", "Directory 2 cannot be the same as Directory 1.")
            return
        self.left_root, self.right_root = left, right
        self.compare_btn.state(["disabled"])
        self.status_var.set("Scanning...")

        def work():
            try:
                self.scan_queue.put(("ok", core.scan(left, right)))
            except Exception as exc:  # surfaced to the UI thread
                self.scan_queue.put(("err", exc))

        threading.Thread(target=work, daemon=True).start()

    def _poll_scan(self):
        try:
            kind, payload = self.scan_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.compare_btn.state(["!disabled"])
            if kind == "err":
                self.status_var.set("Comparison failed.")
                messagebox.showerror(APP_NAME, str(payload))
            else:
                self._load_entries(payload)
        self.root.after(100, self._poll_scan)

    def _load_entries(self, entries):
        self.entries = entries
        counts = {s: 0 for s in FILTER_NAMES}
        for e in entries:
            counts[e.status] += 1
        for status, cb in self.chip_buttons.items():
            cb.configure(text=f"{FILTER_NAMES[status]} ({counts[status]})")
        self.head_left.configure(text=f"Directory 1  -  {self.left_root}")
        self.head_right.configure(text=f"Directory 2  -  {self.right_root}")
        self.clear_viewer("Select a file to see its differences")
        self.refresh_tree()
        differing = counts[core.MODIFIED] + counts[core.LEFT_ONLY] + counts[core.RIGHT_ONLY]
        if not entries:
            self.status_var.set("Both directories are empty.")
        elif differing == 0:
            self.status_var.set(f"{len(entries)} files compared - directories are identical.")
        else:
            self.status_var.set(
                f"{len(entries)} files compared - {counts[core.MODIFIED]} modified, "
                f"{counts[core.LEFT_ONLY]} only in 1, {counts[core.RIGHT_ONLY]} only in 2, "
                f"{counts[core.SAME]} identical.")
        first = next((e for e in entries if e.status == core.MODIFIED), None)
        if first and self.tree.exists("f:" + first.rel):
            self.tree.selection_set("f:" + first.rel)
            self.tree.see("f:" + first.rel)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        needle = self.search_var.get().strip().lower()
        for e in self.entries:
            if not self.filter_vars[e.status].get() or needle not in e.rel.lower():
                continue
            parent = ""
            parts = e.rel.split("/")
            for i in range(len(parts) - 1):
                iid = "d:" + "/".join(parts[:i + 1])
                if not self.tree.exists(iid):
                    self.tree.insert(parent, "end", iid, text=parts[i], open=True, tags=("dir",))
                parent = iid
            self.tree.insert(parent, "end", "f:" + e.rel, text=parts[-1],
                             values=(STATUS_LABEL[e.status],), tags=(e.status,))
        if self.current and self.tree.exists("f:" + self.current.rel):
            self.tree.selection_set("f:" + self.current.rel)

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel or not sel[0].startswith("f:"):
            return
        rel = sel[0][2:]
        entry = next((e for e in self.entries if e.rel == rel), None)
        if entry:
            self.show_entry(entry)

    # ------------------------------------------------------------------ viewer

    def _set_badge(self, status):
        self.badge.configure(text=STATUS_LABEL[status], bg=self.colors["select"],
                             fg=self.colors[status])

    def clear_viewer(self, msg):
        self.current = None
        self.file_title.configure(text="No file selected")
        self.badge.configure(text="", bg=self.colors["card"])
        self.hunk_label.configure(text="")
        self.rows, self.hunks, self.hunk_idx = [], [], -1
        for w in self.panes:
            w.delete("1.0", "end")
        self.message.configure(text=msg)
        self.message.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show_entry(self, entry):
        self.current = entry
        self.file_title.configure(text=entry.rel)
        self._set_badge(entry.status)
        lp = os.path.join(self.left_root, entry.rel)
        rp = os.path.join(self.right_root, entry.rel)
        left, lnote = core.read_lines(lp)
        right, rnote = core.read_lines(rp)
        note = lnote or rnote
        if left is None or right is None:
            self.rows, self.hunks, self.hunk_idx = [], [], -1
            for w in self.panes:
                w.delete("1.0", "end")
            self.hunk_label.configure(text="")
            self.message.configure(text=note)
            self.message.place(relx=0, rely=0, relwidth=1, relheight=1)
            return
        self.message.place_forget()
        self.rows = core.align(left, right)
        self.hunks = core.hunk_starts(self.rows)
        self.hunk_idx = -1
        self._render()
        if entry.status == core.SAME:
            self.hunk_label.configure(text="No differences")
        elif self.hunks:
            self.goto_hunk(1)
        else:
            self.hunk_label.configure(text="")

    def _render(self):
        for w in self.panes:
            w.configure(state="normal")
            w.delete("1.0", "end")
        width = max(3, len(str(len(self.rows))))
        self.gut_l.configure(width=width + 1)
        self.gut_r.configure(width=width + 1)
        last = len(self.rows) - 1
        for i, row in enumerate(self.rows):
            ln = i + 1
            nl = "\n" if i < last else ""
            self._put_side(self.txt_l, self.gut_l, row.left_no, row.left, row.tag, "delete",
                           row.left_spans, ln, nl, width)
            self._put_side(self.txt_r, self.gut_r, row.right_no, row.right, row.tag, "insert",
                           row.right_spans, ln, nl, width)
        for w in self.gut_l, self.gut_r:
            w.configure(state="disabled")
        self.txt_l.yview_moveto(0)

    def _put_side(self, txt, gut, no, text, tag, solo_tag, spans, ln, nl, width):
        if text is None:
            txt.insert("end", nl, "pad")
            gut.insert("end", " " * width + nl, "pad")
            return
        gut.insert("end", str(no).rjust(width) + nl, "row" if tag != "equal" else "")
        if tag == "equal":
            txt.insert("end", text + nl)
        elif tag == solo_tag:
            txt.insert("end", text + nl, "row")
        else:
            txt.insert("end", text + nl, "chg")
            for s, e in spans:
                txt.tag_add("chg_in", f"{ln}.{s}", f"{ln}.{e}")

    def goto_hunk(self, step):
        if not self.hunks or not self.current:
            return
        self.hunk_idx = (self.hunk_idx + step) % len(self.hunks)
        row = self.hunks[self.hunk_idx]
        total = max(1, len(self.rows))
        self.txt_l.yview_moveto(max(0, row - 3) / total)
        self.hunk_label.configure(text=f"Change {self.hunk_idx + 1} of {len(self.hunks)}")


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    app = App(root)
    if len(sys.argv) >= 3:
        app.left_var.set(os.path.normpath(sys.argv[1]))
        app.right_var.set(os.path.normpath(sys.argv[2]))
        root.after(50, app.compare)
    root.mainloop()


if __name__ == "__main__":
    main()
