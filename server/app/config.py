from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# server/.env, no matter which folder you run the command from
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str
    cors_origins: str = "http://localhost:5173"   # comma-separated
    session_days: int = 30                         # sliding, like a Discord login
    demo_school_database_url: str = ""


settings = Settings()