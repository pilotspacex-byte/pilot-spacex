---
phase: 40
slug: webgpu-canvas-ide-editor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest 7.x (backend) |
| **Config file** | `frontend/vitest.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd frontend && pnpm test --run` |
| **Full suite command** | `cd frontend && pnpm test --run && cd ../backend && uv run pytest` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && pnpm test --run`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Populated during planning | - | - | - | - | - | - | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/features/editor/__tests__/monaco-setup.test.ts` — Monaco editor mount/unmount
- [ ] `frontend/src/features/editor/__tests__/view-zone-widget.test.ts` — PM block view zone rendering
- [ ] `frontend/src/features/files/__tests__/file-store.test.ts` — FileStore MobX actions
- [ ] `frontend/src/features/files/__tests__/file-tree.test.ts` — File tree navigation

*Existing vitest infrastructure covers test framework — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spring physics scrolling | Performance | Requires visual inspection of scroll deceleration | Open large note, scroll fast, verify smooth deceleration with no jank |
| Crossfade mode transitions | Performance | CSS animation timing requires visual | Toggle rich/source view, verify 200-300ms crossfade without layout shift |
| Monaco Canvas rendering | Performance | GPU acceleration not testable in headless | Open 1000+ line file, verify smooth scroll at 60fps |
| Tab close with unsaved changes | UX | Requires dialog interaction flow | Edit file, close tab, verify destructive confirmation dialog appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
