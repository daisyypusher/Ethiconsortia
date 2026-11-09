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

# Words that are NOT censored, but trigger an admin alert
SUSPICIOUS_WORDS = [
    "kill you", "kill myself", "suicide", "bomb", "shoot", "stab",
    "rape", "overdose", "leak the exam", "exam answers",
]


def find_suspicious(text: str) -> bool:
    """True if the text contains a word/phrase that should alert admins."""
    for w in SUSPICIOUS_WORDS:
        if re.search(r"\b" + re.escape(w) + r"\b", text, re.IGNORECASE):
            return True
    return False

@dataclass
class FilterResult:
    censored: str
    was_flagged: bool


def filter_message(original: str) -> FilterResult:
    """Checks message for bad words (whole words only), returns censored text + flag status."""
    censored = original
    flagged = False

    for word in BAD_WORDS:
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        if pattern.search(censored):
            flagged = True
            censored = pattern.sub(lambda m: "*" * len(m.group()), censored)

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


def log_flagged(user_id: int, room_msg_id, original: str, censored: str,
                category: str = "filtered"):
    """Logs the flagged message to DB for admin review."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        sub_room_id = None
        if room_msg_id:
            cur.execute("SELECT sub_room_id FROM room_messages WHERE message_id=%s",
                        (room_msg_id,))
            row = cur.fetchone()
            sub_room_id = row[0] if row else None
        cur.execute(
            """
            INSERT INTO flagged_messages
                (user_id, room_msg_id, original, censored, category, sub_room_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, room_msg_id, original, censored, category, sub_room_id),
        )
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.log_flagged error: {ex}")


# An admin's scope = departments they joined, departments of rooms they are a member of
# (joined manually or created), plus any room they belong to directly.
# Needs 3 parameters (admin_id x3) and the table alias `r` for rooms.
_ADMIN_SCOPE = """
    (r.department_id IN (SELECT department_id FROM admin_departments WHERE user_id = %s)
     OR r.department_id IN (SELECT r2.department_id FROM rooms r2
                            JOIN room_members rm2 ON rm2.room_id = r2.room_id
                            WHERE rm2.user_id = %s AND r2.department_id IS NOT NULL)
     OR r.room_id IN (SELECT room_id FROM room_members WHERE user_id = %s))
"""


def count_unread_alerts(admin_id: int) -> int:
    """Flagged messages in the admin's departments that THIS admin hasn't opened yet."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT COUNT(*) FROM flagged_messages fm
            JOIN room_sub_rooms s ON s.sub_room_id = fm.sub_room_id
            JOIN rooms r ON r.room_id = s.room_id
            WHERE {_ADMIN_SCOPE}
              AND NOT EXISTS (SELECT 1 FROM flagged_reads fr
                              WHERE fr.flag_id = fm.id AND fr.admin_id = %s)
            """,
            (admin_id, admin_id, admin_id, admin_id),
        )
        n = cur.fetchone()[0]
        cur.close()
        return n
    except Exception:
        return 0


def get_admin_flagged(admin_id: int, limit: int = 200):
    """Flagged messages from this admin's departments only, with per-admin unread status."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"""
        SELECT fm.id, fm.original, fm.censored, fm.category, fm.flagged_at,
               u.username, r.room_name, s.sub_room_name, s.sub_room_type_detail,
               COALESCE(NULLIF(ua.full_name,''), ua.username) AS dm_a_name,
               COALESCE(NULLIF(ub.full_name,''), ub.username) AS dm_b_name,
               (fr.admin_id IS NULL) AS is_unread
        FROM flagged_messages fm
        JOIN users u ON u.user_id = fm.user_id
        JOIN room_sub_rooms s ON s.sub_room_id = fm.sub_room_id
        LEFT JOIN users ua ON ua.user_id = s.dm_user_a
        LEFT JOIN users ub ON ub.user_id = s.dm_user_b
        JOIN rooms r ON r.room_id = s.room_id
        LEFT JOIN flagged_reads fr ON fr.flag_id = fm.id AND fr.admin_id = %s
        WHERE {_ADMIN_SCOPE}
        ORDER BY fm.flagged_at DESC
        LIMIT %s
        """,
        (admin_id, admin_id, admin_id, admin_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def mark_alerts_read(admin_id: int, flag_ids):
    """Marks the given flagged messages as read for this admin only."""
    if not flag_ids:
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.executemany(
            "INSERT IGNORE INTO flagged_reads (flag_id, admin_id) VALUES (%s, %s)",
            [(fid, admin_id) for fid in flag_ids],
        )
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.mark_alerts_read error: {ex}")


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
