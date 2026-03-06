"""Configuration management for Pilot Space.

Uses Pydantic Settings for environment variable loading and validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import DirectoryPath, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_FOLDER = "/tmp/pilot-space/spaces"

default_folder_path = Path(DEFAULT_FOLDER)
default_folder_path.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    Secret values are stored as SecretStr to prevent accidental logging.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Pilot Space"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database (PostgreSQL via Supabase)
    database_url: SecretStr = Field(
        default=SecretStr("postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"),
        description="PostgreSQL connection URL (async driver)",
    )
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout: int = Field(default=30, ge=1)

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(default=10, ge=1)

    # Supabase
    supabase_url: str = Field(
        default="http://localhost:54321",
        description="Supabase project URL",
    )
    supabase_anon_key: SecretStr = Field(
        default=SecretStr(""),
        description="Supabase anonymous key (public)",
    )
    supabase_service_key: SecretStr = Field(
        default=SecretStr(""),
        description="Supabase service role key (server-side only)",
    )
    supabase_jwt_secret: SecretStr = Field(
        default=SecretStr("super-secret-jwt-token-with-at-least-32-characters-long"),
        description="JWT secret for token validation (same as Supabase)",
    )

    # Meilisearch
    meilisearch_url: str = Field(
        default="http://localhost:7700",
        description="Meilisearch server URL",
    )
    meilisearch_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Meilisearch API key",
    )

    # AI Providers (BYOK - Bring Your Own Key)
    # These are optional at app level; workspace-level keys take precedence
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Default Anthropic API key (Claude)",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="Default OpenAI API key (embeddings)",
    )
    google_api_key: SecretStr | None = Field(
        default=None,
        description="Default Google AI API key (Gemini)",
    )

    # AI Configuration
    ai_timeout_seconds: int = Field(default=300, ge=30, le=600)
    ai_max_retries: int = Field(default=3, ge=1, le=10)
    ai_ghost_text_debounce_ms: int = Field(default=500, ge=100, le=2000)
    ai_ghost_text_max_tokens: int = Field(default=50, ge=10, le=200)

    # Fake AI Mode (development only - no external API calls)
    ai_fake_mode: bool = Field(
        default=False,
        description="Enable fake AI responses for local development (requires app_env=development)",
    )
    ai_fake_latency_ms: int = Field(
        default=500,
        ge=0,
        le=5000,
        description="Simulated AI response latency in milliseconds",
    )
    ai_fake_streaming_chunk_delay_ms: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Delay between streaming chunks in milliseconds",
    )

    # Rate Limiting (NFR-019)
    rate_limit_standard_per_minute: int = Field(default=1000, ge=100)
    rate_limit_ai_per_minute: int = Field(default=100, ge=10)

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )

    # Security
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    encryption_key: SecretStr = Field(
        default=SecretStr(""),
        description="Fernet encryption key for API key storage (32-byte base64-encoded)",
    )

    # Auth Provider (supabase | authcore)
    auth_provider: str = Field(
        default="supabase",
        description="JWT authority to use. 'supabase' (default) or 'authcore'.",
    )
    authcore_public_key: str | None = Field(
        default=None,
        description="PEM-encoded RSA public key for AuthCore RS256 token verification.",
    )
    authcore_url: str | None = Field(
        default=None,
        description="Base URL of the AuthCore service (reserved for future use).",
    )

    # Space Configuration (Agent Isolation)
    space_storage_root: DirectoryPath = Field(
        default=default_folder_path,
        description="Root directory for user workspace storage",
    )
    system_templates_dir: DirectoryPath = Field(
        default=Path(__file__).parent / "ai" / "templates",
        description="Directory containing system-provided .claude templates",
    )

    # GitHub OAuth Integration
    github_client_id: str = Field(
        default="",
        description="GitHub OAuth App Client ID",
    )
    github_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="GitHub OAuth App Client Secret",
    )
    github_webhook_secret: SecretStr = Field(
        default=SecretStr(""),
        description="GitHub Webhook secret for signature verification",
    )
    github_callback_url: str = Field(
        default="http://localhost:8000/api/v1/integrations/github/callback",
        description="GitHub OAuth callback URL",
    )

    # Google OAuth Integration (Drive)
    google_client_id: str = Field(
        default="",
        description="Google OAuth Client ID for Drive integration",
    )
    google_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Google OAuth Client Secret for Drive integration",
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL for OAuth callback construction",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Uses lru_cache to ensure settings are loaded once and reused.

    Returns:
        Settings instance with values from environment.
    """
    return Settings()