"""
db/connection.py
─────────────────────────────────────────────────────────────

Provides a single shared MySQL connection (via mysql-connector-python),
reconnecting automatically if the connection drops.

NOTE: verify these three constants match your local XAMPP / MySQL setup
"""

import os
import sys

if sys.stdout is not None:      # it is None inside a windowed .exe
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

from db.config import load_config

load_dotenv()

_connection = None


def get_settings():
    """Saved setup first; .env as a fallback for development. None = needs setup."""
    cfg = load_config()
    if cfg:
        return cfg
    if os.getenv("DB_HOST"):
        return {"host": os.getenv("DB_HOST"),
                "port": int(os.getenv("DB_PORT", "3306")),
                "database": os.getenv("DB_NAME"),
                "user": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD", "")}
    return None


def reset_connection():
    """Drops the cached connection so the next call uses fresh settings."""
    global _connection
    try:
        if _connection is not None:
            _connection.close()
    except Exception:
        pass
    _connection = None


def test_connection(host, port, database, user, password):
    """Returns (ok, message). Does not touch the shared connection."""
    try:
        conn = mysql.connector.connect(host=host, port=port, database=database,
                                       user=user, password=password,
                                       connection_timeout=5, use_pure=True)
        conn.close()
        return True, "Connected."
    except MySQLError as e:
        return False, str(e)

def get_connection():
    """Returns a live MySQL connection, (re)connecting if necessary."""
    global _connection
    if _connection is None or not _connection.is_connected():
        cfg = get_settings()
        if cfg is None:
            return None
        try:
            _connection = mysql.connector.connect(
                host=cfg["host"],
                port=cfg["port"],
                database=cfg["database"],
                user=cfg["user"],
                password=cfg["password"],
                autocommit=True,
                connection_timeout=5,
                use_pure=True,
            )
            print("\u2705 Database connected!")
        except MySQLError as e:
            print(f"\u274c Connection failed: {e}")
            _connection = None
    return _connection