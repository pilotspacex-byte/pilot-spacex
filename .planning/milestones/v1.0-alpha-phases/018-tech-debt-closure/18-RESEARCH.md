# Phase 18: Tech Debt Closure - Research

**Researched:** 2026-03-11
**Domain:** Backend infrastructure — OIDC verification, MCP approval wiring, audit test fixes, key rotation
**Confidence:** HIGH

## Summary

Phase 18 resolves four known v1.0 gaps, all backend/infrastructure with no new user-facing features. The codebase already contains the correct patterns for each fix — the work is about replacing static/stub implementations with the established correct patterns.

The MCP approval fix (DEBT-02) is the most mechanical: `note_content_server.py` and `issue_relation_server.py` both import `get_tool_approval_level()` (static map lookup) instead of calling `check_approval_from_db()` (DB-backed policy check). Three other MCP servers (`issue_server.py`, `comment_server.py`, `project_server.py`) already use the correct `check_approval_from_db()` pattern. The audit test fix (DEBT-03) requires an `AsyncClient` fixture wired to the FastAPI app with auth headers, which already exists in `tests/conftest.py` but is not available to the `tests/audit/` directory. Key rotation (DEBT-04) needs real re-encryption logic added to `workspace_encryption.py` with dual-key fallback during transition. OIDC verification (DEBT-01) requires a Playwright E2E test using a mock OIDC provider.

**Primary recommendation:** Execute as 4 independent work streams — each DEBT item is self-contained with no cross-dependencies between them.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **OIDC Verification (DEBT-01):** Verify all 3 providers (Okta, Azure AD, Google Workspace). Playwright E2E test using mock IdP for CI. Manual verification checklist for real providers. Full flow: SSO settings page -> initiate login -> IdP redirect -> callback -> authenticated session.
- **MCP Approval Wiring (DEBT-02):** Audit ALL MCP servers. Known gap: `note_content_server.py` uses static `get_tool_approval_level()` — swap to `check_approval_from_db()`. `issue_relation_server.py` same gap. `issue_server.py`, `comment_server.py`, `project_server.py` already correct — verify only. Every tool must receive `ToolContext` with `user_role`.
- **Audit Test Fixes (DEBT-03):** Fix ALL xfail audit tests (17+ across 3 files). Root cause: missing async HTTP client fixture. Create `AsyncClient` (httpx) fixture with auth headers and workspace context. Remove `xfail` markers once passing.
- **Key Rotation (DEBT-04):** Online rotation, no maintenance window. Dual-key read during transition. Batch re-encryption per workspace with progress tracking. Atomic per-workspace with retry. Old key retained until confirmed re-encrypted, then marked inactive. Rotation endpoint restricted to workspace owner.

### Claude's Discretion
- Mock IdP library choice for Playwright tests
- Batch size for key rotation re-encryption
- Exact async client fixture implementation pattern
- Whether to add a rotation progress API endpoint or keep it backend-only

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEBT-01 | OIDC login flow verified end-to-end in browser | SSO router exists at `auth_sso.py` with OIDC config endpoints; frontend has `use-sso-login.ts` and `sso-settings-page.tsx`; Playwright 1.58.0 already installed with E2E infrastructure |
| DEBT-02 | `issue_relation_server` + `note_content_server` use `check_approval_from_db()` | Both files import `get_tool_approval_level` (static); correct pattern exists in `note_server.py`, `issue_server.py`, `comment_server.py`, `project_server.py` |
| DEBT-03 | Async HTTP client fixture added — xfail audit tests passing | 17 xfail tests across 3 files; `conftest.py` has `client`, `authenticated_client`, `client_with_workspace` fixtures not available to `tests/audit/`; audit conftest only has `audit_log_factory` |
| DEBT-04 | Key rotation re-encryption implemented | `workspace_encryption.py` has encrypt/decrypt helpers; `WorkspaceEncryptionKey` model has `key_version` field; `WorkspaceEncryptionRepository.upsert_key()` increments version; xfail test at `test_workspace_encryption.py:107` defines expected behavior |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cryptography (Fernet) | existing | Envelope encryption for workspace keys | Already used in workspace_encryption.py |
| httpx (AsyncClient) | existing | Async HTTP test client for audit API tests | Already used in conftest.py for other API tests |
| Playwright | 1.58.0 | E2E browser testing for OIDC flow | Already installed, playwright.config.ts configured |
| pytest + pytest-asyncio | existing | Test framework | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| oidc-server-mock (Docker) | latest | Mock OIDC IdP for CI testing | DEBT-01 Playwright E2E tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| oidc-server-mock | keycloak dev mode | Heavier; oidc-server-mock is purpose-built for testing |
| Docker mock IdP | Supabase test provider | Supabase doesn't expose mock OIDC providers for E2E |

## Architecture Patterns

### DEBT-02: MCP Approval Wiring Pattern (Correct)

The correct pattern is already established in `note_server.py`, `issue_server.py`, `comment_server.py`, `project_server.py`:

```python
# CORRECT pattern (from note_server.py)
from pilot_space.ai.infrastructure.approval import ActionType as AT
from pilot_space.ai.tools.mcp_server import check_approval_from_db

# Inside create_*_server():
_chk = check_approval_from_db

# Inside each tool handler:
lvl = await _chk("tool_name", AT.ACTION_TYPE, tool_context)
status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
```

```python
# INCORRECT pattern (current in note_content_server.py and issue_relation_server.py)
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level

# Inside tool handler:
approval_level = get_tool_approval_level("insert_block")  # Static lookup, ignores DB policies
status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
```

### DEBT-02: Tool-to-ActionType Mapping

Each tool in the affected servers needs an `ActionType` mapping:

**note_content_server.py** (7 tools):
| Tool | ActionType |
|------|------------|
| search_note_content | None (read-only, auto-execute) |
| insert_block | AT.INSERT_BLOCK |
| remove_block | AT.REMOVE_BLOCK |
| remove_content | AT.REMOVE_CONTENT |
| replace_content | AT.REPLACE_CONTENT |
| create_pm_block | AT.INSERT_BLOCK |
| update_pm_block | AT.REPLACE_CONTENT |

**issue_relation_server.py** (4 tools):
| Tool | ActionType |
|------|------------|
| link_issue_to_note | AT.LINK_ISSUE_TO_NOTE |
| link_issues | AT.LINK_ISSUES |
| add_sub_issue | AT.ADD_SUB_ISSUE |
| transition_issue_state | AT.TRANSITION_ISSUE_STATE |

### DEBT-03: Audit Test Fixture Pattern

The root conftest already has `client`, `authenticated_client`, and `client_with_workspace` fixtures. The audit tests reference a `client` fixture parameter but the audit conftest does not define one.

Fix: Either make audit tests use the root conftest fixtures directly (they should be auto-discovered), or create an audit-specific conftest fixture that provides an `AsyncClient` with workspace context and ADMIN role auth.

Existing pattern from root conftest:
```python
@pytest.fixture
async def client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

The audit tests need a `client` that is authenticated with ADMIN role and has workspace context, since all audit endpoints require `settings:read` permission.

### DEBT-04: Key Rotation Architecture

**Existing infrastructure:**
- `WorkspaceEncryptionKey` model: has `key_version` (monotonic), `encrypted_workspace_key`
- `WorkspaceEncryptionRepository.upsert_key()`: stores new key, increments version
- `workspace_encryption.py`: `encrypt_content()`, `decrypt_content()`, `store_workspace_key()`, `retrieve_workspace_key()`
- Router `PUT /encryption/key`: stores key but does NOT re-encrypt content

**What needs to be added:**
1. `rotate_key()` service function: stores new key, re-encrypts all content with dual-key fallback
2. Content discovery: query all notes and issues in the workspace that have encrypted content
3. Batch re-encryption: decrypt with old key, encrypt with new key, update row
4. Progress tracking: track re-encrypted count per workspace
5. Dual-key read: during rotation, try new key first, fall back to old key
6. Old key retention: store previous key in a `previous_encrypted_key` column or separate table

**Per the xfail test spec:**
```
1. Create workspace with key v1, encrypt 3 notes
2. Rotate to key v2
3. Decrypt all notes with key v2 — plaintext must match original
4. Decrypting with key v1 must fail (InvalidToken)
```

### Anti-Patterns to Avoid
- **Static approval bypass:** Never use `get_tool_approval_level()` in MCP tool handlers that have `tool_context` available — always use `check_approval_from_db()`
- **Mixing old/new key without tracking:** Must know which rows are re-encrypted vs pending; use `key_version` on the row or a batch completion flag
- **Blocking rotation:** Do not hold a single transaction across all rows — process in batches with per-batch commits

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mock OIDC IdP | Custom OAuth server | `oidc-server-mock` Docker image | Standard test IdP with configurable claims, token lifetimes |
| Async HTTP test client | Custom request helper | httpx `AsyncClient` with `ASGITransport` | Already used in project; handles auth headers, cookies |
| Fernet key generation | Custom crypto | `cryptography.fernet.Fernet.generate_key()` | Already used; cryptographically secure |

## Common Pitfalls

### Pitfall 1: note_content_server tool_context is Optional
**What goes wrong:** `tool_context` can be `None` in `create_note_content_server()`, and `check_approval_from_db()` handles this by falling back to static map.
**Why it happens:** Tool context is injected at server creation time, not at tool execution time.
**How to avoid:** `check_approval_from_db()` already handles `tool_context=None` gracefully (returns static fallback). No special handling needed.

### Pitfall 2: Audit Tests Need Both Fixtures AND Data
**What goes wrong:** Providing an `AsyncClient` fixture alone isn't enough — the audit API routes need a workspace in the DB and the RLS context set.
**Why it happens:** Audit endpoints call `_resolve_workspace()` and `set_rls_context()`.
**How to avoid:** Use the `client_with_workspace` pattern from root conftest, which provides auth headers and workspace context. Seed test data using `audit_log_factory`.

### Pitfall 3: Immutability Tests Require PostgreSQL
**What goes wrong:** The 3 immutability trigger tests (`test_immutability.py`) are PostgreSQL-specific — they test `fn_audit_log_immutable` trigger behavior.
**Why it happens:** SQLite has no trigger support matching PostgreSQL's.
**How to avoid:** These tests are `@pytest.mark.integration` — they will only pass with `TEST_DATABASE_URL` set to PostgreSQL. Keep the `xfail` markers if no PostgreSQL test infrastructure is available in CI. The CONTEXT.md says "fix ALL xfail audit tests (17+)" but the 3 immutability tests (3 of 17) are a different category — they test DB triggers, not missing fixtures.
**Warning signs:** Tests pass as XFAIL in SQLite but would fail as real tests without PostgreSQL.

### Pitfall 4: Key Rotation Must Handle Partial Failure
**What goes wrong:** If re-encryption fails mid-batch, some rows are encrypted with new key, others still with old key.
**Why it happens:** Network errors, DB timeouts during batch processing.
**How to avoid:** Track `key_version` per-row or use dual-key decryption that tries new key first, falls back to old. This is already specified in CONTEXT.md decisions.

### Pitfall 5: OIDC Test Requires Docker
**What goes wrong:** Playwright E2E test for OIDC needs a running mock IdP.
**Why it happens:** OIDC flow involves browser redirects to an external IdP.
**How to avoid:** Use `docker compose` to start `oidc-server-mock` before Playwright runs. Add it to the `webServer` config or as a separate service.

## Code Examples

### DEBT-02: Fixing note_content_server.py approval calls

```python
# Change import (line 27):
# FROM:
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level
# TO:
from pilot_space.ai.infrastructure.approval import ActionType as AT
from pilot_space.ai.tools.mcp_server import ToolContext, check_approval_from_db

# Inside create_note_content_server(), add alias:
_chk = check_approval_from_db

# Change each tool handler, e.g. insert_block (line 316):
# FROM:
approval_level = get_tool_approval_level("insert_block")
# TO:
approval_level = await _chk("insert_block", AT.INSERT_BLOCK, tool_context)
```

### DEBT-02: Fixing issue_relation_server.py approval calls

```python
# Change import (line 29):
# FROM:
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level
# TO:
from pilot_space.ai.infrastructure.approval import ActionType as AT
from pilot_space.ai.tools.mcp_server import ToolContext, check_approval_from_db

# Inside create_issue_relation_server(), add alias:
_chk = check_approval_from_db

# Change each tool handler, e.g. link_issue_to_note (line 258):
# FROM:
approval_level = get_tool_approval_level("link_issue_to_note")
# TO:
approval_level = await _chk("link_issue_to_note", AT.LINK_ISSUE_TO_NOTE, tool_context)
```

### DEBT-03: Audit test AsyncClient fixture

```python
# In tests/audit/conftest.py, add:
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def audit_client(
    app: Any,
    mock_auth: Any,
    test_workspace_id: UUID,
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client with ADMIN role for audit endpoint tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac
```

### DEBT-04: Key rotation service sketch

```python
async def rotate_workspace_key(
    session: AsyncSession,
    workspace_id: str,
    new_raw_key: str,
    batch_size: int = 100,
) -> dict[str, int]:
    """Rotate workspace encryption key and re-encrypt all content.

    1. Retrieve old key from DB
    2. Store new key (upsert_key increments key_version)
    3. Batch re-encrypt all notes and issues
    4. Return counts of re-encrypted items
    """
    old_key = await get_workspace_content_key(session, workspace_id)
    if old_key is None:
        raise ValueError("No existing encryption key to rotate from")

    # Store new key
    repo = WorkspaceEncryptionRepository(session)
    await repo.upsert_key(workspace_id, new_raw_key)

    # Re-encrypt notes in batches
    re_encrypted = {"notes": 0, "issues": 0}
    # ... batch query and re-encrypt logic ...
    return re_encrypted
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static tool approval map | DB-backed approval policies | Phase 04 (AI Governance) | Per-workspace/role approval config |
| Single workspace key | Versioned key with rotation | Phase 03 (model exists, rotation stub) | Key rotation possible but not implemented |

**Deprecated/outdated:**
- `get_tool_approval_level()` for MCP server tool handlers: replaced by `check_approval_from_db()` but not yet applied to `note_content_server.py` and `issue_relation_server.py`

## Open Questions

1. **Immutability tests (3 of 17) require PostgreSQL**
   - What we know: These 3 tests in `test_immutability.py` test PostgreSQL triggers; they cannot work with SQLite
   - What's unclear: Whether CI has PostgreSQL available for `TEST_DATABASE_URL`
   - Recommendation: Fix the 14 fixture-related xfail tests. For the 3 immutability tests, keep them as `@pytest.mark.integration` — they pass when `TEST_DATABASE_URL` is set. Count them in the total but note the PostgreSQL dependency.

2. **Where to store the old key during rotation**
   - What we know: `WorkspaceEncryptionKey` model has one `encrypted_workspace_key` column, overwritten on upsert
   - What's unclear: Whether to add a `previous_encrypted_key` column or a separate history table
   - Recommendation: Add a `previous_encrypted_key` column (nullable Text) to `WorkspaceEncryptionKey`. Simpler than a history table; only need the immediately preceding key for dual-key fallback. Clear it after all rows confirmed re-encrypted.

3. **OIDC mock IdP Docker setup**
   - What we know: `oidc-server-mock` is a lightweight Docker image purpose-built for OIDC testing
   - What's unclear: Whether to add it to `infra/` docker-compose or as a separate Playwright-specific compose
   - Recommendation: Add to Playwright config as a separate docker-compose service, keeping it isolated from the main infra stack.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio (backend), Playwright 1.58.0 (E2E) |
| Config file | `backend/pyproject.toml`, `frontend/playwright.config.ts` |
| Quick run command | `cd backend && uv run pytest tests/audit/ tests/unit/test_workspace_encryption.py -x -q` |
| Full suite command | `cd backend && uv run pytest --cov -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-01 | OIDC login flow E2E | E2E (Playwright) | `cd frontend && pnpm test:e2e --grep "oidc"` | No — Wave 0 |
| DEBT-02 | MCP servers use check_approval_from_db | unit | `cd backend && uv run pytest tests/unit/ai/test_mcp_server_approval.py -x` | Yes (existing pattern tests) |
| DEBT-02 | note_content_server approval wiring | unit | `cd backend && uv run pytest tests/ -k "note_content" -x` | No — Wave 0 |
| DEBT-02 | issue_relation_server approval wiring | unit | `cd backend && uv run pytest tests/ -k "issue_relation" -x` | No — Wave 0 |
| DEBT-03 | Audit API tests pass (no xfail) | integration | `cd backend && uv run pytest tests/audit/test_audit_api.py tests/audit/test_audit_export.py -x` | Yes (currently xfail) |
| DEBT-03 | Immutability tests pass | integration | `cd backend && uv run pytest tests/audit/test_immutability.py -x` | Yes (currently xfail, needs PostgreSQL) |
| DEBT-04 | Key rotation re-encrypts content | unit | `cd backend && uv run pytest tests/unit/test_workspace_encryption.py -x` | Yes (currently xfail) |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/audit/ tests/unit/test_workspace_encryption.py -x -q`
- **Per wave merge:** `cd backend && uv run pytest --cov -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/e2e/oidc-login.spec.ts` — covers DEBT-01 OIDC E2E flow
- [ ] `backend/tests/unit/ai/test_note_content_server_approval.py` — covers DEBT-02 note_content_server wiring
- [ ] `backend/tests/unit/ai/test_issue_relation_server_approval.py` — covers DEBT-02 issue_relation_server wiring
- [ ] Audit conftest needs `AsyncClient` fixture with auth — covers DEBT-03

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all MCP server files for approval patterns
- `backend/src/pilot_space/ai/mcp/note_content_server.py` — 7 tools, all use static `get_tool_approval_level()`
- `backend/src/pilot_space/ai/mcp/issue_relation_server.py` — 4 tools, all use static `get_tool_approval_level()`
- `backend/src/pilot_space/ai/mcp/note_server.py` — correct `check_approval_from_db()` pattern
- `backend/tests/audit/test_audit_api.py` — 9 xfail tests
- `backend/tests/audit/test_audit_export.py` — 8 xfail tests
- `backend/tests/audit/test_immutability.py` — 5 tests (3 xfail PostgreSQL + 2 xfail router)
- `backend/tests/unit/test_workspace_encryption.py` — 1 xfail key rotation test
- `backend/src/pilot_space/infrastructure/workspace_encryption.py` — encryption helpers
- `backend/src/pilot_space/infrastructure/database/models/workspace_encryption_key.py` — key model with versioning

### Secondary (MEDIUM confidence)
- `backend/tests/conftest.py` — existing `client`, `authenticated_client`, `client_with_workspace` fixtures (lines 604-665)

### Tertiary (LOW confidence)
- `oidc-server-mock` Docker image suitability — based on training knowledge, needs validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use in the project
- Architecture: HIGH - correct patterns exist in adjacent files, mechanical replication
- Pitfalls: HIGH - identified from direct code inspection of all affected files
- OIDC E2E: MEDIUM - mock IdP setup is less certain, depends on Docker availability

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable — internal tech debt, no external API changes)
