"""LLM provider adapters for Pilot Space.

Providers:
- anthropic: Claude models (Opus 4.5, Sonnet, Haiku)
- openai: GPT models and embeddings
- google: Gemini models (Flash for low-latency)
- mock: Fake responses for development (no API calls)

BYOK (Bring Your Own Key):
- Workspace-level API key configuration
- Encrypted storage via Supabase Vault
- Automatic failover on provider errors

Mock Mode (Development Only):
- Enable with APP_ENV=development and AI_FAKE_MODE=true
- Returns realistic mock responses without API calls
- Useful for local development and testing
"""

from pilot_space.ai.providers.provider_selector import (
    Provider,
    ProviderConfig,
    ProviderSelector,
    TaskType,
    WorkspaceLLMConfig,
    resolve_workspace_llm_config,
)

__all__ = [
    "Provider",
    "ProviderConfig",
    "ProviderSelector",
    "TaskType",
    "WorkspaceLLMConfig",
    "resolve_workspace_llm_config",
]
