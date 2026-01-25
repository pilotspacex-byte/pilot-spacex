"""LLM provider adapters for Pilot Space.

Providers:
- anthropic: Claude models (Opus 4.5, Sonnet, Haiku)
- openai: GPT models and embeddings
- google: Gemini models (Flash for low-latency)

BYOK (Bring Your Own Key):
- Workspace-level API key configuration
- Encrypted storage via Supabase Vault
- Automatic failover on provider errors
"""
