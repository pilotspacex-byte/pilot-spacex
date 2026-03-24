# Data Model: MCP Settings Redevelopment

**Feature**: MCP Settings Redevelopment
**Branch**: `25-mcp-settings`
**Date**: 2026-03-19

---

## Table: `workspace_mcp_servers` (extended)

Extends the existing table. All new columns are additive and nullable or have safe defaults.

### New Enums

```sql
-- Server type
CREATE TYPE mcp_server_type AS ENUM ('remote', 'npx', 'uvx');

-- Transport protocol
CREATE TYPE mcp_transport AS ENUM ('sse', 'stdio', 'streamable_http');

-- 5-state status enum (replaces VARCHAR(16) last_status)
CREATE TYPE mcp_status AS ENUM (
    'enabled',        -- polling healthy, admin has not disabled
    'disabled',       -- admin explicitly disabled; poller skips
    'unhealthy',      -- reachable but returning error responses
    'unreachable',    -- connection timeout or network failure
    'config_error'    -- configuration invalid (e.g. bad URL, missing required field)
);
```

### Column Changes

| Column | Action | Type | Nullable | Default | Notes |
|--------|--------|------|----------|---------|-------|
| `server_type` | ADD | `mcp_server_type` | NOT NULL | `'remote'` | Backfill all existing rows |
| `transport` | ADD | `mcp_transport` | NOT NULL | `'sse'` | Backfill all existing rows |
| `url_or_command` | ADD | `VARCHAR(1024)` | NULL | NULL | Backfill from `url` on existing rows |
| `command_args` | ADD | `VARCHAR(512)` | NULL | NULL | NPX/UVX extra CLI arguments |
| `headers_encrypted` | ADD | `TEXT` | NULL | NULL | Fernet-encrypted JSON object |
| `env_vars_encrypted` | ADD | `TEXT` | NULL | NULL | Fernet-encrypted JSON object |
| `is_enabled` | ADD | `BOOLEAN` | NOT NULL | `TRUE` | Admin toggle; poller respects this |
| `last_status` | ALTER | `mcp_status` | NULL | NULL | Cast from VARCHAR via migration |
| `url` | KEEP | `VARCHAR(512)` | — | — | Backward compat for AI agent hot-loader |

### Unchanged Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | `UUID` | PK, auto |
| `workspace_id` | `UUID FK` | workspaces(id) |
| `display_name` | `VARCHAR(128)` | Unique within workspace (application-level) |
| `auth_type` | `mcp_auth_type` | `bearer` \| `oauth2` |
| `auth_token_encrypted` | `VARCHAR(1024)` | Fernet-encrypted bearer/access token |
| `oauth_client_id` | `VARCHAR(256)` | OAuth2 only |
| `oauth_auth_url` | `VARCHAR(512)` | OAuth2 only |
| `oauth_token_url` | `VARCHAR(512)` | OAuth2 only |
| `oauth_scopes` | `VARCHAR(512)` | OAuth2 only |
| `last_status_checked_at` | `TIMESTAMPTZ` | Last probe timestamp |
| `is_deleted` | `BOOLEAN` | Soft-delete flag |
| `created_at` | `TIMESTAMPTZ` | Auto |
| `updated_at` | `TIMESTAMPTZ` | Auto |

---

## Python Model Update

```python
class McpServerType(StrEnum):
    REMOTE = "remote"
    NPX = "npx"
    UVX = "uvx"

class McpTransport(StrEnum):
    SSE = "sse"
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"

class McpStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"
    CONFIG_ERROR = "config_error"

class WorkspaceMcpServer(WorkspaceScopedModel):
    __tablename__ = "workspace_mcp_servers"

    # --- Existing fields (unchanged) ---
    display_name: Mapped[str]            # VARCHAR(128)
    url: Mapped[str]                     # VARCHAR(512) - kept for backward compat
    auth_type: Mapped[McpAuthType]
    auth_token_encrypted: Mapped[str | None]
    oauth_client_id: Mapped[str | None]
    oauth_auth_url: Mapped[str | None]
    oauth_token_url: Mapped[str | None]
    oauth_scopes: Mapped[str | None]
    last_status_checked_at: Mapped[datetime | None]

    # --- New fields ---
    server_type: Mapped[McpServerType]        # default REMOTE
    transport: Mapped[McpTransport]           # default SSE
    url_or_command: Mapped[str | None]        # VARCHAR(1024)
    command_args: Mapped[str | None]          # VARCHAR(512)
    headers_encrypted: Mapped[str | None]     # TEXT - Fernet JSON blob
    env_vars_encrypted: Mapped[str | None]    # TEXT - Fernet JSON blob
    is_enabled: Mapped[bool]                  # default True
    last_status: Mapped[McpStatus | None]     # replaces String(16)
```

---

## State Transition Diagram

```
                   ┌─────────────────┐
   [Admin create]  │                 │
   ─────────────► │    ENABLED      │ ◄────── [Admin re-enable]
                   │                 │
                   └────────┬────────┘
                            │ Background poller (60s)
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌───────────┐  ┌──────────────┐
        │UNHEALTHY │  │UNREACHABLE│  │ CONFIG_ERROR  │
        │(5xx resp)│  │(no conn)  │  │(bad URL/cmd)  │
        └──────────┘  └───────────┘  └──────────────┘
              │             │             │
              └─────────────┼─────────────┘
                            │ [Issue resolved + poller next run]
                            ▼
                       [ENABLED]

   [Admin disable]
   ENABLED / UNHEALTHY / UNREACHABLE / CONFIG_ERROR
              │
              ▼
        ┌──────────┐
        │ DISABLED │  (poller skips this server)
        └──────────┘
```

---

## Encrypted KV Field Format

Both `headers_encrypted` and `env_vars_encrypted` store Fernet-encrypted JSON:

**Plaintext before encryption**:
```json
{ "Authorization": "Bearer sk-...", "X-Custom-Header": "value" }
```

**Storage** (`headers_encrypted` column): Fernet token string (base64-encoded).

**Decryption** occurs only:
1. At probe/test time (inject headers into HTTP request)
2. At NPX/UVX spawn time (inject env vars into subprocess env)

**Never decrypted** for API responses. Response includes only `has_headers_secret: bool`.

---

## Validation Rules

| Field | Rule |
|-------|------|
| `display_name` | 1–128 chars; unique within workspace (application-level check, not DB unique constraint, to keep soft-delete behaviour clean) |
| `url_or_command` (remote) | HTTPS scheme required; SSRF blocklist (existing `_validate_mcp_url`) |
| `url_or_command` (npx) | Must start with `npx `; no shell metacharacters: `;`, `&`, `\|`, `$`, `` ` ``, `(`, `)`, `{`, `}`, `<`, `>` |
| `url_or_command` (uvx) | Must start with `uvx `; same metacharacter denylist |
| `command_args` | No shell metacharacters; max 512 chars |
| `transport` | `sse` or `streamable_http` for `remote`; `stdio` for `npx`/`uvx` (enforced at schema level with cross-field validator) |
| `headers` keys | Alphanumeric + hyphen only (HTTP header name format); max 10 entries |
| `env_vars` keys | `[A-Z_][A-Z0-9_]*` (POSIX env var format); max 20 entries |

---

## Migration Checklist

- [ ] `alembic heads` returns single head before migration
- [ ] Migration adds new columns as nullable/with defaults first
- [ ] Backfill `url_or_command = url` for all existing rows
- [ ] Backfill `server_type = 'remote'`, `transport = 'sse'`, `is_enabled = TRUE`
- [ ] Cast `last_status`: `'connected'→'enabled'`, `'failed'→'unreachable'`, `'unknown'→NULL`
- [ ] `alembic check` passes (models match DB) after migration
- [ ] `alembic heads` still returns single head after migration
- [ ] Integration tests pass with `TEST_DATABASE_URL` (PostgreSQL; SQLite skips enum casts)
