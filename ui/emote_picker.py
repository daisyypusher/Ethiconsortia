"""
ui/emote_picker.py
─────────────────────────────────────────────────────────────
Usage:
    emote_picker.show(anchor_widget, on_select=lambda emoji: ...)
    emote_picker.close()
    emote_picker.lift()

Emoji come from data/emoji.json (Emojibase, MIT). Category tabs on top,
a search box under them, one scrolling grid below.
─────────────────────────────────────────────────────────────
"""
import json
import os
import re
import sys
import tkinter as tk
from tkinter import messagebox

from ui import theme

# Newest Unicode emoji version your Windows can draw. Empty boxes in the
# picker mean this is too high: lower it (12.1 for Windows 10).
MAX_VERSION = 14.0

# Emojibase groups: 0 smileys, 1 people, 3 animals, 4 food, 5 travel,
# 6 activities, 7 objects, 8 symbols. Skipped: 2 (skin-tone parts), 9 (flags,
# which Windows draws as plain letters).
GROUPS = [
    (0, "\U0001F60A"), (1, "\U0001F44D"), (3, "\U0001F436"), (4, "\U0001F354"),
    (5, "\U0001F697"), (6, "\u26BD"), (7, "\U0001F4A1"), (8, "\u2764\uFE0F"),
]
COLS, CELL = 7, 46
PLACEHOLDER = "Search emotes\u2026"
_WORD = re.compile(r"[a-z0-9]+")

_data = None            # loaded once: {"groups": {id: [entry]}, "all": [entry]}
_active_popup = None
_esc_binding = None     # (window, [(sequence, binding id), ...])


def _data_file():
    base = getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "emoji.json")


def _load():
    """Reads data/emoji.json once. Entry = (emoji, label words, all search words)."""
    global _data
    if _data is not None:
        return _data
    with open(_data_file(), encoding="utf-8") as f:
        raw = json.load(f)
    raw.sort(key=lambda e: e.get("order", 0))
    groups = {g: [] for g, _icon in GROUPS}
    everything = []
    for e in raw:
        g, em = e.get("group"), e.get("emoji", "")
        if g not in groups or not em:
            continue
        if e.get("version", 0) > MAX_VERSION:
            continue
        if "\u200d" in em:          # joined emoji: Tk draws them as separate pieces
            continue
        label_words = set(_WORD.findall(e.get("label", "").lower()))
        words = set(label_words)
        for tag in e.get("tags", []):
            words.update(_WORD.findall(tag.lower()))
        entry = (em, label_words, words)
        groups[g].append(entry)
        everything.append(entry)
    _data = {"groups": groups, "all": everything}
    return _data


def _search(query):
    """Every typed word must start a label word or tag. Name matches come first."""
    terms = _WORD.findall(query.lower())
    if not terms:
        return []
    hits = []
    for pos, (em, label_words, words) in enumerate(_load()["all"]):
        if all(any(w.startswith(t) for w in words) for t in terms):
            in_name = all(any(w.startswith(t) for w in label_words) for t in terms)
            hits.append((0 if in_name else 1, pos, em))
    hits.sort()
    return [h[2] for h in hits]


def show(anchor, on_select):
    """Shows (or, on a second call, closes) the emote picker above the anchor.
    It stays open until closed: X button, Esc, the anchor button again, or close()."""
    global _active_popup, _esc_binding

    if _active_popup is not None and _active_popup.winfo_exists():
        close()
        return

    root = anchor.winfo_toplevel()
    try:
        data = _load()
    except (OSError, ValueError) as ex:
        messagebox.showerror("Emoji data missing",
                             f"Can't read data/emoji.json:\n{ex}", parent=root)
        return

    popup = tk.Toplevel(root)
    _active_popup = popup
    popup.overrideredirect(True)
    popup.configure(bg=theme.INPUT_BG)

    main = tk.Frame(popup, bg=theme.INPUT_BG, highlightbackground=theme.SOFT_BLUE,
                    highlightthickness=1)
    main.pack(fill="both", expand=True)

    tab_row = tk.Frame(main, bg=theme.DARK_NAVY)
    tab_row.pack(side="top", fill="x")
    tk.Button(tab_row, text="\u2716", font=theme.font(10, "bold", emoji=True), width=3,
              bg=theme.RED_ACCENT, fg="white", relief="flat", bd=0, cursor="hand2",
              command=close).pack(side="right", fill="y")

    # search box sits above the grid, so the grid can never push it out
    search_var = tk.StringVar(value=PLACEHOLDER)
    search = tk.Entry(main, textvariable=search_var, font=theme.font(11), fg="gray",
                      relief="flat", highlightthickness=1,
                      highlightbackground=theme.SOFT_BLUE)
    search.pack(side="top", fill="x", padx=1, pady=1)

    body = tk.Frame(main, bg=theme.INPUT_BG)
    body.pack(side="top", fill="both", expand=True)
    scroll = tk.Scrollbar(body, orient="vertical")
    scroll.pack(side="right", fill="y")
    canvas = tk.Canvas(body, bg=theme.INPUT_BG, highlightthickness=0, width=COLS * CELL,
                       yscrollincrement=CELL, yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.configure(command=canvas.yview)

    emoji_font = theme.font(18, emoji=True)
    state = {"list": [], "group": GROUPS[0][0]}
    tabs = []

    def draw(emojis):
        canvas.delete("all")
        canvas.create_rectangle(-10, -10, -10, -10, fill="#c8d7f5", outline="", tags="hover")
        state["list"] = emojis
        if not emojis:
            canvas.create_text(COLS * CELL // 2, 50, text="No emoji found",
                               font=theme.font(11, slant="italic"), fill="gray")
        for i, em in enumerate(emojis):
            r, c = divmod(i, COLS)
            canvas.create_text(c * CELL + CELL // 2, r * CELL + CELL // 2,
                               text=em, font=emoji_font)
        rows = max(1, -(-len(emojis) // COLS))
        canvas.configure(scrollregion=(0, 0, COLS * CELL, rows * CELL))
        canvas.yview_moveto(0)

    def show_group(g):
        for (gid, _icon), tab in zip(GROUPS, tabs):
            tab.configure(bg=theme.MEDIUM_BLUE if gid == g else theme.DARK_NAVY)
        draw([e[0] for e in data["groups"][g]])

    def pick_group(g):
        state["group"] = g
        focused = search.focus_get() is search
        search_var.set("" if focused else PLACEHOLDER)
        search.configure(fg=theme.DARK_NAVY if focused else "gray")
        show_group(g)

    for gid, icon in GROUPS:
        tab = tk.Button(tab_row, text=icon, font=theme.font(13, emoji=True),
                        bg=theme.DARK_NAVY, fg="white", relief="flat", bd=0,
                        activebackground=theme.MEDIUM_BLUE, cursor="hand2",
                        command=lambda g=gid: pick_group(g))
        tab.pack(side="left", expand=True, fill="x")
        tabs.append(tab)

    def cell_at(event):
        c = int(canvas.canvasx(event.x) // CELL)
        r = int(canvas.canvasy(event.y) // CELL)
        i = r * COLS + c
        if 0 <= c < COLS and r >= 0 and i < len(state["list"]):
            return i
        return None

    def on_motion(event):
        i = cell_at(event)
        if i is None:
            canvas.coords("hover", -10, -10, -10, -10)
        else:
            r, c = divmod(i, COLS)
            canvas.coords("hover", c * CELL + 2, r * CELL + 2,
                          (c + 1) * CELL - 2, (r + 1) * CELL - 2)

    def on_click(event):
        i = cell_at(event)
        if i is not None:
            on_select(state["list"][i])

    canvas.bind("<Motion>", on_motion)
    canvas.bind("<Leave>", lambda e: canvas.coords("hover", -10, -10, -10, -10))
    canvas.bind("<Button-1>", on_click)

    def scroll_by(event):
        canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def root_wheel(event):
        # the wheel goes to the focused window, so check the pointer is over the grid
        try:
            w = root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return
        while w is not None:
            if w is canvas:
                scroll_by(event)
                return
            w = w.master

    canvas.bind("<MouseWheel>", scroll_by)

    def on_focus_in(_e):
        if search_var.get() == PLACEHOLDER:
            search_var.set("")
            search.configure(fg=theme.DARK_NAVY)

    def on_focus_out(_e):
        if not search_var.get():
            search_var.set(PLACEHOLDER)
            search.configure(fg="gray")

    def on_search_change(*_a):
        q = search_var.get().strip()
        if not q or q == PLACEHOLDER:
            show_group(state["group"])
        else:
            for tab in tabs:
                tab.configure(bg=theme.DARK_NAVY)
            draw(_search(q))

    search.bind("<FocusIn>", on_focus_in)
    search.bind("<FocusOut>", on_focus_out)
    search_var.trace_add("write", on_search_change)

    show_group(state["group"])

    popup.update_idletasks()
    pw, ph = COLS * CELL + 18, 330
    ax = anchor.winfo_rootx()
    ay = anchor.winfo_rooty()
    aw = anchor.winfo_width()
    x = ax + aw - pw
    y = ay - ph - 6
    popup.geometry(f"{pw}x{ph}+{max(0, x)}+{max(0, y)}")

    def on_escape(_e=None):
        close()

    _esc_binding = (root, [
        ("<Escape>", root.bind("<Escape>", on_escape, add="+")),
        ("<FocusIn>", root.bind("<FocusIn>", lambda _e: lift(), add="+")),
        ("<MouseWheel>", root.bind("<MouseWheel>", root_wheel, add="+")),
    ])
    search.bind("<Escape>", on_escape)

    return popup


def close():
    global _active_popup, _esc_binding
    if _esc_binding is not None:
        win, binds = _esc_binding
        for seq, bind_id in binds:
            try:
                win.unbind(seq, bind_id)
            except tk.TclError:
                pass                    # window already gone
        _esc_binding = None
    try:
        if _active_popup is not None and _active_popup.winfo_exists():
            _active_popup.destroy()
    except tk.TclError:
        pass
    _active_popup = None


def lift():
    """Brings the picker back on top (used after each pick, as a safety net)."""
    try:
        if _active_popup is not None and _active_popup.winfo_exists():
            _active_popup.lift()
    except tk.TclError:
        pass