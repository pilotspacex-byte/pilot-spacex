# Authentication, RLS & Encryption - Pilot Space Infrastructure

**For parent layer overview, see [infrastructure/README.md](../../infrastructure/README.md)**

---

## Overview

Three pillars of Pilot Space security: authentication (Supabase JWT validation), authorization (Row-Level Security at the database level), and encryption (Supabase Vault for API key storage). RLS is the core security boundary -- violations expose sensitive data across workspaces.

---

## RLS (Row-Level Security) - Core Security Boundary

### RLS Context Functions

**File**: `database/rls.py`

- `set_rls_context(session, user_id, workspace_id)`: Sets PostgreSQL session variables (`app.current_user_id`, `app.current_workspace_id`) for RLS policy evaluation
- `clear_rls_context(session)`: Resets session variables on cleanup

RLS context is set by middleware on every request before any data access.

### RLS Policy Pattern

Applied to all tables with `workspace_id` column. Policies enforce that users can only access rows in workspaces where they are active members. See `alembic/versions/004_rls_policies.py` for the initial policy definitions and `031_homepage_rls_policies.py` for additional examples.

**Three policy types**:

| Policy | Scope | Access |
|--------|-------|--------|
| Workspace isolation | All workspace-scoped tables | Members see own workspace data only |
| User self + co-members | `users` table | Users see themselves + workspace co-members |
| Admin-only mutations | `workspace_members` table | Read: all members. Write: owner/admin only |
| Service role bypass | All tables | `service_role` bypasses RLS (admin ops only, never user-facing) |

### RLS in AI Context

Every MCP tool respects RLS with 3-layer enforcement:

1. **Context Layer**: `get_workspace_context()` retrieves current workspace from request
2. **Application Layer**: Explicit `workspace_id` filter in all repository calls
3. **Database Layer**: PostgreSQL RLS policies via session variables

### RLS Verification Checklist

For every new feature or table:

- [ ] RLS policy created for every multi-tenant table
- [ ] Service layer validates workspace membership before mutations
- [ ] Repository queries scoped by `workspace_id` OR rely on RLS
- [ ] `set_rls_context()` called in middleware/request handler
- [ ] Integration tests verify cross-workspace isolation
- [ ] No raw SQL queries without RLS enforcement

### Common Pitfalls

- Querying without workspace scope leaks data across workspaces
- Trusting user-provided `workspace_id` without RLS context set
- Using service role queries in user-facing code paths
- Missing RLS context in AI tool handlers (must call `get_workspace_context()`)

---

## Authentication

### SupabaseAuth

**File**: `supabase_auth.py`

JWT validation (HS256/ES256) with `TokenPayload` dataclass. See `supabase_auth.py:SupabaseAuth` and `supabase_auth.py:TokenPayload`.

**Interface**:
- `verify_token(token) -> TokenPayload`: Validate JWT signature, expiration, extract user_id
- `get_user_by_id(user_id) -> User`: Fetch user via Supabase Admin API

**Token Flow**:
1. Frontend sends JWT via `Authorization: Bearer <token>` (REST) or cookie (SSE)
2. `AuthMiddleware` validates and extracts `user_id` into `request.state.user_id`
3. RLS middleware uses `user_id` to set PostgreSQL session variables
4. All subsequent queries scoped by user's workspace memberships

**Error Types**: See `supabase_auth.py:SupabaseAuthError`, `TokenExpiredError`, `TokenInvalidError`.

### Workspace Roles (4 levels)

| Role | Read Own | Read Workspace | Modify Workspace | Manage Members | Delete Workspace |
|------|---------|----------------|-------------------|----------------|------------------|
| owner | Yes | Yes | Yes | Yes | Yes |
| admin | Yes | Yes | Yes | Yes | No |
| member | Yes | Yes | Limited | No | No |
| guest | Yes | Read-only | No | No | No |

---

## Encryption & Vault

### EncryptionService

**File**: `encryption.py` (at `infrastructure/encryption.py`)

Encrypt/decrypt via Supabase Vault (AES-256-GCM). See `encryption.py:EncryptionService`.

**Interface**:
- `encrypt_api_key(key, key_type) -> str`: Store encrypted key in Vault
- `decrypt_api_key(key_id) -> str`: Retrieve and decrypt on demand

**Key Types**: `github`, `slack`, `openai`, `anthropic`, `google`

**BYOK Pattern** (Bring Your Own Key):
1. User provides API key via Settings UI
2. `EncryptionService.encrypt_api_key()` stores in Supabase Vault
3. `WorkspaceAPIKey` record created with vault reference + workspace_id (see `database/models/workspace_api_key.py`)
4. AI agents call `decrypt_api_key()` at request time
5. Key used for single request, then discarded (no in-memory cache)

**Security Guarantees**: AES-256-GCM authenticated encryption, keys never logged, decryption only at point of use, workspace-scoped storage.

---

## Troubleshooting

- **RLS Context Not Set**: Run `SELECT current_setting('app.current_user_id')` to verify. If NULL, middleware did not set context for this request path.
- **Cross-Workspace Data Leak**: Create integration tests with 2 workspaces. Insert in workspace A, query from workspace B. Verify zero results.
- **Token Validation Failures**: Check JWT algorithm, expiration, and Supabase project URL in environment variables.
- **Vault Decryption Errors**: Verify Supabase Vault is accessible, encrypted reference is valid, service role has vault permissions.

---

## Related Documentation

- **Parent layer**: [infrastructure/README.md](../../infrastructure/README.md)
- **Database models**: [database/README.md](../database/README.md) (WorkspaceScopedMixin, model hierarchy)
- **AI Layer RLS**: [ai/mcp/README.md](../../ai/mcp/README.md) (RLS enforcement in MCP tools)
- **RLS patterns**: `docs/architect/rls-patterns.md`
- **Design decisions**: `docs/DESIGN_DECISIONS.md` (DD-060: Supabase, DD-061: Auth + RLS)
