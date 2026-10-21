"""Configuration loading for the shared application (standard library only).

Reads the variables named in `.env.example`. A local, git-ignored `.env` file
is read if present; variables already set in the shell take precedence. Real
keys are never stored in source, logged or shown in the UI.

Usage:
    from services.config import load_settings
    settings = load_settings()
    if not settings.has_api_key:
        ...  # run in simulated / rule-only mode and say so in the UI
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "http://10.167.60.148:8000/v1"
DEFAULT_MODEL = "campus-qwen"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_RUNTIME_DIR = "data/runtime"


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(repr=False)
    base_url: str
    model: str
    llm_timeout_seconds: float
    runtime_dir: Path

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def redacted(self) -> dict[str, object]:
        """Safe-to-display view for UI and logs. Never exposes the key."""
        return {
            "api_key": "set" if self.has_api_key else "missing",
            "base_url": self.base_url,
            "model": self.model,
            "llm_timeout_seconds": self.llm_timeout_seconds,
            "runtime_dir": str(self.runtime_dir),
        }


def read_dotenv(path: str | os.PathLike) -> dict[str, str]:
    """Parse a simple KEY=VALUE file. Missing file -> empty dict."""
    values: dict[str, str] = {}
    file = Path(path)
    if not file.is_file():
        return values
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_settings(dotenv_path: str | os.PathLike = ".env") -> Settings:
    """Environment variables first, then the .env file, then defaults."""
    file_values = read_dotenv(dotenv_path)

    def get(name: str, default: str = "") -> str:
        return os.environ.get(name, file_values.get(name, default)).strip()

    timeout_text = get("ELEC5620_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        timeout = float(timeout_text)
    except ValueError as exc:
        raise ValueError("ELEC5620_LLM_TIMEOUT_SECONDS must be a number") from exc

    return Settings(
        api_key=get("ELEC5620_API_KEY") or None,
        base_url=get("ELEC5620_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        model=get("ELEC5620_MODEL", DEFAULT_MODEL),
        llm_timeout_seconds=timeout,
        runtime_dir=Path(get("ELEC5620_RUNTIME_DIR", DEFAULT_RUNTIME_DIR)),
    )
