# Settings Modal Migration Investigation

**Branch:** `feat/settings-modal`
**Date:** 2026-03-18
**Author:** Tin Dang
**Status:** Draft — ready for implementation planning

---

## Executive Summary

Pilot Space currently uses 11 full-page routes under `/[workspaceSlug]/settings/*` for workspace
configuration. The UX goal is to convert these into a single settings modal dialog (like Linear
and Vercel) so users stay in context rather than navigating away. This investigation maps the full
scope, identifies migration risks, and proposes a concrete 4-phase migration plan.

**Key finding:** The strangler-fig approach is low-risk because the route files (`app/.../page.tsx`)
are already thin wrappers — the actual page components live in `features/settings/pages/`.
The modal can import these page components directly with minimal or zero changes for most pages.

---

## 1. Settings Page Catalogue

### 1.1 Route Structure

The settings layout is defined at:
- **Layout:** `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx`
- **Route files:** `frontend/src/app/(workspace)/[workspaceSlug]/settings/*/page.tsx` (thin wrappers)
- **Page components:** `frontend/src/features/settings/pages/*.tsx` (actual implementation)

The layout provides a two-column layout: a fixed left sidebar (`w-56`) with `settingsNavSections`
config and a scrollable right content area. On mobile/tablet, the sidebar is replaced by a Sheet
(drawer) triggered from a hamburger button.

### 1.2 Page-by-Page Catalogue

| # | Route | Page File | Lines | Complexity | observer() | useParams | beforeunload | Modal-Readiness |
|---|-------|-----------|-------|-----------|------------|-----------|--------------|-----------------|
| 1 | `/settings` | `workspace-general-page.tsx` | 348 | Medium | Yes | Yes | Yes | 2 |
| 2 | `/settings/profile` | `profile-settings-page.tsx` | 443 | Medium | Yes | No | Yes | 2 |
| 3 | `/settings/ai-providers` | `ai-settings-page.tsx` | 121 | Simple | Yes | Yes | No | 1 |
| 4 | `/settings/mcp-servers` | `mcp-servers-settings-page.tsx` | 181 | Simple | Yes | Yes | No | 1 |
| 5 | `/settings/integrations` | `integrations/page.tsx` (inline) | ~260 | Medium | Yes | Yes | No | 2 |
| 6 | `/settings/encryption` | `encryption-settings-page.tsx` | 328 | Medium | Yes | Yes | No | 1 |
| 7 | `/settings/usage` | `usage-settings-page.tsx` | 328 | Medium | Yes | Yes | No | 1 |
| 8 | `/settings/ai-governance` | `ai-governance-settings-page.tsx` | 371 | Medium | No | Yes | No | 2 |
| 9 | `/settings/skills` | `skills-settings-page.tsx` | 442 | Complex | Yes | Yes | No | 3 |
| 10 | `/settings/roles` | `roles-settings-page.tsx` | 574 | Complex | No | Yes | No | 3 |
| 11 | `/settings/security` | `security-settings-page.tsx` | 483 | Medium | No | Yes | No | 2 |
| 12 | `/settings/sso` | `sso-settings-page.tsx` | 639 | Complex | No | Yes | No | 3 |
| 13 | `/settings/audit` | `audit-settings-page.tsx` | 692 | Complex | No | Yes | No | 3 |
| 14 | `/settings/billing` | `billing/page.tsx` (inline) | ~50 | Simple | No | No | No | 1 |

**Modal-readiness score:** 1 = drop-in, 2 = minor tweaks (unsaved-change guard, layout), 3 = significant rework (nested dialogs, large data tables, multi-step forms)

**Notes on special cases:**
- `/settings/integrations` page component lives in the route file, not in `features/settings/pages/` — will need extraction first
- `/settings/billing` is a simple static placeholder (no data fetching, no state)
- `audit-settings-page.tsx` is explicitly NOT wrapped in `observer()` per its own comment — `AuditSettingsPage` is a plain React component

### 1.3 State Management per Page

| Page | MobX Stores | TanStack Query Hooks | Local State |
|------|-------------|---------------------|-------------|
| workspace-general | `workspaceStore` (slug, role) | `useWorkspaceSettings`, `useUpdateWorkspaceSettings`, `useDeleteWorkspace` | name, slug, description, hasChanges |
| profile | `authStore` (user, updateProfile) | none (MobX-only) | displayName, bio, aiSettings, hasChanges |
| ai-providers | `ai.settings` (AISettingsStore), `workspaceStore` | none (MobX-only) | none (all in MobX store) |
| mcp-servers | `ai.mcpServers`, `workspaceStore` | none (MobX-only) | showAddForm |
| integrations | `workspaceStore` | `useQuery` (settings), `useQuery` (GitHub), `useMutation` (update) | autoTransition, branchFormat, mergeTransition |
| encryption | `workspaceStore` | `useWorkspaceEncryption`, `useUploadEncryptionKey`, `useRotateEncryptionKey` | confirmRotate, showKey |
| usage | `workspaceStore` | `useWorkspaceQuota`, `useUpdateWorkspaceQuota` | editing state |
| ai-governance | `workspaceStore` | TanStack Query (governance policies) | policyMatrix, editMode |
| skills | `workspaceStore` | none | addPluginDialogOpen, confirmDialogs |
| roles | `workspaceStore` | `useCustomRoles`, `useCreateCustomRole`, `useUpdateCustomRole`, `useDeleteCustomRole` | editingRole, createDialogOpen, deleteDialogOpen |
| security | `workspaceStore` | `useSessions`, `useTerminateSession`, `useTerminateAllUserSessions`, `useGenerateScimToken` | confirmDialog, scimToken |
| sso | `workspaceStore` | `useSamlConfig`, `useUpdateSamlConfig`, `useOidcConfig`, `useUpdateOidcConfig`, `useSetSsoRequired`, `useRoleClaimMapping`, `useUpdateRoleClaimMapping` | activeTab, claimMappingRows |
| audit | `workspaceStore` | `useAuditLog`, `useExportAuditLog` | filters, pagination, expandedRows |
| billing | none | none | none |

### 1.4 Sub-components per Page

| Page | Key Sub-components from `features/settings/components/` |
|------|--------------------------------------------------------|
| workspace-general | `DeleteWorkspaceDialog` (nested Dialog) |
| profile | none (self-contained) |
| ai-providers | `ProviderSection`, `ProviderRow`, `ProviderConfigForm`, `CustomProviderForm`, `AIFeatureToggles` |
| mcp-servers | `MCPServerCard`, `MCPServerForm` |
| integrations | `GitHubIntegration` (from `@/components/integrations`) |
| encryption | `APIKeyInput` (key input masking) |
| usage | none (self-contained) |
| ai-governance | `ActionButtonsTabContent` |
| skills | `SkillCard`, `WorkspaceSkillCard`, `SkillGeneratorModal`, `SkillDetailModal`, `PluginsTabContent`, `PluginDetailSheet`, `ConfirmActionDialog`, `CreateTemplateModal`, `EditTemplateModal` |
| roles | `useCustomRoles` hook + inline role editor Dialog |
| security | `useSessions` hook + AlertDialog for confirm, inline Dialog for SCIM token |
| sso | inline SAML/OIDC forms + claim mapping rows |
| audit | `useAuditLog` hook + data table with filters |
| billing | none |

### 1.5 Components Using Dialogs/Sheets Internally

These create nested-dialog scenarios inside the settings modal:

| Component | Type | Used By |
|-----------|------|---------|
| `delete-workspace-dialog.tsx` | Radix Dialog | workspace-general page |
| `skill-generator-modal.tsx` | Dialog (20KB, complex SSE streaming) | skills page |
| `skill-detail-modal.tsx` | Dialog | skills page |
| `create-template-modal.tsx` | Dialog | skills page |
| `edit-template-modal.tsx` | Dialog | skills page |
| `plugin-detail-sheet.tsx` | Sheet | skills page |
| `skill-card.tsx` | contains Dialog triggers | skills page, roles page |
| `workspace-skill-card.tsx` | contains Dialog triggers | skills page |
| `action-buttons-tab-content.tsx` | contains AlertDialog | ai-governance page |
| `mcp-server-form.tsx` | form with sub-interactions | mcp-servers page |
| Inline in roles page | AlertDialog (delete confirm), Dialog (edit role) | roles page |
| Inline in security page | AlertDialog (confirm terminate), Dialog (SCIM token) | security page |
| Inline in audit page | AlertDialog (confirm export/purge) | audit page |

### 1.6 Current Layout Navigation Config

The `settingsNavSections` in `layout.tsx` defines 2 sections (Workspace + Account) with 12 items:

**Workspace section (11 items):** General, AI Providers, MCP Servers, Integrations, SSO, Encryption,
AI Governance, Audit, Custom Roles, Usage, Billing

**Account section (1 item):** Profile

The `SettingsNavContent` component renders nav links using Next.js `Link` components. Active state
is determined by comparing `usePathname()` against each item's `href(slug)` value.

### 1.7 Trigger Mechanism in Sidebar

In `frontend/src/components/layout/sidebar.tsx`, the `SidebarUserControls` component renders a
`DropdownMenu` with two settings-related items:

```tsx
// Profile link
onSelect={() => router.push(`/${workspaceSlug}/settings/profile`)}

// Settings link
onSelect={() => router.push(`/${workspaceSlug}/settings`)}
```

Both use `router.push()` which causes full-page navigation. The modal approach replaces these
with state mutations that open the modal.

### 1.8 Settings Hooks Catalogue

| Hook File | Exports | Stale Time | Notes |
|-----------|---------|------------|-------|
| `use-workspace-settings.ts` | `useWorkspaceSettings`, `useUpdateWorkspaceSettings`, `useDeleteWorkspace` | 60s | General CRUD |
| `use-audit-log.ts` | `useAuditLog`, `useExportAuditLog`, `usePurgeAuditLog` | none (always fresh) | Paginated with filters |
| `use-custom-roles.ts` | `useCustomRoles`, `useCreateCustomRole`, `useUpdateCustomRole`, `useDeleteCustomRole`, `useAssignRole` | 60s | RBAC management |
| `use-scim.ts` | `useGenerateScimToken` | mutation-only | AUTH-07 |
| `use-sessions.ts` | `useSessions`, `useTerminateSession`, `useTerminateAllUserSessions` | 30s, refetchInterval 30s | Live polling |
| `use-sso-settings.ts` | `useSamlConfig`, `useUpdateSamlConfig`, `useOidcConfig`, `useUpdateOidcConfig`, `useSetSsoRequired`, `useRoleClaimMapping`, `useUpdateRoleClaimMapping` | none | Multi-protocol SSO |
| `use-workspace-encryption.ts` | `useWorkspaceEncryption`, `useUploadEncryptionKey`, `useRotateEncryptionKey` | 60s | BYOK encryption |
| `use-workspace-quota.ts` | `useWorkspaceQuota`, `useUpdateWorkspaceQuota` | 30s | Rate limits + storage |

---

## 2. Modal Architecture Proposal

### 2.1 Container

Use the existing shadcn/ui `Dialog` component from `frontend/src/components/ui/dialog.tsx` with a
custom `DialogContent` override. The current `DialogContent` defaults to `sm:max-w-lg` which is too
narrow for settings. The settings modal needs a wide, tall variant:

```tsx
// Override just for SettingsModal — do NOT modify the base dialog.tsx
<DialogPrimitive.Content
  className={cn(
    // Base Dialog animation classes (copy from dialog.tsx)
    'bg-background data-[state=open]:animate-in data-[state=closed]:animate-out ...',
    // Settings-specific dimensions
    'fixed top-[50%] left-[50%] z-50 translate-x-[-50%] translate-y-[-50%]',
    'w-[min(900px,calc(100vw-2rem))] h-[min(700px,calc(100vh-2rem))]',
    'rounded-lg border shadow-lg outline-none overflow-hidden',
    'flex flex-col', // shell layout
    className
  )}
/>
```

This gives ~900px wide × ~700px tall on desktop — comparable to Linear's settings modal.
On mobile: `w-[calc(100vw-1rem)] h-[calc(100vh-1rem)]` becomes nearly full-screen.

The settings modal renders its own Portal and Overlay — it does NOT wrap existing DialogContent.

### 2.2 Internal Layout

```text
┌─────────────────────────────────────────────────────────────┐
│  [Settings]                                          [X]    │  ← modal header (h-12)
├──────────────┬──────────────────────────────────────────────│
│  Workspace   │  [Section Title]                             │
│  • General   │  [Section Description]                       │
│  • AI Prov.. │  ────────────────────                        │
│  • MCP Srv.. │  [Content scrolls here]                      │
│  • Integrat  │                                              │
│  • SSO       │                                              │
│  • Encrypt.  │  ← overflow-y-auto on content area only      │
│  • AI Gov.   │                                              │
│  • Audit     │                                              │
│  • Roles     │                                              │
│  • Usage     │                                              │
│  • Billing   │                                              │
│  ─────────── │                                              │
│  Account     │                                              │
│  • Profile   │                                              │
└──────────────┴──────────────────────────────────────────────┘
  ↑ w-52, shrink-0     ↑ flex-1, overflow-y-auto
  border-r
```

The left sidebar renders `SettingsNavContent` (extracted from `layout.tsx`) unchanged, but with
`Link` replaced by `button` elements that call `setActiveSection(id)`.

### 2.3 Navigation

Replace URL-based navigation with local `activeSection: string` state:

```tsx
// In SettingsModal.tsx
const [activeSection, setActiveSection] = React.useState<string>('general');

// In nav items — replace <Link href={...}> with:
<button
  onClick={() => setActiveSection(item.id)}
  className={cn(
    'flex items-center gap-2.5 ...',
    activeSection === item.id ? 'bg-muted text-foreground' : 'text-muted-foreground'
  )}
>
  <item.icon className="h-4 w-4 shrink-0" />
  {item.label}
</button>
```

Content panels are conditionally rendered based on `activeSection`:

```tsx
const SECTION_MAP: Record<string, React.ComponentType> = {
  'general': WorkspaceGeneralPage,
  'ai-providers': AISettingsPage,
  'mcp-servers': MCPServersSettingsPage,
  // ...
};

const ActivePanel = SECTION_MAP[activeSection] ?? WorkspaceGeneralPage;
return <ActivePanel />;
```

Use `React.lazy` + `Suspense` per panel to preserve code-splitting (see section 2.6).

### 2.4 URL Integration

**Recommendation: Support `?settings=<section-id>` query param** for shareable links.

On modal open: read `searchParams.get('settings')` → set as `activeSection`.
On section switch: update URL with `router.replace` (shallow, no navigation):
```tsx
const handleSectionChange = (id: string) => {
  setActiveSection(id);
  router.replace(`${pathname}?settings=${id}`, { scroll: false });
};
```
On modal close: strip the query param:
```tsx
router.replace(pathname, { scroll: false });
```

Trade-off: adds ~5 lines of code, provides shareable deep links, supports browser back button
to close modal (popstate handling). Benefit outweighs cost.

### 2.5 Trigger Mechanism

Replace `router.push` calls in `sidebar.tsx` with settings modal open actions.

**Option A: Global context (recommended)**

Create `SettingsModalContext` with `{ open: boolean; activeSection: string; openSettings: (section?: string) => void; close: () => void }`.
Provide it in the workspace layout (`app/(workspace)/[workspaceSlug]/layout.tsx`).
The `SettingsModal` itself lives in the workspace layout and reads from context.
`SidebarUserControls` calls `openSettings('general')` or `openSettings('profile')`.

**Option B: MobX UIStore**

Add `settingsModalOpen: boolean` and `settingsModalSection: string` to `UIStore`.
This avoids a new context but couples UI-state to a generic store.

**Recommendation: Option A** (purpose-built context, cleaner separation).

### 2.6 Code Splitting

Use `React.lazy` for each content panel to preserve per-section code splitting:

```tsx
const WorkspaceGeneralPage = React.lazy(() =>
  import('@/features/settings/pages/workspace-general-page').then(m => ({ default: m.WorkspaceGeneralPage }))
);
// ... repeat for each page

<Suspense fallback={<SettingsPanelSkeleton />}>
  <ActivePanel />
</Suspense>
```

This ensures only the currently-active panel's bundle is loaded, not all 13+ panels at mount.

### 2.7 Mobile Behavior

On screens `< lg` (below 1024px):
- Modal is nearly full-screen: `w-[calc(100vw-1rem)] h-[calc(100vh-1rem)]`
- The left sidebar is replaced by a top `<Select>` dropdown showing the current section name
- The select value maps to `activeSection`, triggering the same state change
- No Sheet/drawer needed — the dropdown is simpler and more accessible

```tsx
{/* Mobile: section select */}
<div className="border-b border-border p-3 lg:hidden">
  <Select value={activeSection} onValueChange={setActiveSection}>
    <SelectTrigger className="w-full">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      {settingsNavSections.flatMap(s => s.items).map(item => (
        <SelectItem key={item.id} value={item.id}>
          {item.label}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

{/* Desktop: sidebar nav */}
<nav className="hidden lg:block w-52 ...">
  <SettingsNavContent ... />
</nav>
```

### 2.8 Nested Dialogs

Radix Dialog (the library backing shadcn/ui) supports nested dialogs via `DialogPrimitive.Root`
nesting. Key constraint: each nested Dialog must use its own Portal with an appropriately high
`z-index`. The outer settings modal is `z-50`; nested dialogs should use `z-[60]` or higher.

The existing nested components (`DeleteWorkspaceDialog`, `SkillGeneratorModal`, etc.) already use
Radix `DialogContent` which renders in a Portal. They will stack correctly above the settings
modal without code changes, as Radix manages z-index stacking context internally.

**Verification needed:** Test `SkillGeneratorModal` (the most complex nested component — 20KB,
SSE streaming, multi-step) inside the modal shell. The SSE streaming itself is unaffected by
Dialog nesting since it's purely async, but focus management needs confirming.

---

## 3. Key Technical Challenges

### 3.1 `useParams` Dependency (LOW RISK)

**Finding:** Every settings page that needs the workspace slug uses `useParams()` to get
`workspaceSlug`. In the modal approach, the modal renders within the workspace layout
(`/[workspaceSlug]/...`), so `useParams()` still returns the correct `workspaceSlug`.

**Verdict:** No changes needed. `useParams()` works identically inside a modal rendered
within the same route tree.

### 3.2 `usePathname` Active Nav (RESOLVED)

**Finding:** Current `layout.tsx` uses `usePathname()` for active link highlighting.
`isNavItemActive(pathname, href, exact)` compares the full URL path.

**Resolution:** The modal replaces this with `activeSection` local state. The `SettingsNavContent`
component needs a prop change: replace `pathname` prop with `activeSection` and swap
`isNavItemActive(pathname, href, exact)` for `activeSection === item.id`.

The existing `isNavItemActive` function can be deleted from the new modal sidebar.

### 3.3 `observer()` Wrapping (LOW RISK)

**Finding:** Most settings pages use `observer()`. Settings pages do NOT use TipTap, so the
`flushSync` / MobX `useSyncExternalStore` conflict documented in `.claude/rules/tiptap.md`
does not apply here.

**Verdict:** `observer()` works correctly inside Radix Dialog. No changes needed.

### 3.4 `beforeunload` Guards (REQUIRES REWORK)

**Affected pages:** `workspace-general-page.tsx` (line 89) and `profile-settings-page.tsx` (line 139).

**Problem:** `beforeunload` fires when the browser tab closes or the user navigates away. Inside a
modal, it does NOT fire when the user clicks the X button or presses Escape. Unsaved changes can
be silently lost.

**Solution:** Intercept the Dialog's `onOpenChange` callback:

```tsx
// In SettingsModal.tsx
const handleOpenChange = (open: boolean) => {
  if (!open && hasUnsavedChanges) {
    // Show an AlertDialog confirmation instead of closing
    setShowUnsavedWarning(true);
    return; // block close
  }
  onOpenChange(open);
};
```

The page components need to expose `hasUnsavedChanges` state to the modal shell. Use a
`useSettingsUnsavedChanges` context or a callback prop. The existing `beforeunload` logic
can remain in place for the tab-close scenario — it does not interfere with modal close.

**Scope:** Only 2 pages currently have this guard (workspace-general and profile). Add it to the
close-intercept mechanism in Phase 1 alongside those pages' migration.

### 3.5 Page-Level Data Fetching on Re-mount (LOW RISK)

**Finding:** Settings pages fetch data in `useEffect` on mount (MobX-backed pages like
`AISettingsPage` call `settings.loadSettings(workspaceId)` on mount) or via TanStack Query's
automatic fetch-on-mount behavior.

**Risk:** When the modal is closed and reopened, pages re-mount and re-fetch. TanStack Query
respects `staleTime` (most hooks use 60s or 30s) so re-fetches are gated. MobX stores
(like `AISettingsStore`) re-fetch unconditionally on mount — this is the same behavior as
navigating back to the page, which is acceptable.

**Optimization (optional):** Use `React.lazy` + keep-alive via `display: none` to avoid unmounting
panels on section switch. Not recommended for Phase 1 — keep it simple.

### 3.6 Route-Based Code Splitting (RESOLVED)

**Finding:** Next.js App Router code-splits each `page.tsx` file automatically. Moving to a
modal means all referenced components must be explicitly lazy-loaded.

**Resolution:** Use `React.lazy()` per panel as described in section 2.6. This preserves
dynamic imports and avoids loading all 13+ settings page bundles upfront.

### 3.7 Deep Links (REQUIRES MIGRATION STRATEGY)

**Current:** Users can bookmark `/workspace/settings/audit` and return directly to the audit page.

**After modal migration:** The old routes must either:
- (a) Auto-open the modal with the correct section and redirect to the base workspace path
- (b) Continue to function as standalone pages (reduces UX value of the modal)
- (c) 404

**Recommendation: Option (a)** — keep old routes but have them render a redirect that opens
the modal. Implement with a catch-all route in Phase 4:

```tsx
// app/(workspace)/[workspaceSlug]/settings/[...section]/page.tsx
// Only activated after old routes are removed
export default function SettingsDeepLink({ params }) {
  // Redirect to workspace root with ?settings=<section> query param
  redirect(`/${params.workspaceSlug}?settings=${params.section[0]}`);
}
```

The workspace layout (`layout.tsx`) then reads `?settings=<section>` and auto-opens the modal
on load.

### 3.8 Guest Role Redirect (MUST PRESERVE)

**Finding:** The current settings layout has a redirect guard:

```tsx
if (workspaceStore.currentUserRole === 'guest' && !pathname.includes('/settings/profile')) {
  router.replace(`/${workspaceSlug}/settings/profile`);
}
```

In the modal, this becomes: if guest user tries to open settings, `openSettings('profile')` is
called instead of their requested section. Implement in `SettingsModalProvider.openSettings()`.

---

## 4. Migration Approach

### 4.1 Strategy: Strangler Fig

Build the modal alongside existing routes. Migrate one page at a time. Remove old routes last.

**Advantages:**
- Zero regression risk during migration — old routes remain until explicitly removed
- Can A/B test modal vs. route for specific pages if needed
- Rollback is trivial (revert the sidebar trigger change)

### 4.2 Shared Components: Already Separated

The route files (`app/.../settings/*/page.tsx`) are already thin wrappers:

```tsx
// Typical route file — zero logic
import { AISettingsPage } from '@/features/settings/pages/ai-settings-page';
export default function AIProvidersSettingsRoute() {
  return <AISettingsPage />;
}
```

The modal imports the same `AISettingsPage` component. No changes to the page component needed
for score-1 (drop-in) pages.

### 4.3 New Files Required

| File | Purpose |
|------|---------|
| `frontend/src/features/settings/components/settings-modal.tsx` | Modal shell: Dialog + sidebar + content switcher |
| `frontend/src/features/settings/contexts/settings-modal-context.ts` | Context: open/close/activeSection state |
| `frontend/src/features/settings/providers/settings-modal-provider.tsx` | Provider: wraps context, renders SettingsModal |
| `frontend/src/hooks/use-settings-unsaved-changes.ts` | Hook: tracks unsaved state for close-guard |

**Modifications required:**

| File | Change |
|------|--------|
| `frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx` | Add `SettingsModalProvider` |
| `frontend/src/components/layout/sidebar.tsx` | Replace `router.push` with `openSettings()` calls |
| `frontend/src/features/settings/pages/workspace-general-page.tsx` | Expose unsaved state (Phase 1) |
| `frontend/src/features/settings/pages/profile-settings-page.tsx` | Expose unsaved state (Phase 1) |
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx` | Keep during migration, remove in Phase 4 |

---

## 5. Phased Migration Plan

### Phase 1 — Modal Shell + Drop-In Pages (3 plans)

**Scope:** Build the modal infrastructure and migrate the 4 simplest pages.

**Plan 1.1 — Modal Shell and Context**
- Create `settings-modal-context.ts` with `{ open, activeSection, openSettings, closeSettings }`
- Create `settings-modal-provider.tsx` wrapping `Dialog` with the wide content variant
- Add `SettingsModalProvider` to workspace layout
- Add section switcher (button nav replacing Link nav)
- Wire `SidebarUserControls` to `openSettings()` (removing `router.push`)
- Add URL sync (`?settings=<id>` query param)
- Guest role guard in `openSettings()`
- Files touched: `settings-modal.tsx` (new), `settings-modal-context.ts` (new), `settings-modal-provider.tsx` (new), workspace `layout.tsx`, `sidebar.tsx`

**Plan 1.2 — Migrate AI Providers, MCP Servers, Billing (score-1 pages)**
- `AISettingsPage`, `MCPServersSettingsPage`, Billing — no code changes, direct import in modal
- Add `React.lazy` wrappers for all 3 panels
- Add `SettingsPanelSkeleton` for Suspense fallback
- Files touched: `settings-modal.tsx` (add panels)

**Plan 1.3 — Migrate Workspace General + Profile (score-2, beforeunload)**
- Add `useSettingsUnsavedChanges` hook (register/unregister callbacks)
- Add close-guard Dialog in `SettingsModal` (AlertDialog: "You have unsaved changes. Discard?")
- Update `workspace-general-page.tsx` to call `registerUnsavedChanges(hasChanges)` via context
- Update `profile-settings-page.tsx` similarly
- Files touched: `use-settings-unsaved-changes.ts` (new), `settings-modal.tsx`, both page files

### Phase 2 — Medium Complexity Pages (2 plans)

**Scope:** Migrate 5 medium-complexity pages with nested dialogs.

**Plan 2.1 — Encryption, Usage, Integrations**
- `EncryptionSettingsPage`, `UsageSettingsPage` are score-1 after profile/general are done
- `IntegrationsSettingsPage` lives in the route file — extract to `features/settings/pages/integrations-settings-page.tsx` first
- All three use `useParams` (confirmed safe) and TanStack Query only
- Files touched: `integrations-settings-page.tsx` (new/extracted), `app/.../integrations/page.tsx` (update), `settings-modal.tsx`

**Plan 2.2 — AI Governance, Security**
- `AIGovernanceSettingsPage` — plain React, `useParams`, no nested dialogs. Score 2 due to policy matrix size.
- `SecuritySettingsPage` — plain React, has inline `Dialog` (SCIM token display) and `AlertDialog` (confirm terminate). Radix handles nested Dialog z-index automatically.
- `useSessions` has 30s polling via `refetchInterval` — confirm polling starts/stops correctly on panel mount/unmount
- Files touched: `settings-modal.tsx`

### Phase 3 — Complex Pages (3 plans)

**Scope:** Migrate the 4 most complex pages requiring the most careful handling.

**Plan 3.1 — Custom Roles (574 lines)**
- Permission grid with checkbox matrix (manage-implies-lower logic)
- Contains inline `Dialog` (edit role form) and `AlertDialog` (delete confirm)
- Large data table — may need content-area scroll optimization
- Test nested Dialog z-index with the outer settings modal

**Plan 3.2 — SSO (639 lines)**
- Multi-step: SAML config tab + OIDC config tab + role claim mapping tab
- Uses `useParams` for workspaceSlug (safe)
- Dynamic claim mapping rows (add/remove) — self-contained local state
- No nested dialogs — lower risk than it appears

**Plan 3.3 — Audit (692 lines) + Skills (442 lines)**
- `AuditSettingsPage` is a plain React component (not observer) with TanStack Query
- Large data table with filters, pagination, export — content-area scroll is critical
- `SkillsSettingsPage` is the most complex (observer, 5 nested modals/sheets)
- `SkillGeneratorModal` streams SSE — test streaming inside nested Dialog context
- `PluginDetailSheet` uses Radix `Sheet` (drawer) — verify Sheet opens correctly from inside Dialog
- `TemplateModal` components × 2 — straightforward Dialogs

### Phase 4 — Cleanup (1 plan)

**Plan 4.1 — Remove Old Routes and Add Deep Links**
- Remove `/settings/*` route files (keep layout.tsx temporarily for deep-link transition)
- Add catch-all route `settings/[...section]/page.tsx` that redirects to `?settings=<section>`
- Update workspace layout to auto-open modal on `?settings=` param on page load
- Remove old `settings/layout.tsx`
- Update any E2E/Playwright tests referencing `/settings/*` URLs
- Update `frontend/src/features/settings/README.md` to reflect new architecture
- Files touched: all `app/.../settings/*/page.tsx` (delete), `settings/layout.tsx` (delete), `app/.../settings/[...section]/page.tsx` (new), workspace `layout.tsx`

### Phase Summary

| Phase | Plans | Pages | Risk | Key Challenge |
|-------|-------|-------|------|---------------|
| 1 — Shell + Simple | 3 | General, Profile, AI Providers, MCP, Billing | Low | beforeunload guard, modal shell |
| 2 — Medium | 2 | Encryption, Usage, Integrations, AI Gov, Security | Low | Integration page extraction, session polling |
| 3 — Complex | 3 | Roles, SSO, Audit, Skills | Medium | Nested dialogs, large data tables, SSE streaming |
| 4 — Cleanup | 1 | All (route removal) | Low | Deep-link redirect, test updates |

**Total: 9 plans** across 4 phases to complete full migration.

---

## 6. Alternative Approaches Considered

### 6.1 Sheet (Side Drawer) — Rejected

**Proposal:** Use Radix Sheet (slide-in drawer from left or right) instead of a Dialog.

**Rejected because:** Sheets work for single-purpose panels (notifications, filters, context menus)
but not for 11+ settings sections with wide forms, data tables, and permission grids. The SSO
and Roles pages especially need ~800px width to be usable. A Sheet cannot accommodate this.

### 6.2 Full-Page Modal Without Sidebar — Rejected

**Proposal:** Show settings in a full-screen Dialog with no sidebar navigation — just content and
a breadcrumb/tab strip at the top.

**Rejected because:** 11+ settings sections do not fit in a horizontal tab bar (overflow/scroll
issues). The sidebar model (used by Linear, Vercel, Notion) scales to any number of sections
and is already what users expect from settings UIs. Loss of quick-switch navigation between
related sections (e.g., SSO → Roles → Security) would hurt usability.

### 6.3 Tabs Instead of Sidebar — Rejected

**Proposal:** Use a `<Tabs>` component with horizontal tab items.

**Rejected because:** Tabs scale well up to 5-6 items. At 12 items, overflow handling creates a
poor mobile experience and the condensed tab labels lose context. The sidebar's visible label +
section grouping is strictly better for this content density.

### 6.4 Keep as Routes, Restyle — Rejected

**Proposal:** Keep existing URL-based routing but visually overlay the settings layout over the
workspace view (like a "fake modal").

**Rejected because:** This does not achieve the core UX goal of "stay in context". When settings
occupies a full-page route, the workspace canvas (notes, issues, projects) is completely replaced
in the browser history. The user must press Back to return to their work. A true Dialog modal
preserves the underlying page in DOM and memory, gives a clear dismiss action, and keeps the
user's scroll position and active state when they close settings.

---

## 7. File Reference Map

### Current Architecture

```text
app/(workspace)/[workspaceSlug]/settings/
├── layout.tsx                          ← settings layout (to be removed in Phase 4)
├── page.tsx                            ← general settings route (thin wrapper)
├── ai-providers/page.tsx              ← thin wrapper
├── mcp-servers/page.tsx               ← thin wrapper
├── integrations/page.tsx              ← INLINE component (needs extraction first)
├── encryption/page.tsx                ← thin wrapper
├── usage/page.tsx                     ← thin wrapper
├── ai-governance/page.tsx             ← thin wrapper
├── audit/page.tsx                     ← thin wrapper
├── roles/page.tsx                     ← thin wrapper
├── security/page.tsx                  ← thin wrapper
├── sso/page.tsx                       ← thin wrapper
├── profile/page.tsx                   ← thin wrapper
├── billing/page.tsx                   ← INLINE component (trivial)
└── members/page.tsx                   ← redirect to /members (already migrated)

features/settings/
├── pages/
│   ├── workspace-general-page.tsx     (348 lines, observer, beforeunload)
│   ├── ai-settings-page.tsx           (121 lines, observer, MobX-only)
│   ├── mcp-servers-settings-page.tsx  (181 lines, observer, MobX-only)
│   ├── profile-settings-page.tsx      (443 lines, observer, beforeunload)
│   ├── encryption-settings-page.tsx   (328 lines, observer, TanStack)
│   ├── usage-settings-page.tsx        (328 lines, observer, TanStack)
│   ├── ai-governance-settings-page.tsx (371 lines, plain, TanStack)
│   ├── skills-settings-page.tsx       (442 lines, observer, 5 nested modals)
│   ├── roles-settings-page.tsx        (574 lines, plain, TanStack + nested dialogs)
│   ├── security-settings-page.tsx     (483 lines, plain, TanStack + nested dialogs)
│   ├── sso-settings-page.tsx          (639 lines, plain, TanStack)
│   └── audit-settings-page.tsx        (692 lines, plain, TanStack + AlertDialog)
├── components/
│   ├── delete-workspace-dialog.tsx    ← nested Dialog (workspace-general)
│   ├── skill-generator-modal.tsx      ← nested Dialog + SSE (skills, 20KB)
│   ├── skill-detail-modal.tsx         ← nested Dialog (skills)
│   ├── plugin-detail-sheet.tsx        ← nested Sheet (skills)
│   ├── create-template-modal.tsx      ← nested Dialog (skills)
│   ├── edit-template-modal.tsx        ← nested Dialog (skills)
│   └── ... (other components)
└── hooks/
    ├── use-workspace-settings.ts      (60s stale, CRUD)
    ├── use-audit-log.ts               (no stale, paginated)
    ├── use-custom-roles.ts            (60s stale, RBAC)
    ├── use-scim.ts                    (mutation-only)
    ├── use-sessions.ts                (30s stale + polling)
    ├── use-sso-settings.ts            (multi-protocol SSO)
    ├── use-workspace-encryption.ts    (60s stale, BYOK)
    └── use-workspace-quota.ts         (30s stale)
```

### Target Architecture (after Phase 4)

```text
app/(workspace)/[workspaceSlug]/
├── layout.tsx                          ← add SettingsModalProvider here
└── settings/
    └── [...section]/page.tsx           ← deep-link redirect only

features/settings/
├── pages/                              ← unchanged (same components, now rendered in modal)
├── components/
│   ├── settings-modal.tsx              ← NEW: Dialog shell + sidebar + panel switcher
│   └── ... (existing components unchanged)
├── contexts/
│   └── settings-modal-context.ts      ← NEW: open/activeSection state
├── providers/
│   └── settings-modal-provider.tsx    ← NEW: context provider + Dialog render
└── hooks/
    ├── use-settings-unsaved-changes.ts ← NEW: close-guard registration
    └── ... (existing hooks unchanged)

components/layout/
└── sidebar.tsx                         ← updated: router.push → openSettings()
```

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Nested Dialog z-index issues | Low | Medium | Radix handles this; test in Phase 2 |
| `SkillGeneratorModal` SSE inside Dialog | Low | High | Test SSE streaming early in Phase 3 |
| `beforeunload` guard silent failure | Certain | Medium | Implement close-guard in Phase 1 |
| Session polling (30s) on Security panel | Low | Low | TanStack `refetchInterval` tied to mount/unmount |
| Deep-link breakage before Phase 4 | High | Low | Old routes remain during transition; no break |
| Performance: 13 panels mounted | Medium | Low | `React.lazy` per panel prevents upfront load |
| Guest role accessing non-profile sections | Certain | High | Guard in `openSettings()` in Phase 1 |

---

*Investigation complete. Ready to feed into `/gsd:plan-phase` for Phase 1 implementation.*
