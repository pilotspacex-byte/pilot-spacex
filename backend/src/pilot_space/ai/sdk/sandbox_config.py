"""SDK sandbox configuration for space-rooted execution.

Provides factory functions for creating Claude SDK configurations
with proper sandbox settings, permission modes, and tool restrictions.

Reference: docs/architect/scalable-agent-architecture.md
Design Decisions: DD-002 (BYOK), DD-003 (Human-in-the-Loop)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pilot_space.spaces.base import SpaceContext


class ModelTier(str, Enum):
    """Model tier enum for DD-011 provider routing.

    Users select a tier (sonnet/opus/haiku), which resolves to a full model ID
    via environment variables. This decouples model selection from hardcoded IDs.

    Env vars:
        PILOTSPACE_MODEL_SONNET_DEFAULT: Full model ID for sonnet tier
        PILOTSPACE_MODEL_OPUS_DEFAULT: Full model ID for opus tier
        PILOTSPACE_MODEL_HAIKU_DEFAULT: Full model ID for haiku tier
    """

    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"

    @property
    def model_id(self) -> str:
        """Resolve tier to full model ID from env vars with sensible defaults."""
        defaults = {
            ModelTier.SONNET: "claude-sonnet-4-20250514",
            ModelTier.OPUS: "claude-opus-4-20250514",
            ModelTier.HAIKU: "claude-haiku-4-5-20251001",
        }
        env_keys = {
            ModelTier.SONNET: "PILOTSPACE_MODEL_SONNET_DEFAULT",
            ModelTier.OPUS: "PILOTSPACE_MODEL_OPUS_DEFAULT",
            ModelTier.HAIKU: "PILOTSPACE_MODEL_HAIKU_DEFAULT",
        }
        return os.environ.get(env_keys[self], defaults[self])

    @property
    def default_budget_usd(self) -> float:
        """Default per-request budget ceiling for this tier."""
        budgets = {
            ModelTier.SONNET: 0.50,
            ModelTier.OPUS: 2.00,
            ModelTier.HAIKU: 0.10,
        }
        return budgets[self]

    @property
    def fallback_tier(self) -> ModelTier | None:
        """Automatic fallback tier when this tier's model fails."""
        fallbacks: dict[ModelTier, ModelTier | None] = {
            ModelTier.OPUS: ModelTier.SONNET,
            ModelTier.SONNET: ModelTier.HAIKU,
            ModelTier.HAIKU: None,
        }
        return fallbacks[self]

    @property
    def default_max_turns(self) -> int:
        """Default maximum conversation turns for this tier."""
        limits = {
            ModelTier.SONNET: 25,
            ModelTier.OPUS: 15,
            ModelTier.HAIKU: 50,
        }
        return limits[self]


def resolve_model(model: str | ModelTier) -> str:
    """Resolve a model identifier to a full model ID.

    Accepts either a ModelTier enum or a raw model string.
    If a ModelTier is provided, resolves via env var.
    If a raw string matching a tier name is provided, treats it as a tier.
    Otherwise returns the string as-is (for custom/direct model IDs).

    Args:
        model: ModelTier enum, tier name ("sonnet"/"opus"), or full model ID

    Returns:
        Full model identifier string
    """
    if isinstance(model, ModelTier):
        return model.model_id

    # Check if string matches a tier name
    try:
        tier = ModelTier(model.lower())
        return tier.model_id
    except ValueError:
        return model


class HookExecutor(Protocol):
    """Protocol for hook executors that produce SDK-compatible hooks."""

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]: ...


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
    prompt_caching: bool = True
    max_thinking_tokens: int | None = None
    include_partial_messages: bool = False
    tool_search_enabled: bool = False
    effort: str | None = None  # "low" | "medium" | "high"
    citations_enabled: bool = False
    memory_enabled: bool = False
    # Cost & resilience controls (G1-G3)
    max_budget_usd: float | None = None
    fallback_model: str | None = None
    max_turns: int | None = None
    # Structured output enforcement (G4)
    output_format: dict[str, Any] | None = None
    # Advanced SDK features (G5-G7)
    enable_file_checkpointing: bool = False
    betas: list[str] = field(default_factory=list)
    system_prompt_base: str | None = None  # SDK-native prompt caching

    def to_sdk_params(self) -> dict[str, Any]:
        """Convert to parameters for Claude SDK."""
        params: dict[str, Any] = {
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
        if self.max_thinking_tokens is not None:
            params["max_thinking_tokens"] = self.max_thinking_tokens
        if self.include_partial_messages:
            params["include_partial_messages"] = True
        if self.tool_search_enabled:
            params["tool_search"] = True
        if self.effort is not None:
            params["effort"] = self.effort
        if self.citations_enabled:
            params["citations"] = True
        if self.memory_enabled:
            params["memory"] = True
        # Cost & resilience controls (G1-G3)
        if self.max_budget_usd is not None:
            params["max_budget_usd"] = self.max_budget_usd
        if self.fallback_model is not None:
            params["fallback_model"] = self.fallback_model
        if self.max_turns is not None:
            params["max_turns"] = self.max_turns
        # Structured output enforcement (G4)
        if self.output_format is not None:
            params["output_format"] = self.output_format
        # Advanced SDK features (G5-G7)
        if self.enable_file_checkpointing:
            params["enable_file_checkpointing"] = True
        if self.betas:
            params["betas"] = self.betas
        if self.system_prompt_base is not None:
            params["system_prompt"] = {
                "content": self.system_prompt_base,
                "cache_control": "ephemeral",
            }
        return params


def configure_sdk_for_space(
    space_context: SpaceContext,
    *,
    permission_mode: str = "default",
    model: str | ModelTier = ModelTier.SONNET,
    max_tokens: int = 8192,
    additional_tools: list[str] | None = None,
    additional_env: dict[str, str] | None = None,
    hook_executor: HookExecutor | None = None,
    include_partial_messages: bool = False,
    max_thinking_tokens: int | None = None,
    effort: str | None = None,
    citations_enabled: bool = False,
    memory_enabled: bool = False,
    max_budget_usd: float | None = None,
    max_turns: int | None = None,
    output_format: dict[str, Any] | None = None,
    enable_file_checkpointing: bool = False,
    betas: list[str] | None = None,
    system_prompt_base: str | None = None,
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
        include_partial_messages: Enable partial streaming during tool execution
        max_thinking_tokens: Max tokens for extended thinking (None=disabled)
        effort: Quality/speed tradeoff ("low"|"medium"|"high"|None)
        citations_enabled: Enable source citation tracking
        memory_enabled: Enable cross-session memory persistence
        max_budget_usd: Per-request cost ceiling (None=use tier default)
        max_turns: Maximum conversation turns (None=use tier default)
        output_format: JSON schema dict for structured output enforcement
        enable_file_checkpointing: Enable SDK file checkpoint/rewind (G5)
        betas: SDK beta features list (e.g. ["context-1m-2025-08-07"]) (G6)
        system_prompt_base: Base system prompt for SDK-native caching (G7)

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

    # Auto-enable tool search when >10 tools to optimize context window
    tool_search_enabled = len(allowed_tools) > 10

    # Resolve model tier to full model ID (DD-011 provider routing)
    resolved_model = resolve_model(model)

    # Auto-set max_thinking_tokens for Opus models (B2: extended thinking)
    effective_thinking_tokens = max_thinking_tokens
    if effective_thinking_tokens is None and "opus" in resolved_model.lower():
        effective_thinking_tokens = 10000

    # Derive cost/resilience defaults from tier (G1-G3)
    model_tier = _resolve_tier(model)
    effective_budget = (
        max_budget_usd
        if max_budget_usd is not None
        else (model_tier.default_budget_usd if model_tier else None)
    )
    effective_max_turns = (
        max_turns
        if max_turns is not None
        else (model_tier.default_max_turns if model_tier else None)
    )
    effective_fallback = (
        model_tier.fallback_tier.model_id if model_tier and model_tier.fallback_tier else None
    )

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
        model=resolved_model,
        tool_search_enabled=tool_search_enabled,
        include_partial_messages=include_partial_messages,
        max_thinking_tokens=effective_thinking_tokens,
        effort=effort,
        citations_enabled=citations_enabled,
        memory_enabled=memory_enabled,
        max_budget_usd=effective_budget,
        fallback_model=effective_fallback,
        max_turns=effective_max_turns,
        output_format=output_format,
        enable_file_checkpointing=enable_file_checkpointing,
        betas=betas or [],
        system_prompt_base=system_prompt_base,
    )


def _resolve_tier(model: str | ModelTier) -> ModelTier | None:
    """Resolve model input to a ModelTier if possible.

    Returns None for custom model strings that don't match a tier.
    """
    if isinstance(model, ModelTier):
        return model
    try:
        return ModelTier(model.lower())
    except ValueError:
        return None


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
