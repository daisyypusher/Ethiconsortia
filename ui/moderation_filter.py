"""
ui/moderation_filter.py
─────────────────────────────────────────────────────────────
DB tables required (see ethiconsortia.sql):
    user_warnings, flagged_messages, users.is_banned
─────────────────────────────────────────────────────────────
"""
import re
from dataclasses import dataclass
from tkinter import messagebox

from db.connection import get_connection

# ── Banned word list (extend freely) ────────────────────────────────────────
BAD_WORDS = [
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt",
    "damn", "piss", "crap", "dick", "cock", "pussy",
    "motherfucker", "fucker", "bullshit", "ass", "slut", "whore",
    "nigger", "nigga", "faggot", "retard", "idiot", "moron",
    # Filipino profanities
    "putangina", "putang ina", "gago", "tangina", "bobo",
    "ulol", "tarantado", "leche", "puta", "bwisit", "inutil",
    "siraulo", "pakyu", "hayop", "animal", "tanga",
]

MAX_WARNINGS = 3


@dataclass
class FilterResult:
    censored: str
    was_flagged: bool


def filter_message(original: str) -> FilterResult:
    """Checks message for bad words, returns censored text + flag status."""
    lower = original.lower()
    censored = original
    flagged = False

    for word in BAD_WORDS:
        if word in lower:
            flagged = True
            stars = "*" * len(word)
            censored = re.sub(re.escape(word), stars, censored, flags=re.IGNORECASE)

    return FilterResult(censored, flagged)


def record_warning(user_id: int) -> int:
    """Records a warning for the user; bans them if MAX_WARNINGS reached.
    Returns the current warn count after incrementing (-1 on DB error)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO user_warnings (user_id, warn_count, is_banned)
            VALUES (%s, 1, 0)
            ON DUPLICATE KEY UPDATE warn_count = warn_count + 1
            """,
            (user_id,),
        )
        cur.execute("SELECT warn_count FROM user_warnings WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        count = row[0] if row else 1
        cur.close()

        if count >= MAX_WARNINGS:
            ban_user(user_id)
        return count
    except Exception as ex:
        print(f"ModerationFilter.record_warning error: {ex}")
        return -1


def ban_user(user_id: int):
    """Marks user as banned in user_warnings and users tables."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE user_warnings SET is_banned=1 WHERE user_id=%s", (user_id,))
        cur.execute("UPDATE users SET is_banned=1 WHERE user_id=%s", (user_id,))
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.ban_user error: {ex}")


def is_banned(user_id: int) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_banned FROM user_warnings WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return bool(row and row[0] == 1)
    except Exception:
        return False


def get_warn_count(user_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT warn_count FROM user_warnings WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else 0
    except Exception:
        return 0


def log_flagged(user_id: int, room_msg_id, original: str, censored: str):
    """Logs the flagged message to DB for admin review."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO flagged_messages (user_id, room_msg_id, original, censored)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, room_msg_id, original, censored),
        )
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.log_flagged error: {ex}")


def show_warning_dialog(parent, warn_count: int):
    """Shows a styled warning / ban dialog."""
    remaining = MAX_WARNINGS - warn_count
    if remaining <= 0:
        msg = (
            "\u26d4 You have been BANNED\n\n"
            f"You exceeded {MAX_WARNINGS} profanity warnings.\n"
            "Contact an administrator to appeal."
        )
        messagebox.showwarning("Banned", msg, parent=parent)
    else:
        msg = (
            f"\u26a0 Profanity Warning {warn_count}/{MAX_WARNINGS}\n\n"
            "Your message contained inappropriate language and was censored.\n"
            f"You have {remaining} warning(s) left before being banned."
        )
        messagebox.showwarning("Warning", msg, parent=parent)
