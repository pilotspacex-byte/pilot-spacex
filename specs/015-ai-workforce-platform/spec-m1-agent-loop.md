# M1 — Agent Loop

**Feature**: 015 AI Workforce Core
**Module**: M1 — Agent Loop
**Status**: Implemented (Sprint 1 + Sprint 2 wiring complete)
**Depends on**: None (orchestrator — calls M2, M3, M4)
**Consumed by**: M7 (Chat Engine, via SSE events)

---

## Purpose

Extend the existing `PilotSpaceAgent` orchestrator with a deterministic 6-step pipeline. Replace single-shot `agent.query()` with:

```
message → recall(M4) → detect intents(M2) → select skill(M3) → execute → save(M4) → respond
```

Chat is the command interface. Notes are the artifact store. The agent loop owns no business logic — it calls three stores and emits SSE events.

---

## Codebase Anchor

`backend/src/pilot_space/ai/agents/pilotspace_agent.py`

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-100 | Orchestrator MUST follow loop: recall → analyze → detect intents → select skill → execute → save → respond |
| FR-105 | Chat MUST be the primary command interface |
| FR-107 | Intent detection from chat (primary) and note changes (secondary, 2s debounce) |
| FR-081 | System SHOULD support event-driven agent loop listening for note changes, approvals, webhooks, schedules |
| FR-082 | Non-destructive actions SHOULD execute automatically; output presented in chat for review |
| FR-083 | Destructive actions MUST present output for approval before persisting |
| FR-084 | Event loop MUST resume blocked work within 5s of approval |

---

## Pipeline Steps

```
1. recall       — MemoryStore.search(message, workspace_id) → top-5 context entries
2. analyze      — LLM analysis with memory context injected
3. detect       — IntentStore.detect(text) → WorkIntent[] (if not already confirmed intents)
4. present      — Emit intent_detected SSE events, await confirmation
5. execute      — SkillRunner.execute(confirmed_intent) → AsyncIterator[SSEEvent]
6. save         — MemoryStore.save(intent_summary + skill_outcome + feedback)
7. respond      — Final SSE text_delta / message_stop
```

Step 4 (await confirmation) is event-driven: agent loop blocks on confirmed status, resumes within 5s of confirmation (FR-084).

---

## SSE Events Emitted

| Event | Trigger | Payload |
|-------|---------|---------|
| `intent_detected` | Intent extracted from message | `{ intent_id, what, confidence }` |
| `intent_confirmed` | User confirms intent | `{ intent_id, skill_selected }` |
| `intent_executing` | Skill execution starts | `{ intent_id, skill_name }` |
| `intent_completed` | Skill execution complete | `{ intent_id, artifacts[] }` |
| `text_delta` | LLM token stream | `{ content }` |
| `message_stop` | Pipeline complete | — |

---

## Module Interface

```python
process(message: str, session_context: SessionContext) -> AsyncIterator[SSEEvent]
interrupt(session_id: UUID) -> None
```

---

## Tasks

| ID | Task | Status |
|----|------|--------|
| T-016 | Refactor PilotSpaceAgent pipeline | Done |
| T-017 | Add SSE event types for intent lifecycle | Done |
| T-018 | Implement event-driven resume (FR-084) | Done |
| T-019 | Integration test: full Sprint 1 pipeline | Done |
| T-048 | Wire M4 recall into agent loop | Done |
| T-049 | Wire M3 execution into agent loop | Done |
| T-050 | Wire M4 save into agent loop | Done |

---

## Edge Cases

- **Chat closed while skill running**: Skill continues, output queued. SSE reconnect resumes stream.
- **Multiple intents in one message**: All detected, presented sequentially. Confirm all at once via ConfirmAll (M2).
- **Approval timeout (24h)**: Expired intent → status "review", chat notification. Skill output discarded.

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Memory recall adds relevant context | >80% of skill executions |
| Agent loop resume after approval | <5s |
| SSE events for full intent lifecycle | 100% coverage |
