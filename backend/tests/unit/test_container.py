"""Unit tests for dependency injection container.

Verifies that the container correctly wires dependencies including:
- Repository factory resolution
- Service factory resolution
- Singleton providers (config, engine, auth)
- ContextVar session injection via get_current_session()
- Dependency chains (service → repository → session)
- Provider lifetimes and scoping
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from dependency_injector import providers

# Mock problematic imports before importing container
sys.modules["pilot_space.ai.agents.subagents.pr_review_subagent"] = MagicMock()

from pilot_space.container import Container, create_container, get_container  # noqa: E402
from pilot_space.dependencies.auth import _request_session_ctx, get_current_session  # noqa: E402

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# Container Initialization Tests
# ============================================================================


class TestContainerCreation:
    """Tests for container creation and configuration."""

    def test_create_container_returns_instance(self) -> None:
        """Test that create_container returns a Container instance."""
        container = create_container()

        assert container is not None
        assert isinstance(container, Container)

    def test_create_container_with_settings_override(self) -> None:
        """Test that create_container accepts settings override."""
        from pilot_space.config import Settings

        settings = Settings(
            database_url="postgresql+asyncpg://test",
            redis_url="redis://test",
        )
        container = create_container(settings=settings)

        # Verify override was applied
        resolved_settings = container.config()
        assert resolved_settings.redis_url == "redis://test"

    def test_get_container_returns_global_instance(self) -> None:
        """Test that get_container returns the global container."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2  # Same singleton instance

    def test_container_has_wiring_config(self) -> None:
        """Test that container has correct wiring configuration."""
        container = create_container()

        assert container.wiring_config is not None
        assert len(container.wiring_config.modules) > 0

        # Verify key modules are wired
        module_names = [str(m) for m in container.wiring_config.modules]
        assert "pilot_space.api.v1.routers.issues" in module_names
        assert "pilot_space.api.v1.routers.workspaces" in module_names
        assert "pilot_space.api.v1.routers.ai_chat" in module_names


# ============================================================================
# Singleton Provider Tests
# ============================================================================


class TestSingletonProviders:
    """Tests for singleton providers (config, engine, auth)."""

    def test_config_provider_returns_settings(self) -> None:
        """Test that config provider returns Settings instance."""
        container = create_container()

        config = container.config()

        assert config is not None
        assert hasattr(config, "database_url")
        assert hasattr(config, "redis_url")

    def test_config_provider_is_singleton(self) -> None:
        """Test that config provider returns same instance."""
        container = create_container()

        config1 = container.config()
        config2 = container.config()

        assert config1 is config2

    def test_engine_provider_returns_engine(self) -> None:
        """Test that engine provider returns AsyncEngine."""
        container = create_container()

        engine = container.engine()

        assert engine is not None
        assert hasattr(engine, "dispose")  # Verify it's an engine instance

    def test_engine_provider_is_singleton(self) -> None:
        """Test that engine provider returns same instance."""
        container = create_container()

        engine1 = container.engine()
        engine2 = container.engine()

        assert engine1 is engine2

    def test_session_factory_provider_returns_factory(self) -> None:
        """Test that session_factory provider returns sessionmaker."""
        container = create_container()

        session_factory = container.session_factory()

        assert session_factory is not None
        assert callable(session_factory)

    def test_supabase_auth_provider_returns_auth_instance(self) -> None:
        """Test that supabase_auth provider returns SupabaseAuth."""
        container = create_container()

        auth = container.supabase_auth()

        assert auth is not None
        assert hasattr(auth, "validate_token")


# ============================================================================
# Repository Factory Provider Tests
# ============================================================================


class TestRepositoryProviders:
    """Tests for repository factory providers."""

    def test_user_repository_provider_exists(self) -> None:
        """Test that user_repository provider exists."""
        container = create_container()

        assert hasattr(container, "user_repository")
        assert isinstance(container.user_repository, providers.Factory)

    def test_workspace_repository_provider_exists(self) -> None:
        """Test that workspace_repository provider exists."""
        container = create_container()

        assert hasattr(container, "workspace_repository")
        assert isinstance(container.workspace_repository, providers.Factory)

    def test_issue_repository_provider_exists(self) -> None:
        """Test that issue_repository provider exists."""
        container = create_container()

        assert hasattr(container, "issue_repository")
        assert isinstance(container.issue_repository, providers.Factory)

    def test_note_repository_provider_exists(self) -> None:
        """Test that note_repository provider exists."""
        container = create_container()

        assert hasattr(container, "note_repository")
        assert isinstance(container.note_repository, providers.Factory)

    def test_cycle_repository_provider_exists(self) -> None:
        """Test that cycle_repository provider exists."""
        container = create_container()

        assert hasattr(container, "cycle_repository")
        assert isinstance(container.cycle_repository, providers.Factory)

    def test_ai_context_repository_provider_exists(self) -> None:
        """Test that ai_context_repository provider exists."""
        container = create_container()

        assert hasattr(container, "ai_context_repository")
        assert isinstance(container.ai_context_repository, providers.Factory)

    def test_repository_provider_uses_callable_session(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that repository providers use Callable session injection."""
        container = create_container()

        # Set session in context
        token = _request_session_ctx.set(db_session)
        try:
            # Repository should resolve session from ContextVar
            repo = container.issue_repository()

            assert repo is not None
            assert hasattr(repo, "session")
            # Session should be the one from ContextVar
            assert repo.session is db_session
        finally:
            _request_session_ctx.reset(token)

    def test_repository_factory_creates_new_instance_per_call(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that factory provider creates new instance per call."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            repo1 = container.issue_repository()
            repo2 = container.issue_repository()

            # Different instances
            assert repo1 is not repo2
            # But same session
            assert repo1.session is repo2.session
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# Service Factory Provider Tests
# ============================================================================


class TestServiceProviders:
    """Tests for service factory providers."""

    def test_create_issue_service_provider_exists(self) -> None:
        """Test that create_issue_service provider exists."""
        container = create_container()

        assert hasattr(container, "create_issue_service")
        assert isinstance(container.create_issue_service, providers.Factory)

    def test_update_issue_service_provider_exists(self) -> None:
        """Test that update_issue_service provider exists."""
        container = create_container()

        assert hasattr(container, "update_issue_service")
        assert isinstance(container.update_issue_service, providers.Factory)

    def test_create_note_service_provider_exists(self) -> None:
        """Test that create_note_service provider exists."""
        container = create_container()

        assert hasattr(container, "create_note_service")
        assert isinstance(container.create_note_service, providers.Factory)

    def test_update_note_service_provider_exists(self) -> None:
        """Test that update_note_service provider exists."""
        container = create_container()

        assert hasattr(container, "update_note_service")
        assert isinstance(container.update_note_service, providers.Factory)

    def test_create_cycle_service_provider_exists(self) -> None:
        """Test that create_cycle_service provider exists."""
        container = create_container()

        assert hasattr(container, "create_cycle_service")
        assert isinstance(container.create_cycle_service, providers.Factory)

    def test_generate_ai_context_service_provider_exists(self) -> None:
        """Test that generate_ai_context_service provider exists."""
        container = create_container()

        assert hasattr(container, "generate_ai_context_service")
        assert isinstance(container.generate_ai_context_service, providers.Factory)

    def test_workspace_service_provider_exists(self) -> None:
        """Test that workspace_service provider exists."""
        container = create_container()

        assert hasattr(container, "workspace_service")
        assert isinstance(container.workspace_service, providers.Factory)

    def test_service_factory_creates_new_instance_per_call(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that service factory creates new instance per call."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service1 = container.create_issue_service()
            service2 = container.create_issue_service()

            # Different instances
            assert service1 is not service2
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# ContextVar Session Injection Tests
# ============================================================================


class TestContextVarSessionInjection:
    """Tests for ContextVar-based session injection pattern."""

    def test_get_current_session_returns_active_session(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that get_current_session returns the ContextVar session."""
        token = _request_session_ctx.set(db_session)
        try:
            session = get_current_session()

            assert session is db_session
        finally:
            _request_session_ctx.reset(token)

    def test_get_current_session_raises_when_no_session(self) -> None:
        """Test that get_current_session raises RuntimeError when no session."""
        # Ensure no session in context
        _request_session_ctx.set(None)

        with pytest.raises(
            RuntimeError,
            match="No session in current context",
        ):
            get_current_session()

    def test_context_var_cleanup_with_token_reset(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that token.reset() properly cleans up ContextVar."""
        # Set session
        token = _request_session_ctx.set(db_session)

        # Verify session is set
        assert get_current_session() is db_session

        # Reset token
        _request_session_ctx.reset(token)

        # Verify session is cleared
        with pytest.raises(RuntimeError):
            get_current_session()

    def test_multiple_sessions_with_nested_contexts(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that nested ContextVar contexts work correctly."""
        session2 = MagicMock()  # Second session mock

        # Outer context
        token1 = _request_session_ctx.set(db_session)
        try:
            assert get_current_session() is db_session

            # Inner context
            token2 = _request_session_ctx.set(session2)
            try:
                assert get_current_session() is session2
            finally:
                _request_session_ctx.reset(token2)

            # Back to outer context
            assert get_current_session() is db_session
        finally:
            _request_session_ctx.reset(token1)


# ============================================================================
# Dependency Chain Tests
# ============================================================================


class TestDependencyChains:
    """Tests for dependency resolution chains."""

    def test_service_depends_on_repository(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that service receives repository instance from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_issue_service()

            # Verify service has repository injected
            assert hasattr(service, "_repo")
            assert service._repo is not None
        finally:
            _request_session_ctx.reset(token)

    def test_repository_depends_on_session(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that repository receives session from ContextVar."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            repo = container.issue_repository()

            # Verify repository has session injected
            assert hasattr(repo, "session")
            assert repo.session is db_session
        finally:
            _request_session_ctx.reset(token)

    def test_full_dependency_chain_service_to_session(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test full dependency chain: service → repository → session."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            # Resolve service (should trigger full chain)
            service = container.create_issue_service()

            # Verify chain: service → repository → session
            assert service._repo is not None
            assert service._repo.session is db_session
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# AI Infrastructure Provider Tests
# ============================================================================


class TestAIInfrastructureProviders:
    """Tests for AI infrastructure providers."""

    def test_provider_selector_provider_exists(self) -> None:
        """Test that provider_selector provider exists."""
        container = create_container()

        assert hasattr(container, "provider_selector")
        assert isinstance(container.provider_selector, providers.Singleton)

    def test_resilient_executor_provider_exists(self) -> None:
        """Test that resilient_executor provider exists."""
        container = create_container()

        assert hasattr(container, "resilient_executor")
        assert isinstance(container.resilient_executor, providers.Singleton)

    def test_tool_registry_provider_exists(self) -> None:
        """Test that tool_registry provider exists."""
        container = create_container()

        assert hasattr(container, "tool_registry")
        assert isinstance(container.tool_registry, providers.Singleton)

    def test_pilotspace_agent_provider_exists(self) -> None:
        """Test that pilotspace_agent provider exists."""
        container = create_container()

        assert hasattr(container, "pilotspace_agent")
        assert isinstance(container.pilotspace_agent, providers.Singleton)

    @pytest.mark.skipif(
        True,
        reason="Requires Redis connection - integration test",
    )
    def test_session_manager_provider_with_redis(self) -> None:
        """Test that session_manager provider works with Redis."""
        container = create_container()

        session_manager = container.session_manager()

        # If Redis not configured, should return None
        # If Redis configured, should return SessionManager
        assert session_manager is None or hasattr(session_manager, "create_session")


# ============================================================================
# Optional Infrastructure Provider Tests
# ============================================================================


class TestOptionalInfrastructureProviders:
    """Tests for optional infrastructure providers (Redis, Queue)."""

    def test_redis_client_provider_exists(self) -> None:
        """Test that redis_client provider exists."""
        container = create_container()

        assert hasattr(container, "redis_client")
        assert isinstance(container.redis_client, providers.Singleton)

    def test_queue_client_provider_exists(self) -> None:
        """Test that queue_client provider exists."""
        container = create_container()

        assert hasattr(container, "queue_client")
        assert isinstance(container.queue_client, providers.Singleton)

    def test_redis_client_returns_none_when_not_configured(self) -> None:
        """Test that redis_client returns None when Redis not configured."""
        from pilot_space.config import Settings

        settings = Settings(redis_url=None)
        container = create_container(settings=settings)

        redis_client = container.redis_client()

        assert redis_client is None

    def test_queue_client_returns_none_when_not_configured(self) -> None:
        """Test that queue_client returns None when not configured."""
        from pydantic import SecretStr

        from pilot_space.config import Settings

        settings = Settings(
            supabase_url=None,
            supabase_service_key=SecretStr(""),
        )
        container = create_container(settings=settings)

        queue_client = container.queue_client()

        assert queue_client is None


# ============================================================================
# Provider Override Tests
# ============================================================================


class TestProviderOverrides:
    """Tests for provider override functionality."""

    def test_can_override_repository_provider(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that repository providers can be overridden for testing."""
        container = create_container()

        # Create mock repository
        from unittest.mock import AsyncMock

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        # Override provider
        container.issue_repository.override(mock_repo)

        try:
            # Resolve should return mock
            repo = container.issue_repository()
            assert repo is mock_repo
        finally:
            # Reset override
            container.issue_repository.reset_override()

    def test_can_override_redis_client_provider(self) -> None:
        """Test that redis_client can be overridden for testing."""
        container = create_container()

        mock_redis = MagicMock()
        container.redis_client.override(mock_redis)

        try:
            redis_client = container.redis_client()
            assert redis_client is mock_redis
        finally:
            container.redis_client.reset_override()


# ============================================================================
# Error Case Tests
# ============================================================================


class TestErrorCases:
    """Tests for error handling in container operations."""

    def test_repository_resolution_fails_without_session_context(self) -> None:
        """Test that repository resolution fails without session context."""
        container = create_container()

        # Clear session context
        _request_session_ctx.set(None)

        # Attempting to resolve repository should fail when it tries to get session
        with pytest.raises(RuntimeError, match="No session in current context"):
            container.issue_repository()

    def test_service_resolution_fails_without_session_context(self) -> None:
        """Test that service resolution fails without session context."""
        container = create_container()

        # Clear session context
        _request_session_ctx.set(None)

        # Attempting to resolve service should fail when dependencies need session
        with pytest.raises(RuntimeError, match="No session in current context"):
            container.create_issue_service()


# ============================================================================
# Audit Log Repository Wiring Tests (AUDIT-01)
# ============================================================================


class TestAuditLogRepositoryWiring:
    """Tests verifying audit_log_repository is wired into CRUD service factories."""

    def test_audit_log_repository_provider_exists(self) -> None:
        """audit_log_repository Factory provider must exist on container."""
        container = create_container()

        assert hasattr(container, "audit_log_repository")
        assert isinstance(container.audit_log_repository, providers.Factory)

    def test_audit_log_repository_resolves_to_correct_type(self) -> None:
        """audit_log_repository() must return an AuditLogRepository instance."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        container = create_container()
        mock_session = MagicMock()
        token = _request_session_ctx.set(mock_session)
        try:
            repo = container.audit_log_repository()
            assert repo is not None
            assert isinstance(repo, AuditLogRepository)
        finally:
            _request_session_ctx.reset(token)

    def test_create_issue_service_receives_audit_repo(self) -> None:
        """create_issue_service must receive a non-None audit_log_repository."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        container = create_container()
        mock_session = MagicMock()
        token = _request_session_ctx.set(mock_session)
        try:
            service = container.create_issue_service()
            assert service._audit_repo is not None
            assert isinstance(service._audit_repo, AuditLogRepository)
        finally:
            _request_session_ctx.reset(token)

    def test_all_crud_services_receive_audit_repo(self) -> None:
        """All 10 CRUD services must receive a non-None audit_log_repository."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        container = create_container()
        mock_session = MagicMock()
        token = _request_session_ctx.set(mock_session)
        try:
            services_and_attr = [
                (container.create_issue_service(), "_audit_repo"),
                (container.update_issue_service(), "_audit_repo"),
                (container.delete_issue_service(), "_audit_repo"),
                (container.create_note_service(), "_audit_repo"),
                (container.update_note_service(), "_audit_repo"),
                (container.delete_note_service(), "_audit_repo"),
                (container.create_cycle_service(), "_audit_repo"),
                (container.update_cycle_service(), "_audit_repo"),
                (container.add_issue_to_cycle_service(), "_audit_repo"),
                (container.rbac_service(), "_audit_repo"),
            ]
            for service, attr in services_and_attr:
                repo = getattr(service, attr, None)
                service_name = type(service).__name__
                assert repo is not None, f"{service_name}.{attr} is None — audit wiring missing"
                assert isinstance(repo, AuditLogRepository), (
                    f"{service_name}.{attr} is not AuditLogRepository"
                )
        finally:
            _request_session_ctx.reset(token)
