"""pilot login — configure Pilot Space API credentials."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.prompt import Prompt

from pilot_cli.api_client import PilotAPIClient, PilotAPIError
from pilot_cli.config import PilotConfig

console = Console()


def login_command() -> None:
    """Configure Pilot Space API credentials.

    Prompts for API URL and key, validates against the server,
    then writes ~/.pilot/config.toml.
    """
    console.print("[bold]Pilot Space CLI Login[/bold]")

    api_url = Prompt.ask(
        "Pilot Space API URL",
        default=PilotConfig.DEFAULT_API_URL,
    )
    api_key = Prompt.ask("API Key (from Settings → API Keys)", password=True)
    database_url = Prompt.ask(
        "PostgreSQL database URL",
        default="",
    )
    supabase_url = Prompt.ask(
        "Supabase project URL",
        default="",
    )

    console.print("Validating credentials...", end=" ")

    try:
        result = asyncio.run(_validate(api_url, api_key))
    except PilotAPIError as e:
        console.print("[red]✗[/red]")
        console.print(f"[red]Error {e.status_code}:[/red] Invalid API key")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print("[red]✗[/red]")
        console.print(f"[red]Connection error:[/red] {e}")
        raise typer.Exit(1) from e

    workspace_slug = result["workspace_slug"]
    config = PilotConfig(
        api_url=api_url,
        api_key=api_key,
        workspace_slug=workspace_slug,
        database_url=database_url,
        supabase_url=supabase_url,
    )
    config.save()

    console.print("[green]✓[/green]")
    console.print(f"Logged in to workspace: [bold]{workspace_slug}[/bold]")
    console.print("Config saved to: [dim]~/.pilot/config.toml[/dim]")


async def _validate(api_url: str, api_key: str) -> dict[str, str]:
    client = PilotAPIClient(api_url=api_url, api_key=api_key)
    return await client.validate_key()
