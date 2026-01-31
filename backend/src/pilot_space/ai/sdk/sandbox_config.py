"""SDK sandbox configuration for space-rooted execution.

Provides factory functions for creating Claude SDK configurations
with proper sandbox settings, permission modes, and tool restrictions.

Reference: docs/architect/scalable-agent-architecture.md
Design Decisions: DD-002 (BYOK), DD-003 (Human-in-the-Loop)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pilot_space.ai.sdk.file_hooks import FileBasedHookExecutor
    from pilot_space.spaces.base import SpaceContext


# Safe bash command patterns that auto-execute in sandbox
SAFE_BASH_PATTERNS: list[str] = [
    r"^cat\s+",  # Read files
    r"^ls\s+",  # List directories
    r"^ls$",  # List current directory
    r"^head\s+",  # Read file heads
    r"^tail\s+",  # Read file tails
    r"^grep\s+",  # Search patterns
    r"^find\s+",  # Find files
    r"^wc\s+",  # Word count
    r"^pwd$",  # Print working directory
    r"^echo\s+",  # Echo text
    r"^npm\s+test",  # Run tests
    r"^npm\s+run\s+lint",  # Run linting
    r"^npm\s+run\s+type-check",  # Type checking
    r"^pytest\s+",  # Python tests
    r"^python\s+-m\s+pytest",  # Python module tests
    r"^git\s+status",  # Git status
    r"^git\s+diff",  # Git diff
    r"^git\s+log",  # Git log
    r"^git\s+branch",  # Git branch
    r"^git\s+show",  # Git show
    r"^ruff\s+check",  # Ruff linting
    r"^ruff\s+format\s+--check",  # Ruff format check
    r"^mypy\s+",  # Type checking
    r"^uv\s+pip\s+list",  # List packages
]

# Dangerous bash patterns that should ALWAYS be denied
DANGEROUS_BASH_PATTERNS: list[str] = [
    r"rm\s+-rf\s+/",  # Destructive rm from root
    r"rm\s+-rf\s+\*",  # Destructive rm wildcard
    r"sudo\s+",  # Privilege escalation
    r"chmod\s+-R\s+777",  # Insecure permissions
    r"mkfs",  # Filesystem operations
    r"dd\s+if=/dev/zero",  # Disk operations
    r":\(\)\{.*\};:",  # Fork bomb
    r">\s*/dev/sd",  # Writing to raw devices
    r"/etc/passwd",  # System file access
    r"/etc/shadow",  # System file access
    r"curl\s+.*\|\s*sh",  # Piping curl to shell
    r"wget\s+.*\|\s*sh",  # Piping wget to shell
    r"eval\s+",  # Eval with untrusted input
    r"\$\(.*\)",  # Command substitution (dangerous in some contexts)
]

# Protected file patterns that should not be written
PROTECTED_FILE_PATTERNS: list[str] = [
    r"\.env$",  # Environment files
    r"\.env\.",  # Environment files with suffix
    r"\.pem$",  # Private keys
    r"\.key$",  # Private keys
    r"id_rsa",  # SSH keys
    r"id_ed25519",  # SSH keys
    r"\.ssh/",  # SSH directory
    r"credentials",  # Credentials files
    r"secrets?\.ya?ml",  # Secrets files
    r"\.kube/config",  # Kubernetes config
]


@dataclass
class SandboxSettings:
    """Sandbox configuration for Claude SDK.

    Mirrors the SDK's SandboxSettings structure for type safety.
    """

    enabled: bool = True
    auto_allow_bash_if_sandboxed: bool = True
    network: dict[str, bool] = field(
        default_factory=lambda: {
            "allow_local_binding": False,
            "allow_all_unix_sockets": False,
        }
    )


@dataclass
class SDKConfiguration:
    """Complete SDK configuration for space-rooted execution.

    Use configure_sdk_for_space() to create instances.
    """

    cwd: str
    setting_sources: list[str]
    sandbox: SandboxSettings
    permission_mode: str
    env: dict[str, str]
    allowed_tools: list[str]
    hooks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    max_tokens: int = 8192
    model: str = "claude-sonnet-4-20250514"

    def to_sdk_params(self) -> dict[str, Any]:
        """Convert to parameters for Claude SDK."""
        params = {
            "cwd": self.cwd,
            "setting_sources": self.setting_sources,
            "sandbox": {
                "enabled": self.sandbox.enabled,
                "auto_allow_bash_if_sandboxed": self.sandbox.auto_allow_bash_if_sandboxed,
                "network": self.sandbox.network,
            },
            "permission_mode": self.permission_mode,
            "env": self.env,
            "allowed_tools": self.allowed_tools,
            "max_tokens": self.max_tokens,
            "model": self.model,
        }
        if self.hooks:
            params["hooks"] = self.hooks
        return params


def configure_sdk_for_space(
    space_context: SpaceContext,
    *,
    permission_mode: str = "default",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
    additional_tools: list[str] | None = None,
    additional_env: dict[str, str] | None = None,
    hook_executor: FileBasedHookExecutor | None = None,
) -> SDKConfiguration:
    """Configure Claude SDK with space-rooted sandbox settings.

    Key Security Features:
    1. CWD binding - Agent rooted to user's workspace
    2. SandboxSettings - Prevents path traversal escapes
    3. Permission mode - Human-in-the-loop per DD-003
    4. Hooks - SDK-native permission control via hook_executor

    Args:
        space_context: SpaceContext from SpaceInterface.prepare()
        permission_mode: SDK permission mode (default, bypassAll, ask)
        model: Model identifier
        max_tokens: Maximum output tokens
        additional_tools: Extra tools to enable
        additional_env: Extra environment variables
        hook_executor: Optional FileBasedHookExecutor for SDK hooks

    Returns:
        SDKConfiguration ready for SDK initialization.

    Example:
        async with space.session() as context:
            hook_executor = FileBasedHookExecutor(context.hooks_file)
            config = configure_sdk_for_space(context, hook_executor=hook_executor)
            async for msg in query(prompt, options=config.to_sdk_params()):
                yield msg
    """
    # Base allowed tools (aligned with DD-003)
    base_tools = [
        # Read-only (auto-approved in sandbox)
        "Read",
        "Glob",
        "Grep",
        # Write (may require approval based on permission_mode)
        "Write",
        "Edit",
        # Execution (requires approval outside whitelist)
        "Bash",
        # Skills and subagents
        "Skill",
        "Task",
        # User interaction
        "AskUserQuestion",
        # Web access
        "WebFetch",
        "WebSearch",
        # Planning tools
        "TodoWrite",
        "TodoRead",
    ]

    allowed_tools = base_tools + (additional_tools or [])

    # Build environment
    env = space_context.to_sdk_env()
    if additional_env:
        env.update(additional_env)

    # Get hooks from hook_executor if provided
    hooks: dict[str, list[dict[str, Any]]] = {}
    if hook_executor:
        hooks = hook_executor.to_sdk_hooks()

    return SDKConfiguration(
        cwd=str(space_context.path),
        setting_sources=["project"],  # Load from .claude/
        sandbox=SandboxSettings(
            enabled=True,
            auto_allow_bash_if_sandboxed=True,
            network={
                "allow_local_binding": False,
                "allow_all_unix_sockets": False,
            },
        ),
        permission_mode=permission_mode,
        env=env,
        allowed_tools=allowed_tools,
        hooks=hooks,
        max_tokens=max_tokens,
        model=model,
    )


def is_bash_command_safe(command: str) -> bool:
    """Check if a bash command is safe to auto-execute.

    Args:
        command: Bash command to check

    Returns:
        True if command matches safe patterns and doesn't match
        dangerous patterns.
    """
    command = command.strip()

    # Check dangerous patterns first (always deny)
    if any(re.search(pattern, command, re.IGNORECASE) for pattern in DANGEROUS_BASH_PATTERNS):
        return False

    # Check safe patterns (allow if matches)
    return any(re.match(pattern, command, re.IGNORECASE) for pattern in SAFE_BASH_PATTERNS)


def is_file_protected(file_path: str) -> bool:
    """Check if a file path is protected.

    Args:
        file_path: Path to check

    Returns:
        True if file matches protected patterns.
    """
    return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in PROTECTED_FILE_PATTERNS)
