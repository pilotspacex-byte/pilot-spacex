---
phase: quick-08
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/FEATURES_MAP.md
autonomous: true
requirements: []

must_haves:
  truths:
    - "Complete features map document exists covering all 6 layers plus CLI"
    - "Document reflects actual implemented state, not aspirational features"
    - "Browser testing covers login, navigation, and key feature accessibility"
  artifacts:
    - path: "docs/FEATURES_MAP.md"
      provides: "Complete Pilot Space features map organized by 6 layers"
      min_lines: 100
  key_links: []
---

<objective>
Save the comprehensive Pilot Space features map to a permanent document, then verify key features are accessible via browser testing.

Purpose: Create a reference document of all platform capabilities and validate the running application.
Output: docs/FEATURES_MAP.md with full features map; browser test results for key features.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/PILOT_SPACE_FEATURES.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write complete features map document</name>
  <files>docs/FEATURES_MAP.md</files>
  <action>
Create `docs/FEATURES_MAP.md` containing the complete Pilot Space features map organized by the 6 architectural layers plus CLI. This is a NEW file (not overwriting PILOT_SPACE_FEATURES.md which is the older spec doc).

The document must cover these layers with all features listed under each:

**Layer 1 — Core PM:** Issues (CRUD, state machine, priority, labels, cycles, assignees, note-first detail page with TipTap), Notes (TipTap rich editor, auto-save, ghost text), Cycles (time-boxed sprints, issue assignment, progress tracking), Projects (grouping, status, lead assignment), Members (invite, roles, RBAC), Onboarding (workspace setup checklist, collapsible), Skills and Roles (workspace member capabilities), Intents (action routing for AI commands).

**Layer 2 — AI-Augmented:** PilotSpaceAgent (orchestrator, SSE streaming, Claude Agent SDK), Ghost Text (independent agent, sub-2s latency, inline completions), AI Chat (conversational sidebar, tool use), Issue Extraction (extract issues from note text), Margin Annotations (contextual AI suggestions), AI Context Builder (codebase summarization for LLM), PR Review Agent (multi-turn code review), AI Approvals (human-in-the-loop DD-003), AI Cost Tracking (per-user/workspace token usage), AI Governance (provider routing DD-011, BYOK).

**Layer 3 — Knowledge and Memory:** Knowledge Graph (nodes, edges, visualization with D3/force-graph), KG Auto-Population (markdown chunker, background job pipeline), Memory/Recall (semantic search, context retrieval), Related Issues (similarity-based suggestions), Dependency Graph (issue dependency visualization).

**Layer 4 — Integrations:** GitHub (OAuth, repo sync, PR linking), MCP Servers (tool registration, dynamic routing), Plugins (extensibility framework), Webhooks (event dispatch).

**Layer 5 — Enterprise:** RBAC (Owner/Admin/Member/Guest, workspace-scoped), SSO (Supabase Auth), SCIM (user provisioning placeholder), Audit (action logging), Encryption (at-rest via Supabase, in-transit TLS), RLS (row-level security, multi-tenant isolation), Quotas (usage limits per workspace).

**Layer 6 — PM Intelligence:** Sprint Board (Kanban view, drag-and-drop), Release Notes (AI-generated from cycle), Capacity Planning (workload distribution), PM Dependency Graph (cross-issue blocking), Block Insights (bottleneck detection).

**CLI:** `pilot login` (auth flow), `pilot implement` (AI-driven issue implementation, interactive and oneshot modes).

For each feature, include a brief description (1-2 sentences) of what it does. Mark features with their implementation status where known: [Implemented], [Partial], [Planned]. Group by layer with clear headings. Include a summary table at the top showing layer counts.

Do NOT overwrite `docs/PILOT_SPACE_FEATURES.md` — that is a separate older specification document.
  </action>
  <verify>
    <automated>test -f docs/FEATURES_MAP.md && wc -l docs/FEATURES_MAP.md | awk '{if ($1 >= 100) print "PASS: " $1 " lines"; else print "FAIL: only " $1 " lines"}'</automated>
  </verify>
  <done>docs/FEATURES_MAP.md exists with 100+ lines covering all 6 layers, CLI, and feature descriptions with implementation status</done>
</task>

<task type="checkpoint:human-verify" gate="non-blocking">
  <name>Task 2: Browser testing of running application features</name>
  <what-built>Features map document saved. Now the orchestrator should perform browser testing to verify key features are accessible on the running application.</what-built>
  <how-to-verify>
NOTE TO ORCHESTRATOR: After executor completes Task 1, use `agent-browser` to perform the following verification:

1. Navigate to http://localhost:3000
2. Log in with e2e-test@pilotspace.dev / TestPassword123!
3. Navigate to workspace "workspace" and verify these pages load:
   - /workspace/issues — Issues list renders
   - /workspace/cycles — Cycles page renders
   - /workspace/projects — Projects page renders
   - /workspace/members — Members page renders
   - /workspace/settings — Settings page renders
   - /workspace/knowledge-graph — Knowledge graph renders
   - Click into an issue — Note editor (TipTap) renders
   - /workspace/ai-chat or AI sidebar — AI chat accessible
4. Record which features are accessible and which have errors
5. Update docs/FEATURES_MAP.md with any status corrections based on findings

Browser commands:
```
agent-browser navigate http://localhost:3000
agent-browser type "e2e-test@pilotspace.dev" --selector "input[type=email]"
agent-browser type "TestPassword123!" --selector "input[type=password]"
agent-browser click "button[type=submit]"
```
  </how-to-verify>
  <resume-signal>Orchestrator completes browser testing and reports results, or type "skip" to skip browser testing</resume-signal>
</task>

</tasks>

<verification>
- docs/FEATURES_MAP.md exists and contains all 6 layers
- Document has 100+ lines with structured content
- Browser testing verifies key pages are accessible (orchestrator task)
</verification>

<success_criteria>
- Complete features map saved to docs/FEATURES_MAP.md
- All 6 layers plus CLI documented with feature descriptions
- Implementation status marked for each feature
- Browser testing results recorded (if orchestrator performs Task 2)
</success_criteria>

<output>
After completion, create `.planning/quick/8-save-features-map-and-browser-test-all-f/8-SUMMARY.md`
</output>
