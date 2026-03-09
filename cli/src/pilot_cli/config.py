"""Pilot CLI configuration management.

Config stored at ~/.pilot/config.toml:
    api_url = "https://api.pilotspace.io"
    api_key = "ps_..."
    workspace_slug = "acme"
    database_url = "postgresql://user:pw@host:5432/db"  # for pg_dump/pg_restore
    supabase_url = "https://<project>.supabase.co"      # for Storage API
"""

from __future__ import annotations

import os as _os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import tomli_w

CONFIG_DIR: Path = Path.home() / ".pilot"
CONFIG_FILE: Path = CONFIG_DIR / "config.toml"


@dataclass
class PilotConfig:
    """Pilot Space CLI configuration loaded from ~/.pilot/config.toml."""

    api_url: str
    api_key: str
    workspace_slug: str
    database_url: str = field(default="")  # postgresql:// connection string for pg_dump/pg_restore
    supabase_url: str = field(default="")  # Supabase project URL for Storage API

    DEFAULT_API_URL: ClassVar[str] = "https://api.pilotspace.io"

    @classmethod
    def load(cls) -> PilotConfig:
        """Load config from ~/.pilot/config.toml.

        Raises:
            FileNotFoundError: If config file does not exist.
            KeyError: If required keys are missing from config.
        """
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(
                f"Config not found at {CONFIG_FILE}. Run `pilot login` first."
            )
        with CONFIG_FILE.open("rb") as f:
            data = tomllib.load(f)
        database_url = data.get("database_url") or _os.environ.get("DATABASE_URL") or ""
        supabase_url = data.get("supabase_url") or _os.environ.get("SUPABASE_URL") or ""
        return cls(
            api_url=data["api_url"],
            api_key=data["api_key"],
            workspace_slug=data["workspace_slug"],
            database_url=database_url,
            supabase_url=supabase_url,
        )

    def save(self) -> None:
        """Write config to ~/.pilot/config.toml (creates dir if needed).

        File permissions are set to 0o600 (user-only read/write) to protect
        the API key from other users on the system.
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = _os.open(str(CONFIG_FILE), _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
        with _os.fdopen(fd, "wb") as f:
            tomli_w.dump(
                {
                    "api_url": self.api_url,
                    "api_key": self.api_key,
                    "workspace_slug": self.workspace_slug,
                    "database_url": self.database_url,
                    "supabase_url": self.supabase_url,
                },
                f,
            )
