"""Claude Agent SDK configuration for PilotSpace.

Provides configuration options and factory functions for creating
Claude Agent SDK client instances with PilotSpace-specific settings.

Reference: docs/architect/claude-agent-sdk-architecture.md
Design Decisions: DD-002 (BYOK), DD-058 (SDK mode clarification)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID

from pilot_space.ai.sdk.sandbox_config import ModelTier

# Centralized model ID constants (DD-011 provider routing)
# These are default fallbacks; at runtime, use ModelTier.*.model_id or
# get_model_for_task() which respect PILOTSPACE_MODEL_*_DEFAULT env vars.
MODEL_SONNET: Final[str] = "claude-sonnet-4-20250514"
MODEL_OPUS: Final[str] = "claude-opus-4-5-20251101"
MODEL_HAIKU: Final[str] = "claude-haiku-4-5-20251001"
MODEL_GEMINI_FLASH: Final[str] = "gemini-2.0-flash"
MODEL_EMBEDDING: Final[str] = "text-embedding-3-large"

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.session.session_manager import SessionManager
    from pilot_space.ai.tools.mcp_server import ToolRegistry


@dataclass(frozen=True, kw_only=True)
class ClaudeAgentOptions:
    """Configuration options for Claude Agent SDK.

    Provides all settings needed to create a configured ClaudeSDKClient
    or use the query() function with PilotSpace infrastructure.

    Attributes:
        api_key: Anthropic API key (from SecureKeyStorage)
        model: Model identifier (default: claude-sonnet-4-20250514)
        max_tokens: Maximum output tokens per request
        temperature: Sampling temperature (0.0-1.0)
        system_prompt: Optional system prompt override
        tools: Optional list of MCP tools
        tool_registry: Optional tool registry for MCP server
        session_manager: Optional session manager for multi-turn
        max_retries: Maximum retry attempts on failure
        timeout_seconds: Request timeout in seconds
        stream: Whether to enable streaming responses
        metadata: Additional metadata for tracking
    """

    api_key: str
    model: str = MODEL_SONNET
    max_tokens: int = 8192
    temperature: float = 0.7
    system_prompt: str | None = None
    tools: list[dict[str, Any]] | None = None
    tool_registry: ToolRegistry | None = None
    session_manager: SessionManager | None = None
    max_retries: int = 3
    timeout_seconds: int = 300
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_sdk_params(self) -> dict[str, Any]:
        """Convert to parameters for Claude Agent SDK client.

        Returns:
            Dictionary of parameters suitable for ClaudeSDKClient constructor
            or query() function call.
        """
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if self.system_prompt:
            params["system"] = self.system_prompt

        if self.tools:
            params["tools"] = self.tools

        if self.stream:
            params["stream"] = True

        return params


async def create_agent_options(
    workspace_id: str,
    user_id: str,
    key_storage: SecureKeyStorage,
    model: str = MODEL_SONNET,
    tool_registry: ToolRegistry | None = None,
    session_manager: SessionManager | None = None,
    **kwargs: Any,
) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions with decrypted API key.

    Factory function that:
    1. Retrieves and decrypts Anthropic API key from SecureKeyStorage
    2. Validates key exists for workspace/user
    3. Returns configured ClaudeAgentOptions

    Args:
        workspace_id: Workspace UUID for key lookup
        user_id: User UUID for key lookup
        key_storage: SecureKeyStorage instance for key retrieval
        model: Model identifier (default: claude-sonnet-4-20250514)
        tool_registry: Optional MCP tool registry
        session_manager: Optional session manager for multi-turn
        **kwargs: Additional options to pass to ClaudeAgentOptions

    Returns:
        Configured ClaudeAgentOptions instance

    Raises:
        ValueError: If API key not found for workspace/user
        Exception: If key decryption fails
    """
    # Retrieve API key from secure storage
    # SecureKeyStorage.get_api_key only takes workspace_id and provider
    api_key = await key_storage.get_api_key(
        workspace_id=UUID(workspace_id),
        provider="anthropic",
    )

    if not api_key:
        raise ValueError(
            f"Anthropic API key not found for workspace {workspace_id}, "
            f"user {user_id}. Please configure API keys in workspace settings."
        )

    return ClaudeAgentOptions(
        api_key=api_key,
        model=model,
        tool_registry=tool_registry,
        session_manager=session_manager,
        **kwargs,
    )


def get_model_for_task(task_type: str) -> str:
    """Get optimal model for task type based on DD-011.

    Provider routing rules:
    - Code/Architecture: Claude Sonnet/Opus (best reasoning)
    - Latency-sensitive: Gemini Flash (fastest)
    - Embeddings: OpenAI text-embedding-3-large (best quality)

    Anthropic model IDs are resolved via ModelTier.model_id which respects
    PILOTSPACE_MODEL_*_DEFAULT env vars for deployment-time overrides.

    Args:
        task_type: Task classification (code, latency, embedding, general)

    Returns:
        Model identifier string
    """
    model_mapping: dict[str, ModelTier | str] = {
        "code": ModelTier.SONNET,
        "architecture": ModelTier.OPUS,
        "latency": MODEL_GEMINI_FLASH,
        "embedding": MODEL_EMBEDDING,
        "general": ModelTier.SONNET,
    }

    tier_or_id = model_mapping.get(task_type, ModelTier.SONNET)
    if isinstance(tier_or_id, ModelTier):
        return tier_or_id.model_id
    return tier_or_id


def build_sdk_env(api_key: str) -> dict[str, str]:
    """Build minimal env dict for SDK subprocess with base URL forwarding.

    Centralizes the env dict pattern used by ai_context_agent,
    plan_generation_agent, and subagents. Forwards ANTHROPIC_BASE_URL
    when set, enabling admin-configured proxies/staging endpoints.

    Args:
        api_key: Anthropic API key for the workspace.

    Returns:
        Environment dict for SDK subprocess execution.
    """
    env: dict[str, str] = {
        "ANTHROPIC_API_KEY": api_key,
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
    }
    from pilot_space.config import get_settings

    base_url = get_settings().anthropic_base_url
    if base_url:
        env["ANTHROPIC_BASE_URL"] = base_url
    return env


def build_sdk_env_for_user(
    api_key: str,
    user_ai_settings: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Build env dict for SDK subprocess with user-level overrides.

    Extends build_sdk_env with per-user base_url override from ai_settings.

    Args:
        api_key: Anthropic API key for the workspace.
        user_ai_settings: Optional per-user AI settings dict.

    Returns:
        Environment dict for SDK subprocess execution.
    """
    env = build_sdk_env(api_key)

    # User base_url override takes priority over system setting
    if user_ai_settings:
        user_base_url = user_ai_settings.get("base_url")
        if user_base_url:
            env["ANTHROPIC_BASE_URL"] = str(user_base_url)

    return env
