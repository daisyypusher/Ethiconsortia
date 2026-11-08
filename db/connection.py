"""
db/connection.py
─────────────────────────────────────────────────────────────

Provides a single shared MySQL connection (via mysql-connector-python),
reconnecting automatically if the connection drops.

NOTE: verify these three constants match your local XAMPP / MySQL setup
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

import mysql.connector
from mysql.connector import Error as MySQLError

import os
from dotenv import load_dotenv

load_dotenv()

URL_HOST = os.getenv("DB_HOST")
URL_PORT = int(os.getenv("DB_PORT", "3306"))
URL_DB = os.getenv("DB_NAME")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")

_connection = None

def get_connection():
    """Returns a live MySQL connection, (re)connecting if necessary."""
    global _connection
    if _connection is None or not _connection.is_connected():
        try:
            _connection = mysql.connector.connect(
                host=URL_HOST,
                port=URL_PORT,
                database=URL_DB,
                user=USER,
                password=PASSWORD,
                autocommit=True,
            )
            print("\u2705 Database connected!")
        except MySQLError as e:
            print(f"\u274c Connection failed: {e}")
            _connection = None
    return _connection


def cursor(dictionary=True):
    """Convenience helper: returns a cursor off the shared connection."""
    conn = get_connection()
    if conn is None:
        raise MySQLError("No database connection available.")
    return conn.cursor(dictionary=dictionary)
