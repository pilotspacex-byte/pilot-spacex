"""Tests for pilot login command — credentials, validation, config persistence."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from pilot_cli.api_client import PilotAPIError
from pilot_cli.main import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_URL = "https://api.example.io"
_API_KEY = "ps_test_key"
_WORKSPACE_SLUG = "acme"
_DATABASE_URL = "postgresql://user:pw@localhost:5432/db"
_SUPABASE_URL = "https://proj.supabase.co"

# All 4 prompt answers in order: api_url, api_key, database_url, supabase_url
_ALL_PROMPTS = [_API_URL, _API_KEY, _DATABASE_URL, _SUPABASE_URL]


def _make_validate_result(slug: str = _WORKSPACE_SLUG) -> dict[str, str]:
    return {"workspace_slug": slug}


# ---------------------------------------------------------------------------
# TestLoginHappyPath
# ---------------------------------------------------------------------------


class TestLoginHappyPath:
    def test_successful_login_saves_config(self) -> None:
        """Valid credentials → config saved → success message with workspace slug."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(return_value=_make_validate_result()),
            ),
            patch("pilot_cli.commands.login.PilotConfig") as mock_config_cls,
        ):
            mock_config_instance = MagicMock()
            mock_config_cls.DEFAULT_API_URL = _API_URL
            mock_config_cls.return_value = mock_config_instance

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.output
        mock_config_instance.save.assert_called_once()

    def test_successful_login_prints_workspace_slug(self) -> None:
        """Successful login prints the workspace slug from the server response."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(return_value=_make_validate_result("my-workspace")),
            ),
            patch("pilot_cli.commands.login.PilotConfig") as mock_config_cls,
        ):
            mock_config_cls.DEFAULT_API_URL = _API_URL
            mock_config_cls.return_value = MagicMock()

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.output
        assert "my-workspace" in result.output

    def test_successful_login_prints_config_path_hint(self) -> None:
        """Successful login prints config file location hint."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(return_value=_make_validate_result()),
            ),
            patch("pilot_cli.commands.login.PilotConfig") as mock_config_cls,
        ):
            mock_config_cls.DEFAULT_API_URL = _API_URL
            mock_config_cls.return_value = MagicMock()

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.output
        assert "config.toml" in result.output

    def test_login_passes_database_url_and_supabase_url_to_config(self) -> None:
        """login_command passes database_url and supabase_url to PilotConfig constructor."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(return_value=_make_validate_result()),
            ),
            patch("pilot_cli.commands.login.PilotConfig") as mock_config_cls,
        ):
            mock_config_cls.DEFAULT_API_URL = _API_URL
            mock_config_cls.return_value = MagicMock()

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.output
        # Verify PilotConfig was constructed with database_url and supabase_url
        mock_config_cls.assert_called_once_with(
            api_url=_API_URL,
            api_key=_API_KEY,
            workspace_slug=_WORKSPACE_SLUG,
            database_url=_DATABASE_URL,
            supabase_url=_SUPABASE_URL,
        )


# ---------------------------------------------------------------------------
# TestLoginPilotAPIError
# ---------------------------------------------------------------------------


class TestLoginPilotAPIError:
    def test_invalid_api_key_exits_1(self) -> None:
        """PilotAPIError from validate → prints error with status code → exits 1."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=[_API_URL, "ps_bad_key", _DATABASE_URL, _SUPABASE_URL],
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=PilotAPIError(401, "Invalid API key")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1
        assert "401" in result.output

    def test_403_api_error_exits_1(self) -> None:
        """403 PilotAPIError → exits 1 with error output."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=PilotAPIError(403, "Forbidden")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1

    def test_500_api_error_exits_1(self) -> None:
        """500 PilotAPIError → exits 1."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=PilotAPIError(500, "Server error")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# TestLoginConnectionError
# ---------------------------------------------------------------------------


class TestLoginConnectionError:
    def test_connection_refused_exits_1(self) -> None:
        """Non-PilotAPIError exception (e.g. ConnectionRefusedError) → exits 1."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=ConnectionRefusedError("Connection refused")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1
        assert "Connection error" in result.output

    def test_timeout_error_exits_1(self) -> None:
        """TimeoutError exits 1 and prints connection error message."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=TimeoutError("timed out")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1
        assert "Connection error" in result.output

    def test_generic_exception_exits_1(self) -> None:
        """Any generic Exception → exits 1 and prints connection error."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=RuntimeError("unexpected failure")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1
        assert "Connection error" in result.output

    def test_connection_error_prints_exception_message(self) -> None:
        """Connection error output includes the exception message."""
        with (
            patch(
                "pilot_cli.commands.login.Prompt.ask",
                side_effect=list(_ALL_PROMPTS),
            ),
            patch(
                "pilot_cli.commands.login._validate",
                new=AsyncMock(side_effect=OSError("Network unreachable")),
            ),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 1
        assert "Network unreachable" in result.output


# ---------------------------------------------------------------------------
# TestValidateHelper
# ---------------------------------------------------------------------------


class TestValidateHelper:
    @pytest.mark.asyncio
    async def test_validate_calls_api_client(self) -> None:
        """_validate constructs PilotAPIClient and calls validate_key."""
        from pilot_cli.commands.login import _validate

        mock_result = {"workspace_slug": "test-ws"}
        with patch("pilot_cli.commands.login.PilotAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.validate_key.return_value = mock_result
            mock_client_cls.return_value = mock_client

            result = await _validate(_API_URL, _API_KEY)

        assert result == mock_result
        mock_client_cls.assert_called_once_with(api_url=_API_URL, api_key=_API_KEY)
        mock_client.validate_key.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validate_propagates_pilot_api_error(self) -> None:
        """_validate lets PilotAPIError bubble up to the caller."""
        from pilot_cli.commands.login import _validate

        with patch("pilot_cli.commands.login.PilotAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.validate_key.side_effect = PilotAPIError(401, "bad key")
            mock_client_cls.return_value = mock_client

            with pytest.raises(PilotAPIError) as exc_info:
                await _validate(_API_URL, "bad_key")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_propagates_network_error(self) -> None:
        """_validate propagates non-API exceptions (network failures, etc.)."""
        from pilot_cli.commands.login import _validate

        with patch("pilot_cli.commands.login.PilotAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.validate_key.side_effect = ConnectionError("refused")
            mock_client_cls.return_value = mock_client

            with pytest.raises(ConnectionError):
                await _validate(_API_URL, _API_KEY)
