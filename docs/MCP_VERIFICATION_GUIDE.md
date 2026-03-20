# MCP Platform Hardening — Verification & Test Guide

**Branch:** `improve/mcp-setup`
**Milestone:** v1.1.0 — 50 commits, 84 files changed, +11,003 lines
**Migrations:** 091–097 (run `alembic upgrade head` before testing)

---

## Prerequisites

```bash
# 1. Start Supabase local stack
cd infra/supabase && docker compose up -d

# 2. Apply all migrations (use supabase_admin for DDL privileges)
cd backend
DATABASE_URL="postgresql://supabase_admin:<POSTGRES_PASSWORD>@localhost:15433/postgres" \
  uv run alembic upgrade head

# 3. Start backend
cd backend && uv run uvicorn pilot_space.main:app --reload --port 8000

# 4. Start frontend
cd frontend && pnpm dev

# 5. Open browser
open http://localhost:3000
```

> **Find POSTGRES_PASSWORD:** `docker exec supabase-db env | grep POSTGRES_PASSWORD`

---

## Test Flow 1: MCP Catalog Browse & Install

**Requirements:** MCPC-01, MCPC-02, MCPC-04

### Steps

1. **Login** → Navigate to any workspace
2. **Open Settings** → Click gear icon → Select **"MCP Servers"** from sidebar
3. **Verify two tabs exist:** "Registered Servers" and "Catalog"
4. **Click "Catalog" tab**
5. **Verify 3 official entries appear:**

   | Name | Transport | Auth | Official Badge |
   |------|-----------|------|----------------|
   | Context7 | HTTP | Bearer | Blue "Official" |
   | GitHub | HTTP | OAuth2 | Blue "Official" |
   | Sequential Thinking | Stdio | None | Blue "Official" |

6. **Test filter chips:**
   - Click **"HTTP"** → Only Context7 and GitHub visible
   - Click **"Stdio"** → Only Sequential Thinking visible
   - Click **"All"** → All 3 visible

7. **Install Sequential Thinking:**
   - Click **"Install"** button on Sequential Thinking card
   - **Expected:** Success toast "Server installed — add your auth token to activate it."
   - **Expected:** Tab switches to "Registered Servers"
   - **Expected:** Sequential Thinking appears in list with:
     - Violet "Stdio" badge (not Bearer/OAuth badge)
     - Command line: `npx -y @anthropic-ai/sequential-thinking`
     - No "Authorize" button (stdio doesn't need it)
     - No "Refresh status" button (stdio has no URL to probe)

8. **Switch back to Catalog tab:**
   - Sequential Thinking card should show "Installed" badge (disabled Install button)

### Pass Criteria
- [ ] 3 catalog entries visible with correct badges
- [ ] Filter chips work correctly
- [ ] One-click install creates server with correct stdio config
- [ ] Installed server shows stdio-specific UI (no OAuth/probe buttons)
- [ ] Catalog shows "Installed" state after install

---

## Test Flow 2: Manual Stdio Server Registration

**Requirements:** Stdio transport support

### Steps

1. Go to **Settings → MCP Servers → Registered Servers tab**
2. Click **"Register New MCP Server"** (expand the form)
3. **Verify transport mode selector** with two options:
   - "Remote (SSE/HTTP)" — default
   - "Local (stdio)"

4. **Select "Local (stdio)":**
   - **Expected:** URL field disappears
   - **Expected:** Auth type selector disappears
   - **Expected:** Command + Args fields appear
   - **Expected:** OAuth fields hidden

5. **Fill the form:**
   - Display Name: `My Custom Thinking Tool`
   - Command: `npx`
   - Args: `-y @anthropic-ai/sequential-thinking`

6. **Click "Register Server"**
   - **Expected:** Success toast
   - **Expected:** Server appears in list with stdio badge and command display

7. **Test "Remote (SSE/HTTP)" mode still works:**
   - Expand form again, select "Remote (SSE/HTTP)"
   - **Expected:** URL field returns, auth type selector returns

### Pass Criteria
- [ ] Transport mode selector renders with 2 options
- [ ] Switching to stdio hides URL/auth, shows command/args
- [ ] Stdio server registers successfully
- [ ] Switching back to remote mode restores original form

---

## Test Flow 3: Remote MCP Server with Bearer Token

**Requirements:** MCPI-02 (SSE/HTTP), existing MCP-01..06

### Steps

1. Go to **Settings → MCP Servers → Register New MCP Server**
2. Keep transport mode as **"Remote (SSE/HTTP)"**
3. Fill:
   - Display Name: `Test Context7`
   - Server URL: `https://mcp.context7.com/mcp`
   - Auth Type: Bearer Token
   - Bearer Token: `test-token-12345`
4. Click **"Register Server"**
5. **Verify server appears** with:
   - "Bearer" auth badge
   - URL displayed
   - "Refresh status" button visible
   - "Require approval" toggle visible

6. **Click "Refresh status":**
   - Status badge should update (likely "connected" or "failed" depending on token)

7. **Toggle "Require approval for tool calls":**
   - Switch should toggle
   - No error

8. **Delete the server:**
   - Click trash icon → Confirm in dialog
   - Server removed from list

### Pass Criteria
- [ ] Bearer token server registers successfully
- [ ] Status refresh works
- [ ] Approval toggle works
- [ ] Delete works with confirmation

---

## Test Flow 4: Per-Workspace Server Cap (Max 10)

**Requirements:** MCPI-04

### Steps

1. Register 10 MCP servers (mix of stdio and remote):
   - Use the form or catalog install
   - Can create quick ones like `Test Server 1` through `Test Server 10`

2. **Attempt to register the 11th:**
   - **Expected:** HTTP 422 error
   - **Expected:** Error message contains "maximum of 10" and "Delete an existing server"

3. **Delete one server, then re-register:**
   - Should succeed now (count = 9)

### Pass Criteria
- [ ] 10th server registers OK
- [ ] 11th server blocked with clear error message
- [ ] After delete, can register again

---

## Test Flow 5: Approval Mode in Chat

**Requirements:** MCPA-01, MCPA-02, MCPA-03, MCPA-04

### Steps

1. **Register a remote MCP server** (e.g., Context7 with a valid API key)
2. **Toggle "Require approval"** ON in the server card
3. **Open the AI Chat** panel
4. **Send a message** that would trigger the MCP tool (e.g., "Look up React documentation using context7")
5. **If the tool fires:**
   - **Expected (require_approval=ON):** An inline approval card appears in chat showing:
     - Tool name
     - Server name
     - Input preview
     - Approve/Deny buttons
   - Click **"Approve"** → tool executes, response streams
   - Click **"Deny"** → tool blocked, Claude adapts

6. **Toggle "Require approval"** OFF
7. **Send the same message again:**
   - **Expected (auto_approve):** Tool executes immediately without approval card

### Pass Criteria
- [ ] require_approval shows inline approval card
- [ ] Approve allows execution
- [ ] Deny blocks execution
- [ ] auto_approve executes without interruption

---

## Test Flow 6: Token Expiry Badge (OAuth Servers)

**Requirements:** MCPO-03

### Steps

1. **Register a GitHub MCP server** from catalog (OAuth2 type)
2. **In the server card, verify:**
   - "OAuth2" auth badge visible
   - "Authorize" button visible
   - Token expiry badge shows:
     - Before authorization: no expiry badge (no token yet)
     - After authorization: "Expires in Xh" or similar

3. **To test expired state** (optional, requires DB manipulation):
   ```sql
   UPDATE workspace_mcp_servers
   SET token_expires_at = NOW() - interval '1 hour'
   WHERE display_name = 'GitHub';
   ```
   - Refresh page → card shows red "Token expired" badge

### Pass Criteria
- [ ] OAuth2 badge visible
- [ ] Authorize button visible
- [ ] Expiry badge reflects token state

---

## Test Flow 7: MCP Tool Usage Dashboard

**Requirements:** MCPOB-01, MCPOB-02

### Steps

1. **Use an MCP tool in chat** (any registered server with tools)
2. **Navigate to Settings → AI Usage/Cost dashboard** (or similar)
3. **Click "MCP Tools" tab**
4. **Verify:**
   - Bar chart or table shows per-server invocation counts
   - Tool names visible
   - Date range filter works

5. **If no MCP tools have been used:**
   - Empty state: "No MCP tool usage recorded yet"

### Pass Criteria
- [ ] MCP Tools tab exists in dashboard
- [ ] Data reflects actual tool usage
- [ ] Empty state when no data

---

## Test Flow 8: Catalog Version Update Detection

**Requirements:** MCPC-03

### Steps

1. **Install a server from catalog** (e.g., Sequential Thinking)
2. **Verify "Installed" badge** appears on catalog card (no update badge)
3. **Simulate version bump** (requires DB):
   ```sql
   UPDATE mcp_catalog_entries
   SET catalog_version = '2.0.0'
   WHERE name = 'Sequential Thinking';
   ```
4. **Refresh the page** → Switch to Catalog tab
5. **Verify:** Amber "Update Available" badge appears on Sequential Thinking card

### Pass Criteria
- [ ] No update badge when versions match
- [ ] Amber "Update Available" badge when catalog_version > installed_catalog_version

---

## Test Flow 9: Security — Stdio Command Allow-List

**Requirements:** Security hardening

### Steps

1. **Register a stdio server with an allowed command:**
   - Command: `npx`, Args: `-y @anthropic-ai/sequential-thinking`
   - **Expected:** Registers successfully, loads at session time

2. **Register a stdio server with a blocked command:**
   - Command: `rm`, Args: `-rf /`
   - **Expected:** Server registers (DB doesn't block), BUT at session load time:
     - Server is silently skipped
     - Log entry: `mcp_stdio_command_blocked`
     - AI cannot use tools from this server

3. **Allowed commands:** `npx`, `node`, `python3`, `python`, `uvx`

### Pass Criteria
- [ ] Allowed commands load successfully
- [ ] Blocked commands silently skipped at session time
- [ ] No arbitrary command execution possible

---

## Test Flow 10: Production Encryption Key Enforcement

**Requirements:** MCPI-06

### Steps (local verification only)

1. **Start backend normally** (development mode):
   - **Expected:** Starts without error (dev mode allows missing ENCRYPTION_KEY)

2. **Start backend with production flag but no key:**
   ```bash
   APP_ENV=production ENCRYPTION_KEY="" \
     uv run uvicorn pilot_space.main:app --port 8001
   ```
   - **Expected:** Immediate `RuntimeError` at startup
   - **Expected:** Error message contains "ENCRYPTION_KEY must be set in production"
   - **Expected:** Message includes key generation command

3. **Start backend with production flag and valid key:**
   ```bash
   APP_ENV=production ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
     uv run uvicorn pilot_space.main:app --port 8001
   ```
   - **Expected:** Starts successfully, log shows `encryption_key_validated`

### Pass Criteria
- [ ] Dev mode: no enforcement
- [ ] Production + empty key: RuntimeError with helpful message
- [ ] Production + valid key: starts OK

---

## Test Flow 11: Health-Check Gating

**Requirements:** MCPI-03

### Steps

1. **Register a remote MCP server** with an invalid/unreachable URL
2. **Click "Refresh status"** → Status shows "Failed"
3. **Open AI Chat and send a message**
4. **Verify** in backend logs:
   - `mcp_server_skipped_failed` log entry for this server
   - Other registered servers still load normally
   - Chat response is not delayed by the failed server

### Pass Criteria
- [ ] Failed servers skipped at session load
- [ ] Other servers unaffected
- [ ] No timeout delays from failed servers

---

## Automated Test Verification

Run these commands to verify all automated tests pass:

```bash
# Backend unit tests (all agent tests)
cd backend && uv run pytest tests/unit/ai/ -q

# Backend MCP-specific tests
cd backend && uv run pytest tests/unit/ai/agents/test_build_stream_config_allowed_tools.py \
  tests/unit/ai/agents/test_pilotspace_stream_utils.py \
  tests/unit/ai/sdk/test_question_adapter.py \
  tests/api/test_workspace_mcp_servers.py \
  tests/unit/api/test_mcp_catalog_router.py \
  tests/unit/test_startup_encryption_enforcement.py \
  -v --tb=short

# Frontend type check + lint
cd frontend && pnpm type-check && pnpm lint

# Backend quality gates
cd backend && uv run ruff check && uv run pyright
```

### Expected Results
- All backend tests: **PASS**
- Frontend type-check: **0 errors**
- Frontend lint: **0 errors**
- Ruff: **All checks passed**
- Pyright: **0 errors, 0 warnings**

---

## Migration Verification

```bash
# Verify single head
cd backend && uv run alembic heads
# Expected: 097_add_stdio_mcp_support (head)

# Verify all tables exist
docker exec supabase-db psql -U postgres -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_name IN ('mcp_catalog_entries', 'workspace_mcp_servers')
  ORDER BY table_name;
"

# Verify catalog seeds
docker exec supabase-db psql -U postgres -c "
  SELECT name, transport_type, auth_type, is_official
  FROM mcp_catalog_entries ORDER BY sort_order;
"
# Expected:
# Context7            | http  | bearer | t
# GitHub              | http  | oauth2 | t
# Sequential Thinking | stdio | none   | t

# Verify new columns on workspace_mcp_servers
docker exec supabase-db psql -U postgres -c "
  SELECT column_name, is_nullable
  FROM information_schema.columns
  WHERE table_name = 'workspace_mcp_servers'
    AND column_name IN (
      'transport_type', 'approval_mode', 'refresh_token_encrypted',
      'token_expires_at', 'catalog_entry_id', 'installed_catalog_version',
      'stdio_command', 'stdio_args'
    )
  ORDER BY column_name;
"
# Expected: 8 columns, all present
```

---

## Summary of Changes by Phase

| Phase | What Changed | Key Files |
|-------|-------------|-----------|
| 30 | `allowed_tools` wildcard fix | `pilotspace_agent.py` |
| 31 | SSE+HTTP transport, health gating, server cap, SSRF, encryption | `pilotspace_stream_utils.py`, `ssrf.py`, `main.py`, migrations 091-094 |
| 32 | OAuth refresh tokens, auto-refresh, expiry badge | `workspace_mcp_servers.py`, `mcp-server-card.tsx`, migration 092 |
| 33 | DD-003 approval for remote MCP, per-server toggle, ChatView cards | `question_adapter.py`, `mcp-server-card.tsx`, migration 093 |
| 34 | Audit trail, MCP usage dashboard tab | `hooks_lifecycle.py`, `mcp_usage.py`, `cost-dashboard-page.tsx`, migration 094 |
| 35 | MCP catalog, one-click install, version tracking | `mcp_catalog.py`, `mcp-catalog-card.tsx`, migrations 095-096 |
| +stdio | Stdio transport, Sequential Thinking, auth_type=none | model, schema, stream_utils, form, migration 097 |
