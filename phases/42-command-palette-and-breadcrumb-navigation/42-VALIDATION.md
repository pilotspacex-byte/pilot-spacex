---
phase: 42
slug: command-palette-and-breadcrumb-navigation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.x + jsdom |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && pnpm test -- --run --reporter=verbose` |
| **Full suite command** | `cd frontend && pnpm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && pnpm test -- --run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && pnpm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | CMD-01, CMD-04 | unit | `cd frontend && pnpm test -- --run src/features/command-palette/registry/ActionRegistry.test.ts src/features/command-palette/hooks/useRecentActions.test.ts` | No - Wave 0 | pending |
| 42-01-02 | 01 | 1 | CMD-01, CMD-04 | unit | `cd frontend && pnpm test -- --run src/features/command-palette/components/CommandPalette.test.tsx` | No - Wave 0 | pending |
| 42-02-01 | 02 | 1 | CMD-02 | unit | `cd frontend && pnpm test -- --run src/features/breadcrumbs/hooks/useBreadcrumbs.test.ts` | No - Wave 0 | pending |
| 42-02-02 | 02 | 1 | CMD-03 | unit | `cd frontend && pnpm test -- --run src/features/symbol-outline/parsers/markdownSymbols.test.ts src/features/symbol-outline/hooks/useSymbolOutline.test.ts` | No - Wave 0 | pending |
| 42-03-01 | 03 | 2 | CMD-01, CMD-02, CMD-03, CMD-04 | integration | `cd frontend && pnpm type-check && pnpm lint` | N/A (type-check) | pending |
| 42-03-02 | 03 | 2 | CMD-01, CMD-02, CMD-03, CMD-04 | manual | Human verification of all three features | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `src/features/command-palette/registry/ActionRegistry.test.ts` — registry CRUD + filter
- [ ] `src/features/command-palette/hooks/useRecentActions.test.ts` — localStorage persist, cap at 5
- [ ] `src/features/command-palette/components/CommandPalette.test.tsx` — render + keyboard interaction + filtering
- [ ] `src/features/breadcrumbs/hooks/useBreadcrumbs.test.ts` — path splitting, sibling resolution
- [ ] `src/features/symbol-outline/parsers/markdownSymbols.test.ts` — heading hierarchy, PM blocks
- [ ] `src/features/symbol-outline/hooks/useSymbolOutline.test.ts` — active tracking, debounce

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Command palette opens on Cmd+Shift+P with fuzzy search | CMD-01 | Visual verification of overlay UI | Plan 42-03 Task 2 how-to-verify steps 3-9 |
| Breadcrumb segments are clickable with sibling dropdowns | CMD-02 | Visual/interactive verification | Plan 42-03 Task 2 how-to-verify steps 10-14 |
| Symbol outline shows hierarchy with click-to-navigate | CMD-03 | Visual/interactive verification | Plan 42-03 Task 2 how-to-verify steps 15-21 |
| Keyboard shortcuts work inside Monaco editor | CMD-01, CMD-03 | Monaco keybinding override verification | Plan 42-03 Task 2 how-to-verify steps 22-24 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
