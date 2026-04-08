"""Pytest configuration and fixtures for Pilot Space backend tests.

Provides:
- Database fixtures with transaction rollback
- Redis mock fixtures using fakeredis
- Authenticated user fixtures with Supabase auth mock
- Factory fixtures for all domain models
- HTTP client fixtures for API testing
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.infrastructure.database.base import Base
from pilot_space.infrastructure.database.models import (
    Issue,
    Note,
    Project,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

from .factories import (
    IssueFactory,
    NoteFactory,
    ProjectFactory,
    StateFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
    create_default_states,
    create_test_scenario,
)
from .fixtures.anthropic_mock import (
    MOCK_CHAT_RESPONSES,
    MOCK_STREAMING_CHUNKS,
    mock_anthropic_api,
    mock_anthropic_skill_responses,
    mock_anthropic_streaming,
    mock_claude_sdk_demo_mode,
)

# Initialize faker for generating test data
fake = Faker()


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL.

    Uses environment variable or falls back to in-memory SQLite for tests.
    For PostgreSQL-specific tests, set TEST_DATABASE_URL environment variable.

    Returns:
        Database connection URL.
    """
    return os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
async def test_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for tests.

    Creates tables on startup and drops them on teardown.
    Changed from session to function scope to work with pytest-asyncio.

    Args:
        test_database_url: Database URL for tests.

    Yields:
        AsyncEngine instance.
    """
    # Use StaticPool for SQLite to share connections across threads
    if "sqlite" in test_database_url:
        engine = create_async_engine(
            test_database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        engine = create_async_engine(
            test_database_url,
            pool_pre_ping=True,
            echo=False,
        )

    # Create all tables (drop first to ensure clean state with StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session with transaction rollback.

    Each test gets its own session with automatic rollback,
    ensuring test isolation without affecting other tests.

    Args:
        test_engine: The test database engine.

    Yields:
        AsyncSession for database operations.
    """
    # Create session factory bound to test engine
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session, session.begin():
        # Yield session for test with automatic rollback
        yield session
        # Rollback on completion (automatic with context manager)


@pytest.fixture
async def db_session_committed(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session that commits changes.

    Use this fixture when you need to test behavior that requires
    committed data (e.g., testing unique constraints).

    Warning: This does not rollback - use with caution.

    Args:
        test_engine: The test database engine.

    Yields:
        AsyncSession for database operations.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.commit()


# ============================================================================
# Redis Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_redis() -> Generator[MagicMock, None, None]:
    """Create mock Redis client using fakeredis pattern.

    Provides a mock Redis client with common operations.

    Yields:
        MagicMock Redis client.
    """
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=-1)
    mock.setex = AsyncMock(return_value=True)
    mock.incr = AsyncMock(return_value=1)
    mock.decr = AsyncMock(return_value=0)
    mock.hget = AsyncMock(return_value=None)
    mock.hset = AsyncMock(return_value=1)
    mock.hdel = AsyncMock(return_value=1)
    mock.hgetall = AsyncMock(return_value={})
    mock.lpush = AsyncMock(return_value=1)
    mock.rpush = AsyncMock(return_value=1)
    mock.lpop = AsyncMock(return_value=None)
    mock.rpop = AsyncMock(return_value=None)
    mock.lrange = AsyncMock(return_value=[])
    mock.close = AsyncMock()

    return mock


@pytest.fixture
def redis_cache(mock_redis: MagicMock) -> dict[str, Any]:
    """Provide in-memory cache dict alongside Redis mock.

    Useful for tests that need to verify cached values.

    Args:
        mock_redis: Mock Redis client.

    Returns:
        Dictionary acting as in-memory cache.
    """
    cache: dict[str, Any] = {}

    async def mock_get(key: str) -> Any:
        return cache.get(key)

    async def mock_set(key: str, value: Any, **kwargs: Any) -> bool:
        cache[key] = value
        return True

    async def mock_delete(key: str) -> int:
        if key in cache:
            del cache[key]
            return 1
        return 0

    mock_redis.get = AsyncMock(side_effect=mock_get)
    mock_redis.set = AsyncMock(side_effect=mock_set)
    mock_redis.delete = AsyncMock(side_effect=mock_delete)

    return cache


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def test_user_id() -> UUID:
    """Generate a consistent test user ID.

    Returns:
        UUID for test user.
    """
    return uuid4()


@pytest.fixture
def test_user_email() -> str:
    """Generate test user email.

    Returns:
        Email string.
    """
    return "test@example.com"


@pytest.fixture
def mock_token_payload(test_user_id: UUID, test_user_email: str) -> TokenPayload:
    """Create mock token payload for authenticated user.

    Args:
        test_user_id: User UUID.
        test_user_email: User email.

    Returns:
        TokenPayload instance.
    """
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub=str(test_user_id),
        email=test_user_email,
        role="authenticated",
        aud="authenticated",
        exp=int((now.timestamp()) + 3600),  # 1 hour from now
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={"full_name": "Test User"},
    )


@pytest.fixture
def mock_auth(mock_token_payload: TokenPayload) -> Generator[MagicMock, None, None]:
    """Mock Supabase auth for testing.

    Patches the auth dependency to return mock token payload.

    Args:
        mock_token_payload: Token payload to return.

    Yields:
        Mock auth instance.
    """
    with patch(
        "pilot_space.dependencies.get_auth",
    ) as mock_get_auth:
        mock_auth = MagicMock()
        mock_auth.validate_token.return_value = mock_token_payload
        mock_get_auth.return_value = mock_auth
        yield mock_auth


@pytest.fixture
def authenticated_user(
    mock_token_payload: TokenPayload,
) -> Generator[TokenPayload, None, None]:
    """Provide authenticated user context.

    Patches get_current_user dependency to return the mock user.

    Args:
        mock_token_payload: Token payload for the user.

    Yields:
        TokenPayload for use in tests.
    """
    with patch(
        "pilot_space.dependencies.get_current_user",
        return_value=mock_token_payload,
    ):
        yield mock_token_payload


# ============================================================================
# Workspace Context Fixtures
# ============================================================================


@pytest.fixture
def test_workspace_id() -> UUID:
    """Generate a consistent test workspace ID.

    Returns:
        UUID for test workspace.
    """
    return uuid4()


@pytest.fixture
def mock_workspace_context(test_workspace_id: UUID) -> Generator[UUID, None, None]:
    """Mock workspace context for testing.

    Patches get_current_workspace_id to return test workspace.

    Args:
        test_workspace_id: Workspace UUID.

    Yields:
        Workspace UUID.
    """
    with patch(
        "pilot_space.dependencies.get_current_workspace_id",
        return_value=test_workspace_id,
    ):
        yield test_workspace_id


# ============================================================================
# Factory Fixtures
# ============================================================================


@pytest.fixture
def user_factory() -> type[UserFactory]:
    """Provide UserFactory class.

    Returns:
        UserFactory class.
    """
    return UserFactory


@pytest.fixture
def workspace_factory() -> type[WorkspaceFactory]:
    """Provide WorkspaceFactory class.

    Returns:
        WorkspaceFactory class.
    """
    return WorkspaceFactory


@pytest.fixture
def project_factory() -> type[ProjectFactory]:
    """Provide ProjectFactory class.

    Returns:
        ProjectFactory class.
    """
    return ProjectFactory


@pytest.fixture
def issue_factory() -> type[IssueFactory]:
    """Provide IssueFactory class.

    Returns:
        IssueFactory class.
    """
    return IssueFactory


@pytest.fixture
def note_factory() -> type[NoteFactory]:
    """Provide NoteFactory class.

    Returns:
        NoteFactory class.
    """
    return NoteFactory


@pytest.fixture
def state_factory() -> type[StateFactory]:
    """Provide StateFactory class.

    Returns:
        StateFactory class.
    """
    return StateFactory


@pytest.fixture
def sample_user() -> User:
    """Create a sample user instance.

    Returns:
        User instance.
    """
    return UserFactory()


@pytest.fixture
def sample_workspace(sample_user: User) -> Workspace:
    """Create a sample workspace with owner.

    Args:
        sample_user: Owner user.

    Returns:
        Workspace instance.
    """
    return WorkspaceFactory(owner_id=sample_user.id, owner=sample_user)


@pytest.fixture
def sample_project(sample_workspace: Workspace, sample_user: User) -> Project:
    """Create a sample project in workspace.

    Args:
        sample_workspace: Parent workspace.
        sample_user: Project lead.

    Returns:
        Project instance.
    """
    project = ProjectFactory(
        workspace_id=sample_workspace.id,
        workspace=sample_workspace,
        lead_id=sample_user.id,
        lead=sample_user,
    )
    project.states = create_default_states(sample_workspace.id, project.id)
    return project


@pytest.fixture
def sample_issue(sample_project: Project, sample_user: User) -> Issue:
    """Create a sample issue in project.

    Args:
        sample_project: Parent project.
        sample_user: Reporter.

    Returns:
        Issue instance.
    """
    state = sample_project.states[0] if sample_project.states else StateFactory()
    return IssueFactory(
        workspace_id=sample_project.workspace_id,
        project_id=sample_project.id,
        project=sample_project,
        reporter_id=sample_user.id,
        reporter=sample_user,
        state_id=state.id,
        state=state,
    )


@pytest.fixture
def sample_note(sample_workspace: Workspace, sample_user: User) -> Note:
    """Create a sample note in workspace.

    Args:
        sample_workspace: Parent workspace.
        sample_user: Note owner.

    Returns:
        Note instance.
    """
    from uuid import uuid4 as _uuid4

    from pilot_space.infrastructure.database.models.note import Note as _Note

    # Build Note directly — NoteFactory's `owner` relationship field can
    # override owner_id to None when added to a session without the user loaded.
    return _Note(
        id=_uuid4(),
        title="Test Note",
        workspace_id=sample_workspace.id,
        owner_id=sample_user.id,
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Test content"}],
                }
            ],
        },
    )


@pytest.fixture
def test_scenario() -> dict[str, Any]:
    """Create complete test scenario with all entities.

    Returns:
        Dictionary with workspace, owner, project, states, issues, notes.
    """
    return create_test_scenario()


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest.fixture
async def app(redis_cache: dict[str, Any]) -> AsyncGenerator[Any, None]:
    """Create FastAPI test application with mocked Redis.

    Args:
        redis_cache: In-memory cache dict for Redis mock.

    Yields:
        FastAPI application instance with Redis mocked.
    """
    # Override Redis client with mock
    # This ensures SessionManager and other Redis-dependent services use mock
    from unittest.mock import MagicMock

    from pilot_space.container import Container
    from pilot_space.main import app

    mock_redis_client = MagicMock()
    mock_redis_client.get = AsyncMock(side_effect=redis_cache.get)

    def mock_set(key: str, value: Any, **_kwargs: Any) -> bool:
        redis_cache[key] = value
        return True

    mock_redis_client.set = AsyncMock(side_effect=mock_set)
    mock_redis_client.delete = AsyncMock(
        side_effect=lambda key: redis_cache.pop(key, None) is not None
    )
    mock_redis_client.expire = AsyncMock(return_value=True)

    # Override the container's redis_client provider
    Container.redis_client.override(mock_redis_client)

    try:
        yield app
    finally:
        # Reset override after test
        Container.redis_client.reset_override()


@pytest.fixture
async def client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing.

    Args:
        app: FastAPI application.

    Yields:
        AsyncClient for making requests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authenticated_client(
    app: Any,
    mock_auth: MagicMock,
    mock_token_payload: TokenPayload,
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated HTTP client for API testing.

    Overrides get_current_user FastAPI dependency so the mock token payload
    is returned directly, bypassing JWT validation.

    Args:
        app: FastAPI application.
        mock_auth: Mock auth instance.
        mock_token_payload: Token payload for auth.

    Yields:
        AsyncClient with auth headers.
    """
    from pilot_space.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_token_payload
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def client_with_workspace(
    app: Any,
    mock_auth: MagicMock,
    mock_token_payload: TokenPayload,
    test_workspace_id: UUID,
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated HTTP client with workspace context.

    Args:
        app: FastAPI application.
        mock_auth: Mock auth instance.
        mock_token_payload: Token payload for auth.
        test_workspace_id: Workspace UUID.

    Yields:
        AsyncClient with auth and workspace headers.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "Authorization": "Bearer test-token",
            "X-Workspace-ID": str(test_workspace_id),
        },
    ) as ac:
        yield ac


# ============================================================================
# AI Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_ai_client() -> MagicMock:
    """Create mock AI client for testing.

    Returns:
        MagicMock AI client with common methods.
    """
    mock = MagicMock()

    # Mock completion/query method
    mock.query = AsyncMock(
        return_value={
            "content": "Mocked AI response",
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
    )

    # Mock streaming method
    async def mock_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[str, None]:
        yield "Mocked "
        yield "streaming "
        yield "response"

    mock.stream = mock_stream

    # Mock embedding method
    mock.embed = AsyncMock(return_value=[0.1] * 1536)  # OpenAI embedding dimension

    return mock


@pytest.fixture
def mock_duplicate_detector() -> MagicMock:
    """Create mock duplicate detector for testing.

    Returns:
        MagicMock duplicate detector.
    """
    mock = MagicMock()
    mock.find_duplicates = AsyncMock(return_value=[])
    mock.check_similarity = AsyncMock(return_value=0.0)
    return mock


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def faker_instance() -> Faker:
    """Provide Faker instance for generating test data.

    Returns:
        Faker instance.
    """
    return fake


@pytest.fixture
def random_uuid() -> UUID:
    """Generate a random UUID.

    Returns:
        Random UUID.
    """
    return uuid4()


# ============================================================================
# Workspace Role Fixtures
# ============================================================================


@pytest.fixture
def owner_user(sample_workspace: Workspace, sample_user: User) -> tuple[User, WorkspaceMember]:
    """Create owner user with workspace membership.

    Args:
        sample_workspace: Workspace.
        sample_user: User to make owner.

    Returns:
        Tuple of (User, WorkspaceMember).
    """
    membership = WorkspaceMemberFactory(
        user=sample_user,
        workspace=sample_workspace,
        role=WorkspaceRole.OWNER,
    )
    return sample_user, membership


@pytest.fixture
def admin_user(sample_workspace: Workspace) -> tuple[User, WorkspaceMember]:
    """Create admin user with workspace membership.

    Args:
        sample_workspace: Workspace.

    Returns:
        Tuple of (User, WorkspaceMember).
    """
    user = UserFactory()
    membership = WorkspaceMemberFactory(
        user=user,
        workspace=sample_workspace,
        role=WorkspaceRole.ADMIN,
    )
    return user, membership


@pytest.fixture
def member_user(sample_workspace: Workspace) -> tuple[User, WorkspaceMember]:
    """Create member user with workspace membership.

    Args:
        sample_workspace: Workspace.

    Returns:
        Tuple of (User, WorkspaceMember).
    """
    user = UserFactory()
    membership = WorkspaceMemberFactory(
        user=user,
        workspace=sample_workspace,
        role=WorkspaceRole.MEMBER,
    )
    return user, membership


@pytest.fixture
def guest_user(sample_workspace: Workspace) -> tuple[User, WorkspaceMember]:
    """Create guest user with workspace membership.

    Args:
        sample_workspace: Workspace.

    Returns:
        Tuple of (User, WorkspaceMember).
    """
    user = UserFactory()
    membership = WorkspaceMemberFactory(
        user=user,
        workspace=sample_workspace,
        role=WorkspaceRole.GUEST,
    )
    return user, membership


# ============================================================================
# E2E Test Fixtures
# ============================================================================


@pytest.fixture
def test_api_key() -> str:
    """Generate test API key for E2E tests.

    Returns:
        API key string.
    """
    return "test-api-key-12345"


@pytest.fixture
def auth_headers(test_api_key: str, test_workspace_id: UUID) -> dict[str, str]:
    """Create authentication headers for E2E tests.

    Args:
        test_api_key: API key for authentication.
        test_workspace_id: Workspace UUID.

    Returns:
        Dictionary with Authorization and X-Workspace-ID headers.
    """
    return {
        "Authorization": f"Bearer {test_api_key}",
        "X-Workspace-ID": str(test_workspace_id),
        "X-API-Key": test_api_key,
    }


@pytest.fixture
async def e2e_client(
    app: Any,
    auth_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    """Create E2E test client with authentication.

    Args:
        app: FastAPI application.
        auth_headers: Authentication headers.

    Yields:
        AsyncClient configured for E2E testing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers,
    ) as ac:
        yield ac


@pytest.fixture
async def test_workspace(
    db_session: AsyncSession,
    sample_workspace: Workspace,
) -> Workspace:
    """Create test workspace in database for E2E tests.

    Args:
        db_session: Database session.
        sample_workspace: Workspace factory instance.

    Returns:
        Persisted workspace instance.
    """
    db_session.add(sample_workspace)
    await db_session.commit()
    await db_session.refresh(sample_workspace)
    return sample_workspace


@pytest.fixture
async def test_issue(
    db_session: AsyncSession,
    sample_issue: Issue,
    test_workspace: Workspace,
) -> Issue:
    """Create test issue in database for E2E tests.

    Args:
        db_session: Database session.
        sample_issue: Issue factory instance.
        test_workspace: Workspace for issue.

    Returns:
        Persisted issue instance.
    """
    sample_issue.workspace_id = test_workspace.id
    db_session.add(sample_issue)
    await db_session.commit()
    await db_session.refresh(sample_issue)
    return sample_issue


# ============================================================================
# Phase 70: postgres_session fixture for real-PG RLS integration tests
# ============================================================================


@pytest.fixture
async def postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession bound to a real PostgreSQL instance.

    Gated on ``TEST_DATABASE_URL``: if unset or not pointing at PostgreSQL,
    the test is skipped. Unlike ``db_session`` (which wraps a rollback),
    this fixture COMMITS — required for RLS policy tests where two
    sessions need to see each other's committed rows.

    The caller is responsible for cleaning up rows it creates (typically
    by scoping data to a fresh workspace UUID and deleting on teardown).

    SQLite caveat (see ``.claude/rules/testing.md``): statements like
    ``SET LOCAL app.current_user_id = '...'`` are PostgreSQL-specific
    no-ops on SQLite, which silently defeats RLS coverage. Tests that
    depend on RLS MUST use this fixture, not ``db_session``.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not url.startswith(("postgresql", "postgres")):
        pytest.skip("TEST_DATABASE_URL not set to a PostgreSQL URL")

    # Ensure settings cache is clean so other tests don't see stale env.
    try:
        from pilot_space.config import get_settings

        get_settings.cache_clear()
    except Exception:  # pragma: no cover - defensive
        pass

    engine: AsyncEngine = create_async_engine(url, future=True, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        await engine.dispose()


__all__ = [
    "MOCK_CHAT_RESPONSES",
    "MOCK_STREAMING_CHUNKS",
    "app",
    "auth_headers",
    "authenticated_client",
    "authenticated_user",
    "client",
    "client_with_workspace",
    "db_session",
    "db_session_committed",
    "e2e_client",
    "event_loop",
    "faker_instance",
    "issue_factory",
    "mock_ai_client",
    "mock_anthropic_api",
    "mock_anthropic_skill_responses",
    "mock_anthropic_streaming",
    "mock_auth",
    "mock_claude_sdk_demo_mode",
    "mock_duplicate_detector",
    "mock_redis",
    "mock_token_payload",
    "mock_workspace_context",
    "note_factory",
    "postgres_session",
    "project_factory",
    "random_uuid",
    "redis_cache",
    "sample_issue",
    "sample_note",
    "sample_project",
    "sample_user",
    "sample_workspace",
    "state_factory",
    "test_api_key",
    "test_database_url",
    "test_engine",
    "test_issue",
    "test_scenario",
    "test_user_email",
    "test_user_id",
    "test_workspace",
    "test_workspace_id",
    "user_factory",
    "workspace_factory",
]
