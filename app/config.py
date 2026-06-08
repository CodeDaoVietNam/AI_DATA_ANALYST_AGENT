"""
Application configuration via Pydantic Settings.
All values can be overridden by environment variables or a .env file.
"""
from __future__ import annotations

import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "AI Data Analyst Agent"
    app_version: str = "0.2.0"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: object) -> bool:
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "n", "off", "release", "prod", "production"}:
                return False
        return bool(v)

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list in .env: ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
    allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:3000",
    ]
    # Local dev safety valve for Vite's automatic port fallback, e.g. 5173 -> 5174.
    # Set to an empty string in production if you want to rely only on ALLOWED_ORIGINS.
    allowed_origin_regex: str = r"^http://(localhost|127\.0\.0\.1):\d+$"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return list(v)  # type: ignore[arg-type]

    # ── Upload ───────────────────────────────────────────────────────────────
    max_upload_bytes: int = 100 * 1024 * 1024   # 100 MB
    upload_dir: str = "data/uploads"

    # ── LLM / Ollama ─────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_router_model: str = "qwen2.5:3b"
    ollama_router_timeout: int = 60
    ollama_explain_timeout: int = 60

    # ── Code Interpreter ─────────────────────────────────────────────────────
    code_interpreter_timeout: int = 10   # seconds per execution
    code_interpreter_max_rows: int = 100

    # ── Database & Auth ──────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/analyst.db"
    api_key: str = ""

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"


# Singleton — import this everywhere
settings = Settings()
