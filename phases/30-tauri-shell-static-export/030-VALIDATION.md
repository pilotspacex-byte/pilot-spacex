---
phase: 30
slug: tauri-shell-static-export
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), cargo test (Rust/Tauri) |
| **Config file** | `frontend/vitest.config.ts`, `tauri-app/src-tauri/Cargo.toml` |
| **Quick run command** | `cd frontend && pnpm test -- --run` |
| **Full suite command** | `cd frontend && pnpm test -- --run && cd ../tauri-app/src-tauri && cargo test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && pnpm test -- --run`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | SHELL-01 | build | `cd tauri-app/src-tauri && cargo check` | ❌ W0 | ⬜ pending |
| 30-02-01 | 02 | 1 | SHELL-02 | build | `cd frontend && NEXT_TAURI=true pnpm build` | ❌ W0 | ⬜ pending |
| 30-02-02 | 02 | 1 | SHELL-02 | unit | `cd frontend && pnpm test -- --run` | ❌ W0 | ⬜ pending |
| 30-03-01 | 03 | 2 | SHELL-01 | ci | `gh workflow run tauri-build.yml` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tauri-app/src-tauri/` — Tauri project scaffolded with Cargo.toml
- [ ] `frontend/next.config.ts` — NEXT_TAURI guard verifiable via build

*Existing frontend test infrastructure (vitest) covers route testing.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tauri window shows full UI | SHELL-01 | Visual — requires native window | Launch `cargo tauri dev`, verify Pilot Space UI renders |
| Dynamic routes navigate in WebView | SHELL-02 | SPA navigation in WebView | Navigate /workspace/issues/1 in Tauri dev, verify no 404 |
| CI produces 4 platform artifacts | SHELL-01 | CI infra — requires GitHub Actions runners | Push to branch, verify 4 artifacts uploaded |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
