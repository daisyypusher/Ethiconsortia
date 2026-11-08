"""
ui/emote_picker.py
─────────────────────────────────────────────────────────────
Usage:
    EmotePicker.show(anchor_widget, on_select=lambda emoji: ...)
─────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import font as tkfont

from ui import theme

CAT_NAMES = ["\U0001F60A Faces", "\U0001F44D Gestures", "\u2764\uFE0F Hearts",
             "\U0001F389 Celebrate", "\U0001F4DA School", "\U0001F31F Misc"]

CAT_EMOTES = [
    # Faces
    ["\U0001F60A", "\U0001F602", "\U0001F60D", "\U0001F97A", "\U0001F60E", "\U0001F62D",
     "\U0001F914", "\U0001F605", "\U0001F601", "\U0001F973",
     "\U0001F622", "\U0001F624", "\U0001F929", "\U0001F60F", "\U0001F61C", "\U0001F917",
     "\U0001F636", "\U0001F62C", "\U0001F644", "\U0001F634"],
    # Gestures
    ["\U0001F44D", "\U0001F44E", "\U0001F44F", "\U0001F64C", "\U0001F91D", "\u270C\uFE0F",
     "\U0001F91E", "\U0001F44B", "\U0001F919", "\U0001F4AA",
     "\U0001FAF6", "\U0001F91C", "\U0001F91B", "\U0001F44C", "\U0001F90C", "\U0001FAE1",
     "\U0001FAC2", "\U0001F64F", "\U0001F448", "\U0001F446"],
    # Hearts
    ["\u2764\uFE0F", "\U0001F9E1", "\U0001F49B", "\U0001F49A", "\U0001F499", "\U0001F49C",
     "\U0001F5A4", "\U0001F90D", "\U0001F495", "\U0001F49E",
     "\U0001F493", "\U0001F497", "\U0001F496", "\U0001F49D", "\U0001F498", "\u2763\uFE0F",
     "\U0001F494", "\U0001FAC0", "\u2665\uFE0F", "\u2764\uFE0F\u200D\U0001F525"],
    # Celebrate
    ["\U0001F389", "\U0001F38A", "\U0001F973", "\U0001F388", "\U0001F381", "\U0001F3C6",
     "\U0001F947", "\U0001F3AF", "\U0001F386", "\U0001F387",
     "\u2728", "\U0001F31F", "\u2B50", "\U0001F308", "\U0001F380", "\U0001F397\uFE0F",
     "\U0001F396\uFE0F", "\U0001F3AE", "\U0001F3B8", "\U0001F3BA"],
    # School
    ["\U0001F4DA", "\U0001F4D6", "\u270F\uFE0F", "\U0001F4DD", "\U0001F58A\uFE0F", "\U0001F4D0",
     "\U0001F4CF", "\U0001F52C", "\U0001F52D", "\U0001F9EA",
     "\U0001F9EC", "\U0001F4A1", "\U0001F4CA", "\U0001F4C8", "\U0001F5A5\uFE0F", "\U0001F4BB",
     "\U0001F5A8\uFE0F", "\U0001F4D3", "\U0001F3EB", "\U0001F393"],
    # Misc
    ["\U0001F30D", "\U0001F319", "\u2600\uFE0F", "\U0001F30A", "\U0001F525", "\U0001F4A5",
     "\u26A1", "\u2744\uFE0F", "\U0001F338", "\U0001F340",
     "\U0001F436", "\U0001F431", "\U0001F98A", "\U0001F43C", "\U0001F981", "\U0001F355",
     "\U0001F354", "\u2615", "\U0001F3B5", "\U0001F680"],
]

_active_popup = None


def show(anchor, on_select):
    """Shows (or, on a second call, closes) the categorized emote picker
    positioned above the given anchor widget."""
    global _active_popup

    if _active_popup is not None and _active_popup.winfo_exists():
        _active_popup.destroy()
        _active_popup = None
        return

    root = anchor.winfo_toplevel()
    popup = tk.Toplevel(root)
    _active_popup = popup
    popup.overrideredirect(True)
    popup.configure(bg=theme.INPUT_BG)

    main = tk.Frame(popup, bg=theme.INPUT_BG, highlightbackground=theme.SOFT_BLUE,
                     highlightthickness=1)
    main.pack(fill="both", expand=True)

    tab_row = tk.Frame(main, bg=theme.DARK_NAVY)
    tab_row.pack(side="top", fill="x")

    cards = tk.Frame(main, bg=theme.INPUT_BG)
    cards.pack(side="top", fill="both", expand=True)

    card_frames = {}
    tabs = []

    def show_card(key):
        for f in card_frames.values():
            f.pack_forget()
        card_frames[key].pack(fill="both", expand=True)
        for i, t in enumerate(tabs):
            t.configure(bg=theme.MEDIUM_BLUE if str(i) == key else theme.DARK_NAVY)

    for c, cat in enumerate(CAT_NAMES):
        tab = tk.Button(tab_row, text=cat.split(" ")[0], font=theme.font(14, emoji=True),
                         bg=theme.DARK_NAVY, fg="white", relief="flat", bd=0,
                         activebackground=theme.MEDIUM_BLUE, cursor="hand2",
                         command=lambda k=str(c): show_card(k))
        tab.pack(side="left", expand=True, fill="x")
        tabs.append(tab)

        grid_frame = tk.Frame(cards, bg=theme.INPUT_BG)
        card_frames[str(c)] = grid_frame

        for i, emote in enumerate(CAT_EMOTES[c]):
            btn = tk.Label(grid_frame, text=emote, font=theme.font(20, emoji=True),
                            bg=theme.INPUT_BG, width=2, height=1, cursor="hand2")
            btn.grid(row=i // 5, column=i % 5, padx=1, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#c8d7f5"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=theme.INPUT_BG))
            btn.bind("<Button-1>", lambda e, em=emote: on_select(em))

    # Search bar
    search_var = tk.StringVar(value="Search emotes\u2026")
    search = tk.Entry(main, textvariable=search_var, font=theme.font(11), fg="gray",
                       relief="flat", highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
    search.pack(side="bottom", fill="x", padx=1, pady=1)

    search_grid = tk.Frame(cards, bg=theme.INPUT_BG)
    card_frames["search"] = search_grid
    all_emotes = [e for cat in CAT_EMOTES for e in cat]
    for i, emote in enumerate(all_emotes):
        btn = tk.Label(search_grid, text=emote, font=theme.font(20, emoji=True),
                        bg=theme.INPUT_BG, width=2, height=1, cursor="hand2")
        btn.grid(row=i // 5, column=i % 5, padx=1, pady=1)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#c8d7f5"))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=theme.INPUT_BG))
        btn.bind("<Button-1>", lambda e, em=emote: on_select(em))

    def on_focus_in(_e):
        if search_var.get() == "Search emotes\u2026":
            search_var.set("")
            search.configure(fg=theme.DARK_NAVY)

    def on_focus_out(_e):
        if not search_var.get():
            search_var.set("Search emotes\u2026")
            search.configure(fg="gray")

    def on_search_change(*_a):
        q = search_var.get().strip()
        if not q or q == "Search emotes\u2026":
            show_card("0")
        else:
            show_card("search")

    search.bind("<FocusIn>", on_focus_in)
    search.bind("<FocusOut>", on_focus_out)
    search_var.trace_add("write", on_search_change)

    show_card("0")

    popup.update_idletasks()
    pw, ph = 340, 290
    ax = anchor.winfo_rootx()
    ay = anchor.winfo_rooty()
    aw = anchor.winfo_width()
    x = ax + aw - pw
    y = ay - ph - 6
    popup.geometry(f"{pw}x{ph}+{max(0, x)}+{max(0, y)}")

    def close_on_click_outside(event):
        try:
            if popup.winfo_exists():
                wx, wy = popup.winfo_rootx(), popup.winfo_rooty()
                ww, wh = popup.winfo_width(), popup.winfo_height()
                if not (wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh):
                    popup.destroy()
        except tk.TclError:
            pass

    root.bind_all("<Button-1>", close_on_click_outside, add="+")


def close():
    global _active_popup
    if _active_popup is not None and _active_popup.winfo_exists():
        _active_popup.destroy()
    _active_popup = None
