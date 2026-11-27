from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import current_user
from .db import pool

router = APIRouter(prefix="/api", tags=["chat"])

TAGS = {"none": "No tag", "announcement": "Announcement", "question": "Question",
        "emergency": "Emergency", "wrong_sent": "Wrong sent", "other": "Other"}


class SendIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    tag: str = "none"
    tag_label: str | None = Field(default=None, max_length=20)


class EditIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class TagIn(BaseModel):
    tag: str
    tag_label: str | None = Field(default=None, max_length=20)


def _tag(tag: str, label: str | None):
    if tag not in TAGS:
        raise HTTPException(400, "Unknown tag.")
    if tag == "other":
        label = (label or "").strip()
        if not label:
            raise HTTPException(400, 'The "Other" tag needs a label.')
        return tag, label
    return tag, None


def _tag_text(tag: str, label: str | None) -> str:
    return f"Other: {label}" if tag == "other" and label else TAGS.get(tag, tag)


_SELECT = (
    "select m.message_id, m.sender_id, m.content, m.tag, m.tag_label, m.is_edited, "
    "m.edited_at, m.created_at, u.full_name, u.username, u.role "
    "from messages m join users u on u.user_id = m.sender_id ")


def _msg(r: dict, me: int) -> dict:
    return {
        "message_id": r["message_id"], "sender_id": r["sender_id"],
        "name": r["full_name"] or r["username"], "role": r["role"],
        "content": r["content"], "tag": r["tag"], "tag_label": r["tag_label"],
        "is_edited": r["is_edited"], "created_at": r["created_at"],
        "mine": r["sender_id"] == me,
    }


async def _member(conn, room_id: int, user_id: int):
    cur = await conn.execute(
        "select room_role, can_send_messages, can_read_history from room_members "
        "where room_id = %s and user_id = %s", (room_id, user_id))
    m = await cur.fetchone()
    if not m:
        raise HTTPException(403, "You are not in this room.")
    cur = await conn.execute(
        "select 1 as b from room_bans where room_id = %s and user_id = %s", (room_id, user_id))
    return m, await cur.fetchone() is not None


def _perms(m: dict, banned: bool, sr: dict):
    host = m["room_role"] == "host"
    can_read = host or (m["can_read_history"] and sr["everyone_read"])
    can_send = not banned and (host or (m["can_send_messages"] and sr["everyone_send"]))
    return bool(can_read), bool(can_send)


async def _access(conn, sub_room_id: int, user_id: int):
    cur = await conn.execute(
        "select sub_room_id, room_id, name, kind, visibility, everyone_read, everyone_send "
        "from sub_rooms where sub_room_id = %s and not is_deleted", (sub_room_id,))
    sr = await cur.fetchone()
    if not sr or sr["visibility"] != "public":     # private DMs come in a later step
        raise HTTPException(404, "No such sub-room.")
    m, banned = await _member(conn, sr["room_id"], user_id)
    can_read, can_send = _perms(m, banned, sr)
    return {"can_read": can_read, "can_send": can_send}


async def _fetch_one(conn, message_id: int):
    cur = await conn.execute(_SELECT + "where m.message_id = %s", (message_id,))
    return await cur.fetchone()


@router.get("/rooms/{room_id}/sub-rooms")
async def sub_rooms(room_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        m, banned = await _member(conn, room_id, user["user_id"])
        cur = await conn.execute(
            "select sub_room_id, name, kind, everyone_read, everyone_send from sub_rooms "
            "where room_id = %s and visibility = 'public' and not is_deleted "
            "order by position, sub_room_id", (room_id,))
        rows = await cur.fetchall()
    out = []
    for r in rows:
        can_read, can_send = _perms(m, banned, r)
        out.append({"sub_room_id": r["sub_room_id"], "name": r["name"], "kind": r["kind"],
                    "can_read": can_read, "can_send": can_send})
    return out


@router.get("/sub-rooms/{sub_room_id}/messages")
async def messages(sub_room_id: int, after: int | None = None,
                   since: datetime | None = None, user=Depends(current_user)):
    """No `after`: last 50. With `after`: newer messages, plus older ones edited since `since`."""
    async with pool.connection() as conn:
        a = await _access(conn, sub_room_id, user["user_id"])
        if not a["can_read"]:
            raise HTTPException(403, "You can't read this sub-room.")
        if after is None:
            cur = await conn.execute(
                f"select * from ({_SELECT} where m.sub_room_id = %s "
                "order by m.message_id desc limit 50) t order by message_id", (sub_room_id,))
        else:
            cur = await conn.execute(
                _SELECT + "where m.sub_room_id = %s and (m.message_id > %s "
                "or (m.is_edited and m.edited_at > %s)) order by m.message_id",
                (sub_room_id, after, since or datetime(1970, 1, 1, tzinfo=timezone.utc)))
        rows = await cur.fetchall()
        cur = await conn.execute("select now() as now")
        now = (await cur.fetchone())["now"]
    return {"messages": [_msg(r, user["user_id"]) for r in rows],
            "now": now, "can_send": a["can_send"]}


@router.post("/sub-rooms/{sub_room_id}/messages", status_code=201)
async def send(sub_room_id: int, body: SendIn, user=Depends(current_user)):
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "Type something first.")
    tag, label = _tag(body.tag, body.tag_label)
    async with pool.connection() as conn:
        a = await _access(conn, sub_room_id, user["user_id"])
        if not a["can_send"]:
            raise HTTPException(403, "You can't post here.")
        cur = await conn.execute(
            "insert into messages (sub_room_id, sender_id, content, tag, tag_label) "
            "values (%s, %s, %s, %s, %s) returning message_id",
            (sub_room_id, user["user_id"], content, tag, label))
        mid = (await cur.fetchone())["message_id"]
        row = await _fetch_one(conn, mid)
    return _msg(row, user["user_id"])


async def _own_message(conn, message_id: int, user_id: int):
    """Locks the row. Only the sender may change it, and only while allowed to post."""
    cur = await conn.execute(
        "select sub_room_id, sender_id, content, tag, tag_label from messages "
        "where message_id = %s for update", (message_id,))
    m = await cur.fetchone()
    if not m:
        raise HTTPException(404, "No such message.")
    if m["sender_id"] != user_id:
        raise HTTPException(403, "You can only change your own messages.")
    a = await _access(conn, m["sub_room_id"], user_id)
    if not a["can_send"]:
        raise HTTPException(403, "You can't change messages here.")
    return m


@router.patch("/messages/{message_id}")
async def edit_message(message_id: int, body: EditIn, user=Depends(current_user)):
    new = body.content.strip()
    if not new:
        raise HTTPException(400, "Message can't be empty.")
    async with pool.connection() as conn:
        async with conn.transaction():
            m = await _own_message(conn, message_id, user["user_id"])
            if new != m["content"]:
                await conn.execute(
                    "insert into message_edits (message_id, old_content, new_content) "
                    "values (%s, %s, %s)", (message_id, m["content"], new))
                await conn.execute(
                    "update messages set content = %s, is_edited = true, edited_at = now() "
                    "where message_id = %s", (new, message_id))
            row = await _fetch_one(conn, message_id)
    return _msg(row, user["user_id"])


@router.patch("/messages/{message_id}/tag")
async def retag_message(message_id: int, body: TagIn, user=Depends(current_user)):
    tag, label = _tag(body.tag, body.tag_label)
    async with pool.connection() as conn:
        async with conn.transaction():
            m = await _own_message(conn, message_id, user["user_id"])
            if (tag, label) != (m["tag"], m["tag_label"]):
                await conn.execute(
                    "insert into message_tag_edits (message_id, old_tag, old_label, new_tag, new_label) "
                    "values (%s, %s, %s, %s, %s)",
                    (message_id, m["tag"], m["tag_label"], tag, label))
                await conn.execute(
                    "update messages set tag = %s, tag_label = %s, is_edited = true, "
                    "edited_at = now() where message_id = %s", (tag, label, message_id))
            row = await _fetch_one(conn, message_id)
    return _msg(row, user["user_id"])


@router.get("/messages/{message_id}/history")
async def history(message_id: int, user=Depends(current_user)):
    """Edit history is visible to everyone who can read the sub-room."""
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select sub_room_id from messages where message_id = %s", (message_id,))
        m = await cur.fetchone()
        if not m:
            raise HTTPException(404, "No such message.")
        a = await _access(conn, m["sub_room_id"], user["user_id"])
        if not a["can_read"]:
            raise HTTPException(403, "You can't read this sub-room.")
        cur = await conn.execute(
            "select old_content, new_content, edited_at from message_edits "
            "where message_id = %s", (message_id,))
        texts = await cur.fetchall()
        cur = await conn.execute(
            "select old_tag, old_label, new_tag, new_label, edited_at from message_tag_edits "
            "where message_id = %s", (message_id,))
        tags = await cur.fetchall()
    events = [{"kind": "text", "at": r["edited_at"],
               "old": r["old_content"], "new": r["new_content"]} for r in texts]
    events += [{"kind": "tag", "at": r["edited_at"],
                "old": _tag_text(r["old_tag"], r["old_label"]),
                "new": _tag_text(r["new_tag"], r["new_label"])} for r in tags]
    events.sort(key=lambda e: e["at"])
    return events