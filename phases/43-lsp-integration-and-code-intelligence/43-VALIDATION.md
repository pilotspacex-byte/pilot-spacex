---
phase: 43
slug: lsp-integration-and-code-intelligence
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-24
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (jsdom environment) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && pnpm vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && pnpm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && pnpm vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && pnpm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | LSP-01, LSP-03 | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/typescriptConfig.test.ts` | W0 | pending |
| 43-01-02 | 01 | 1 | LSP-01 | unit | `cd frontend && pnpm type-check` | existing | pending |
| 43-02-01 | 02 | 2 | LSP-04 | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/DiagnosticsPanel.test.tsx` | W0 | pending |
| 43-02-02 | 02 | 2 | LSP-04 | unit | `cd frontend && pnpm type-check && pnpm lint` | existing | pending |
| 43-03-01 | 03 | 2 | LSP-02 | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/pythonLanguage.test.ts` | W0 | pending |
| 43-03-02 | 03 | 2 | LSP-05, LSP-06 | unit | `cd frontend && pnpm vitest run src/features/command-palette/__tests__/lspNavigateActions.test.ts` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `src/features/editor/__tests__/typescriptConfig.test.ts` -- TS defaults configuration, verify JSON/CSS/HTML defaults untouched
- [ ] `src/features/editor/__tests__/diagnosticsPanel.test.ts` -- marker subscription logic, Diagnostic[] production
- [ ] `src/features/editor/__tests__/DiagnosticsPanel.test.tsx` -- panel component rendering, filter toggles, click-to-navigate
- [ ] `src/features/command-palette/__tests__/lspNavigateActions.test.ts` -- action registration for Go to Definition / Find References
- [ ] `src/features/editor/__tests__/pythonLanguage.test.ts` -- lazy loading behavior, fallback on failure

Note: Monaco editor APIs will need mocking in unit tests (jsdom has no real Monaco). Focus tests on: configuration objects are correct, React component rendering, action registration, and lazy-loading logic.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| IntelliSense autocomplete popup appears on dot-trigger | LSP-01 | Requires live Monaco editor with TS worker | Open a .ts file, type `const x: string = ''; x.`, verify autocomplete popup shows string methods |
| Pyright loading indicator + subsequent Python autocomplete | LSP-02 | Requires live WASM worker initialization | Open a .py file, observe "Loading Python IntelliSense..." badge, wait for it to disappear, type `"hello".`, verify autocomplete |
| JSON/CSS/HTML intelligence not regressed | LSP-03 | Requires live Monaco built-in services | Open a .json file, verify syntax validation; open .css, verify property autocomplete |
| Click diagnostic row navigates to correct file and line | LSP-04 | Requires live editor with real diagnostics | Introduce a type error, open Problems panel, click the error row, verify editor jumps to correct location |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
