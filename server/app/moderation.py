import re

from fastapi import HTTPException

MAX_WARNINGS = 3

BAD_WORDS = [
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "damn", "piss", "crap",
    "dick", "cock", "pussy", "motherfucker", "fucker", "bullshit", "ass", "slut",
    "whore", "nigger", "nigga", "faggot", "retard", "idiot", "moron",
    "putangina", "putang ina", "gago", "tangina", "bobo", "ulol", "tarantado",
    "leche", "puta", "bwisit", "inutil", "siraulo", "pakyu", "hayop", "tanga",
]
SUSPICIOUS = [
    "kill you", "kill myself", "suicide", "bomb", "shoot", "stab", "rape",
    "overdose", "leak the exam", "exam answers",
]


def _censor(text, words):
    out, hit = text, False
    for w in sorted(words, key=len, reverse=True):      # "putang ina" before "puta"
        pat = re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.IGNORECASE)
        if pat.search(out):
            hit = True
            out = pat.sub(lambda m: "*" * len(m.group()), out)
    return out, hit


def _suspicious(text):
    return any(re.search(r"\b" + re.escape(w) + r"\b", text, re.IGNORECASE)
               for w in SUSPICIOUS)


async def screen(conn, user_id, texts, *, sub_room_id=None, thread_id=None):
    """texts = [(label, text)]. Clean: returns. Bad: logs it, never posts, raises."""
    if sub_room_id:
        cur = await conn.execute(
            "select room_id from sub_rooms where sub_room_id = %s", (sub_room_id,))
    else:
        cur = await conn.execute(
            "select room_id from dm_threads where thread_id = %s", (thread_id,))
    room_id = (await cur.fetchone())["room_id"]

    cur = await conn.execute(
        "select word from filtered_words where room_id is null or room_id = %s", (room_id,))
    words = set(BAD_WORDS) | {r["word"].lower() for r in await cur.fetchall()}

    first, filtered, suspicious = None, False, False
    for label, text in texts:
        if not text:
            continue
        censored, f = _censor(text, words)
        s = _suspicious(text)
        if (f or s) and first is None:
            first = (label, text, censored)
        filtered, suspicious = filtered or f, suspicious or s
    if first is None:
        return

    label, text, censored = first
    pre = f"[{label}] " if label else ""
    await conn.execute(
        "insert into flagged_messages "
        "(user_id, sub_room_id, thread_id, original, censored, category) "
        "values (%s, %s, %s, %s, %s, %s)",
        (user_id, sub_room_id, thread_id, pre + text, pre + censored,
         "suspicious" if suspicious else "filtered"))

    if not filtered:
        raise HTTPException(
            400, "Message not sent. A host or administrator may follow up with you.")

    cur = await conn.execute(          # host of a room with no department can't be punished
        "select 1 as x from rooms where room_id = %s and host_id = %s "
        "and department_id is null", (room_id, user_id))
    if await cur.fetchone():
        raise HTTPException(400, "Message not sent: inappropriate language.")

    cur = await conn.execute(
        "insert into room_warnings (room_id, user_id, warn_count) values (%s, %s, 1) "
        "on conflict (room_id, user_id) "
        "do update set warn_count = room_warnings.warn_count + 1 returning warn_count",
        (room_id, user_id))
    n = (await cur.fetchone())["warn_count"]
    if n >= MAX_WARNINGS:
        await conn.execute(
            "insert into room_bans (room_id, user_id) values (%s, %s) on conflict do nothing",
            (room_id, user_id))
        raise HTTPException(
            403, "You are banned from this room after 3 warnings. Contact an administrator.")
    raise HTTPException(
        400, f"Warning {n}/{MAX_WARNINGS}: inappropriate language, message not sent. "
             f"{MAX_WARNINGS - n} left before a room ban. The host and admins were notified.")