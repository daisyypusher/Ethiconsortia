"""
db/config.py
Saves and loads the database login in the user's own app folder.
To switch to keyring later, only this file changes.
"""
import json
import os
from pathlib import Path

APP_NAME = "Ethiconsortia"


def config_path() -> Path:
    base = os.getenv("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME / "config.json"


def load_config():
    """Returns {host, port, database, user, password}, or None if not set up."""
    try:
        with open(config_path(), encoding="utf-8") as f:
            data = json.load(f)
        if data.get("host") and data.get("database") and data.get("user"):
            data["port"] = int(data.get("port", 3306))
            data["password"] = data.get("password", "")
            return data
    except (OSError, ValueError):
        pass
    return None


def save_config(host, port, database, user, password):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"host": host, "port": port, "database": database,
                   "user": user, "password": password}, f, indent=2)