from fastapi import APIRouter, Depends, HTTPException

from .auth import current_user
from .chat import _is_dept_admin
from .db import pool

router = APIRouter(prefix="/api/rooms", tags=["people"])

_ORDER = ("case when rm.room_role = 'host' then 0 when u.role = 'admin' then 1 "
          "when u.role = 'professor' then 2 else 3 end")


async def _viewer(conn, room_id: int, user_id: int):
    cur = await conn.execute(
        "select room_role, can_manage_members from room_members "
        "where room_id = %s and user_id = %s", (room_id, user_id))
    m = await cur.fetchone()
    admin = await _is_dept_admin(conn, room_id, user_id)
    if not m and not admin:
        raise HTTPException(403, "You are not in this room.")
    return {"admin": admin,
            "host": bool(m and m["room_role"] == "host"),
            "manage": admin or bool(m and m["can_manage_members"])}


def _can_kick(v, target_sys_role, target_room_role, is_me):
    if is_me or target_room_role == "host":          # nobody removes the host (yet)
        return False
    return v["admin"] or (v["manage"] and target_sys_role != "admin")


@router.get("/{room_id}/people")
async def people(room_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        v = await _viewer(conn, room_id, user["user_id"])
        cur = await conn.execute(
            "select u.user_id, u.full_name, u.username, u.role, rm.room_role, "
            "exists (select 1 from room_bans b where b.room_id = rm.room_id "
            "        and b.user_id = u.user_id) as banned "
            "from room_members rm join users u on u.user_id = rm.user_id "
            "where rm.room_id = %s order by " + _ORDER +
            ", lower(coalesce(nullif(u.full_name, ''), u.username))", (room_id,))
        rows = await cur.fetchall()
    out = []
    for r in rows:
        me = r["user_id"] == user["user_id"]
        out.append({
            "user_id": r["user_id"], "name": r["full_name"] or r["username"],
            "role": r["role"], "room_role": r["room_role"],
            "banned": r["banned"], "me": me,
            "can_kick": _can_kick(v, r["role"], r["room_role"], me),
            "can_unban": bool(r["banned"] and (v["admin"] or v["host"])),
        })
    return out


@router.delete("/{room_id}/members/{target_id}", status_code=204)
async def kick(room_id: int, target_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        v = await _viewer(conn, room_id, user["user_id"])
        cur = await conn.execute(
            "select rm.room_role, u.role from room_members rm "
            "join users u on u.user_id = rm.user_id "
            "where rm.room_id = %s and rm.user_id = %s", (room_id, target_id))
        t = await cur.fetchone()
        if not t:
            raise HTTPException(404, "That person isn't in this room.")
        if not _can_kick(v, t["role"], t["room_role"], target_id == user["user_id"]):
            raise HTTPException(403, "You can't remove that person.")
        await conn.execute(
            "delete from room_members where room_id = %s and user_id = %s",
            (room_id, target_id))


@router.post("/{room_id}/members/{target_id}/unban", status_code=204)
async def unban(room_id: int, target_id: int, user=Depends(current_user)):
    async with pool.connection() as conn:
        v = await _viewer(conn, room_id, user["user_id"])
        if not (v["admin"] or v["host"]):
            raise HTTPException(403, "Only the host or an admin can unban.")
        async with conn.transaction():
            await conn.execute(
                "delete from room_bans where room_id = %s and user_id = %s",
                (room_id, target_id))
            await conn.execute(
                "delete from room_warnings where room_id = %s and user_id = %s",
                (room_id, target_id))