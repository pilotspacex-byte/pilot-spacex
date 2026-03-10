"""Tests for config read/write round-trip."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pilot_cli.config import PilotConfig


def test_config_save_and_load(tmp_path: Path) -> None:
    """Config round-trip: save then load returns same values."""
    config_dir = tmp_path / ".pilot"
    config_file = config_dir / "config.toml"

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
    ):
        cfg = PilotConfig(
            api_url="https://api.example.io",
            api_key="ps_test123",
            workspace_slug="acme",
        )
        cfg.save()
        loaded = PilotConfig.load()

    assert loaded.api_url == "https://api.example.io"
    assert loaded.api_key == "ps_test123"
    assert loaded.workspace_slug == "acme"


def test_config_save_sets_restrictive_permissions(tmp_path: Path) -> None:
    """Saved config file has 0o600 permissions to protect the API key."""
    config_dir = tmp_path / ".pilot"
    config_file = config_dir / "config.toml"

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
    ):
        cfg = PilotConfig(
            api_url="https://api.example.io",
            api_key="ps_secret",
            workspace_slug="acme",
        )
        cfg.save()

    # 0o600 = owner read+write only
    assert oct(config_file.stat().st_mode & 0o777) == oct(0o600)


def test_config_load_missing_raises(tmp_path: Path) -> None:
    """Load raises FileNotFoundError when config is absent."""
    missing = tmp_path / "no_config.toml"

    with patch("pilot_cli.config.CONFIG_FILE", missing):
        with pytest.raises(FileNotFoundError, match="pilot login"):
            PilotConfig.load()


def test_config_load_raises_on_missing_key(tmp_path: Path) -> None:
    """Load raises KeyError when required field is absent from config file."""
    config_dir = tmp_path / ".pilot"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    # Write a config that is missing workspace_slug
    config_file.write_bytes(b'api_url = "https://x.io"\napi_key = "ps_k"\n')

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
    ):
        with pytest.raises(KeyError):
            PilotConfig.load()


def test_config_save_creates_parent_dir(tmp_path: Path) -> None:
    """save() creates ~/.pilot/ directory if it does not exist."""
    config_dir = tmp_path / "deeply" / "nested" / ".pilot"
    config_file = config_dir / "config.toml"

    assert not config_dir.exists()

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
    ):
        cfg = PilotConfig(
            api_url="https://api.example.io",
            api_key="ps_test",
            workspace_slug="test-ws",
        )
        cfg.save()

    assert config_file.exists()


def test_default_api_url_class_var() -> None:
    """DEFAULT_API_URL class variable points to production endpoint."""
    assert PilotConfig.DEFAULT_API_URL == "https://api.pilotspace.io"


# ── New field: database_url and supabase_url ──────────────────────────────────


def test_config_has_database_url_field() -> None:
    """PilotConfig has a database_url field defaulting to empty string."""
    cfg = PilotConfig(
        api_url="https://api.example.io",
        api_key="ps_test",
        workspace_slug="acme",
        database_url="postgresql://user:pw@localhost:5432/db",
        supabase_url="https://proj.supabase.co",
    )
    assert cfg.database_url == "postgresql://user:pw@localhost:5432/db"
    assert cfg.supabase_url == "https://proj.supabase.co"


def test_config_save_and_load_includes_new_fields(tmp_path: Path) -> None:
    """Round-trip: database_url and supabase_url persist across save/load."""
    config_dir = tmp_path / ".pilot"
    config_file = config_dir / "config.toml"

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
    ):
        cfg = PilotConfig(
            api_url="https://api.example.io",
            api_key="ps_test123",
            workspace_slug="acme",
            database_url="postgresql://user:s3cr3t@localhost:5432/pilotdb",
            supabase_url="https://proj.supabase.co",
        )
        cfg.save()
        loaded = PilotConfig.load()

    assert loaded.database_url == "postgresql://user:s3cr3t@localhost:5432/pilotdb"
    assert loaded.supabase_url == "https://proj.supabase.co"


def test_config_load_database_url_falls_back_to_env(tmp_path: Path) -> None:
    """load() uses DATABASE_URL env var when database_url is absent from toml."""
    import os

    config_dir = tmp_path / ".pilot"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    # Config without database_url or supabase_url
    config_file.write_bytes(
        b'api_url = "https://x.io"\napi_key = "ps_k"\nworkspace_slug = "ws"\n'
    )

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
        patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://env-host/db",
                "SUPABASE_URL": "https://env.supabase.co",
            },
        ),
    ):
        loaded = PilotConfig.load()

    assert loaded.database_url == "postgresql://env-host/db"
    assert loaded.supabase_url == "https://env.supabase.co"


def test_config_load_database_url_empty_when_not_configured(tmp_path: Path) -> None:
    """load() returns empty string for database_url when absent from toml and env."""
    import os

    config_dir = tmp_path / ".pilot"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_bytes(
        b'api_url = "https://x.io"\napi_key = "ps_k"\nworkspace_slug = "ws"\n'
    )

    env_without_db = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "SUPABASE_URL")}

    with (
        patch("pilot_cli.config.CONFIG_FILE", config_file),
        patch("pilot_cli.config.CONFIG_DIR", config_dir),
        patch.dict(os.environ, env_without_db, clear=True),
    ):
        loaded = PilotConfig.load()

    assert loaded.database_url == ""
    assert loaded.supabase_url == ""
