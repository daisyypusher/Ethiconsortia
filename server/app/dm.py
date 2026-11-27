from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import current_user
from .chat import EditIn, SendIn, _member, _msg, _tag
from .db import pool

router = APIRouter(prefix="/api", tags=["dm"])

_SELECT = (
    "select m.message_id, m.sender_id, m.content, m.tag, m.tag_label, m.is_edited, "
    "m.edited_at, m.created_at, u.full_name, u.username, u.role "
    "from dm_messages m join users u on u.user_id = m.sender_id ")


class OpenIn(BaseModel):
    user_id: int


async def _thread(conn, thread_id: int, user_id: int):
    """Only the two people in a thread may open it. Banned or kicked people can't send."""
    cur = await conn.execute(
        "select thread_id, room_id, user_a, user_b from dm_threads where thread_id = %s",
        (thread_id,))
    t = await cur.fetchone()
    if not t or user_id not in (t["user_a"], t["user_b"]):
        raise HTTPException(404, "No such conversation.")
    _, banned = await _member(conn, t["room_id"], user_id)      # 403 if no longer a member
    other = t["user_b"] if t["user_a"] == user_id else t["user_a"]
    cur = await conn.execute(
        "select (exists (select 1 from room_members where room_id = %s and user_id = %s) "
        "and not exists (select 1 from room_bans where room_id = %s and user_id = %s)) as ok",
        (t["room_id"], other, t["room_id"], other))
    other_ok = (await cur.fetchone())["ok"]
    return {"thread": t, "can_send": (not banned) and bool(other_ok)}


async def _fetch_one(conn, message_id: int):
    cur = await conn.execute(_SELECT + "where m.message_id = %s", (message_id,))
    return await cur.fetchone()


@router.get("/rooms/{room_id}/members")
async def room_members(room_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        await _member(conn, room_id, user["user_id"])
        cur = await conn.execute(
            "select u.user_id, u.full_name, u.username, u.role, rm.room_role "
            "from room_members rm join users u on u.user_id = rm.user_id "
            "where rm.room_id = %s and rm.user_id <> %s and not exists "
            "(select 1 from room_bans b where b.room_id = rm.room_id and b.user_id = rm.user_id) "
            "order by case u.role when 'admin' then 0 when 'professor' then 1 else 2 end, "
            "lower(coalesce(nullif(u.full_name, ''), u.username))",
            (room_id, user["user_id"]))
        rows = await cur.fetchall()
    return [{"user_id": r["user_id"], "name": r["full_name"] or r["username"],
             "role": r["role"], "room_role": r["room_role"]} for r in rows]


@router.get("/rooms/{room_id}/dms")
async def my_threads(room_id: int, user=Depends(current_user)):
    uid = user["user_id"]
    async with pool.connection() as conn:
        await _member(conn, room_id, uid)
        cur = await conn.execute(
            "select t.thread_id, u.user_id, u.full_name, u.username, u.role, "
            "coalesce((select max(m.created_at) from dm_messages m "
            "          where m.thread_id = t.thread_id), t.created_at) as last_at "
            "from dm_threads t "
            "join users u on u.user_id = (case when t.user_a = %s then t.user_b else t.user_a end) "
            "where t.room_id = %s and (t.user_a = %s or t.user_b = %s) "
            "and (t.created_by = %s or exists "
            "     (select 1 from dm_messages x where x.thread_id = t.thread_id)) "
            "order by last_at desc", (uid, room_id, uid, uid, uid))
        rows = await cur.fetchall()
    return [{"thread_id": r["thread_id"], "user_id": r["user_id"],
             "name": r["full_name"] or r["username"], "role": r["role"],
             "last_at": r["last_at"]} for r in rows]


@router.post("/rooms/{room_id}/dms")
async def open_thread(room_id: int, body: OpenIn, user=Depends(current_user)):
    me, other = user["user_id"], body.user_id
    if other == me:
        raise HTTPException(400, "You can't message yourself.")
    async with pool.connection() as conn:
        _, banned = await _member(conn, room_id, me)
        if banned:
            raise HTTPException(403, "You are banned from this room.")
        cur = await conn.execute(
            "select 1 as ok from room_members rm where rm.room_id = %s and rm.user_id = %s "
            "and not exists (select 1 from room_bans b "
            "                where b.room_id = rm.room_id and b.user_id = rm.user_id)",
            (room_id, other))
        if not await cur.fetchone():
            raise HTTPException(404, "That person isn't in this room.")
        a, b = sorted((me, other))
        await conn.execute(
            "insert into dm_threads (room_id, user_a, user_b, created_by) values (%s, %s, %s, %s) "
            "on conflict (room_id, user_a, user_b) do nothing", (room_id, a, b, me))
        cur = await conn.execute(
            "select thread_id from dm_threads where room_id = %s and user_a = %s and user_b = %s",
            (room_id, a, b))
        t = await cur.fetchone()
    return {"thread_id": t["thread_id"]}


@router.get("/dms/unread")
async def unread(user=Depends(current_user)):
    uid = user["user_id"]
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select t.thread_id, t.room_id, r.room_name, count(*) as n, "
            "max(m.created_at) as last_at, u.full_name, u.username "
            "from dm_messages m "
            "join dm_threads t on t.thread_id = m.thread_id "
            "join rooms r on r.room_id = t.room_id "
            "join users u on u.user_id = m.sender_id "
            "where m.read_at is null and m.sender_id <> %s and (t.user_a = %s or t.user_b = %s) "
            "and not r.is_archived "
            "and exists (select 1 from room_members rm "
            "            where rm.room_id = t.room_id and rm.user_id = %s) "
            "group by t.thread_id, t.room_id, r.room_name, u.user_id, u.full_name, u.username "
            "order by last_at desc", (uid, uid, uid, uid))
        rows = await cur.fetchall()
    return [{"thread_id": r["thread_id"], "room_id": r["room_id"], "room_name": r["room_name"],
             "from_name": r["full_name"] or r["username"], "n": r["n"],
             "last_at": r["last_at"]} for r in rows]


@router.get("/dms/{thread_id}/messages")
async def thread_messages(thread_id: int, after: int | None = None,
                          since: datetime | None = None, user=Depends(current_user)):
    uid = user["user_id"]
    async with pool.connection() as conn:
        a = await _thread(conn, thread_id, uid)
        if after is None:
            cur = await conn.execute(
                f"select * from ({_SELECT} where m.thread_id = %s "
                "order by m.message_id desc limit 50) t order by message_id", (thread_id,))
        else:
            cur = await conn.execute(
                _SELECT + "where m.thread_id = %s and (m.message_id > %s "
                "or (m.is_edited and m.edited_at > %s)) order by m.message_id",
                (thread_id, after, since or datetime(1970, 1, 1, tzinfo=timezone.utc)))
        rows = await cur.fetchall()
        await conn.execute(          # opening the chat marks the other person's messages read
            "update dm_messages set read_at = now() "
            "where thread_id = %s and sender_id <> %s and read_at is null", (thread_id, uid))
        cur = await conn.execute("select now() as now")
        now = (await cur.fetchone())["now"]
    return {"messages": [_msg(r, uid) for r in rows], "now": now, "can_send": a["can_send"]}


@router.post("/dms/{thread_id}/messages", status_code=201)
async def send_dm(thread_id: int, body: SendIn, user=Depends(current_user)):
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "Type something first.")
    tag, label = _tag(body.tag, body.tag_label)
    async with pool.connection() as conn:
        a = await _thread(conn, thread_id, user["user_id"])
        if not a["can_send"]:
            raise HTTPException(403, "You can't send private messages here.")
        cur = await conn.execute(
            "insert into dm_messages (thread_id, sender_id, content, tag, tag_label) "
            "values (%s, %s, %s, %s, %s) returning message_id",
            (thread_id, user["user_id"], content, tag, label))
        mid = (await cur.fetchone())["message_id"]
        row = await _fetch_one(conn, mid)
    return _msg(row, user["user_id"])


@router.patch("/dm-messages/{message_id}")
async def edit_dm(message_id: int, body: EditIn, user=Depends(current_user)):
    new = body.content.strip()
    if not new:
        raise HTTPException(400, "Message can't be empty.")
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "select thread_id, sender_id, content from dm_messages "
                "where message_id = %s for update", (message_id,))
            m = await cur.fetchone()
            if not m:
                raise HTTPException(404, "No such message.")
            if m["sender_id"] != user["user_id"]:
                raise HTTPException(403, "You can only change your own messages.")
            a = await _thread(conn, m["thread_id"], user["user_id"])
            if not a["can_send"]:
                raise HTTPException(403, "You can't change messages here.")
            if new != m["content"]:
                await conn.execute(
                    "insert into dm_message_edits (message_id, old_content, new_content) "
                    "values (%s, %s, %s)", (message_id, m["content"], new))
                await conn.execute(
                    "update dm_messages set content = %s, is_edited = true, edited_at = now() "
                    "where message_id = %s", (new, message_id))
            row = await _fetch_one(conn, message_id)
    return _msg(row, user["user_id"])


@router.get("/dm-messages/{message_id}/history")
async def dm_history(message_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select thread_id from dm_messages where message_id = %s", (message_id,))
        m = await cur.fetchone()
        if not m:
            raise HTTPException(404, "No such message.")
        await _thread(conn, m["thread_id"], user["user_id"])
        cur = await conn.execute(
            "select old_content, new_content, edited_at from dm_message_edits "
            "where message_id = %s order by edited_at, edit_id", (message_id,))
        rows = await cur.fetchall()
    return [{"kind": "text", "at": r["edited_at"],
             "old": r["old_content"], "new": r["new_content"]} for r in rows]