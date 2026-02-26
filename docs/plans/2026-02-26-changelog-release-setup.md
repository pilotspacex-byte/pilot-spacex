# Changelog & Release Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create CHANGELOG.md with full back-filled history, add `scripts/release.sh` for future releases, and tag `v0.1.0-alpha.1`.

**Architecture:** Three discrete tasks with no interdependencies except Task 3 depends on Task 1. CHANGELOG is a standalone markdown file; release script is a standalone bash script; tagging runs last to capture final state.

**Tech Stack:** Bash, `sed`, `jq`, `gh` CLI, `git`

---

## Task 1: Create CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md` (repo root)

### Step 1: Create the file

Write `/CHANGELOG.md` with the content below. Copy exactly.

```markdown
# Changelog

All notable changes to Pilot Space are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha.1] - 2026-02-26

### Added

- `ProjectContextHeader` component with navigation tabs (notes, issues) across note and issue detail pages
- GitHub integration: end-to-end webhook sync, MCP tools (6 new tools), PR review panel in issue detail
- ChatView AI commands in issue editor (`/plan`, `/decompose`, `/enhance`, note card links)
- AI implementation plan generation for issues with markdown export
- Terminal streaming view for Claude Code plan execution
- Intent engine service with background job worker (Feature 015)
- Block ownership engine with attribution tracking (Feature 016)
- Collaboration toolbar with change attribution TipTap extension
- PM blocks capacity fields: `estimate_hours` on issues, `weekly_available_hours` on members
- Note editor enhancements: linking, gutter TOC, issue indicators, project picker
- Landing page with 12 sections and AI interaction demos
- Daily routine contextual AI chat experience (Feature 019)
- Tri-view issue management: Board, List, Table with unified filter bar
- 6-layer dynamic prompt assembly for PilotSpaceAgent
- Project list and detail pages with real API integration
- Issue detail 9 UX improvements with note-first redesign

### Changed

- Ghost text migrated from Gemini Flash to Claude Haiku
- Issue detail redesigned with Note-First layout (TipTap note canvas + ChatView tab)
- `NoteCanvasLayout` unwrapped from `observer()` to fix React 19 flushSync conflict

### Fixed

- AI: 19 API contract mismatches resolved between backend and frontend
- Issues: state blink in collapsed property block view (4 progressive fixes)
- AI approvals: `AttributeError` on `User.name` causing 500 errors
- Note link: chip empty display and suggestion loading state
- Issue detail: `link_type` uppercase serialization mismatch
- GitHub: 3 webhook/activity bugs in PRReviewSubagent

### Security

- Pre-mutation IDOR checks added to all 6 issue mutation endpoints
- RLS context now enforced before DB query in `require_workspace_member`
- Atomic Redis rate limiters replace TOCTOU in-memory counters in ghost text and AI context
- Fail-closed Redis policy prevents rate limit bypass on infrastructure outage

## [0.0.4] - 2026-02-11

### Added

- PM Note Extensions: 10 block types (RACI, Risk Matrix, ADR, System Diagram, Mermaid, Decision Log, Dashboard, Timeline, Capacity Plan, Checklist)
- Persistent task management with AI decomposition and context export
- Approval & user input UX overhaul with MCP interaction server
- Multi-question wizard with `skipWhen` logic and "Other" option
- Tool call event persistence for session resume rendering
- AI ChatView: 10 design improvements including auto-collapse and block navigation
- Homepage Hub 3-zone layout (US-19): recent notes, active issues, AI activity feed
- Role-skills: MCP tools + 8 role templates (Features 010-011)
- Onboarding: 3-step wizard merged into single two-panel form
- MCP tools expanded from 6 to 27 across 4 categories (notes, issues, projects, workspace)
- `focus_block` SSE event with edit guard and visual feedback
- Note editor: table/list support, linked issues display, line gutter
- Issue extraction: full flow with selection + creation UI
- Multi-context session architecture with resume support

### Changed

- `AIContextSubagent` replaced by `PilotSpaceAgent` delegation (DD-086)
- GhostTextService wired into DI container with BYOK, client pool, ResilientExecutor, CostTracker
- DI container split to resolve circular imports; session store ORM errors fixed
- Auth, workspace, and issues routers migrated to service layer
- RLS enum case corrected in policies (`OWNER`, `ADMIN`, `MEMBER`, `GUEST`)

### Fixed

- DB: race condition in issue `sequence_id` generation
- Editor: XSS vulnerability in PM block renderer; error boundary added
- AI tools: workspace verification added to all mutation tools
- Ghost text: stale error state, type safety, and accessibility issues
- Ghost text: prompt injection hardening

## [0.0.3] - 2026-02-06

### Added

- AI chat: thinking blocks, tool call cards, streaming UX
- SSE delta buffer for event reduction (water pumping pattern)
- Multi-context session architecture with resume support
- Compact layout redesign with sidebar controls migration
- AI Context Tab in issue detail with structured SSE sections

### Fixed

- AI: 3 P0 critical security and persistence issues
- AI: 17 high-priority security findings across backend and frontend
- AI sessions: auto-restore conversation history when opening note page
- AI MCP: `write_to_note` tool, workspace headers, deprecated agent cleanup
- Activity: metadata attribute mismatch and state null-safety

## [0.0.2] - 2026-02-04

### Added

- PilotSpace Conversational Agent Architecture (Waves 1-8): PilotSpaceAgent orchestrator with skill dispatch
- SSE streaming for all AI interactions
- Claude Agent SDK integration for GhostTextAgent, PRReviewAgent, AIContextAgent
- Session resume: auto-restore conversation history
- MCP tool registry: 6 initial tools (notes/issues)
- Approval queue: backend persistence + frontend queue UI
- Cost Dashboard with charts and analytics
- AssigneeRecommenderAgent with expertise loading
- MarginAnnotationAgent with SDK
- IssueExtractorAgent with confidence tags

### Changed

- Demo user fallback removed; real Supabase Auth required

### Fixed

- AI streaming: real-time `StreamEvent` forwarding with dedup and session leak prevention
- AI security: 17 high-priority findings remediated across backend and frontend

## [0.0.1] - 2026-01-25

### Added

- Note Canvas with block-based TipTap editor (13 extensions)
- Issue management with state machine (Backlog → Todo → In Progress → In Review → Done)
- Ghost text AI (500ms trigger, Tab accept, Escape dismiss)
- PR Review Agent with GitHub webhook integration
- Margin Annotation Agent
- Issue Extraction with confidence tags
- Approval queue backend
- Cost Dashboard with charts and analytics
- BYOK configuration for Anthropic and Gemini providers
- Workspace multi-tenant isolation with Supabase Row-Level Security
- 21 Alembic database migrations
- SSE streaming for all AI endpoints
- Supabase Auth + JWT middleware
- Redis session cache (30-min sliding TTL)
- Meilisearch full-text search integration
- pgvector 768-dim HNSW embeddings for semantic search

[Unreleased]: https://github.com/TinDang97/pilot-space/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/TinDang97/pilot-space/compare/v0.0.4...v0.1.0-alpha.1
[0.0.4]: https://github.com/TinDang97/pilot-space/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/TinDang97/pilot-space/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/TinDang97/pilot-space/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/TinDang97/pilot-space/releases/tag/v0.0.1
```

### Step 2: Verify the file was created

```bash
head -5 CHANGELOG.md
wc -l CHANGELOG.md
```

Expected: First line is `# Changelog`, file has ~160 lines.

### Step 3: Commit

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add CHANGELOG.md with full back-filled history"
```

Expected: Pre-commit hooks pass, commit created.

---

## Task 2: Create `scripts/release.sh`

**Files:**
- Create: `scripts/release.sh`

### Step 1: Create the scripts directory if missing

```bash
mkdir -p scripts
```

### Step 2: Write the script

Write `scripts/release.sh` with the content below:

```bash
#!/usr/bin/env bash
# Pilot Space release script.
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.1.1-alpha.2
set -euo pipefail

# ── Validate args ─────────────────────────────────────────────────────────────
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Error: version argument required" >&2
  echo "Usage: $0 <version>  (e.g. 0.1.1-alpha.2)" >&2
  exit 1
fi

TAG="v${VERSION}"
DATE=$(date +%Y-%m-%d)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"
FE_PKG="$REPO_ROOT/frontend/package.json"
BE_TOML="$REPO_ROOT/backend/pyproject.toml"

# ── Validate working tree is clean ────────────────────────────────────────────
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  echo "Error: working tree has uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

# ── Validate [Unreleased] has content ─────────────────────────────────────────
# Extract lines between "## [Unreleased]" and the next "## [" heading
UNRELEASED=$(awk '/^## \[Unreleased\]/{found=1; next} found && /^## \[/{exit} found{print}' "$CHANGELOG" | grep -v '^$' || true)
if [[ -z "$UNRELEASED" ]]; then
  echo "Error: [Unreleased] section in CHANGELOG.md is empty. Add entries before releasing." >&2
  exit 1
fi

echo "Releasing $TAG on $DATE..."

# ── Extract [Unreleased] content for GitHub release notes ─────────────────────
RELEASE_NOTES=$(awk '/^## \[Unreleased\]/{found=1; next} found && /^## \[/{exit} found{print}' "$CHANGELOG")

# ── Update CHANGELOG.md ───────────────────────────────────────────────────────
# 1. Insert new [VERSION] heading after [Unreleased] line
# 2. Add empty [Unreleased] section at top
TMP=$(mktemp)
awk -v ver="$VERSION" -v date="$DATE" '
  /^## \[Unreleased\]/ {
    print "## [Unreleased]"
    print ""
    print "## [" ver "] - " date
    next
  }
  { print }
' "$CHANGELOG" > "$TMP" && mv "$TMP" "$CHANGELOG"

# ── Bump frontend/package.json ────────────────────────────────────────────────
if command -v jq &>/dev/null; then
  TMP=$(mktemp)
  jq --arg v "$VERSION" '.version = $v' "$FE_PKG" > "$TMP" && mv "$TMP" "$FE_PKG"
else
  sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$FE_PKG" && rm -f "$FE_PKG.bak"
fi

# ── Bump backend/pyproject.toml ───────────────────────────────────────────────
sed -i.bak "s/^version = \"[^\"]*\"/version = \"$VERSION\"/" "$BE_TOML" && rm -f "$BE_TOML.bak"

# ── Commit + tag ──────────────────────────────────────────────────────────────
git -C "$REPO_ROOT" add CHANGELOG.md frontend/package.json backend/pyproject.toml
git -C "$REPO_ROOT" commit -m "chore(release): $TAG"
git -C "$REPO_ROOT" tag -a "$TAG" -m "Release $TAG"

# ── Push ──────────────────────────────────────────────────────────────────────
git -C "$REPO_ROOT" push
git -C "$REPO_ROOT" push --tags

# ── GitHub Release ────────────────────────────────────────────────────────────
PRERELEASE_FLAG=""
if [[ "$VERSION" == *"-alpha"* ]] || [[ "$VERSION" == *"-beta"* ]] || [[ "$VERSION" == *"-rc"* ]]; then
  PRERELEASE_FLAG="--prerelease"
fi

gh release create "$TAG" \
  --title "Pilot Space $TAG" \
  --notes "$RELEASE_NOTES" \
  $PRERELEASE_FLAG \
  --repo TinDang97/pilot-space

echo ""
echo "Released $TAG successfully."
```

### Step 3: Make the script executable

```bash
chmod +x scripts/release.sh
```

### Step 4: Smoke-test (dry run — do NOT run the full script yet)

Verify the script parses correctly:

```bash
bash -n scripts/release.sh
```

Expected: no output (syntax is valid).

### Step 5: Commit

```bash
git add scripts/release.sh
git commit -m "chore(scripts): add release.sh for semver release automation"
```

---

## Task 3: Tag `v0.1.0-alpha.1` and Create GitHub Release

> **Note:** Run this task AFTER Task 1 and Task 2 are committed.
> The `[Unreleased]` section must have at least one entry before running the script.
> Before running, add a brief `[Unreleased]` entry for the wiki docs work currently on `feat/wiki`.

**Files:**
- Modify: `CHANGELOG.md` (add `[Unreleased]` entry for current feat/wiki work)
- Modify: `frontend/package.json` (version bump)
- Modify: `backend/pyproject.toml` (version bump)

### Step 1: Add an [Unreleased] entry for current work

Edit `CHANGELOG.md` to add one entry under `## [Unreleased]`:

```markdown
## [Unreleased]

### Added

- Agent wiki documentation: full cross-referenced docs for PilotSpaceAgent, subagents, MCP tools, skills, ChatView components, and editor AI extensions
```

### Step 2: Verify the entry exists

```bash
grep -A 5 "## \[Unreleased\]" CHANGELOG.md
```

Expected: Shows the "Agent wiki documentation" bullet.

### Step 3: Commit the unreleased entry

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add unreleased entry for wiki documentation work"
```

### Step 4: Run the release script

```bash
./scripts/release.sh 0.1.0-alpha.1
```

Expected output (step by step):
1. `Releasing v0.1.0-alpha.1 on 2026-02-26...`
2. Pre-commit hooks pass
3. `chore(release): v0.1.0-alpha.1` commit created
4. Tag `v0.1.0-alpha.1` created
5. `git push` and `git push --tags` succeed
6. GitHub Release created at `https://github.com/TinDang97/pilot-space/releases/tag/v0.1.0-alpha.1`
7. `Released v0.1.0-alpha.1 successfully.`

### Step 5: Verify the release

```bash
git tag --sort=-v:refname | head -5
gh release view v0.1.0-alpha.1
```

Expected: Tag `v0.1.0-alpha.1` appears first; GitHub Release shows the release notes from `[0.1.0-alpha.1]` section.

---

## Verification Checklist

- [ ] `CHANGELOG.md` exists at repo root with 5 versioned sections
- [ ] `## [Unreleased]` section is present and empty (agent wiki entry moved to `[0.1.0-alpha.1]`)
- [ ] Comparison links at bottom of CHANGELOG resolve correctly
- [ ] `scripts/release.sh` is executable and passes `bash -n`
- [ ] `frontend/package.json` version = `0.1.0-alpha.1`
- [ ] `backend/pyproject.toml` version = `0.1.0-alpha.1`
- [ ] `git tag` shows `v0.1.0-alpha.1`
- [ ] GitHub Release page exists with correct notes and `--prerelease` flag

---

## Quick Reference: Future Releases

```bash
# 1. Edit CHANGELOG.md — add entries under [Unreleased]
# 2. Run:
./scripts/release.sh 0.1.1-alpha.2
```

That's it. The script handles everything else.
