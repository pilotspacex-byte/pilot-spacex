# Quickstart Validation: AI Workforce Platform

**Feature**: 015 — AI Workforce Platform
**Plan**: `specs/015-ai-workforce-platform/plan.md`

---

## Phase A: Foundation

### Scenario 1: Block Ownership — Happy Path

**Source**: US-1, FR-001-009

1. Login as test user (e2e-test@pilotspace.dev), open workspace "workspace"
2. Create a new note titled "Auth Feature Spec"
3. Type 3 paragraphs of text
4. **Verify**: All blocks have subtle "human" ownership indicator (default)
5. Open chat panel, type: "Create a spec for user authentication"
6. Confirm the detected intent in chat
7. **Verify**: AI skill creates blocks in the note with "ai:create-spec" indicator
8. Try to click and type inside an AI-owned block
9. **Verify**: Cursor is blocked, tooltip says "AI-owned block — use Approve/Reject"
10. Click [Approve] on the AI-owned block group
11. **Verify**: Blocks become editable (ownership changed to "shared")

---

### Scenario 2: Chat-Primary Intent Detection

**Source**: US-2, US-3, US-26, FR-010-019

1. Open chat panel
2. Type: "We need a password reset flow via email and a 2FA setup page"
3. **Verify**: Chat response contains 2 detected intents:
   - Intent 1: "Password reset via email" (confidence ~0.85)
   - Intent 2: "Two-factor authentication setup" (confidence ~0.80)
4. Each intent shows: what, why, confidence, [Confirm] [Edit] [Dismiss]
5. Click [Edit] on Intent 1, change "why" field, save
6. **Verify**: Intent re-scored, presented again for confirmation
7. Click [Confirm] on Intent 1
8. **Verify**: Chat shows "Queued for create-spec", status = "confirmed"
9. Click [Dismiss] on Intent 2
10. **Verify**: Intent removed from chat, optional feedback input shown

---

### Scenario 3: Intent from Note (Secondary Path)

**Source**: US-2, FR-012

1. Open a note, ensure chat panel is visible
2. Type in a new paragraph: "Users should be able to export their data as CSV"
3. Wait 3 seconds (2s debounce + processing)
4. **Verify**: Chat panel shows detected intent from note content
5. Intent card shows source = "note block" with block reference

---

### Scenario 4: Real-Time Collaborative Editing

**Source**: US-4, US-5, FR-024-033

1. Open note "Auth Feature Spec" in Browser Window 1
2. Open same note in Browser Window 2 (same user or different user)
3. In Window 1, type "# Architecture Overview" in a new paragraph
4. **Verify** (Window 2): Text appears within 200ms with cursor indicator
5. In Window 2, type in a different paragraph simultaneously
6. **Verify** (Window 1): Both edits visible, no conflict
7. Close Window 2, reopen after 5 seconds
8. **Verify**: Reconnection merges any buffered changes without data loss

---

### Scenario 5: Block Ownership in CRDT

**Source**: US-5, FR-008

1. Note with human-owned block and AI-owned block (from Scenario 1)
2. Browser Window 2 (simulating AI): attempt to modify human-owned block via CRDT
3. **Verify**: Modification rejected at CRDT layer, block unchanged
4. Browser Window 1 (human): attempt to type in AI-owned block
5. **Verify**: Keystroke prevented, tooltip displayed

---

### Scenario 6: Ghost Text TTL

**Source**: US-7, FR-045-047

1. Open note, type a few words, trigger ghost text (500ms pause)
2. **Verify**: Ghost text suggestion appears
3. Press Escape to dismiss
4. Wait 6 minutes without typing
5. Resume typing at same position
6. **Verify**: New suggestion fetched (not stale cached version)

---

### Scenario 7: Focus Mode and Note Density

**Source**: US-24, FR-095-099

1. Note with mixed content: 5 human paragraphs, 3 AI intent blocks, 2 AI progress blocks
2. **Verify**: AI blocks show collapsible headers ("3 intents — 2 confirmed, 1 pending")
3. Click collapse toggle on intent group
4. **Verify**: Collapses to single-line summary
5. Toggle Focus Mode (button in toolbar)
6. **Verify**: All AI-owned blocks hidden, only 5 human paragraphs visible
7. Toggle Focus Mode off
8. **Verify**: All blocks restored to previous collapse/expand state

---

### Scenario 8: PM Block Contract Safety

**Source**: US-6, FR-043-044

1. Run backend test: `pytest tests/contract/test_pm_block_types.py`
2. **Verify**: Test passes (backend and frontend types match)
3. Add a new type to backend `_VALID_PM_BLOCK_TYPES` only
4. Re-run test
5. **Verify**: Test FAILS, listing the divergent type

---

### Scenario 9: Large Document Performance

**Source**: US-9, FR-078-080

1. Create note with 200+ blocks (via test seed or manual)
2. Type rapidly in a paragraph at position ~150
3. **Verify**: Keystroke renders within 100ms (no jank)
4. Scroll through the full document
5. **Verify**: 60fps maintained (browser DevTools performance tab)
6. Add 50 more blocks, re-test typing
7. **Verify**: Structural hash dirty detection keeps typing responsive (<50ms)

---

### Scenario 10: Annotation Performance

**Source**: US-8, FR-076-077

1. Create note with 200+ annotations (via test seed or manual)
2. Load note page
3. **Verify**: Annotations render within 100ms (browser DevTools performance tab)
4. Filter by confidence >= 0.8
5. **Verify**: Query completes within 50ms

---

## Phase B: Skills & Agent Loop

### Scenario 11: Skill Execution via SDK

**Source**: US-22, FR-085-090

1. Chat: "Create a detailed specification for user authentication"
2. Confirm detected intent
3. **Verify**: Chat shows "create-spec skill executing..." with progress updates
4. Wait for skill completion (< 5 minutes)
5. **Verify**: Chat shows output preview with [Approve] [Revise] [Reject]
6. Click [Approve]
7. **Verify**: Spec blocks written to note with "ai:create-spec" ownership

---

### Scenario 12: Memory Recall Across Sessions

**Source**: US-23, FR-100-104

1. In Session 1: Chat "Create a spec for user auth with OAuth2"
2. Confirm and complete the intent
3. **Verify**: Memory engine saves context (intent, skill outcome)
4. Start new session (click New Session)
5. Chat: "What authentication approach did we decide on?"
6. **Verify**: Agent recalls prior auth context from memory engine
7. Response references OAuth2 decision from Session 1

---

### Scenario 13: Sprint Board with AI Insights

**Source**: US-11, FR-048-060

1. Create note, insert Sprint Board PM block (via slash command)
2. Link 10 issues across different states
3. **Verify**: 6 lanes rendered with correct issue placement
4. **Verify**: AI insight badges appear (green/yellow/red) on board header
5. Hover over a yellow badge
6. **Verify**: Tooltip shows analysis, referenced issues, suggested actions
7. Click dismiss on a badge
8. **Verify**: Badge hidden, not shown on next render

---

### Scenario 13b: Dependency Map with Critical Path

**Source**: US-12, FR-051-052

1. Create note, insert Dependency Map PM block (via slash command)
2. Link 8 issues with dependency relationships (A→B→C→D chain + branching)
3. **Verify**: DAG renders with dagre hierarchical layout
4. **Verify**: Critical path highlighted in red (longest chain)
5. Zoom in/out with scroll wheel
6. **Verify**: SVG zoom/pan works for 20+ nodes without performance issues
7. Click on a node
8. **Verify**: Popover shows issue details and linked dependencies

---

### Scenario 13c: User + Skill Presence

**Source**: US-13, FR-027, FR-031-033

1. Open note in 2 browser windows (User A, User B)
2. **Verify**: Presence list shows both users with name + colored cursor
3. Trigger AI skill (confirm an intent that writes to this note)
4. **Verify**: Presence list shows new "AI Skills" section with skill name + intent summary
5. Wait for skill to complete
6. **Verify**: Skill presence removed within 5 seconds
7. **Verify**: Presence list reverts to "Users" section only

---

### Scenario 14: Version History and Restore

**Source**: US-14, FR-034-042

1. Edit note for 6+ minutes (auto-version at 5 min)
2. Trigger AI skill (creates before/after versions)
3. Click "Save Version" manually
4. Open version history panel (sidebar)
5. **Verify**: 3+ versions visible (auto, ai_before, ai_after, manual)
6. Click on AI-after version
7. **Verify**: Read-only preview shown
8. Select two versions, click "Compare"
9. **Verify**: Side-by-side diff with green/red/yellow highlighting
10. Click "Restore" on an older version
11. **Verify**: Content reverted, new version created (audit trail preserved)
12. Click AI digest icon on a version
13. **Verify**: Natural language summary appears within 3 seconds

---

### Scenario 15: Custom Skill Management

**Source**: US-25, FR-091-094

1. Go to Settings → Skills
2. **Verify**: 20+ core skills listed (read-only)
3. Click "Create Custom Skill"
4. Fill: name="summarize-standup", model=haiku, approval=auto, tools=[search_notes, create_note]
5. **Verify**: Skill appears in list, marked "custom"
6. Open chat, type: `\summarize-standup`
7. **Verify**: Skill appears in skill menu and can be invoked

---

## Phase C: Always-On

### Scenario 16: Capacity Plan

**Source**: US-17, FR-053, FR-061-062

1. Add `estimate_hours` to 5 issues (3, 5, 8, 13, 2)
2. Set `weekly_available_hours` for 3 team members (40, 32, 40)
3. Insert Capacity Plan PM block
4. **Verify**: Stacked bar chart: committed vs available per member
5. **Verify**: Over-committed member shows red indicator

---

### Scenario 17: Always-On Event Loop

**Source**: US-21, FR-081-084

1. Enable always-on mode for workspace (settings)
2. Write in note: "We need to add rate limiting to all API endpoints"
3. Wait 5 seconds (no manual invocation)
4. **Verify**: Chat shows detected intent from note change (event loop triggered)
5. Intent presented with confidence and [Confirm] [Dismiss]

---

## Error Scenarios

### Scenario E1: Skill Timeout

**Source**: US-22, FR-087

1. Trigger a skill with large input (very long spec requirement)
2. Set timeout artificially low (for testing)
3. **Verify**: Skill terminates, partial output persisted
4. Chat shows "Skill timed out — [Retry]"
5. Intent status = "failed" with label "timeout"

---

### Scenario E2: Concurrent Skill Limit

**Source**: FR-109

1. Rapidly confirm 6 intents
2. **Verify**: First 5 skills execute concurrently
3. 6th intent shows "Waiting for slot" in chat
4. When first skill completes, 6th starts

---

### Scenario E3: Offline Reconnect

**Source**: FR-028

1. Open note in collaborative mode
2. Disconnect network (browser DevTools → Offline)
3. Type several paragraphs
4. Reconnect network
5. **Verify**: Changes merge with remote state, no data loss
