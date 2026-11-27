from pathlib import Path
from fastapi.staticfiles import StaticFiles
from .auth import router as auth_router
from .rooms import router as rooms_router
from .chat import router as chat_router

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open(wait=True, timeout=30)
    yield
    await pool.close()


app = FastAPI(title="Ethiconsortia API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health():
    async with pool.connection() as conn:
        cur = await conn.execute("select count(*) as users from users")
        row = await cur.fetchone()
    return {"status": "ok", "users": row["users"]}

WEB = Path(__file__).resolve().parents[2] / "web"
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(chat_router)
app.mount("/", StaticFiles(directory=WEB, html=True), name="web")