"""Pilot CLI — AI-augmented SDLC developer workflow.

Usage:
    pilot login              Configure API key and workspace
    pilot implement PS-42    Implement an issue with Claude Code
"""

import typer

from pilot_cli.commands.backup import backup_app
from pilot_cli.commands.implement import implement_command
from pilot_cli.commands.login import login_command

app = typer.Typer(
    name="pilot",
    help="Pilot Space CLI — close the loop between issue and PR",
    no_args_is_help=True,
)

app.command("login")(login_command)
app.command("implement")(implement_command)
app.add_typer(backup_app, name="backup")


if __name__ == "__main__":
    app()
