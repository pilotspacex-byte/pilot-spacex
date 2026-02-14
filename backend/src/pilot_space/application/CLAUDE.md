# Application Layer - Pilot Space

**Purpose**: Command and query handlers for all business logic. Domain-focused, async-first, dependency-injected.

---

## Submodule Documentation

- **[services/CLAUDE.md](services/CLAUDE.md)** -- All service groups by domain with interfaces and constraints

---

## Core Pattern: CQRS-lite (DD-064)

Every service follows `Service.execute(Payload) -> Result` with explicit dataclass payloads and typed results. Payloads and results are defined as `@dataclass` in each service file.

- **Commands** (mutations): e.g., `CreateIssueService.execute(CreateIssuePayload) -> CreateIssueResult`
- **Queries** (reads): e.g., `GetIssueService.execute(GetIssuePayload) -> GetIssueResult`

### Payload Design

One `@dataclass` per operation. Optional fields use sensible defaults. Update payloads use `UNCHANGED` sentinel to distinguish "no change" from "set to null". See `services/issue/update_issue_service.py` for the sentinel pattern.

### Result Design

Always include computed metadata beyond the domain entity (e.g., `activities`, `changed_fields`, `ai_enhanced`).

---

## Service Composition & Dependency Injection

### Instantiation Patterns

**Pattern 1 (Recommended)**: Router with type aliases from `api/v1/dependencies.py`. Uses `@inject` decorator with `SessionDep` (triggers ContextVar session) and service dependency types (auto-injected from container).

**Pattern 2**: Container provider for complex setups. See `container.py` for all 38+ service definitions.

**Pattern 3 (Testing only)**: Manual instantiation with explicit repositories.

### Container Configuration

All services defined in `container.py`. Session injection uses `providers.Callable(get_current_session)` for ContextVar-based session scoping. Repositories are `providers.Factory` instances wired to services.

**Singletons**: Config, Engine, SessionFactory, ResilientExecutor

**Factories**: Repositories, Services (new instance per request)

---

## Transaction Boundaries

Each service receives `AsyncSession` (not sessionmaker). Session created per request, auto-commits on exit, rollback on exception. For multi-operation atomicity, use `async with self._session.begin()`.

---

## Error Handling

Services raise `ValueError` for validation/business errors. Middleware converts to RFC 7807. See `api/v1/middleware/` for error conversion.

---

## Standards

- One `@dataclass` payload per operation (optional fields default to `field(default_factory=...)` for mutables)
- One `@dataclass` result per operation with computed metadata
- Async `execute(payload: Payload) -> Result` method
- All database access via repositories (never direct SQLAlchemy)
- Eager load all relationships
- Create activity records for all mutations
- Tests: happy path + 2 edge cases, coverage >80%
- Type hints on all parameters and returns

---

## Best Practices

1. **Single Responsibility**: Each service = one command or query
2. **Validate at Boundaries**: Pydantic validates shape in router; service validates business logic
3. **Eager Loading**: Every repository query must eager-load relationships
4. **Strategic Logging**: Log at entry/exit/errors, not inside loops
5. **Test Services, Not Routers**: Test via `service.execute()`, not HTTP
6. **Soft Deletes**: Never hard delete; use `is_deleted` flag

---

## Related Documentation

- **Backend architecture**: `backend/CLAUDE.md`
- **Repository pattern**: [infrastructure/database/CLAUDE.md](../infrastructure/database/CLAUDE.md)
- **Domain entities**: [domain/CLAUDE.md](../domain/CLAUDE.md)
- **Design decisions**: `docs/DESIGN_DECISIONS.md` (DD-064: CQRS-lite)
- **Dev patterns**: `docs/dev-pattern/45-pilot-space-patterns.md`
