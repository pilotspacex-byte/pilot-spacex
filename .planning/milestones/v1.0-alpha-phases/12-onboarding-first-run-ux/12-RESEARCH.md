# Phase 12: Onboarding & First-Run UX - Research

**Researched:** 2026-03-09
**Domain:** Next.js App Router · MobX · TanStack Query · FastAPI · Supabase Auth
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ONBD-01 | New user first sign-in auto-creates a workspace (name derived from email/display name) | Auth flow traced: callback → `/` → no-workspace UI. Auto-create belongs in `app/page.tsx` resolveWorkspace branch. User email + `user_metadata.name` available from Supabase session. |
| ONBD-02 | After workspace creation, user lands on onboarding checklist — never an empty page | OnboardingChecklist renders as Dialog on `[workspaceSlug]/page.tsx`. The checklist is server-state driven (TanStack Query); auto-open controlled by OnboardingStore.modalOpen. |
| ONBD-03 | API key setup step includes inline guidance (where to get key, format hint, test connection button) | Step currently navigates away to `/settings/ai-providers`. Needs an inline expansion within the checklist dialog instead. Validate endpoint exists at `POST /workspaces/{id}/ai-providers/validate`. |
| ONBD-04 | Role + skill generation step shows clear success confirmation when skill saved and active | SkillGenerationWizard calls `createRoleSkillMutation` → on success it immediately calls `onComplete()`. No success state visible in the checklist between steps. Need a confirmation toast/state. |
| ONBD-05 | Each onboarding step links directly to relevant settings action | Currently only ai_providers and invite_members navigate to settings pages. role_setup and first_note are in-dialog. ONBD-05 requires actionable links/buttons on each item. |
| BUG-01 | Skill wizard "Save and Accept" resolves workspaceId to UUID before API call | CONFIRMED: `app/(workspace)/[workspaceSlug]/page.tsx` line 16: `workspaceStore.currentWorkspace?.id ?? workspaceSlug`. WorkspaceGuard calls `workspaceStore.setCurrentWorkspace(workspace)` asynchronously — if the store hasn't resolved yet, fallback is the slug string "workspace", not a UUID. API call path becomes `/workspaces/workspace/role-skills` → 422. |
| BUG-02 | Sign-up empty page fixed — new accounts redirected to workspace creation flow | Auth callback redirects to `/`. `app/page.tsx` checks for workspaces; if none found, shows 2-step creation wizard. Problem: first-time users see a form with no pre-filled name. ONBD-01 is the fix. |
| WS-01 | Workspace switcher shows workspace metadata (name, member count) | `workspace-switcher.tsx` only shows `ws.name`. memberCount is on the `Workspace` type and populated by `workspacesApi.list()`. Display is `Building2 + name + check`. Member count missing. |
| WS-02 | Workspace switch lands user on last visited page within that workspace | `handleSelectWorkspace` calls `router.push(\`/\${ws.slug}\`)` — always goes to workspace root. Need per-workspace last-page tracking. `addRecentWorkspace(slug)` in workspace-selector only tracks the slug, not the last path. |
</phase_requirements>

---

## Summary

Phase 12 is primarily a UX polish phase targeting first-run experience and two concrete bugs. The core onboarding infrastructure (OnboardingChecklist, SkillGenerationWizard, OnboardingStore, TanStack Query hooks, backend onboarding router + service) is fully implemented and working. The phase is about wiring, fixing, and enriching — not building from scratch.

BUG-01 is a race condition: `OnboardingChecklist` receives `workspaceId` from the workspace home page, which falls back to `workspaceSlug` (a string) when `workspaceStore.currentWorkspace` is null. WorkspaceGuard populates the store asynchronously after the page renders. The fix is to derive `workspaceId` from the `WorkspaceContext` (already available via `useWorkspace()`) rather than the MobX store.

BUG-02 and ONBD-01 share the same fix location: `app/page.tsx`. Currently it shows a manual 2-step form to new users. ONBD-01 requires auto-creating the workspace from the user's email/display name without user input — derive the workspace name from `supabase.auth.getUser()` and call `workspacesApi.create()` directly, skipping the form.

WS-01 requires one line addition to the workspace switcher list item. WS-02 requires localStorage tracking of last visited path per workspace slug, read during `handleSelectWorkspace`.

**Primary recommendation:** Fix BUG-01 by passing workspace ID from WorkspaceContext into OnboardingChecklist, not from the store. Implement ONBD-01 in `app/page.tsx` resolveWorkspace. Enhance workspace switcher and checklist steps. All changes are frontend-only except potential backend additions for inline API key testing (endpoint already exists).

---

## Standard Stack

### Core (already in use — no new dependencies)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Next.js App Router | 15.x | Routing, layouts | All changes are in existing route files |
| MobX + mobx-react-lite | 6.x | UI state | OnboardingStore already exists |
| TanStack Query | 5.x | Server state | All hooks already exist |
| shadcn/ui | latest | Dialog, Button, Input, Toast | All primitives already imported |
| Supabase JS client | 2.x | Auth session access | `supabase.auth.getUser()` already used |
| motion/react | 11.x | Animations | Already used in `app/page.tsx` |

### No new dependencies required.

---

## Architecture Patterns

### BUG-01 Fix: WorkspaceId Source

**Problem:** `app/(workspace)/[workspaceSlug]/page.tsx` line 16 uses MobX store as source of truth:
```typescript
// BUGGY — store may not be populated yet
const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;
```

**Fix:** Read from `WorkspaceContext` (populated synchronously before children render):
```typescript
// CORRECT — WorkspaceGuard ensures workspace is available before this page renders
import { useWorkspace } from '@/components/workspace-guard';

const { workspace } = useWorkspace();
const workspaceId = workspace.id; // Always a UUID
```

`WorkspaceGuard` sets `state.status === 'ready'` only after `workspacesApi.get(workspaceSlug)` resolves, then calls `workspaceStore.setCurrentWorkspace(workspace)`. The `WorkspaceContext` holds the same workspace object. Reading from context is correct; reading from the MobX store has a race.

### ONBD-01: Auto Workspace Creation in `app/page.tsx`

The `resolveWorkspace()` function in `app/page.tsx` already handles the "no workspaces" case:
```typescript
// Current: shows a 2-step form
setHasWorkspaces(false);
setIsLoading(false);

// Required: auto-create from email
const { data: { user } } = await supabase.auth.getUser();
const displayName = user?.user_metadata?.name
  || user?.user_metadata?.full_name
  || user?.email?.split('@')[0]
  || 'my-workspace';
const slug = toSlug(displayName); // already imported in app/page.tsx
// Append random suffix to avoid collisions: `${slug}-${Math.random().toString(36).slice(2,6)}`
const workspace = await workspacesApi.create({ name: displayName, slug: uniqueSlug });
addRecentWorkspace(workspace.slug);
router.replace(`/${workspace.slug}`);
```

The `toSlug` utility is already imported. The `workspacesApi.create()` function is already imported. The Supabase client is already imported. Slug collision handling: append a 4-character random suffix, retry once if 409.

### ONBD-02: Ensure Checklist Shows After Auto-Creation

OnboardingChecklist auto-shows when `onboardingStore.isModalOpen === true` (default) and the server returns data without `dismissedAt` or `completedAt`. The backend `GetOnboardingService` auto-creates the onboarding record via `upsert_for_workspace`. This means as long as the workspace exists, the checklist will appear on first visit. No additional wiring needed.

Verification needed: ensure `onboardingStore.modalOpen` defaults to `true` (it does — line 33 of `OnboardingStore.ts`).

### ONBD-03: Inline API Key Guidance

Currently `handleStepAction('ai_providers')` closes the modal and navigates to settings. Instead, expand the `ai_providers` step inline within the dialog:

```typescript
// In OnboardingStepItem or OnboardingChecklist, add an expanded panel for ai_providers:
// - Anthropic key format hint: "Keys start with sk-ant-"
// - Link to console.anthropic.com
// - Input field for the key
// - "Test connection" button calling useValidateProviderKey
// - On success: call updateStep.mutate({ step: 'ai_providers', completed: true })
```

The `useValidateProviderKey` hook already exists in `useOnboardingActions.ts`. The backend endpoint `POST /workspaces/{id}/ai-providers/validate` is implemented in `onboarding.py`. The hook returns `ValidateKeyResponse` with `valid`, `errorMessage`, and `modelsAvailable`.

### ONBD-04: Skill Save Success Confirmation

After `createRoleSkillMutation.onSuccess`, the wizard calls `onComplete()` which calls `updateStep.mutate({ step: 'role_setup', completed: true })`. A toast fires in `useCreateRoleSkill.onSuccess` (but only "Failed to save role skill" on error — no success toast).

Fix: Add a success toast in `useCreateRoleSkill.onSuccess`:
```typescript
onSuccess: () => {
  toast.success('Skill saved and active'); // ADD THIS
  queryClient.invalidateQueries(...);
}
```

Additionally, show a confirmation state in the `SkillPreviewView` after save — the `isSaving` flag transitions but no "saved" state is shown. Add a `isSaved` local state to display a green confirmation badge.

### ONBD-05: Settings Links Per Step

Currently only `ai_providers` and `invite_members` navigate to settings. For `first_note`, the action is in-dialog (creates a note). For `role_setup`, the action is in-dialog too. ONBD-05 says each step "links directly to relevant settings action."

Implementation: Each `OnboardingStepItem` should show a secondary "Go to settings" link for steps that have a settings equivalent:
- `ai_providers` → `/settings/ai-providers` (existing)
- `invite_members` → `/settings/members` (existing)
- `role_setup` → `/settings/skills` (existing)
- `first_note` → No settings page, action is in-dialog (create note)

### WS-01: Member Count in Workspace Switcher

The `Workspace` type already has `memberCount: number`. The `workspaceStore.workspaceList` returns workspaces from `this.workspaces` Map. The `memberCount` is populated when `fetchWorkspaces()` is called (from `workspacesApi.list()` → `transformWorkspace()` → `memberCount: response.memberCount`).

In `workspace-switcher.tsx`, the list item currently renders:
```tsx
<span className="flex-1 truncate text-left">{ws.name}</span>
```

Add member count:
```tsx
<div className="flex flex-col items-start flex-1 min-w-0">
  <span className="truncate text-left text-xs font-medium">{ws.name}</span>
  <span className="text-[10px] text-muted-foreground">{ws.memberCount} member{ws.memberCount !== 1 ? 's' : ''}</span>
</div>
```

### WS-02: Last-Visited Page Per Workspace

The existing `addRecentWorkspace(slug)` only tracks slug + timestamp. Extend to also track last path:

```typescript
// In workspace-switcher.tsx handleSelectWorkspace:
const handleSelectWorkspace = useCallback((ws: Workspace) => {
  workspaceStore.selectWorkspace(ws.id);
  addRecentWorkspace(ws.slug);
  setPopoverOpen(false);
  // Read last path for this workspace before navigating
  const lastPath = getLastWorkspacePath(ws.slug);
  router.push(lastPath ?? `/${ws.slug}`);
}, [workspaceStore, router]);
```

Track current path when user navigates within a workspace:
```typescript
// In [workspaceSlug]/layout.tsx, add a usePathname effect:
const pathname = usePathname();
useEffect(() => {
  saveLastWorkspacePath(workspaceSlug, pathname);
}, [pathname, workspaceSlug]);
```

Store in localStorage as `pilot-space:last-path:{slug}` → path string.

### Anti-Patterns to Avoid
- **Do not read `workspaceStore.currentWorkspace?.id` as workspace ID source in child pages.** The WorkspaceContext is the authoritative source within `[workspaceSlug]` route group.
- **Do not add inline API key storage** in the onboarding step. The validate endpoint is for testing only — actual key saving belongs in settings.
- **Do not add new files >700 lines.** Inline API key step goes into a new sub-component, not expanding `OnboardingChecklist.tsx`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key validation | Custom fetch + error handling | `useValidateProviderKey` hook (already exists) | Hook handles loading, error toast, response mapping |
| Slug generation | Custom regex | `toSlug()` from `@/lib/slug` | Already imported in `app/page.tsx` |
| Toast notifications | Custom notification UI | `toast` from `sonner` | Already used throughout; consistent style |
| Onboarding state persistence | Custom API calls | `useOnboardingActions` hooks | Already implement optimistic updates + rollback |
| Workspace metadata | Re-fetching members separately | `memberCount` on Workspace object from existing API | `workspacesApi.list()` already returns `memberCount` |

---

## Common Pitfalls

### Pitfall 1: workspaceId Race Condition (BUG-01 root cause)
**What goes wrong:** `workspaceStore.currentWorkspace` is null when `WorkspaceHomePage` first renders, even though `WorkspaceGuard` has already fetched the workspace. The guard calls `setCurrentWorkspace()` asynchronously after `setState({ status: 'ready' })` — there's a React render cycle between the guard setting ready and the store being populated.
**Why it happens:** `WorkspaceContext.Provider` wraps children with the workspace object synchronously; the MobX store update is triggered in the same useEffect but goes through an observable mutation that needs an extra render cycle to propagate.
**How to avoid:** Always use `useWorkspace()` context hook inside `[workspaceSlug]` route group, not the MobX store, for the workspace ID.

### Pitfall 2: Slug Collision During Auto-Creation
**What goes wrong:** Auto-generated slug from email may conflict with existing workspace.
**Why it happens:** Common email prefixes ("admin", "user", "john") collide across users.
**How to avoid:** Append 4-char random suffix (`Math.random().toString(36).slice(2,6)`). On 409 response, generate a new suffix and retry once.

### Pitfall 3: OnboardingChecklist Renders Before workspaceId Is UUID
**What goes wrong:** If workspaceId is still the slug string, the onboarding API call hits `GET /workspaces/workspace/onboarding` → backend tries UUID parse → 422 or 404.
**Why it happens:** Same race as BUG-01.
**How to avoid:** The BUG-01 fix (reading from WorkspaceContext) directly fixes this.

### Pitfall 4: WS-02 Path Tracking Stores Settings Pages
**What goes wrong:** User is in settings when they switch workspaces; last path is `/settings/members`. When returning to first workspace, they land in settings instead of their last work page.
**How to avoid:** Only save paths under `[workspaceSlug]` that are not settings paths. Filter: do not save if path includes `/settings/`.

### Pitfall 5: Inline API Key Step Size
**What goes wrong:** Adding inline API key UX to `OnboardingChecklist.tsx` pushes it over 700 lines.
**How to avoid:** Extract inline key step as `ApiKeySetupStep.tsx` sub-component in `features/onboarding/components/`.

---

## Code Examples

### Read workspaceId from WorkspaceContext (BUG-01 fix)
```typescript
// Source: frontend/src/components/workspace-guard.tsx (WorkspaceContext pattern)
import { useWorkspace } from '@/components/workspace-guard';

const WorkspaceHomePage = observer(function WorkspaceHomePage({ params }) {
  const { workspaceSlug } = use(params);
  const { workspace } = useWorkspace(); // always UUID, never slug fallback

  return (
    <div className="flex h-full flex-col">
      <OnboardingChecklist workspaceId={workspace.id} workspaceSlug={workspaceSlug} />
      <HomepageHub workspaceSlug={workspaceSlug} />
    </div>
  );
});
```

### Auto-create workspace from email (ONBD-01)
```typescript
// Source: pattern from frontend/src/app/page.tsx (existing imports: toSlug, workspacesApi, supabase)
async function autoCreateWorkspace(): Promise<string> {
  const { data: { user } } = await supabase.auth.getUser();
  const displayName =
    user?.user_metadata?.name ||
    user?.user_metadata?.full_name ||
    user?.email?.split('@')[0] ||
    'my-workspace';
  const baseSlug = toSlug(displayName);
  const suffix = Math.random().toString(36).slice(2, 6);
  const slug = `${baseSlug}-${suffix}`;
  const workspace = await workspacesApi.create({ name: displayName, slug });
  addRecentWorkspace(workspace.slug);
  return workspace.slug;
}
```

### Test connection button (ONBD-03)
```typescript
// Source: useOnboardingActions.ts — useValidateProviderKey hook already wired
const { mutate: validateKey, isPending, data } = useValidateProviderKey({ workspaceId });

<Button
  size="sm"
  variant="outline"
  disabled={!apiKey || isPending}
  onClick={() => validateKey({ provider: 'anthropic', apiKey })}
>
  {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Test connection'}
</Button>
{data?.valid && <span className="text-xs text-green-600">Connected — {data.modelsAvailable.length} models</span>}
{data && !data.valid && <span className="text-xs text-destructive">{data.errorMessage}</span>}
```

### Per-workspace last-path tracking (WS-02)
```typescript
// New utility functions (add to workspace-selector.tsx or a new lib/workspace-nav.ts)
const LAST_PATH_PREFIX = 'pilot-space:last-path:';

export function saveLastWorkspacePath(slug: string, path: string): void {
  if (typeof window === 'undefined') return;
  if (path.includes('/settings/')) return; // Don't save settings paths
  try {
    localStorage.setItem(`${LAST_PATH_PREFIX}${slug}`, path);
  } catch { /* ignore */ }
}

export function getLastWorkspacePath(slug: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(`${LAST_PATH_PREFIX}${slug}`);
  } catch {
    return null;
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact for Phase 12 |
|--------------|------------------|---------------------|
| Manual workspace creation form on first login | Auto-create from user metadata | ONBD-01 eliminates the form entirely |
| Navigate away for API key setup | Inline expand in checklist | ONBD-03 — keep user in context |
| Workspace switcher shows only name | Shows name + member count | WS-01 — trivial data is already available |
| Switch always goes to workspace root | Switch to last visited page | WS-02 — localStorage tracking |

---

## Open Questions

1. **Auto-create slug uniqueness strategy**
   - What we know: 409 on conflict; `toSlug` + random suffix works
   - What's unclear: Should we show the derived name to the user for confirmation, or fully silent?
   - Recommendation: Silent auto-create (ONBD-01 says "no extra step"). If 409 after one retry, fall back to showing the form.

2. **API key save vs test in onboarding step**
   - What we know: validate endpoint tests without saving; settings page saves
   - What's unclear: Should the inline onboarding step also save the key, or only test?
   - Recommendation: Test-only inline. The "Add API Key" step label and link go to settings where the key is actually saved. Test button confirms it works before navigating.

3. **WS-02 scope — which paths to restore**
   - What we know: filter out `/settings/` paths
   - What's unclear: Should we also filter project settings, billing, etc.?
   - Recommendation: Only restore paths under `[workspaceSlug]` that don't contain `/settings`. If no saved path, navigate to workspace root.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (frontend) |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && pnpm test -- --reporter=verbose` |
| Full suite command | `cd frontend && pnpm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-01 | `WorkspaceHomePage` uses `workspace.id` from context, not store | unit | `pnpm test -- src/app/\\(workspace\\)/\\[workspaceSlug\\]/page` | ❌ Wave 0 |
| BUG-01 | `OnboardingChecklist` receives UUID, not slug string | unit | `pnpm test -- features/onboarding/components/OnboardingChecklist` | ❌ Wave 0 |
| ONBD-01 | Auto workspace creation from email in `app/page.tsx` | unit | `pnpm test -- src/app/page` | ❌ Wave 0 |
| ONBD-01 | Slug collision → retry once with new suffix | unit | `pnpm test -- src/app/page` | ❌ Wave 0 |
| ONBD-03 | `ApiKeySetupStep` renders format hint and test button | unit | `pnpm test -- features/onboarding/components/ApiKeySetupStep` | ❌ Wave 0 |
| ONBD-03 | Test connection button calls `useValidateProviderKey` | unit | existing `useRoleSkillActions.test.ts` pattern | ❌ Wave 0 |
| ONBD-04 | Success toast fires after skill save | unit | `pnpm test -- features/onboarding/components/SkillGenerationWizard` | ✅ Extend |
| WS-01 | Workspace switcher shows member count | unit | `pnpm test -- components/layout/workspace-switcher` | ❌ Wave 0 |
| WS-02 | `saveLastWorkspacePath` ignores settings paths | unit | `pnpm test -- lib/workspace-nav` | ❌ Wave 0 |
| WS-02 | `handleSelectWorkspace` reads saved path | unit | `pnpm test -- components/layout/workspace-switcher` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && pnpm test -- --reporter=dot 2>&1 | tail -5`
- **Per wave merge:** `cd frontend && pnpm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/app/page.test.tsx` — covers ONBD-01 (auto-create), BUG-02
- [ ] `frontend/src/app/(workspace)/[workspaceSlug]/page.test.tsx` — covers BUG-01
- [ ] `frontend/src/features/onboarding/components/ApiKeySetupStep.test.tsx` — covers ONBD-03
- [ ] `frontend/src/features/onboarding/components/OnboardingChecklist.test.tsx` — covers ONBD-02, ONBD-04, ONBD-05
- [ ] `frontend/src/components/layout/workspace-switcher.test.tsx` — covers WS-01, WS-02
- [ ] `frontend/src/lib/workspace-nav.test.ts` — covers WS-02 path utilities

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — all findings are from reading actual source files
  - `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx` — BUG-01 location confirmed at line 16
  - `frontend/src/components/workspace-guard.tsx` — WorkspaceContext pattern
  - `frontend/src/app/page.tsx` — auth redirect flow, workspace creation form
  - `frontend/src/features/onboarding/components/OnboardingChecklist.tsx` — checklist structure
  - `frontend/src/features/onboarding/components/SkillGenerationWizard.tsx` — save flow
  - `frontend/src/features/onboarding/hooks/useOnboardingActions.ts` — validate hook
  - `frontend/src/components/layout/workspace-switcher.tsx` — WS-01, WS-02 gaps confirmed
  - `frontend/src/services/api/workspaces.ts` — memberCount field confirmed
  - `backend/src/pilot_space/api/v1/routers/onboarding.py` — validate endpoint confirmed
  - `backend/src/pilot_space/application/services/onboarding/get_onboarding_service.py` — auto-upsert confirmed
  - `frontend/src/stores/OnboardingStore.ts` — modalOpen defaults to true
  - `frontend/src/stores/WorkspaceStore.ts` — setCurrentWorkspace async pattern

---

## Metadata

**Confidence breakdown:**
- BUG-01 root cause: HIGH — confirmed by reading the exact line and the WorkspaceGuard pattern
- BUG-02 fix location: HIGH — `app/page.tsx` resolveWorkspace function is the right place
- ONBD-01 implementation: HIGH — all imports are already present in `app/page.tsx`
- ONBD-03 inline step: HIGH — validate hook and endpoint both exist
- ONBD-04 success confirmation: HIGH — missing toast in `useCreateRoleSkill.onSuccess` is confirmed
- WS-01 member count: HIGH — field exists on Workspace type, confirmed in workspaces.ts
- WS-02 last-path tracking: HIGH — localStorage pattern is established; filter logic is straightforward

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable frontend stack)
