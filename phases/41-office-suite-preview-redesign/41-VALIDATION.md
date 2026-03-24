---
phase: 41
slug: office-suite-preview-redesign
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest 8.x (backend) |
| **Config file** | `frontend/vitest.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd frontend && pnpm test -- --run --reporter=dot` |
| **Full suite command** | `make quality-gates-frontend && make quality-gates-backend` |
| **Estimated runtime** | ~45 seconds (frontend), ~60 seconds (backend) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && pnpm test -- --run --reporter=dot`
- **After every plan wave:** Run `make quality-gates-frontend && make quality-gates-backend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | XLSX-redesign | visual + unit | `pnpm test -- XlsxRenderer` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DOCX-redesign | visual + unit | `pnpm test -- DocxRenderer` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PPTX-redesign | visual + unit | `pnpm test -- PptxRenderer` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Annotation-UX | unit + integration | `pnpm test -- PptxAnnotation` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Responsive-modal | visual | `pnpm test -- FilePreviewModal` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Keyboard-nav | unit | `pnpm test -- keyboard` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/features/artifacts/__tests__/xlsx-renderer.test.tsx` — stubs for XLSX redesign
- [ ] `frontend/src/features/artifacts/__tests__/docx-renderer.test.tsx` — stubs for DOCX redesign
- [ ] `frontend/src/features/artifacts/__tests__/pptx-renderer.test.tsx` — stubs for PPTX redesign
- [ ] `frontend/src/features/artifacts/__tests__/annotation-panel.test.tsx` — stubs for annotation UX
- [ ] `frontend/src/features/artifacts/__tests__/file-preview-modal.test.tsx` — stubs for responsive modal

*Existing vitest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| XLSX frozen header scrolling feel | SC-1 | Visual/interaction quality | Open .xlsx, scroll table, verify header stays fixed with clean shadow |
| DOCX page-like feel | SC-2 | Visual quality assessment | Open .docx, verify prose renders with proper page shadow/margins |
| PPTX slide transitions | SC-3 | Animation smoothness | Navigate slides, verify smooth canvas transitions |
| Fullscreen slideshow mode | SC-3 | Full-screen rendering | Enter fullscreen, navigate slides, verify proper display |
| Responsive modal sizing | SC-5 | Layout responsiveness | Maximize/minimize modal, verify all renderers adapt |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
