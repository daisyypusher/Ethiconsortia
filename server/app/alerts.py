from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import current_user
from .chat import _member
from .db import pool

router = APIRouter(prefix="/api", tags=["alerts"])

# who sees a flagged message: the host of that room, or an admin whose
# school department matches the room's department
_FROM = """
from flagged_messages fm
join users u on u.user_id = fm.user_id
left join sub_rooms s on s.sub_room_id = fm.sub_room_id
left join dm_threads t on t.thread_id = fm.thread_id
join rooms r on r.room_id = coalesce(s.room_id, t.room_id)
left join flagged_reads fr on fr.flag_id = fm.id and fr.admin_id = %(me)s
where (r.host_id = %(me)s
   or (%(admin)s and r.department_id is not null and r.department_id = %(dept)s))
"""


class ReadIn(BaseModel):
    ids: list[int] = Field(max_length=200)


class WordIn(BaseModel):
    word: str = Field(min_length=1, max_length=50)
    all_rooms: bool = False


async def _who(conn, user):
    cur = await conn.execute(
        "select school_department_id from users where user_id = %s", (user["user_id"],))
    dept = (await cur.fetchone())["school_department_id"]
    return {"me": user["user_id"], "dept": dept,
            "admin": user["role"] == "admin" and dept is not None}


@router.get("/alerts/count")
async def alerts_count(user=Depends(current_user)):
    async with pool.connection() as conn:
        p = await _who(conn, user)
        cur = await conn.execute(
            "select count(*) as n " + _FROM + " and fr.admin_id is null", p)
        n = (await cur.fetchone())["n"]
        cur = await conn.execute(
            "select exists (select 1 from rooms where host_id = %(me)s) as h", p)
        hosts = (await cur.fetchone())["h"]
    return {"unread": n, "show": bool(p["admin"] or hosts or user["role"] == "professor")}


@router.get("/alerts")
async def alerts(user=Depends(current_user)):
    async with pool.connection() as conn:
        p = await _who(conn, user)
        cur = await conn.execute(
            "select fm.id, fm.original, fm.category, fm.flagged_at, s.name as sub_name, "
            "(fm.thread_id is not null) as is_dm, r.room_name, "
            "coalesce(nullif(u.full_name, ''), u.username) as sender, "
            "(fr.admin_id is null) as unread " + _FROM +
            " order by fm.flagged_at desc limit 200", p)
        rows = await cur.fetchall()
    return [{"id": r["id"], "original": r["original"], "category": r["category"],
             "flagged_at": r["flagged_at"], "room_name": r["room_name"],
             "place": "Private message" if r["is_dm"] else "# " + r["sub_name"],
             "sender": r["sender"], "unread": r["unread"]} for r in rows]


@router.post("/alerts/read", status_code=204)
async def alerts_read(body: ReadIn, user=Depends(current_user)):
    if not body.ids:
        return
    async with pool.connection() as conn:
        p = await _who(conn, user)
        p["ids"] = body.ids
        await conn.execute(
            "insert into flagged_reads (flag_id, admin_id) select fm.id, %(me)s " + _FROM +
            " and fm.id = any(%(ids)s) on conflict do nothing", p)


# ---------- filtered words ----------
async def _staff_member(conn, room_id, user):
    if user["role"] not in ("professor", "admin"):
        raise HTTPException(403, "Only professors and admins manage filtered words.")
    await _member(conn, room_id, user["user_id"])


@router.get("/rooms/{room_id}/words")
async def list_words(room_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        await _staff_member(conn, room_id, user)
        cur = await conn.execute(
            "select word_id, word, (room_id is null) as is_all from filtered_words "
            "where room_id is null or room_id = %s order by is_all desc, word", (room_id,))
        rows = await cur.fetchall()
    return [{"word_id": r["word_id"], "word": r["word"],
             "scope": "all" if r["is_all"] else "room"} for r in rows]


@router.post("/rooms/{room_id}/words", status_code=201)
async def add_word(room_id: int, body: WordIn, user=Depends(current_user)):
    word = body.word.strip().lower()
    if not word:
        raise HTTPException(400, "Type a word first.")
    scope = None if (body.all_rooms and user["role"] == "admin") else room_id
    async with pool.connection() as conn:
        await _staff_member(conn, room_id, user)
        cur = await conn.execute(
            "select 1 as x from filtered_words "
            "where word = %s and room_id is not distinct from %s", (word, scope))
        if await cur.fetchone():
            raise HTTPException(409, "That word is already in the list.")
        await conn.execute(
            "insert into filtered_words (room_id, word, added_by) values (%s, %s, %s)",
            (scope, word, user["user_id"]))
    return {"ok": True}


@router.delete("/words/{word_id}", status_code=204)
async def remove_word(word_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select room_id from filtered_words where word_id = %s", (word_id,))
        w = await cur.fetchone()
        if not w:
            raise HTTPException(404, "No such word.")
        if w["room_id"] is None:
            if user["role"] != "admin":
                raise HTTPException(403, "Only an admin can remove all-room words.")
        else:
            await _staff_member(conn, w["room_id"], user)
        await conn.execute("delete from filtered_words where word_id = %s", (word_id,))