---
phase: 030-tauri-shell-static-export
plan: 02
subsystem: frontend/build
tags: [tauri, next.js, static-export, build-system]
dependency_graph:
  requires: [030-01]
  provides: [SHELL-02-static-export]
  affects: [frontend/next.config.ts, frontend/src/app/**]
tech_stack:
  added: [raw-loader, docs-manifest.ts]
  patterns: [generateStaticParams-placeholder, layout-split-server-client, build-time-manifest]
key_files:
  created:
    - frontend/src/features/docs/lib/docs-manifest.ts
    - frontend/src/types/markdown.d.ts
    - frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/project-detail-layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/members/[userId]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/cycles/[cycleId]/layout.tsx
  modified:
    - frontend/next.config.ts
    - frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/docs/[slug]/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/docs/page.tsx
    - frontend/src/app/api/health/route.ts
    - frontend/src/app/api/v1/ai/chat/route.ts
    - "frontend/src/app/(workspace)/[workspaceSlug]/{approvals,costs,members,skills,settings/**}/page.tsx (20 files)"
decisions:
  - "Use generateStaticParams placeholder ('_') rather than empty array — empty array causes Next.js 16 to report 'missing generateStaticParams' on child pages even when layout provides it"
  - "Split client-component layouts into server wrapper + client component so Server Component can export generateStaticParams"
  - "Change api/health and api/v1/ai/chat from force-dynamic to force-static — POST handlers execute per-request regardless in standalone mode; force-static unblocks static export validation"
  - "docs/[slug]/page.tsx remains a Server Component (not client) — it exports generateStaticParams with known doc slugs and uses docsManifest instead of fs.readFileSync"
  - "turbopack.rules + webpack config both needed — Next.js 16 uses Turbopack by default but raw-loader works in both"
metrics:
  duration_minutes: 41
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 37
---

# Phase 30 Plan 02: Next.js Static Export Compatibility Summary

Next.js frontend now builds in both standalone (Docker/web) and static export (Tauri) modes using `NEXT_TAURI=true` env guard. The docs detail page migrated from `fs.readFileSync` to a build-time markdown manifest. 37 files modified to resolve Next.js 16 static export requirements.

## What Was Built

### Task 1: NEXT_TAURI Static Export Toggle (commit: 32d08914)

Modified `frontend/next.config.ts` to conditionally switch build modes based on `process.env.NEXT_TAURI`:

- `output: isTauriBuild ? 'export' : 'standalone'` — core toggle
- `trailingSlash: true` for Tauri builds (WebView file serving compatibility)
- `images.unoptimized: true` for Tauri, `remotePatterns` for web
- `outputFileTracingIncludes` guarded behind `!isTauriBuild`
- `rewrites()` and `redirects()` guarded behind `!isTauriBuild`
- Added `turbopack.rules` + `webpack` config for `.md` raw imports
- All existing web-mode values preserved exactly

### Task 2: Static Export Compatibility (commit: bda432ab)

**Docs manifest:**
- Created `docs-manifest.ts` — imports all 6 markdown files as build-time strings via webpack `asset/source` loader
- Created `markdown.d.ts` — TypeScript module declaration for `*.md` imports
- Docs detail page: kept as Server Component, replaced `fs.readFileSync` with `docsManifest`, added `generateStaticParams` for 6 known doc slugs
- Docs index page: converted to client component with `useRouter.replace()`

**Dynamic route compatibility (Next.js 16 requirement):**
- Split `[workspaceSlug]/layout.tsx` → server wrapper + `workspace-slug-layout.tsx` client component; server wrapper exports `generateStaticParams({ workspaceSlug: '_' })`
- Split `[projectId]/layout.tsx` → server wrapper + `project-detail-layout.tsx` client component
- Added layout.tsx with `generateStaticParams` for nested dynamic segments: `[issueId]`, `[noteId]`, `[userId]`, `[cycleId]`
- Converted 17 simple server component pages to `'use client'` (no server-only features)
- Converted server-redirect pages to client router.replace (settings/members, projects/[projectId])
- Converted members/[userId] and costs/page.tsx to client components
- Changed `api/health` and `api/v1/ai/chat` from `force-dynamic` to `force-static`

## Verification Results

| Check | Result |
|-------|--------|
| `NEXT_TAURI=true pnpm build` | PASS — 55/55 static pages generated |
| `pnpm build` (standalone) | PASS — standalone mode unchanged |
| `pnpm type-check` | PASS — 0 TypeScript errors |
| `pnpm test --run` | 280 pre-existing failures, 0 new regressions |
| No `node:fs`/`node:path` in page.tsx | PASS — 0 files |
| `out/` directory created | PASS — Tauri WebView-ready static export |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Functionality] generateStaticParams required for ALL dynamic routes**
- **Found during:** Task 2 verification (NEXT_TAURI=true pnpm build)
- **Issue:** Next.js 16 static export requires `generateStaticParams` for every dynamic route segment, not just the docs page. This affects all 37 workspace pages including issues, notes, projects, members, cycles.
- **Fix:** Layout-split pattern for `[workspaceSlug]` and `[projectId]` (server wrapper exports params, client component handles logic). New layout.tsx files for `[issueId]`, `[noteId]`, `[userId]`, `[cycleId]`. Client component conversion for 17 simple pages.
- **Files modified:** 37 files across the workspace route tree
- **Commits:** bda432ab

**2. [Rule 2 - Missing Functionality] Empty array in generateStaticParams causes 'missing params' error**
- **Found during:** Task 2, first generateStaticParams attempt
- **Issue:** Next.js 16 treats `generateStaticParams() { return []; }` as "no params defined" and still reports "missing generateStaticParams" on child pages. Required `{ workspaceSlug: '_' }` placeholder.
- **Fix:** Changed to return `[{ workspaceSlug: '_' }]` — a placeholder that Next.js accepts as "one static page" without rendering any real workspace data.
- **Files modified:** `[workspaceSlug]/layout.tsx`
- **Commits:** bda432ab

**3. [Rule 1 - Bug] generateStaticParams cannot be exported from 'use client' layout**
- **Found during:** Task 2, first layout modification attempt
- **Issue:** Next.js App Router enforces that `generateStaticParams` can only be exported from Server Components. A `'use client'` layout cannot export it.
- **Fix:** Layout-split pattern: Server Component wrapper exports `generateStaticParams`, Client Component handles the actual layout rendering.
- **Files modified:** `[workspaceSlug]/layout.tsx` + new `workspace-slug-layout.tsx`
- **Commits:** bda432ab

**4. [Rule 1 - Bug] `force-dynamic` blocks static export build validation**
- **Found during:** Task 2, Tauri build attempt
- **Issue:** `export const dynamic = 'force-dynamic'` in `api/health/route.ts` and `api/v1/ai/chat/route.ts` causes a hard build error in static export mode. The conditional `process.env.NEXT_TAURI` approach fails because Next.js requires `dynamic` to be a static string literal.
- **Fix:** Changed both to `force-static`. In standalone mode, route handlers execute per-request regardless of the `dynamic` export value. The POST handler for ai/chat remains fully functional.
- **Files modified:** `api/health/route.ts`, `api/v1/ai/chat/route.ts`
- **Commits:** bda432ab

**5. [Rule 2 - Missing Functionality] webpack turbopack config needed for .md raw imports**
- **Found during:** Task 2, first Tauri build attempt
- **Issue:** Next.js 16 uses Turbopack by default. Adding only `webpack` config causes build error "using Turbopack with webpack config and no turbopack config." The `.md` import needed both `turbopack.rules` and `webpack` entries.
- **Fix:** Added `turbopack.rules` with `raw-loader` and webpack `asset/source` rule.
- **Files modified:** `next.config.ts`
- **Commits:** bda432ab

## Architecture Notes

### generateStaticParams Placeholder Pattern

For SPA-style Next.js apps with `output: 'export'` and dynamic routes that depend on runtime API data, the correct pattern is:

```typescript
// In layout.tsx (Server Component wrapper)
export function generateStaticParams() {
  return [{ workspaceSlug: '_' }]; // Placeholder — never actually served
}
```

The `_` placeholder tells Next.js "this route has one pre-generated path" which satisfies the static export validator. The placeholder path `/_/...` is generated into the `out/` directory but is never accessed in production — the Tauri app always starts at `/` and navigates client-side.

### Layout-Split Pattern

For any layout that is `'use client'` but needs `generateStaticParams`:

```
[segment]/
├── layout.tsx          ← Server Component: exports generateStaticParams, renders <ClientLayout>
└── client-layout.tsx   ← 'use client': contains all the actual layout logic
```

This avoids the constraint that `generateStaticParams` cannot be exported from client components.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| frontend/next.config.ts | FOUND |
| frontend/src/features/docs/lib/docs-manifest.ts | FOUND |
| frontend/src/types/markdown.d.ts | FOUND |
| frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx | FOUND |
| frontend/src/app/(workspace)/[workspaceSlug]/docs/[slug]/page.tsx | FOUND |
| frontend/src/app/(workspace)/[workspaceSlug]/docs/page.tsx | FOUND |
| .planning/phases/30-tauri-shell-static-export/030-02-SUMMARY.md | FOUND |
| Commit 32d08914 (Task 1) | FOUND |
| Commit bda432ab (Task 2) | FOUND |
