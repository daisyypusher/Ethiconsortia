"""
ui/image_message_handler.py
─────────────────────────────────────────────────────────────
"""
import base64
import io
import tkinter as tk
from tkinter import filedialog, messagebox
import mimetypes
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageTk

MAX_PREVIEW_PX = 320
MAX_BYTES = 5 * 1024 * 1024
ACCEPT_EXT = [("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp")]
MAX_ATTACH_BYTES = 10 * 1024 * 1024  # 10 MB for any file/video


def choose_image_file(parent):
    """Opens a file chooser; returns the file path or None if cancelled/invalid."""
    path = filedialog.askopenfilename(parent=parent, title="Choose an Image to Send",
                                       filetypes=ACCEPT_EXT)
    if not path:
        return None
    import os
    if os.path.getsize(path) > MAX_BYTES:
        messagebox.showwarning(
            "Image Too Large",
            "File is too large (max 5 MB). Please choose a smaller image.",
            parent=parent,
        )
        return None
    return path


def scale_image(img: Image.Image, max_px: int) -> Image.Image:
    """Proportionally scales a PIL Image so neither dimension exceeds max_px."""
    w, h = img.size
    if w <= max_px and h <= max_px:
        return img
    scale = max_px / max(w, h)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return img.resize(new_size, Image.LANCZOS)


def file_to_base64(path: str) -> str:
    """Reads an image file, scales it, and returns Base64-encoded PNG bytes."""
    img = Image.open(path).convert("RGBA")
    scaled = scale_image(img, MAX_PREVIEW_PX)
    buf = io.BytesIO()
    scaled.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def file_to_base64_raw(path: str) -> str:
    """Reads raw file bytes (no re-encode) and returns Base64 text —
    matches the 'mime|base64' storage format used by ChatFrame/RoomFrame."""
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii")


def guess_mime(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


def decode_base64_image(b64_data: str):
    """Decodes a Base64 string (optionally 'mime|base64') to a PIL Image, or None."""
    try:
        if "|" in b64_data:
            b64_data = b64_data.split("|", 1)[1]
        raw = base64.b64decode(b64_data)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        return None


def make_photo(img: Image.Image, max_w=260, max_h=200):
    """Scales a PIL image to fit within max_w/max_h and returns a PhotoImage.
    The caller MUST keep a reference to the returned PhotoImage (Tk quirk)."""
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    resized = img.resize(new_size, Image.LANCZOS)
    return ImageTk.PhotoImage(resized)


def show_full_image(parent, img: Image.Image):
    """Opens a scrollable dialog showing the full-resolution image."""
    dialog = tk.Toplevel(parent)
    dialog.title("Image")
    dialog.transient(parent)
    dialog.grab_set()

    screen_w = dialog.winfo_screenwidth()
    screen_h = dialog.winfo_screenheight()
    max_w, max_h = int(screen_w * 0.85), int(screen_h * 0.85)

    display = scale_image(img, min(max_w, max_h))
    photo = ImageTk.PhotoImage(display)

    canvas = tk.Canvas(dialog, width=display.width, height=display.height,
                        highlightthickness=0)
    canvas.pack(padx=10, pady=10)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    canvas.image = photo  # keep reference

    close_btn = tk.Button(dialog, text="Close", command=dialog.destroy)
    close_btn.pack(pady=(0, 10))

    dialog.update_idletasks()
    px = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(0, px)}+{max(0, py)}")

# ── Generic attachments (files / videos) ────────────────────────────────────
def choose_attachment(parent):
    """Opens a file chooser for ANY file type; returns the path or None."""
    path = filedialog.askopenfilename(parent=parent, title="Choose a file to send")
    if not path:
        return None
    if os.path.getsize(path) > MAX_ATTACH_BYTES:
        messagebox.showwarning(
            "File Too Large",
            f"File is too large (max {MAX_ATTACH_BYTES // (1024 * 1024)} MB).",
            parent=parent,
        )
        return None
    return path


def guess_mime_any(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def encode_attachment(path: str) -> str:
    """Returns 'mime|filename|base64' for files and videos."""
    with open(path, "rb") as f:
        data = f.read()
    name = os.path.basename(path).replace("|", "_")
    return f"{guess_mime_any(path)}|{name}|{base64.b64encode(data).decode('ascii')}"


def decode_attachment(content: str):
    """Returns (mime, filename, raw_bytes) or None if the data is broken."""
    try:
        mime, name, b64 = content.split("|", 2)
        return mime, name, base64.b64decode(b64)
    except Exception:
        return None


def open_attachment(content: str):
    """Writes the attachment to a temp file and opens it with the default app."""
    att = decode_attachment(content)
    if not att:
        return
    _mime, name, data = att
    tmp_dir = tempfile.mkdtemp(prefix="ethic_")
    path = os.path.join(tmp_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def save_attachment(parent, content: str):
    """Lets the user save the attachment anywhere."""
    att = decode_attachment(content)
    if not att:
        return
    _mime, name, data = att
    dest = filedialog.asksaveasfilename(parent=parent, initialfile=name)
    if dest:
        with open(dest, "wb") as f:
            f.write(data)

def logo_to_base64(path: str, size: int = 128) -> str:
    """Center-crops the image to a square, scales it to size x size and returns
    Base64 PNG text (small enough to store in the rooms table)."""
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def make_logo_photo(b64_data: str, size: int, radius: int):
    """Logo as a PhotoImage with rounded corners (radius = size/2 gives a circle).
    Returns None if the data is broken. The caller MUST keep a reference."""
    img = decode_base64_image(b64_data)
    if img is None:
        return None
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)      # 4x bigger -> smooth edges
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * 4 - 1, size * 4 - 1), radius=radius * 4, fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    img.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
    return ImageTk.PhotoImage(img)