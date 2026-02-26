# Contributing to Pilot Space

Thank you for contributing. This document covers everything you need to get a change merged: workflow, standards, commit format, quality gates, and architecture constraints.

---

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Reporting Issues](#reporting-issues)
- [Development Workflow](#development-workflow)
- [Commit Format](#commit-format)
- [Code Standards](#code-standards)
- [Quality Gates](#quality-gates)
- [Pull Request Process](#pull-request-process)
- [Architecture Constraints](#architecture-constraints)
  - [Backend Patterns](#backend-patterns)
  - [Frontend Patterns](#frontend-patterns)
  - [AI Layer Rules](#ai-layer-rules)
  - [Database & Migrations](#database--migrations)
  - [Security Requirements](#security-requirements)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)

---

## Ways to Contribute

- **Bug fixes** — fix a confirmed bug with a test that proves it
- **Features** — work from an existing issue or open one first to discuss scope
- **Documentation** — improve wiki docs, architecture docs, or code comments
- **Tests** — add missing test coverage (threshold: >80%)
- **Performance** — backed by a benchmark showing improvement

Open an issue before starting significant work. It avoids duplicate effort and lets the team align on approach before you write code.

---

## Reporting Issues

Use GitHub Issues. Include:

**Bug reports:**
- Pilot Space version / branch
- Steps to reproduce (minimal)
- Expected vs. actual behavior
- Logs or screenshots if applicable
- Environment (OS, Node version, Python version)

**Feature requests:**
- Problem you're solving
- Proposed solution
- Alternatives considered
- Which layer it affects (frontend / backend / AI / infra)

**Security vulnerabilities:** Do **not** open a public issue. Email `tin@pilotspace.dev` directly.

---

## Development Workflow

```bash
# 1. Fork and clone
git clone https://github.com/<your-fork>/pilot-space.git
cd pilot-space

# 2. Create a branch from main
git checkout -b feat/issue-123-short-description
# or: fix/issue-456-what-it-fixes
# or: refactor/service-name-reason

# 3. Set up your environment (see README.md → Setup)

# 4. Make changes, keeping commits small and focused

# 5. Run quality gates before pushing (see Quality Gates section)

# 6. Push and open a PR against main
```

**Branch naming:**
```
feat/<issue-number>-<short-description>
fix/<issue-number>-<short-description>
refactor/<scope>-<reason>
docs/<what-is-documented>
test/<what-is-tested>
chore/<task>
```

---

## Commit Format

All commits **must** follow Conventional Commits. Non-conforming commits are rejected by pre-commit hooks.

```
<type>(<scope>): <short summary>

<body — detailed description, motivation, context>

<footer — issue references, breaking changes>
author: Tin Dang
```

**Types:** `feat` | `fix` | `refactor` | `docs` | `test` | `chore` | `perf` | `ci` | `build` | `style` | `revert`

**Scopes:** `module` | `service` | `component` | `api` | `infra` | `config`

**Examples:**
```
feat(api): add bulk issue state transition endpoint

Adds POST /api/v1/issues/bulk-state to transition multiple issues
atomically. Required for sprint closure workflow. Validates state
machine constraints per issue before executing any transitions.

Closes #234
author: Tin Dang
```

```
fix(component): resolve MobX observer/TipTap flushSync conflict in IssueEditorContent

observer() + ReactNodeViewRenderer causes nested flushSync error in React 19.
Removed observer() from IssueEditorContent; data now flows via IssueNoteContext
(context bridge pattern). PropertyBlockView remains observer-wrapped as it
renders inside ProseMirror transaction boundary.

Refs: .claude/rules/tiptap.md
author: Tin Dang
```

**Write commit messages to a file and use `-F`:**
```bash
git commit -F tmp/my-commit-msg.txt
```

---

## Code Standards

These are enforced by pre-commit hooks and CI. Violations block merge.

### Universal

| Rule | Enforcement |
|------|-------------|
| No TODOs, mocks, stubs, or placeholder functions | Pre-commit |
| No files > 700 lines (Python, TS, JS — excludes `.md`) | Pre-commit |
| Conventional commit format | Pre-commit |
| Secrets must not be committed | Pre-commit (detect-secrets) |
| >80% test coverage for new code | CI |

### Python (Backend)

- Python 3.12+, strict type hints everywhere
- Pydantic v2 for all validation — no raw `dict` passing across layer boundaries
- Async-only for I/O: no `time.sleep()`, no blocking `open()`, no synchronous DB calls inside `async def`
- No N+1 queries — use `selectinload` / `joinedload`, never lazy-load in loops
- Repository pattern for all data access — domain services never import SQLAlchemy directly
- `set_rls_context()` before every workspace-scoped DB call
- Dependency injection via `dependency-injector` — no global state, no module-level singletons

### TypeScript (Frontend)

- TypeScript strict mode — no `any`, no `as unknown as X`
- MobX `observer()` for components that read observables — but never on `IssueEditorContent` or any component wrapping `ReactNodeViewRenderer` (React 19 `flushSync` constraint — see `.claude/rules/tiptap.md`)
- TanStack Query for all server state — no `useState` + `useEffect` for API calls
- No direct store mutations from components — go through action methods
- WCAG 2.2 AA accessibility on all interactive UI: `aria-label`, `role`, focus management

### Prohibited patterns

```python
# ❌ Blocking I/O in async
async def get_data():
    time.sleep(1)          # blocks event loop
    open("file.txt")       # sync I/O

# ❌ N+1 query
for issue in issues:
    await issue.awaitable_attrs.labels  # N queries

# ❌ TODO placeholder
async def create_issue(...):
    # TODO: implement
    pass
```

```typescript
// ❌ observer() on TipTap NodeView parent
export const IssueEditorContent = observer(({ ... }) => {  // causes flushSync crash
  return <EditorContent editor={editor} />
})

// ❌ Raw any
const data: any = await fetch(url)
```

---

## Quality Gates

Run both gates before every push. CI enforces the same checks and blocks merge on failure.

### Backend

```bash
cd backend
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

| Gate | Command | Threshold |
|------|---------|-----------|
| Type check | `uv run pyright` | Zero errors |
| Lint | `uv run ruff check` | Zero violations |
| Tests + coverage | `uv run pytest --cov=.` | >80% |

### Frontend

```bash
cd frontend
pnpm lint && pnpm type-check && pnpm test
```

| Gate | Command | Threshold |
|------|---------|-----------|
| Lint | `pnpm lint` | Zero errors |
| Type check | `pnpm type-check` | Zero errors |
| Tests | `pnpm test` | >80% coverage |

**Do not bypass hooks with `--no-verify`.** If a hook is failing and you believe it is a false positive, discuss it in the issue thread before disabling.

---

## Pull Request Process

1. **One logical change per PR.** A PR that fixes a bug and refactors a module is two PRs.
2. **Link the issue.** `Closes #123` in the PR description.
3. **Fill in the template.** Summary, test plan, affected files.
4. **All quality gates must be green** before requesting review.
5. **Resolve all review comments** before re-requesting review. Pushing a new commit counts as a response — explain what changed.
6. **One approving review required** from a codeowner before merge.
7. **Squash merge** — the PR title becomes the squash commit message; ensure it follows the commit format.

### PR Description Template

```markdown
## Summary
- What changed and why (bullet points)

## Test Plan
- [ ] Unit tests added / updated
- [ ] Integration tests pass
- [ ] Manual test steps (if UI change)

## Affected Areas
- [ ] Backend
- [ ] Frontend
- [ ] AI layer
- [ ] Database migration required

## Breaking Changes
None / describe here
```

---

## Architecture Constraints

Read the relevant architecture docs before making structural changes:
- `docs/dev-pattern/45-pilot-space-patterns.md` — project-specific overrides
- `backend/README.md` — backend layer patterns
- `frontend/README.md` — frontend patterns
- `backend/src/pilot_space/ai/README.md` — AI layer architecture

### Backend Patterns

**5-layer Clean Architecture — do not skip layers:**
```
Presentation (FastAPI routers + Pydantic schemas)
   ↓ Payload
Application (Service.execute — CQRS-lite)
   ↓ Domain Entity
Domain (Rich entities + domain services — no I/O)
   ↓ Repository interface
Infrastructure (SQLAlchemy, Redis, Meilisearch)
   ↓ (separate path)
AI (PilotSpaceAgent + MCP tools)
```

- Routers only validate and delegate — no business logic in router functions
- Services own transactions — `async with uow:` wraps all mutations
- Domain entities are framework-agnostic — no SQLAlchemy imports in domain layer
- New services go in `application/services/` — one file per domain concept, max 700 lines

**Error handling:** RFC 7807 — use `ProblemDetail` response schema, not raw `HTTPException` with string messages.

### Frontend Patterns

**State split:**
- **MobX** — UI state, streaming state, optimistic updates, editor state
- **TanStack Query** — server data (notes, issues, workspace members)
- No `useState` for data that comes from the server or that multiple components need

**Feature folder structure:**
```
features/<domain>/
  components/     ← React components
  hooks/          ← custom hooks
  stores/         ← MobX store (if domain-specific)
  services/       ← API client
  types.ts        ← shared types
  index.ts        ← barrel exports (public API only)
```

**TipTap / ProseMirror constraint:**
Any component that mounts `<EditorContent>` via `ReactNodeViewRenderer` must **not** be wrapped in `observer()`. Use the context bridge pattern: pass data through `React.createContext` from an `observer()` parent, and make the editor component a plain function. See `.claude/rules/tiptap.md` and `frontend/src/features/issues/contexts/issue-note-context.ts`.

### AI Layer Rules

These rules implement DD-086 (centralized agent), DD-003 (approval), DD-011 (provider routing). Violating them breaks the security model.

**PilotSpaceAgent is the single entry point.** Do not add new SSE endpoints that bypass it for non-ghost-text use cases.

**New skills** (single-turn, stateless operations):
1. Add YAML definition to `backend/src/pilot_space/ai/prompts/skills/`
2. Register in `skills/skill_registry.py`
3. Add to `frontend/src/features/ai/ChatView/constants.ts` (display name + category)
4. Write unit test for the skill executor

**New subagents** (multi-turn, stateful):
1. Extend `AgentBase` — inherits BYOK, RLS, retry, telemetry
2. Stream progress back through orchestrator's SSE pipe — no direct SSE connections
3. Register in `pilotspace_intent_pipeline.py`
4. Add `@agent-name` to `ChatView/constants.ts`

**Provider routing (DD-011):**
Never hardcode model names. Always route through `providers/provider_selector.py`. Use the correct task tier:
- Opus: PR review, AI context (deep reasoning)
- Sonnet: issue ops, doc gen, conversation (balanced)
- Haiku/Flash: ghost text, scoring (latency-critical)

**Approval tiers (DD-003):**
- `AUTO_EXECUTE` — read-only, reversible
- `DEFAULT` — content creation / update
- `CRITICAL` — permanent deletion, merge, archive (always require)

New MCP tools must declare an approval tier in `mcp/registry.py`. Default to `DEFAULT` when unsure.

**Resilience (required for all external API calls):**
```python
# All provider calls must use execute_with_resilience()
result = await self.execute_with_resilience(
    operation=lambda: provider.call(...),
    timeout=30.0,
)
```

### Database & Migrations

**Never edit existing migration files.** Files in `backend/alembic/versions/` are immutable once committed. Create a new migration to fix a mistake.

**Verify the revision chain before creating a migration:**
```bash
cd backend
alembic heads  # must show exactly one head
```

**Every migration creating a new table must include:**
1. `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY`
2. `ALTER TABLE <name> FORCE ROW LEVEL SECURITY`
3. Workspace isolation policy using `current_setting('app.current_user_id', true)::uuid`
4. Service role bypass policy

RLS enum values in policies use **UPPERCASE**: `'OWNER'`, `'ADMIN'`, `'MEMBER'`, `'GUEST'`.

See `.claude/rules/rls-check.md` for the full RLS template.

**Post-migration validation:**
```bash
cd backend
alembic heads   # single head
alembic check   # head matches models
```

### Security Requirements

- **No plaintext secrets in code or logs.** Use `SecretStr` for Pydantic fields holding keys.
- **BYOK keys are encrypted at rest.** Use `SecureKeyStorage.store_api_key()` — never write raw keys to the database.
- **RLS context set before every DB call.** `await set_rls_context(workspace_id, user_id, role)` at the start of every service method that performs workspace-scoped queries.
- **Validate inputs at system boundaries.** FastAPI routers validate via Pydantic schemas; domain logic trusts validated payloads.
- **No cross-workspace data leakage.** Every repository query must include `WHERE workspace_id = :workspace_id`. RLS is defense-in-depth, not the only layer.

---

## Testing Requirements

### What to test

| Change | Required tests |
|--------|----------------|
| New API endpoint | Integration test covering success + error paths |
| New service method | Unit tests for business logic branches |
| New domain entity | Unit tests for validation + state machine transitions |
| New React component | Unit tests for render states + user interactions |
| New MobX store method | Unit tests for state transitions |
| New TipTap extension | Unit tests for command behavior |
| Bug fix | Regression test that fails before fix, passes after |

### Test markers (backend)

```python
@pytest.mark.unit          # Fast, no I/O, no DB
@pytest.mark.integration   # Requires DB + Redis
@pytest.mark.api           # FastAPI TestClient endpoint tests
@pytest.mark.e2e           # Full stack (Playwright)
@pytest.mark.slow          # Skip in fast CI runs
```

Run only the relevant tier during development:
```bash
uv run pytest tests/unit/                    # fast feedback loop
uv run pytest -m "not slow and not e2e"     # CI gate
uv run pytest                                # full suite before PR
```

### Test structure

```python
# backend — AAA pattern
async def test_create_issue_sets_backlog_state(issue_service, workspace_ctx):
    # Arrange
    payload = IssueCreatePayload(title="Fix auth", workspace_id=workspace_ctx.id)

    # Act
    issue = await issue_service.create(payload)

    # Assert
    assert issue.state == IssueState.BACKLOG
```

```typescript
// frontend — Testing Library
it('shows approval modal for destructive actions', async () => {
  const { getByRole } = render(<ChatView workspaceId="test" />);
  act(() => store.pushApproval({ actionType: 'delete_issue', ... }));
  expect(getByRole('dialog', { name: /confirm deletion/i })).toBeInTheDocument();
});
```

---

## Documentation

- **Code comments** — only where logic is non-obvious. No restating what the code says.
- **Wiki docs** (`docs/wiki/`) — update when adding a new feature area. Follow the existing structure: Overview → Architecture → Key Flows → Implicit Features → Design Decisions → Files Reference.
- **Design decisions** (`docs/DESIGN_DECISIONS.md`) — add a DD entry for any architectural decision that is non-obvious or has significant trade-offs. Follow the existing format.
- **Architecture docs** (`docs/architect/`) — update if you change system topology, request flows, or layer boundaries.
- **`CLAUDE.md`** — update if you add permanent project-wide conventions that all contributors (and AI agents) should follow.

---

## Questions

- Architecture questions → open a GitHub Discussion
- Bug clarifications → comment on the issue
- Urgent / blocking → tag `@TinDang97` in the issue or PR
