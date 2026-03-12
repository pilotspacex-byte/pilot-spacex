# Phase 13: AI Provider Registry + Model Selection - Research

**Researched:** 2026-03-09
**Domain:** AI provider BYOK extension — custom provider registry, model listing, per-session model selection, agent routing
**Confidence:** HIGH

---

## Summary

The project already has substantial BYOK infrastructure: `AIConfiguration` model + `ai_configurations` table (migration `012`), `ai_configuration.py` router with full CRUD + test endpoints, `SecureKeyStorage` with Fernet encryption, `AIProviderKeyValidator` for Anthropic key validation. The `LLMProvider` enum covers only `anthropic | openai | google`. `SecureKeyStorage.VALID_PROVIDERS` is similarly hard-coded.

Phase 13 extends this in three directions:

1. **Provider registry expansion** — add Kimi, GLM, Gemini, and a `CUSTOM` (OpenAI-compatible) provider category; extend `LLMProvider` enum and the `AIConfiguration` model to carry `base_url` + `display_name` fields so custom providers work.

2. **Model listing endpoint** — new `GET /ai/providers/{workspace_id}/models` endpoint that iterates all valid-key configurations, queries each provider's models list, and returns a flat list of `{provider_id, model_id, display_name, is_selectable}` tuples. The frontend uses this to populate the model selector.

3. **Per-session model selection** — extend `ChatRequest` with optional `model_override: {provider: str, model: str}`, persist selection in `AISession.context`, and route `PilotSpaceAgent._get_api_key` + `_build_stream_config` to the selected provider.

The `PilotSpaceAgent` already supports `user_override` in `ProviderSelector.select()`. The gap is wiring the frontend-selected model down to the agent.

**Primary recommendation:** Extend `AIConfiguration`/`LLMProvider` for custom providers via a new migration (070); add model-listing endpoint in `ai_configuration.py`; add `model_override` to `ChatRequest`; add `selectedModel` MobX state to `PilotSpaceStore` persisted in `localStorage` per workspace; thread the selection through `PilotSpaceActions.sendMessage`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AIPR-01 | Admin configures API keys for pre-defined providers (Anthropic, OpenAI, Kimi, GLM, Gemini) with connected/invalid/unreachable status | `ai_configuration.py` router + `AIConfiguration` model handle this; need to expand `LLMProvider` enum and add key-format validators per new provider |
| AIPR-02 | Admin registers custom OpenAI-compatible provider (name + base URL + API key) | Need `CUSTOM` provider variant, `base_url` + `display_name` columns on `ai_configurations`, and OpenAI-compat test logic |
| AIPR-03 | All configured providers' models surface in model selector | Need new `GET /ai/providers/{workspace_id}/models` endpoint; reuse provider SDK clients to call `/models` list |
| AIPR-04 | PilotSpaceAgent routes to selected provider/model | `ProviderSelector.select()` has `user_override` param; wire `model_override` from `ChatRequest` through to agent dispatch |
| AIPR-05 | Provider status: connected / invalid key / unreachable | Already implemented for test endpoint; expose per-provider status on GET settings response |
| CHAT-01 | User selects AI model for chat session from available workspace models | New `ModelSelector` component in `ChatHeader`, reads from model listing API |
| CHAT-02 | Selected model persists per workspace session (no navigation reset) | `localStorage` key `chat_model_{workspaceId}`, loaded into `PilotSpaceStore.selectedModel` on mount |
| CHAT-03 | Model selector disabled if no valid API key for that provider | `is_selectable` flag from model listing endpoint; disable option in selector |
</phase_requirements>

---

## Standard Stack

### Core (Already in Use — No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | latest in uv.lock | Anthropic SDK — `client.models.list()` | Already imported in `key_storage.py` |
| openai | latest in uv.lock | OpenAI SDK — also covers OpenAI-compat providers via `base_url=` param | Already imported in `key_storage.py` |
| google-generativeai | latest in uv.lock | Gemini key test | Already imported in `key_storage.py` |
| httpx | latest in uv.lock | HTTP client for custom provider test calls | Already imported in `key_validator.py` |
| alembic | latest in uv.lock | Migration tool | Project standard |
| MobX | latest in package.json | Reactive state for `selectedModel` | Project standard frontend state |
| shadcn/ui Select | — | Model selector dropdown | Project UI component library |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `openai.AsyncOpenAI(base_url=X)` | any | OpenAI-compat client for Kimi/GLM/custom | When testing custom providers — pass `base_url` constructor arg |
| `localStorage` | browser built-in | Persist selected model across navigation | Per-workspace key so workspace switch gets own selection |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `localStorage` for model persistence | `AISession.context` field | Session is server-managed; localStorage is synchronous, zero latency, survives page refresh without extra API call |
| Extending `LLMProvider` enum | Free-form provider string | Enum preserves DB integrity; add `CUSTOM` as a catch-all for unknown OpenAI-compat providers |

---

## Architecture Patterns

### Recommended Project Structure

New files:

```
backend/src/pilot_space/
├── ai/providers/
│   └── model_listing.py          # ModelListingService: per-provider model fetch
├── api/v1/routers/
│   └── ai_configuration.py       # EXTEND: add /models endpoint
├── api/v1/schemas/
│   └── ai_configuration.py       # EXTEND: ModelListResponse, ProviderModelItem
├── infrastructure/database/models/
│   └── ai_configuration.py       # EXTEND: base_url, display_name columns
├── alembic/versions/
│   └── 070_extend_ai_config_custom_provider.py  # new migration

frontend/src/
├── features/settings/
│   └── components/
│       └── provider-registry-panel.tsx   # new: list + add custom provider
├── stores/ai/
│   └── PilotSpaceStore.ts         # EXTEND: selectedModel, setSelectedModel
├── features/ai/ChatView/
│   └── ModelSelector.tsx          # new: model picker dropdown in ChatHeader
```

### Pattern 1: Custom Provider via OpenAI Compat `base_url`

**What:** OpenAI Python SDK accepts a `base_url` constructor param, making it work with any OpenAI-compatible endpoint (Kimi `https://api.moonshot.cn/v1`, GLM `https://open.bigmodel.cn/api/paas/v4`, etc.)
**When to use:** For AIPR-02 and Kimi/GLM built-in providers.

```python
# Source: openai Python SDK docs — base_url param
from openai import AsyncOpenAI

async def _test_openai_compat_key(api_key: str, base_url: str) -> tuple[bool, str]:
    """Test OpenAI-compatible provider key."""
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        await client.models.list()
        return True, "API key is valid"
    except Exception as e:
        return False, f"Connection failed: {e}"
```

### Pattern 2: Extended LLMProvider Enum + base_url Column

**What:** Add new enum values and optional `base_url`/`display_name` columns to `ai_configurations`.
**When to use:** Migration 070.

```python
# ai_configuration.py model extension
class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    KIMI = "kimi"
    GLM = "glm"
    CUSTOM = "custom"   # any OpenAI-compat endpoint

# New columns on AIConfiguration:
base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
```

Migration must `op.execute("ALTER TYPE llm_provider ADD VALUE IF NOT EXISTS 'kimi'")` etc. — PostgreSQL enum extension is append-only.

### Pattern 3: Model Listing via Provider SDKs

**What:** Service that queries each active provider and returns available models.
**When to use:** For AIPR-03, called by `GET /ai/configurations/models`.

```python
# ai/providers/model_listing.py
@dataclass
class ProviderModel:
    provider_config_id: str  # AIConfiguration.id as str
    provider: str
    model_id: str
    display_name: str
    is_selectable: bool  # True if provider key is_valid

class ModelListingService:
    async def list_models_for_workspace(
        self,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> list[ProviderModel]:
        """Fetch models from all active providers for a workspace."""
        # 1. Load all active AIConfiguration rows for workspace
        # 2. Decrypt each key
        # 3. Call provider SDK .models.list() with httpx timeout=10s
        # 4. Aggregate results — hardcode fallback list for providers that
        #    don't expose a /models endpoint (Kimi, GLM, Gemini)
```

**Key constraint:** Gemini and some OpenAI-compat providers may not implement `GET /models`. Use hardcoded known-model lists as fallback per provider.

### Pattern 4: Model Selection Persistence (Frontend)

**What:** MobX store holds `selectedModel` per workspace; localStorage persists across navigation.
**When to use:** CHAT-02.

```typescript
// PilotSpaceStore extension
selectedModel: { provider: string; modelId: string } | null = null;

setSelectedModel(provider: string, modelId: string): void {
    this.selectedModel = { provider, modelId };
    const wsId = this.currentWorkspaceId;
    if (wsId) {
        localStorage.setItem(`chat_model_${wsId}`, JSON.stringify({ provider, modelId }));
    }
}

loadSelectedModel(workspaceId: string): void {
    const raw = localStorage.getItem(`chat_model_${workspaceId}`);
    if (raw) {
        try { this.selectedModel = JSON.parse(raw); } catch { /* ignore */ }
    }
}
```

### Pattern 5: Routing model_override to PilotSpaceAgent

**What:** Add optional `model_override` to `ChatRequest`; thread through to `_get_api_key` and `_build_stream_config`.

```python
# api/v1/schemas/ai_chat.py or inline
class ChatRequest(BaseSchema):
    # existing fields...
    model_override: ModelOverride | None = None

class ModelOverride(BaseSchema):
    provider: str   # e.g. "anthropic", "kimi", "custom"
    model: str      # e.g. "claude-sonnet-4-20250514"
    config_id: str  # AIConfiguration.id — used to look up correct api_key + base_url

# In PilotSpaceAgent._get_api_key():
# If model_override is set, look up AIConfiguration by config_id
# rather than defaulting to provider="anthropic"
```

### Anti-Patterns to Avoid

- **Returning encrypted keys in API responses:** Never expose `api_key_encrypted`. `_config_to_response` already omits it.
- **genai.configure() without lock:** `ai_configuration.py` already uses `_google_api_lock` for Gemini. All new Gemini test calls must also acquire this lock.
- **Blocking list() calls:** The Google genai SDK `list_models()` is synchronous — wrap in `asyncio.to_thread()`.
- **Extending files over 700 lines:** `ai_chat.py` is at risk. `model_override` handling goes through `ChatInput` field, not new router logic.
- **Hardcoding env fallback for new providers:** `_get_api_key` must use `AIConfiguration` rows only — no `os.getenv()` fallback for new providers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI-compat provider calls | Custom HTTP wrapper | `openai.AsyncOpenAI(base_url=X)` | Handles auth headers, error codes, retries |
| Anthropic model list | Parse HTML from console | `anthropic.AsyncAnthropic().models.list()` (or `GET /v1/models` — already in `key_validator.py`) | Official API |
| Encryption of new provider keys | New encryption scheme | Existing `encrypt_api_key()` / `decrypt_api_key()` in `infrastructure/encryption.py` | Already tested, consistent |
| Provider enum extension | String column | `ALTER TYPE llm_provider ADD VALUE` migration | DB integrity, type safety |

---

## Common Pitfalls

### Pitfall 1: PostgreSQL Enum Extension Semantics

**What goes wrong:** `ALTER TYPE llm_provider ADD VALUE 'kimi'` cannot be rolled back in a transaction (PostgreSQL limitation). `downgrade()` for migration 070 cannot remove enum values.
**Why it happens:** PostgreSQL enum type modifications are DDL and not transactional in the usual sense.
**How to avoid:** `downgrade()` should be a no-op or drop+recreate if acceptable. Document this in the migration file.
**Warning signs:** `alembic downgrade` fails with "cannot drop type llm_provider because other objects depend on it".

### Pitfall 2: genai.configure() Global State Race

**What goes wrong:** Concurrent Gemini model list calls overwrite each other's API key via the global `genai.configure()`.
**Why it happens:** The google-generativeai SDK uses a module-level configuration object.
**How to avoid:** Always use `_google_api_lock` (already established in `ai_configuration.py`) for any `genai.configure()` call. New `ModelListingService` must acquire the same lock.
**Warning signs:** Intermittent "Invalid API key" errors for Gemini when load is high.

### Pitfall 3: SecureKeyStorage.VALID_PROVIDERS Gating

**What goes wrong:** `SecureKeyStorage.store_api_key()` raises `ValueError` for any provider not in `VALID_PROVIDERS = frozenset({"anthropic", "openai", "google"})`.
**Why it happens:** Hard-coded whitelist.
**How to avoid:** Update `VALID_PROVIDERS` or switch `store_api_key` to accept any provider string when `AIConfiguration` already enforces the enum constraint.
**Warning signs:** `ValueError: Invalid provider: kimi` when trying to store new provider keys.

### Pitfall 4: Models Endpoint — Provider Unavailability Leaking as 500

**What goes wrong:** If one provider is unreachable, the whole models list endpoint fails.
**Why it happens:** Unhandled exception from provider SDK call propagates.
**How to avoid:** Catch per-provider exceptions, mark provider models as `is_selectable=False` with an error field; aggregate remaining results. Never let one provider failure block the response.

### Pitfall 5: AISession.context Missing Model Override on Resume

**What goes wrong:** User selects model, starts session, navigates away, resumes session — model reverts to default.
**Why it happens:** Model selection not persisted in `AISession.context`.
**How to avoid:** When `model_override` is provided in `ChatRequest`, write it into `AISession.context["model_override"]`. On session resume, read it back.

### Pitfall 6: CHAT-02 — localStorage Key Collision Across Workspaces

**What goes wrong:** User switches workspaces, wrong model shown.
**Why it happens:** Single localStorage key shared across workspaces.
**How to avoid:** Key format: `chat_model_{workspaceId}`. Load in `loadSelectedModel(workspaceId)` called on workspace switch.

---

## Code Examples

### Adding a New Provider Type to Existing Key Validation

```python
# Source: existing pattern in ai_configuration.py:_test_provider_api_key
async def _test_kimi_key(api_key: str) -> tuple[bool, str]:
    """Test Kimi (Moonshot) API key — OpenAI-compat at https://api.moonshot.cn/v1"""
    from openai import AsyncOpenAI, AuthenticationError

    try:
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
        await client.models.list()
        return True, "API key is valid"
    except AuthenticationError:
        return False, "Invalid API key"
    except Exception as e:
        return False, f"Connection error: {e}"
```

### Frontend Model Selector in ChatHeader

```typescript
// Source: shadcn/ui Select pattern (used elsewhere in project)
// ModelSelector.tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { observer } from 'mobx-react-lite';

export const ModelSelector = observer(function ModelSelector() {
    const { ai } = useStore();
    const { pilotSpace, availableModels } = ai;

    return (
        <Select
            value={pilotSpace.selectedModel?.modelId ?? ''}
            onValueChange={(modelId) => {
                const model = availableModels.find(m => m.model_id === modelId);
                if (model) pilotSpace.setSelectedModel(model.provider, modelId);
            }}
        >
            <SelectTrigger className="h-7 w-[160px] text-xs">
                <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
                {availableModels.map(m => (
                    <SelectItem key={m.model_id} value={m.model_id} disabled={!m.is_selectable}>
                        {m.display_name}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
});
```

### Migration 070 Skeleton

```python
# alembic/versions/070_extend_ai_config_custom_provider.py
# Revises: 069_add_operation_type_to_costs

def upgrade() -> None:
    # Add new enum values (non-transactional in PostgreSQL — downgrade cannot remove them)
    for val in ('kimi', 'glm', 'custom'):
        op.execute(f"ALTER TYPE llm_provider ADD VALUE IF NOT EXISTS '{val}'")

    # Add columns to ai_configurations
    op.add_column('ai_configurations', sa.Column('base_url', sa.String(512), nullable=True))
    op.add_column('ai_configurations', sa.Column('display_name', sa.String(128), nullable=True))

def downgrade() -> None:
    # Cannot remove enum values in PostgreSQL — columns are reversible
    op.drop_column('ai_configurations', 'display_name')
    op.drop_column('ai_configurations', 'base_url')
    # NOTE: enum values kimi/glm/custom remain — document this in migration
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single Anthropic provider (BYOK) | Multi-provider registry with custom endpoints | Phase 13 | Workspace admins can use any OpenAI-compat API |
| Model hard-coded in `ProviderSelector._ROUTING_TABLE` | User can override model per chat session | Phase 13 | Per-session model flexibility |
| `LLMProvider` enum: anthropic/openai/google | Extended: kimi/glm/custom added | Phase 13 | No more `ValueError` for new providers |

**Existing but partial:**
- `ai_configuration.py` router: CRUD + test endpoint exists, but no `/models` list endpoint.
- `SecureKeyStorage.VALID_PROVIDERS`: must be expanded or removed as gatekeeping.
- `AISettingsPage`: currently hardcodes `anthropic` and `openai` cards — must be generalized.
- `ProviderStatusCard`: typed `provider: 'anthropic' | 'openai'` — must accept `string`.

---

## Open Questions

1. **Kimi / GLM model list availability**
   - What we know: Both use OpenAI-compat base URLs; OpenAI SDK `models.list()` should work.
   - What's unclear: Whether their `/v1/models` endpoint returns a complete model list or a subset.
   - Recommendation: Hardcode known model lists as fallback; use API list when available. At runtime, merge API response with hardcoded list, deduplicating by model ID.

2. **Gemini model list via google-generativeai**
   - What we know: `genai.list_models()` returns all models including non-chat models; filtering by `supported_generation_methods` is needed.
   - What's unclear: SDK async support for `list_models()` (currently `asyncio.to_thread` pattern used).
   - Recommendation: Wrap `genai.list_models()` in `asyncio.to_thread()` with `_google_api_lock`. Filter to `generateContent` methods only.

3. **ChatRequest model_override wiring to PilotSpaceAgent**
   - What we know: `ChatInput` dataclass is constructed in `ai_chat.py`; `PilotSpaceAgent._get_api_key` currently only handles provider="anthropic".
   - What's unclear: Whether the agent should look up `AIConfiguration` directly or receive the decrypted key from the router.
   - Recommendation: Router decrypts and passes `api_key` + `model` + `base_url` as a `ResolvedModelConfig` dataclass to avoid the agent needing DB access for key lookup.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio (uv run pytest) |
| Frontend framework | Vitest + React Testing Library |
| Config file | `backend/pyproject.toml` (pytest section), `frontend/vitest.config.ts` |
| Quick run command (backend) | `cd backend && uv run pytest tests/unit/ai/ tests/unit/routers/test_ai_configuration.py -x -q` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AIPR-01 | Pre-defined providers appear in settings | unit | `uv run pytest tests/unit/routers/test_ai_configuration.py -x` | ❌ Wave 0 |
| AIPR-02 | Custom provider stored with base_url | unit | `uv run pytest tests/unit/routers/test_ai_configuration.py::test_create_custom_provider -x` | ❌ Wave 0 |
| AIPR-03 | Models endpoint aggregates all providers | unit | `uv run pytest tests/unit/ai/test_model_listing.py -x` | ❌ Wave 0 |
| AIPR-04 | Agent routes to user-selected provider | unit | `uv run pytest tests/unit/ai/test_pilotspace_agent_model_override.py -x` | ❌ Wave 0 |
| AIPR-05 | Provider status reflects key validity | unit | `uv run pytest tests/unit/routers/test_ai_configuration.py::test_provider_status -x` | ❌ Wave 0 |
| CHAT-01 | ModelSelector renders available models | unit | `pnpm test src/features/ai/ChatView/__tests__/ModelSelector.test.tsx` | ❌ Wave 0 |
| CHAT-02 | Selected model persists in localStorage | unit | `pnpm test src/stores/ai/__tests__/PilotSpaceStore.model.test.ts` | ❌ Wave 0 |
| CHAT-03 | Selector disabled for invalid-key provider | unit | `pnpm test src/features/ai/ChatView/__tests__/ModelSelector.test.tsx` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/unit/ai/ tests/unit/routers/test_ai_configuration.py -x -q`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/unit/routers/test_ai_configuration.py` — covers AIPR-01, AIPR-02, AIPR-05
- [ ] `backend/tests/unit/ai/test_model_listing.py` — covers AIPR-03
- [ ] `backend/tests/unit/ai/test_pilotspace_agent_model_override.py` — covers AIPR-04
- [ ] `frontend/src/features/ai/ChatView/__tests__/ModelSelector.test.tsx` — covers CHAT-01, CHAT-03
- [ ] `frontend/src/stores/ai/__tests__/PilotSpaceStore.model.test.ts` — covers CHAT-02

---

## Sources

### Primary (HIGH confidence)

- Codebase direct read — `backend/src/pilot_space/ai/providers/provider_selector.py` — ProviderSelector, LLMProvider, user_override support
- Codebase direct read — `backend/src/pilot_space/ai/infrastructure/key_storage.py` — SecureKeyStorage.VALID_PROVIDERS, store/get/validate API
- Codebase direct read — `backend/src/pilot_space/api/v1/routers/ai_configuration.py` — existing CRUD + test endpoints, `_google_api_lock` pattern
- Codebase direct read — `backend/src/pilot_space/infrastructure/database/models/ai_configuration.py` — AIConfiguration model, LLMProvider enum
- Codebase direct read — `frontend/src/stores/ai/AISettingsStore.ts` — existing MobX settings store pattern
- Codebase direct read — `frontend/src/stores/ai/PilotSpaceStore.ts` — existing model selection hook points
- Codebase direct read — `backend/alembic/versions/012_ai_configurations.py` — migration pattern for this table

### Secondary (MEDIUM confidence)

- OpenAI Python SDK docs (from training): `AsyncOpenAI(base_url=X)` for OpenAI-compat providers — standard pattern, well-documented

### Tertiary (LOW confidence)

- Kimi/Moonshot base URL `https://api.moonshot.cn/v1` — from public documentation; verify before implementation
- GLM base URL `https://open.bigmodel.cn/api/paas/v4` — from public documentation; verify before implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all core dependencies already in use in codebase
- Architecture: HIGH — patterns derived from reading existing code, not from external sources
- Pitfalls: HIGH — all pitfalls identified from direct code inspection (VALID_PROVIDERS check, genai lock, enum extension limitations)
- Model list for Kimi/GLM: LOW — external API behavior unverified

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable — openai/anthropic SDK APIs are stable; Kimi/GLM base URLs may change)
