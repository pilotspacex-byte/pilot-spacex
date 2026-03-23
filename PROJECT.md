# Pilot Space

## What This Is

AI-augmented SDLC platform built on a "Note-First" paradigm. Users write in a note canvas, AI provides ghost text completions, extracts issues, and reviews PRs. BYOK model — no AI cost pass-through. Teams of 5-100 members per workspace.

## Core Value

Think first, structure later — notes are the entry point, not forms. AI is a co-pilot teammate.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Workspace management (create, invite, roles) — v1.0
- ✓ Project management (CRUD, member assignment) — v1.0
- ✓ Note editor (TipTap, rich text, blocks, markdown) — v1.0
- ✓ Issue tracking (create, state machine, properties, labels, cycles) — v1.0
- ✓ AI agent (PilotSpaceAgent, skills, SSE streaming, BYOK) — v1.0
- ✓ Artifact system (upload, preview: image, CSV, markdown, JSON, code, HTML) — v1.1
- ✓ Voice input (ElevenLabs STT, audio artifacts) — v1.1
- ✓ Member management (roles, demotion guards) — v1.1
- ✓ AI provider settings (BYOK configuration UI) — v1.0

### Active

<!-- Current scope. Building toward these. -->

- [ ] Office document preview (Excel, Word, PowerPoint) in artifact modal
- [ ] PPTX slide-by-slide navigation with annotation support
- [ ] Backend support for Office MIME types (.docx, .doc, .pptx, .ppt)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Live editing of Office documents — Deferred to next milestone. Complex integration (Office Web Apps / Google Docs API). Preview-first approach validates user need before investing in editing.
- File size limit increase — Keep at 10 MB. Sufficient for most Office documents.
- PDF preview — Not requested. Current download fallback is acceptable.
- Video/audio file preview — Existing download fallback covers these.

## Current Milestone: v1.2 Office Suite Preview

**Goal:** Enable rich preview of Excel, Word, and PowerPoint files inside the artifact modal, with PPTX annotation support tied to Pilot Space notes.

**Target features:**
- Excel (.xlsx/.xls) spreadsheet preview with table rendering
- Word (.docx/.doc) document preview rendered as formatted HTML
- PowerPoint (.pptx/.ppt) slide-by-slide preview with annotations
- Backend extension allowlist for Office MIME types

## Context

- Artifact rendering pipeline is well-architected for extension (5 touchpoints per new type)
- `resolveRenderer()` in `mime-type-router.ts` is the single routing table
- `FilePreviewModal` uses lazy-loaded renderers via `next/dynamic`
- `useFileContent` currently returns text only — needs ArrayBuffer support for binary files
- `.xlsx` and `.xls` already in backend allowlist; `.docx`, `.doc`, `.pptx`, `.ppt` are NOT
- Supabase Storage signed URLs (1hr TTL) serve file content

## Constraints

- **Binary formats**: useFileContent must support ArrayBuffer for Office files — current `res.text()` corrupts binary data
- **Bundle size**: Office parsing libraries are heavy (SheetJS ~450KB, mammoth ~200KB). Must lazy-load via `next/dynamic`
- **Security**: DOCX→HTML conversion must be sanitized (DOMPurify) before rendering, same as HTML artifacts
- **10 MB limit**: Unchanged. Large presentations with embedded HD media may not fit.
- **Client-side only**: No server-side rendering/conversion. All parsing happens in the browser.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Preview-only, no editing | Validate user need before investing in complex Office Web Apps integration | — Pending |
| Client-side parsing (SheetJS, mammoth) | No server dependency, works with signed URLs, no public URL requirement | — Pending |
| PPTX preview + annotate | Full PPTX editing is extremely complex; annotations tie into existing note system | — Pending |
| Keep 10 MB limit | Sufficient for most Office docs; avoids storage cost increase | — Pending |

---
*Last updated: 2026-03-21 after milestone v1.2 initialization*
