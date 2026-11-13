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


def get_custom_words(room_id=None) -> list:
    """Global words (room_id NULL) plus the words set for this room."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        if room_id is None:
            cur.execute("SELECT word FROM filtered_words WHERE room_id IS NULL")
        else:
            cur.execute(
                "SELECT word FROM filtered_words WHERE room_id IS NULL OR room_id=%s",
                (room_id,),
            )
        words = [r[0] for r in cur.fetchall()]
        cur.close()
        return words
    except Exception as ex:
        print(f"ModerationFilter.get_custom_words error: {ex}")
        return []


def add_filtered_word(word: str, room_id, added_by: int):
    """room_id=None -> global word. Returns (ok, message)."""
    word = word.strip().lower()
    if not word:
        return False, "Please type a word."
    if len(word) > 50:
        return False, "Word can be at most 50 characters."
    try:
        conn = get_connection()
        cur = conn.cursor()
        if room_id is None:
            cur.execute("SELECT 1 FROM filtered_words WHERE room_id IS NULL AND word=%s", (word,))
        else:
            cur.execute("SELECT 1 FROM filtered_words WHERE room_id=%s AND word=%s",
                        (room_id, word))
        if cur.fetchone():
            cur.close()
            return False, "That word is already in the list."
        cur.execute(
            "INSERT INTO filtered_words (room_id, word, added_by) VALUES (%s,%s,%s)",
            (room_id, word, added_by),
        )
        cur.close()
        return True, ""
    except Exception as ex:
        return False, f"DB Error: {ex}"


def remove_filtered_word(word_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM filtered_words WHERE word_id=%s", (word_id,))
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.remove_filtered_word error: {ex}")


def filter_message(original: str, room_id=None) -> FilterResult:
    """Whole-word check against the built-in list + this room's custom words
    + global custom words. Returns censored text + flag status."""
    words = set(BAD_WORDS) | {w.lower() for w in get_custom_words(room_id)}
    censored = original
    flagged = False

    # longest first, so "putang ina" is handled before "puta"
    for word in sorted(words, key=len, reverse=True):
        pattern = re.compile(r"(?<!\w)" + re.escape(word) + r"(?!\w)", re.IGNORECASE)
        if pattern.search(censored):
            flagged = True
            censored = pattern.sub(lambda m: "*" * len(m.group()), censored)

    return FilterResult(censored, flagged)

def is_exempt_host(user_id: int, room_id: int) -> bool:
    """True if the user hosts a room that has NO department. With no department there
    are no administrators over it, so the host has full power and can't be banned."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM rooms WHERE room_id=%s AND host_id=%s "
            "AND (department_id IS NULL OR department_id = '')",
            (room_id, user_id),
        )
        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return False

def record_warning(user_id: int, room_id: int) -> int:
    """Records a warning for the user IN THIS ROOM; bans them from the room
    if MAX_WARNINGS is reached. Returns the warn count (-1 on DB error)."""
    if is_exempt_host(user_id, room_id):
        return 0
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO room_warnings (user_id, room_id, warn_count)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE warn_count = warn_count + 1
            """,
            (user_id, room_id),
        )
        cur.execute("SELECT warn_count FROM room_warnings WHERE user_id=%s AND room_id=%s",
                    (user_id, room_id))
        row = cur.fetchone()
        count = row[0] if row else 1
        cur.close()

        if count >= MAX_WARNINGS:
            ban_user(user_id, room_id)
        return count
    except Exception as ex:
        print(f"ModerationFilter.record_warning error: {ex}")
        return -1


def ban_user(user_id: int, room_id: int, banned_by=None):
    """Bans the user from ONE room only."""
    if is_exempt_host(user_id, room_id):
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT IGNORE INTO room_bans (room_id, user_id, banned_by) "
                    "VALUES (%s, %s, %s)", (room_id, user_id, banned_by))
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.ban_user error: {ex}")


def unban_user_in_room(user_id: int, room_id: int) -> bool:
    """Lifts the room ban and resets the warnings for that room.
    Returns True if the user can now post (False if a department ban still applies)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM room_bans WHERE room_id=%s AND user_id=%s", (room_id, user_id))
        cur.execute("DELETE FROM room_warnings WHERE room_id=%s AND user_id=%s", (room_id, user_id))
        cur.close()
    except Exception as ex:
        print(f"ModerationFilter.unban_user_in_room error: {ex}")
    return not is_banned(user_id, room_id)


def is_banned(user_id: int, room_id: int) -> bool:
    """True if the user is banned from this room, directly or through its department."""
    if is_exempt_host(user_id, room_id):
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM rooms r
            WHERE r.room_id = %s
              AND (EXISTS (SELECT 1 FROM room_bans b
                           WHERE b.room_id = r.room_id AND b.user_id = %s)
                   OR (r.department_id IS NOT NULL AND EXISTS (
                           SELECT 1 FROM department_bans d
                           WHERE d.department_id = r.department_id AND d.user_id = %s)))
            """,
            (room_id, user_id, user_id),
        )
        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return False

def is_department_banned(user_id: int, department_id) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM department_bans WHERE department_id=%s AND user_id=%s",
                    (department_id, user_id))
        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return False


def is_locked_out(user_id: int, room_id: int) -> bool:
    """True if the user may not open this room at all: banned from its department,
    or (for a host / admin) banned from the room itself. Students who are only
    banned in a room are NOT locked out; they just can't send there."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM rooms r
            WHERE r.room_id = %s
              AND ((r.department_id IS NOT NULL AND EXISTS (
                        SELECT 1 FROM department_bans d
                        WHERE d.department_id = r.department_id AND d.user_id = %s))
                   OR (EXISTS (SELECT 1 FROM room_bans b
                               WHERE b.room_id = r.room_id AND b.user_id = %s)
                       AND ((r.host_id = %s AND r.department_id IS NOT NULL
                             AND r.department_id <> '')
                            OR EXISTS (SELECT 1 FROM users u
                                       WHERE u.user_id = %s AND u.role = 'admin'))))
            """,
            (room_id, user_id, user_id, user_id, user_id),
        )
        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return False

def get_warn_count(user_id: int, room_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT warn_count FROM room_warnings WHERE user_id=%s AND room_id=%s",
                    (user_id, room_id))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else 0
    except Exception:
        return 0


# ── Department-level moderation (used by the admin dashboard) ───────────────
def get_admin_departments(admin_id: int) -> list:
    """[(department_id, department_name)]: departments the admin joined,
    plus departments of rooms they are a member of (minus any they are banned from)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.department_id, MAX(r.department_name)
        FROM rooms r
        WHERE r.department_id IS NOT NULL
          AND (r.department_id IN (SELECT department_id FROM admin_departments WHERE user_id=%s)
               OR r.room_id IN (SELECT room_id FROM room_members WHERE user_id=%s))
          AND NOT EXISTS (SELECT 1 FROM department_bans b
                          WHERE b.department_id = r.department_id AND b.user_id = %s)
        GROUP BY r.department_id
        ORDER BY r.department_id
        """,
        (admin_id, admin_id, admin_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_department_people(department_id: str, admin_id: int) -> list:
    """Admins and professors in a department (members of its rooms, admins who joined it,
    or people currently banned from it). The calling admin is left out."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT u.user_id, u.full_name, u.username, u.role,
               EXISTS(SELECT 1 FROM department_bans db
                      WHERE db.department_id = %s AND db.user_id = u.user_id) AS is_banned
        FROM users u
        WHERE u.role IN ('professor', 'admin') AND u.user_id != %s
          AND (u.user_id IN (SELECT rm.user_id FROM room_members rm
                             JOIN rooms r ON r.room_id = rm.room_id
                             WHERE r.department_id = %s)
               OR u.user_id IN (SELECT user_id FROM admin_departments WHERE department_id = %s)
               OR u.user_id IN (SELECT user_id FROM department_bans WHERE department_id = %s))
        ORDER BY FIELD(u.role, 'admin', 'professor'), u.full_name ASC
        """,
        (department_id, admin_id, department_id, department_id, department_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def ban_in_department(user_id: int, department_id: str, banned_by: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT IGNORE INTO department_bans (department_id, user_id, banned_by) "
                "VALUES (%s, %s, %s)", (department_id, user_id, banned_by))
    cur.close()


def unban_in_department(user_id: int, department_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM department_bans WHERE department_id=%s AND user_id=%s",
                (department_id, user_id))
    cur.close()


def kick_from_department(user_id: int, department_id: str) -> int:
    """Removes the user from every room in the department. Returns how many rooms.
    Rooms they hosted are left with no host (an admin assigns a new one)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE rm FROM room_members rm JOIN rooms r ON r.room_id = rm.room_id "
        "WHERE r.department_id=%s AND rm.user_id=%s", (department_id, user_id))
    removed = cur.rowcount
    cur.execute(
        "DELETE mr FROM room_member_roles mr JOIN rooms r ON r.room_id = mr.room_id "
        "WHERE r.department_id=%s AND mr.user_id=%s", (department_id, user_id))
    cur.execute("UPDATE rooms SET host_id=NULL WHERE department_id=%s AND host_id=%s",
                (department_id, user_id))
    cur.execute("DELETE FROM admin_departments WHERE department_id=%s AND user_id=%s",
                (department_id, user_id))
    cur.close()
    return removed

def log_flagged(user_id: int, room_msg_id, original: str, censored: str,
                category: str = "filtered", sub_room_id=None):
    """Logs the flagged message to DB for admin/host review."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        if sub_room_id is None and room_msg_id:
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


def count_unread_alerts(user_id: int, is_admin: bool = True) -> int:
    """Held-back messages this user hasn't opened yet.
    Admins: their departments. Hosts: the rooms they host."""
    scope = _ADMIN_SCOPE if is_admin else "r.host_id = %s"
    n_scope = 3 if is_admin else 1
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT COUNT(*) FROM flagged_messages fm
            JOIN room_sub_rooms s ON s.sub_room_id = fm.sub_room_id
            JOIN rooms r ON r.room_id = s.room_id
            WHERE {scope}
              AND NOT EXISTS (SELECT 1 FROM flagged_reads fr
                              WHERE fr.flag_id = fm.id AND fr.admin_id = %s)
            """,
            (user_id,) * (n_scope + 1),
        )
        n = cur.fetchone()[0]
        cur.close()
        return n
    except Exception:
        return 0


def get_admin_flagged(user_id: int, limit: int = 200, is_admin: bool = True):
    """Held-back messages for this admin's departments (or this host's rooms),
    with per-user unread status."""
    scope = _ADMIN_SCOPE if is_admin else "r.host_id = %s"
    n_scope = 3 if is_admin else 1
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
        WHERE {scope}
        ORDER BY fm.flagged_at DESC
        LIMIT %s
        """,
        (user_id,) * (n_scope + 1) + (limit,),
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
    if warn_count <= 0:
        messagebox.showwarning(
            "Message not sent",
            "Your message contained inappropriate language and was not sent.",
            parent=parent)
        return
    remaining = MAX_WARNINGS - warn_count
    if remaining <= 0:
        msg = (
            "\u26d4 You have been BANNED from this room\n\n"
            f"You exceeded {MAX_WARNINGS} profanity warnings.\n"
            "Contact an administrator to appeal."
        )
        messagebox.showwarning("Banned", msg, parent=parent)
    else:
        msg = (
            f"\u26a0 Profanity Warning {warn_count}/{MAX_WARNINGS}\n\n"
            "Your message contained inappropriate language and was not sent.\n"
            "The host and administrators have been notified.\n"
            f"You have {remaining} warning(s) left before being banned from this room."
        )
        messagebox.showwarning("Warning", msg, parent=parent)
