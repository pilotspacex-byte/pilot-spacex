"""pilot implement — full workflow: fetch → clone → branch → inject → claude → PR."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import git
import typer
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from pilot_cli.api_client import PilotAPIClient, PilotAPIError
from pilot_cli.config import PilotConfig
from pilot_cli.github_client import GitHubClient, GitHubClientError

console = Console()

# Path where repos are cloned: ~/.pilot/workspaces/<workspace-slug>/<issue-id>/
WORKSPACES_DIR = Path.home() / ".pilot" / "workspaces"

_BACKEND_GATE = "uv run pyright && uv run ruff check && uv run pytest --cov=."
_FRONTEND_GATE = "pnpm lint && pnpm type-check && pnpm test"

# Allowed git hosting domains for clone_url (F-8: SSRF prevention)
_ALLOWED_CLONE_HOSTS = frozenset({"github.com", "gitlab.com", "bitbucket.org"})

# Safe slug pattern — alphanumeric, hyphens, underscores only (F-7: path traversal)
_SAFE_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def implement_command(
    issue_id: Annotated[str, typer.Argument(help="Issue ID, e.g. PS-42")],
    oneshot: Annotated[
        bool,
        typer.Option(
            "--oneshot",
            "-n",
            help="Non-interactive mode: run 'claude --print' for CI/automation.",
        ),
    ] = False,
) -> None:
    """Implement an issue with Claude Code — full automated workflow.

    Steps:
      1. Fetch issue context from Pilot Space API
      2. Clone the project repository
      3. Create a feature branch
      4. Inject CLAUDE.md with issue context
      5. Launch Claude Code (interactive or --oneshot for CI)
      6. Commit, push, create GitHub PR, update issue status
    """
    if not oneshot and os.environ.get("CLAUDECODE"):
        console.print(
            "[red]Error:[/red] Cannot run [bold]pilot implement[/bold] "
            "inside a Claude Code session."
        )
        console.print("[dim]Nested Claude Code sessions are not supported.[/dim]")
        console.print(
            f"[dim]Open a new terminal and run: "
            f"[bold]pilot implement {issue_id}[/bold][/dim]"
            f"\n[dim]Or use [bold]--oneshot[/bold] for non-interactive automation.[/dim]"
        )
        raise typer.Exit(1)

    try:
        config = PilotConfig.load()
    except FileNotFoundError as e:
        console.print("[red]Not logged in.[/red] Run [bold]pilot login[/bold] first.")
        raise typer.Exit(1) from e

    asyncio.run(_run_implement(issue_id, config, oneshot=oneshot))


_ONESHOT_PROMPT = (
    "Read CLAUDE.md in this repository. It contains an issue to implement. "
    "Implement the issue completely following every instruction in CLAUDE.md. "
    "Run the quality gates before finishing. Stage all changes when done."
)


async def _run_implement(issue_id: str, config: PilotConfig, *, oneshot: bool = False) -> None:
    client = PilotAPIClient.from_config(config)

    # ── Step 1: Fetch context ────────────────────────────────────────────────
    console.print(
        f"\n[dim][[/dim]1/6[dim]][/dim] Fetching issue context for "
        f"[bold]{issue_id}[/bold]...",
        end=" ",
    )
    try:
        ctx = await client.get_implement_context(issue_id)
    except PilotAPIError as e:
        console.print("[red]✗[/red]")
        if e.status_code == 403:
            console.print(
                "[red]Error:[/red] You are not assigned to this issue "
                "(or not an admin)."
            )
        elif e.status_code == 422:
            console.print(
                "[red]Error:[/red] No GitHub integration configured for this workspace."
            )
        else:
            console.print(f"[red]Error {e.status_code}:[/red] {e.detail}")
        raise typer.Exit(1) from e

    issue_title: str = ctx["issue"]["title"]
    suggested_branch: str = ctx["suggestedBranch"]
    clone_url: str = ctx["repository"]["cloneUrl"]
    default_branch: str = ctx["repository"]["defaultBranch"]
    console.print(f"[green]✓[/green] [dim]{issue_title!r}[/dim]")

    # F-8: Validate clone_url against allowed hosts to prevent SSRF
    _validate_clone_url(clone_url)

    # ── Step 2: Clone repository ─────────────────────────────────────────────
    # F-7: Validate path components to prevent directory traversal
    _validate_path_component(config.workspace_slug, "workspace_slug")
    _validate_path_component(issue_id, "issue_id")
    target_path = WORKSPACES_DIR / config.workspace_slug / issue_id
    # Extra check: ensure resolved path stays inside WORKSPACES_DIR
    if not str(target_path.resolve()).startswith(str(WORKSPACES_DIR.resolve())):
        console.print("[red]Error:[/red] Invalid workspace/issue path detected.")
        raise typer.Exit(1)
    console.print("[dim][[/dim]2/6[dim]][/dim] Cloning repository...", end=" ")

    if target_path.exists():
        console.print(
            f"\n[yellow]Warning:[/yellow] {target_path} already exists. "
            "Using existing clone."
        )
        repo = git.Repo(str(target_path))
    else:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            repo = git.Repo.clone_from(
                clone_url,
                str(target_path),
                depth=1,
                env=env,
            )
        except git.GitCommandError as e:
            console.print("[red]✗[/red]")
            console.print(
                f"[red]Clone failed:[/red] {e}\n"
                "[dim]Ensure you have SSH key configured or have run "
                "[bold]gh auth login[/bold][/dim]"
            )
            raise typer.Exit(1) from e

    console.print(f"[green]✓[/green] [dim]{target_path}[/dim]")

    # ── Step 3: Create branch ────────────────────────────────────────────────
    console.print(
        f"[dim][[/dim]3/6[dim]][/dim] Creating branch "
        f"[bold]{suggested_branch}[/bold]...",
        end=" ",
    )
    try:
        repo.git.checkout("-b", suggested_branch)
    except git.GitCommandError:
        # Branch already exists — check it out
        repo.git.checkout(suggested_branch)
    console.print("[green]✓[/green]")

    # ── Step 4: Inject CLAUDE.md ─────────────────────────────────────────────
    console.print(
        "[dim][[/dim]4/6[dim]][/dim] Injecting CLAUDE.md with issue context...",
        end=" ",
    )
    _inject_claude_md(target_path, ctx)
    console.print("[green]✓[/green]")

    # Snapshot HEAD SHA before Claude runs so step 6 can detect new commits.
    pre_claude_sha = repo.head.commit.hexsha

    # ── Step 5: Launch Claude Code ───────────────────────────────────────────
    if oneshot:
        console.print("[dim][[/dim]5/6[dim]][/dim] Running Claude Code (oneshot)...")
        claude_cmd = [
            "claude",
            "--print",
            _ONESHOT_PROMPT,
            "--dangerously-skip-permissions",
        ]
        # Strip CLAUDECODE so claude's own nested-session guard does not block us.
        # Safe: oneshot is a single non-interactive subprocess, not a recursive spawn.
        child_env: dict[str, str] | None = {
            k: v for k, v in os.environ.items() if k != "CLAUDECODE"
        }
    else:
        console.print("[dim][[/dim]5/6[dim]][/dim] Launching Claude Code...")
        console.print("[dim]  (press Ctrl-C or type /exit to stop Claude Code)[/dim]\n")
        claude_cmd = ["claude"]
        child_env = None  # inherit full environment

    try:
        result = subprocess.run(claude_cmd, cwd=str(target_path), env=child_env)
    except FileNotFoundError:
        console.print("\n[red]Error:[/red] [bold]claude[/bold] command not found.")
        console.print("[dim]Install Claude Code: https://docs.anthropic.com/claude-code[/dim]")
        raise typer.Exit(1)
    if not oneshot:
        console.print()  # newline after interactive session exits
    if result.returncode != 0:
        console.print(
            f"[yellow]Warning:[/yellow] Claude Code exited with code {result.returncode}. "
            "Any staged changes will still be committed."
        )

    # ── Step 6: Commit, push, PR ─────────────────────────────────────────────
    console.print("[dim][[/dim]6/6[dim]][/dim] Creating pull request...", end=" ")

    repo.git.add("-A")
    # Claude may have committed changes itself (common in oneshot mode).
    # Detect both cases: unstaged/staged changes AND new commits from Claude.
    has_staged = repo.is_dirty(untracked_files=True)
    has_new_commits = repo.head.commit.hexsha != pre_claude_sha
    if not has_staged and not has_new_commits:
        console.print()
        console.print(
            "[yellow]Warning:[/yellow] No changes after Claude Code "
            "— skipping commit and PR."
        )
        return

    # Only create a new commit when there are staged changes to wrap.
    # If Claude already committed its work, skip creating a duplicate commit.
    if has_staged:
        # F-13: Sanitize issue_title to prevent commit message injection
        safe_title = _sanitize_text(issue_title, max_len=100)
        commit_msg = (
            f"feat({issue_id}): {safe_title}\n\n"
            f"Implemented via `pilot implement {issue_id}`.\n\n"
            f"Closes #{issue_id}"
        )
        repo.index.commit(commit_msg)

    repo.git.push("origin", suggested_branch)

    # Create GitHub PR
    github_token = _get_github_token()
    if github_token:
        try:
            gh = GitHubClient.from_clone_url(token=github_token, clone_url=clone_url)
            pr_body = _build_pr_body(issue_id, issue_title, ctx)
            pr = await gh.create_pull_request(
                title=f"feat({issue_id}): {issue_title}",
                body=pr_body,
                head=suggested_branch,
                base=default_branch,
            )
            console.print(f"[green]✓[/green] {pr.url}")
        except GitHubClientError as e:
            console.print(
                f"[yellow]⚠[/yellow] PR creation failed ({e.status_code}): {e}"
            )
            console.print("[dim]Branch pushed. Create PR manually at GitHub.[/dim]")
    else:
        console.print(
            "[yellow]⚠[/yellow] No GITHUB_TOKEN found "
            "— branch pushed but no PR created."
        )
        console.print("[dim]Set GITHUB_TOKEN env var or run: gh auth login[/dim]")

    # Update issue status → In Review
    try:
        await client.update_issue_status(issue_id, "in_review")
        console.print(f"Issue [bold]{issue_id}[/bold] updated → [bold]In Review[/bold]")
    except PilotAPIError as e:
        console.print(f"[yellow]Warning:[/yellow] Could not update issue status: {e}")


def _sanitize_text(text: str, max_len: int = 500) -> str:
    """Strip control characters and Markdown code-fence markers from user text.

    Prevents prompt injection when user-controlled content is rendered into
    CLAUDE.md (Claude Code's instruction context) or git commit messages.

    Args:
        text: Raw user-supplied string.
        max_len: Maximum allowed length after stripping.

    Returns:
        Sanitized, length-capped string safe for use in Markdown context.
    """
    # Remove carriage returns and other control characters (keep newlines + tabs)
    sanitized = re.sub(r"[\r\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Strip triple-backtick sequences that could escape/inject code blocks
    sanitized = sanitized.replace("```", "")
    return sanitized[:max_len].strip()


def _sanitize_context(ctx: dict[str, Any]) -> dict[str, Any]:
    """Sanitize all user-controlled text fields in the normalized context dict.

    Called before Jinja2 template rendering to prevent prompt injection of
    workspace/project/issue content into CLAUDE.md (F-5).
    """
    issue = ctx["issue"]
    issue["title"] = _sanitize_text(issue.get("title", ""), max_len=200)
    issue["description"] = _sanitize_text(issue.get("description") or "", max_len=2000)
    issue["acceptance_criteria"] = [
        _sanitize_text(c, max_len=500) for c in (issue.get("acceptance_criteria") or [])
    ]

    project = ctx["project"]
    project["name"] = _sanitize_text(project.get("name", ""), max_len=100)
    project["tech_stack_summary"] = _sanitize_text(
        project.get("tech_stack_summary", ""), max_len=300
    )

    workspace = ctx["workspace"]
    workspace["name"] = _sanitize_text(workspace.get("name", ""), max_len=100)

    linked_notes = ctx.get("linked_notes", [])
    for note in linked_notes:
        note["note_title"] = _sanitize_text(note.get("note_title", ""), max_len=200)
        note["relevant_blocks"] = [
            _sanitize_text(b, max_len=500) for b in (note.get("relevant_blocks") or [])
        ]

    return ctx


def _validate_clone_url(clone_url: str) -> None:
    """Validate that clone_url points to an allowed git hosting domain.

    Prevents SSRF attacks where a malicious server returns a crafted clone_url
    pointing to an attacker-controlled host (F-8).

    Args:
        clone_url: URL from the implement-context API response.

    Raises:
        typer.Exit: If the URL is invalid or points to a disallowed host.
    """
    try:
        parsed = urlparse(clone_url)
        host = parsed.hostname or ""
        # Strip port and normalize
        if host not in _ALLOWED_CLONE_HOSTS and not any(
            host.endswith(f".{allowed}") for allowed in _ALLOWED_CLONE_HOSTS
        ):
            console.print(
                f"[red]Error:[/red] Untrusted clone URL host: {host!r}. "
                f"Allowed: {', '.join(sorted(_ALLOWED_CLONE_HOSTS))}"
            )
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        console.print(f"[red]Error:[/red] Invalid clone URL: {clone_url!r}")
        raise typer.Exit(1)


def _validate_path_component(value: str, field: str) -> None:
    """Ensure a path component contains only safe characters.

    Prevents directory traversal attacks where a malicious server returns
    a workspace_slug or issue_id containing path separators (F-7).

    Args:
        value: The path component to validate (workspace slug or issue ID).
        field: Field name for error messages.

    Raises:
        typer.Exit: If the value contains unsafe characters.
    """
    if not _SAFE_SLUG_RE.match(value):
        console.print(
            f"[red]Error:[/red] Unsafe {field} value received from server: {value!r}"
        )
        raise typer.Exit(1)


def _normalize_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Normalize camelCase API response keys to snake_case for the Jinja2 template.

    The API returns camelCase (e.g. ``acceptanceCriteria``, ``cloneUrl``) but
    the CLAUDE_MD_TEMPLATE uses snake_case (e.g. ``acceptance_criteria``,
    ``clone_url``).  Only the fields referenced in the template are mapped.
    """
    issue_raw: dict[str, Any] = ctx["issue"]
    issue: dict[str, Any] = {
        "id": issue_raw.get("id", ""),
        "title": issue_raw.get("title", ""),
        "status": issue_raw.get("status", ""),
        "priority": issue_raw.get("priority", ""),
        "labels": issue_raw.get("labels", []),
        "description": issue_raw.get("description", ""),
        "acceptance_criteria": issue_raw.get("acceptanceCriteria", []),
    }

    repo_raw: dict[str, Any] = ctx["repository"]
    repository: dict[str, Any] = {
        "clone_url": repo_raw.get("cloneUrl", ""),
        "default_branch": repo_raw.get("defaultBranch", ""),
        "provider": repo_raw.get("provider", ""),
    }

    project_raw: dict[str, Any] = ctx["project"]
    project: dict[str, Any] = {
        "name": project_raw.get("name", ""),
        "tech_stack_summary": project_raw.get("techStackSummary", ""),
    }

    workspace_raw: dict[str, Any] = ctx["workspace"]
    workspace: dict[str, Any] = {
        "name": workspace_raw.get("name", ""),
        "slug": workspace_raw.get("slug", ""),
    }

    notes_raw: list[dict[str, Any]] = ctx.get("linkedNotes", [])
    linked_notes: list[dict[str, Any]] = [
        {
            "note_title": n.get("noteTitle", n.get("note_title", "")),
            "relevant_blocks": n.get("relevantBlocks", n.get("relevant_blocks", [])),
        }
        for n in notes_raw
    ]

    return {
        "issue": issue,
        "repository": repository,
        "project": project,
        "workspace": workspace,
        "linked_notes": linked_notes,
        "suggested_branch": ctx.get("suggestedBranch", ""),
    }


def _inject_claude_md(target_path: Path, ctx: dict[str, Any]) -> None:
    """Render CLAUDE.md from template; append to existing file if present.

    User-controlled text fields (title, description, notes, tech stack) are
    sanitized before rendering to prevent prompt injection into Claude Code's
    instruction context (F-5).
    """
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("CLAUDE_MD_TEMPLATE.md")

    normalized = _sanitize_context(_normalize_ctx(ctx))

    rendered = template.render(
        issue=normalized["issue"],
        linked_notes=normalized["linked_notes"],
        workspace=normalized["workspace"],
        project=normalized["project"],
        repository=normalized["repository"],
        suggested_branch=normalized["suggested_branch"],
        backend_quality_gate=_BACKEND_GATE,
        frontend_quality_gate=_FRONTEND_GATE,
    )

    claude_md = target_path / "CLAUDE.md"
    if claude_md.exists():
        # Append to existing CLAUDE.md — don't overwrite project conventions
        existing = claude_md.read_text()
        claude_md.write_text(existing + "\n\n---\n\n" + rendered)
    else:
        claude_md.write_text(rendered)


def _get_github_token() -> str | None:
    """Get GitHub token from GITHUB_TOKEN env var or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    # Try gh CLI
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip() or None
    return None


def _extract_issue_number(issue_id: str) -> str:
    """Extract numeric part from issue ID like 'PS-42' → '42'."""
    parts = issue_id.split("-")
    return parts[-1] if len(parts) > 1 else issue_id


def _build_pr_body(issue_id: str, title: str, ctx: dict[str, Any]) -> str:
    """Build a GitHub PR body with issue reference."""
    acceptance: list[str] = ctx["issue"].get("acceptanceCriteria", [])
    ac_lines = (
        "\n".join(f"- [ ] {c}" for c in acceptance)
        if acceptance
        else "_None specified._"
    )
    return (
        f"## Summary\n\n"
        f"Implements [{issue_id}] {title}\n\n"
        f"## Acceptance Criteria\n\n{ac_lines}\n\n"
        f"## Implementation\n\n"
        f"Implemented via `pilot implement {issue_id}`.\n\n"
        f"Closes #{issue_id}"
    )
