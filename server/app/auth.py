import asyncio
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.errors import UniqueViolation
from psycopg.rows import tuple_row
from pydantic import BaseModel, Field

from .config import settings
from .db import pool
from .schools import CodeRejected, get_verifier

router = APIRouter(prefix="/api/auth", tags=["auth"])
ph = PasswordHasher()
DUMMY_HASH = ph.hash("not-a-real-password")   # makes unknown usernames take the same time
COOKIE = "session"
ROLES = {"student", "professor", "admin"}
SCHOOL_ADAPTER = "demo_db"


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: str
    code: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _one(conn, sql, params=()):
    async with conn.cursor(row_factory=tuple_row) as cur:
        await cur.execute(sql, params)
        return await cur.fetchone()


async def _start_session(conn, response: Response, user_id: int):
    token = secrets.token_urlsafe(32)
    await conn.execute(
        "insert into sessions (token_hash, user_id, expires_at) "
        "values (%s, %s, now() + make_interval(days => %s))",
        (_h(token), user_id, settings.session_days))
    response.set_cookie(
        COOKIE, token, max_age=settings.session_days * 86400,
        httponly=True, samesite="lax", secure=False, path="/")   # secure=True once on https


@router.post("/register", status_code=201)
async def register(body: RegisterIn, response: Response):
    role = body.role.strip().lower()
    username = body.username.strip()
    full_name = body.full_name.strip()
    if role not in ROLES:
        raise HTTPException(400, "Pick student, professor or admin.")
    code = (body.code or "").strip()
    if role != "student" and not code:
        raise HTTPException(400, "Staff accounts need an access code.")

    # staff: look at the code first WITHOUT burning it
    verifier = get_verifier(SCHOOL_ADAPTER)
    staff = None
    if role != "student":
        try:
            staff = await verifier.redeem(code, role, consume=False)
        except CodeRejected:
            raise HTTPException(400, "That code isn't valid.")
        full_name = staff.full_name        # trust the school's name for staff

    pw_hash = await asyncio.to_thread(ph.hash, body.password)
    try:
        async with pool.connection() as conn:
            async with conn.transaction():
                if await _one(conn, "select 1 from users where lower(username) = lower(%s)",
                              (username,)):
                    raise HTTPException(409, "That username is taken.")
                row = await _one(
                    conn,
                    "insert into users (full_name, username, password_hash, role, "
                    "school_staff_ref, school_department_id, school_department_name) "
                    "values (%s, %s, %s, %s, %s, %s, %s) returning user_id",
                    (full_name, username, pw_hash, role,
                     staff.ref if staff else None,
                     staff.department_id if staff else None,
                     staff.department_name if staff else None))
                user_id = row[0]
                await _start_session(conn, response, user_id)
                # LAST step before commit: burn the code (once only).
                # If someone else burned it meanwhile, this raises and EVERYTHING rolls back.
                if staff:
                    try:
                        await verifier.redeem(code, role, consume=True)
                    except CodeRejected:
                        raise HTTPException(400, "That code isn't valid.")
    except UniqueViolation:
        raise HTTPException(409, "That username is taken.")
    return {"user_id": user_id, "full_name": full_name, "role": role}


@router.post("/login")
async def login(body: LoginIn, response: Response):
    async with pool.connection() as conn:
        row = await _one(
            conn,
            "select user_id, full_name, role, password_hash from users "
            "where lower(username) = lower(%s)", (body.username.strip(),))
        try:
            await asyncio.to_thread(ph.verify, row[3] if row else DUMMY_HASH, body.password)
            ok = row is not None
        except (VerificationError, InvalidHashError):
            ok = False
        if not ok:
            raise HTTPException(401, "Wrong username or password.")
        await _start_session(conn, response, row[0])
    return {"user_id": row[0], "full_name": row[1], "role": row[2]}


async def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in.")
    async with pool.connection() as conn:
        # also pushes the expiry forward: sliding 30 days
        row = await _one(
            conn,
            "update sessions s set expires_at = now() + make_interval(days => %s) "
            "from users u where s.token_hash = %s and s.expires_at > now() "
            "and u.user_id = s.user_id "
            "returning u.user_id, u.full_name, u.username, u.role",
            (settings.session_days, _h(token)))
    if not row:
        raise HTTPException(401, "Session expired.")
    return {"user_id": row[0], "full_name": row[1], "username": row[2], "role": row[3]}


@router.get("/me")
async def me(user=Depends(current_user)):
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        async with pool.connection() as conn:
            await conn.execute("delete from sessions where token_hash = %s", (_h(token),))
    response.delete_cookie(COOKIE, path="/")