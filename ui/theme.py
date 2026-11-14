"""
theme.py
─────────────────────────────────────────────────────────────
Shared color palette, fonts and small reusable widget helpers
used across every screen of Ethiconsortia
─────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import font as tkfont

# ── Colors (ported 1:1 from the Java Color constants) ──────────────────────
DARK_NAVY = "#1c2951"
DARKER_NAVY = "#141e41"
MEDIUM_BLUE = "#3d5a99"
SOFT_BLUE = "#96afdc"
RED_ACCENT = "#b41414"
INPUT_BG = "#f0f5ff"
SUCCESS = "#1ea050"
WARN_YELLOW = "#dca000"
WARN_ORANGE = "#c86400"

CHAT_BG = "#f0f5ff"
MSG_THEM_BG = "#ffffff"
MSG_YOU_BG = "#dce6ff"
RIGHT_BG = "#dce6f8"
ROOM_CARD_BG = "#2d4173"
ROOMS_BG = "#233260"
GREEN_BTN = "#327850"
GREEN_ON = "#32b450"
SUB_ROOM_BG = "#233260"
DM_COLOR = "#500078"
DM_BADGE_BG = "#6e28b4"

FONT_FAMILY = "Segoe UI" if tk._default_root is None else "Segoe UI"
EMOJI_FONT_FAMILY = "Segoe UI Emoji"


def font(size=11, weight="normal", slant="roman", emoji=False):
    """Returns a tkfont.Font tuple-like object matching the requested style."""
    family = EMOJI_FONT_FAMILY if emoji else "Arial"
    return tkfont.Font(family=family, size=size, weight=weight, slant=slant)


def darker(hex_color, factor=0.7):
    """Returns a darker version of a hex color (mimics Java's Color.darker())."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = int(r * factor), int(g * factor), int(b * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def add_hover(widget, normal_bg, hover_bg):
    """Adds a simple hover-color effect to a button-like widget."""
    widget.bind("<Enter>", lambda e: widget.configure(bg=hover_bg))
    widget.bind("<Leave>", lambda e: widget.configure(bg=normal_bg))


def make_button(parent, text, bg, fg="white", hover_bg=None, font_size=12,
                 bold=True, command=None, emoji=False, cursor="hand2", **kw):
    """Creates a flat, hover-highlighted button matching the app's style."""
    f = font(font_size, "bold" if bold else "normal", emoji=emoji)
    btn = tk.Button(
        parent, text=text, bg=bg, fg=fg, font=f, relief="flat",
        activebackground=hover_bg or darker(bg), activeforeground=fg,
        cursor=cursor, bd=0, highlightthickness=1,
        highlightbackground=darker(bg), command=command, **kw
    )
    if hover_bg:
        add_hover(btn, bg, hover_bg)
    return btn


def placeholder_entry(parent, placeholder, show=None, font_obj=None,
                       fg=DARK_NAVY, placeholder_fg="gray", bg="white"):
    """
    Creates an Entry that shows greyed-out placeholder text until focused,
    mirroring the focus listener trick used throughout the Java UI.
    """
    entry = tk.Entry(parent, font=font_obj or font(12), fg=placeholder_fg,
                      bg=bg, relief="solid", bd=1,
                      highlightthickness=1, highlightbackground=SOFT_BLUE,
                      insertbackground=fg)
    entry.insert(0, placeholder)
    entry._is_placeholder = True
    entry._placeholder = placeholder
    entry._real_fg = fg
    entry._show_char = show

    def on_focus_in(_e):
        if entry._is_placeholder:
            entry.delete(0, tk.END)
            entry.configure(fg=entry._real_fg)
            if entry._show_char:
                entry.configure(show=entry._show_char)
            entry._is_placeholder = False

    def on_focus_out(_e):
        if not entry.get():
            entry.configure(fg=placeholder_fg)
            if entry._show_char:
                entry.configure(show="")
            entry.insert(0, entry._placeholder)
            entry._is_placeholder = True

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    return entry


def add_password_toggle(entry, x, y, width, height, btn_width=32, hide_char="\u2022"):
    """
    Places `entry` (an already-created password Entry, using show=hide_char)
    at (x, y) but narrower — leaving room on the right for a small eye-icon
    button that toggles the password between hidden and visible.

    Usage:
        self.txt_password = tk.Entry(card, font=theme.font(13), fg=theme.DARK_NAVY,
                                      bg="white", relief="solid", bd=1, show="\u2022", ...)
        theme.add_password_toggle(self.txt_password, 20, 120, 280, 35)
        # (do NOT call .place() on the entry yourself — the helper does it)

    Returns the toggle Button widget.
    """
    parent = entry.master
    entry.configure(show=hide_char)
    entry.place(x=x, y=y, width=width - btn_width, height=height)

    state = {"visible": False}

    btn = tk.Button(parent, text="\U0001F441", font=font(12, emoji=True),
                     fg="gray", bg="white", relief="solid", bd=1,
                     highlightthickness=1, highlightbackground=SOFT_BLUE,
                     activebackground="#eef3ff", cursor="hand2")

    def toggle():
        state["visible"] = not state["visible"]
        entry.configure(show="" if state["visible"] else hide_char)
        btn.configure(text="\U0001F576" if state["visible"] else "\U0001F441")

    btn.configure(command=toggle)
    btn.place(x=x + width - btn_width, y=y, width=btn_width, height=height)
    return btn


def entry_value(entry):
    """Returns '' for a placeholder-entry still showing its placeholder."""
    if getattr(entry, "_is_placeholder", False):
        return ""
    return entry.get().strip()


class RoundedCanvas(tk.Canvas):
    """A small Canvas subclass with a helper for drawing rounded rectangles,
    used for chat bubbles and circular avatar/icon badges."""

    def rounded_rect(self, x1, y1, x2, y2, radius=14, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def circle(self, cx, cy, r, **kwargs):
        return self.create_oval(cx - r, cy - r, cx + r, cy + r, **kwargs)

def draw_room_icon(canvas, name, logo_b64, size, radius, font_size=18):
    """Draws a room's logo on a RoundedCanvas. No logo (or a broken one) -> the
    coloured tile with the first letter of the room name."""
    canvas.delete("all")
    photo = None
    if logo_b64:
        from ui import image_message_handler as imh
        photo = imh.make_logo_photo(logo_b64, size, radius)
    if photo:
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas._logo_ref = photo        # Tk drops the image if nothing holds it
    else:
        canvas.rounded_rect(0, 0, size, size, radius=radius, fill=MEDIUM_BLUE, outline="")
        canvas.create_text(size // 2, size // 2, text=name[0].upper(), fill="white",
                           font=font(font_size, "bold"))

def role_badge(role):
    return {"professor": "[Professor]", "admin": "[Admin]"}.get(role, "[Student]")


def role_label(role):
    return {"professor": "Professor", "admin": "Administrator"}.get(role, "Student")


def role_emoji(role):
    return {"professor": "\U0001F468\u200D\U0001F3EB", "admin": "\U0001F6E1"}.get(role, "\U0001F393")


def role_color(role):
    return {"professor": "#1e82b4", "admin": "#961e1e"}.get(role, "#3c783c")

def fmt_time(dt):
    """12-hour time without a leading zero, e.g. 1:00 PM."""
    return dt.strftime("%I:%M %p").lstrip("0")


def fmt_datetime(dt):
    """e.g. 2026-11-12 1:00 PM"""
    return f"{dt.strftime('%Y-%m-%d')} {fmt_time(dt)}"