import secrets

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field

from .auth import current_user
from .db import pool

router = APIRouter(prefix="/api/rooms", tags=["rooms"])
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no I, L, O, 0, 1


class RoomIn(BaseModel):
    room_name: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)


class JoinIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)


def _code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(8))


def _shape(row: dict, role: str) -> dict:
    return {
        "room_id": row["room_id"],
        "room_name": row["room_name"],
        "description": row["description"],
        "room_role": role,
        # only the host sees the invite code
        "invite_code": row["invite_code"] if role == "host" else None,
    }


@router.get("")
async def my_rooms(user=Depends(current_user)):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select r.room_id, r.room_name, r.description, r.invite_code, m.room_role "
            "from room_members m join rooms r on r.room_id = m.room_id "
            "where m.user_id = %s and not r.is_archived order by r.created_at",
            (user["user_id"],))
        rows = await cur.fetchall()
    return [_shape(r, r["room_role"]) for r in rows]


@router.post("", status_code=201)
async def create_room(body: RoomIn, user=Depends(current_user)):
    name = body.room_name.strip()
    if not name:
        raise HTTPException(400, "Room name is required.")
    for _ in range(5):                      # retry if the random code collides
        try:
            async with pool.connection() as conn:
                async with conn.transaction():
                    cur = await conn.execute(
                        "insert into rooms (room_name, description, host_id, invite_code) "
                        "values (%s, %s, %s, %s) "
                        "returning room_id, room_name, description, invite_code",
                        (name, body.description.strip(), user["user_id"], _code()))
                    room = await cur.fetchone()
                    await conn.execute(
                        "insert into room_members (room_id, user_id, room_role, can_manage_members) "
                        "values (%s, %s, 'host', true)", (room["room_id"], user["user_id"]))
                    await conn.execute(
                        "insert into sub_rooms (room_id, name, kind, position, everyone_send) values "
                        "(%s, 'General', 'text', 0, true), "
                        "(%s, 'Announcements', 'announcement', 1, false)",
                        (room["room_id"], room["room_id"]))
            return _shape(room, "host")
        except UniqueViolation:
            continue
    raise HTTPException(500, "Could not make an invite code. Try again.")


@router.post("/join")
async def join_room(body: JoinIn, user=Depends(current_user)):
    code = "".join(ch for ch in body.code.upper() if ch.isalnum())
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select room_id, room_name, description, invite_code, is_archived "
            "from rooms where invite_code = %s", (code,))
        room = await cur.fetchone()
        if not room or room["is_archived"]:
            raise HTTPException(404, "No room has that code.")
        cur = await conn.execute(
            "select 1 as banned from room_bans where room_id = %s and user_id = %s",
            (room["room_id"], user["user_id"]))
        if await cur.fetchone():
            raise HTTPException(403, "You are banned from this room.")
        await conn.execute(
            "insert into room_members (room_id, user_id) values (%s, %s) "
            "on conflict do nothing", (room["room_id"], user["user_id"]))
        cur = await conn.execute(
            "select room_role from room_members where room_id = %s and user_id = %s",
            (room["room_id"], user["user_id"]))
        role = (await cur.fetchone())["room_role"]
    return _shape(room, role)