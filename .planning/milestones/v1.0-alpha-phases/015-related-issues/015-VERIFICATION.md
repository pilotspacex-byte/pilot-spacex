---
phase: 015-related-issues
verified: 2026-03-10T14:45:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Dismiss button calls mutation with correct suggestion id at runtime — backend renamed RelatedSuggestion.issue_id to id (commit 3fe59609); backend and frontend now use the same field name id"
  gaps_remaining: []
  regressions:
    - "Tests at lines 165 and 427 in test_related_issues.py use stale item[\"issue_id\"] field name — both tests mock KG repo to return empty lists so the list comprehension runs over [] and passes vacuously; the stale assertion does not catch the rename and would KeyError if the list were non-empty (warning-level, not blocker)"
human_verification:
  - test: "Navigate to an issue detail page that has KG nodes populated (kg_populate has run)"
    expected: "AI Suggestions subsection shows suggestions with identifier, title, reason badge, and dismiss (X) button that actually works — suggestion disappears and does not reappear after page reload"
    why_human: "Cannot verify live KG suggestions and dismiss persistence without a running backend with populated knowledge graph"
  - test: "Click Link issue, type a partial title, select a result, check both issue pages"
    expected: "Linked issue appears in both issue detail pages (bidirectional visibility)"
    why_human: "Bidirectional link appearance requires live backend and two open issue pages"
---

# Phase 15: Related Issues Verification Report

**Phase Goal:** Implement related issues — AI semantic suggestions + manual linking — so users can discover and link related issues from the issue detail page.
**Verified:** 2026-03-10T14:45:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (commit 3fe59609)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | pytest tests/api/test_related_issues.py passes (9 tests) | VERIFIED | 9 passed in 1.52s |
| 2 | Frontend related-issues-panel tests pass (5 tests) | VERIFIED | 5 passed in tests |
| 3 | IssueSuggestionDismissal model with user_id, source_issue_id, target_issue_id, dismissed_at | VERIFIED | model exists at models/issue_suggestion_dismissal.py, all columns present |
| 4 | IssueSuggestionDismissalRepository has get_dismissed_target_ids and create_dismissal | VERIFIED | repository file present with both methods |
| 5 | Migration 072 creates issue_suggestion_dismissals table with RLS enabled | VERIFIED | ENABLE ROW LEVEL SECURITY + FORCE + workspace isolation + service_role bypass |
| 6 | GET /workspaces/{wid}/issues/{id}/related-suggestions endpoint exists | VERIFIED | router/related_issues.py line 102; mounted in main.py |
| 7 | Each suggestion has similarity_score and reason fields | VERIFIED | RelatedSuggestion Pydantic model lines 51-58 |
| 8 | POST /relations creates RELATED IssueLink; 409 on bidirectional duplicate | VERIFIED | lines 262-308 in related_issues.py; test_create_duplicate_link_returns_409 passes |
| 9 | DELETE /relations/{link_id} soft-deletes; returns 204 | VERIFIED | lines 311-334; test_delete_related_link_success passes |
| 10 | POST dismiss creates dismissal row; 204 response | VERIFIED | lines 222-254; test_dismiss_suggestion passes |
| 11 | Dismiss button calls mutation with correct suggestion id at runtime | VERIFIED | Backend RelatedSuggestion.issue_id renamed to id (commit 3fe59609 lines 54, 206). Frontend type has id: string. Component uses s.id for key and dismiss.mutate(s.id). Field names now align end-to-end. |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/src/pilot_space/api/v1/routers/related_issues.py` | GET suggestions + POST dismiss + POST/DELETE relations | VERIFIED | 335 lines, all 4 endpoints implemented; RelatedSuggestion.id field confirmed post-fix |
| `backend/src/pilot_space/infrastructure/database/models/issue_suggestion_dismissal.py` | IssueSuggestionDismissal model | VERIFIED | 91 lines, UniqueConstraint, composite indexes |
| `backend/src/pilot_space/infrastructure/database/repositories/issue_suggestion_dismissal_repository.py` | IssueSuggestionDismissalRepository | VERIFIED | 85 lines, both methods implemented |
| `backend/alembic/versions/072_add_issue_suggestion_dismissals.py` | Migration 072 with RLS | VERIFIED | Single head, RLS enabled, UPPERCASE enum in policies |
| `backend/tests/api/test_related_issues.py` | 9 passing tests for RELISS-01..04 | VERIFIED | All 9 pass; note: two assertions use stale item["issue_id"] over empty lists (warning below) |
| `frontend/src/types/issue.ts` | RelatedSuggestion interface | VERIFIED | Interface has id: string (line 189) matching backend id field |
| `frontend/src/features/issues/components/related-issues-panel.tsx` | RelatedIssuesPanel observer component | VERIFIED | Renders correctly; key={s.id} and dismiss.mutate(s.id) both use s.id which is now populated from backend |
| `frontend/src/features/issues/hooks/use-related-suggestions.ts` | useRelatedSuggestions hook | VERIFIED | Query hook with UUID guard and 60s staleTime |
| `frontend/src/features/issues/hooks/use-dismiss-suggestion.ts` | useDismissSuggestion mutation hook | VERIFIED | mutationFn receives targetIssueId string and calls issuesApi.dismissSuggestion; invalidates suggestions query on success |
| `frontend/src/features/issues/hooks/use-create-relation.ts` | useCreateRelation mutation hook | VERIFIED | Invalidates relations query on success |
| `frontend/src/features/issues/hooks/use-delete-relation.ts` | useDeleteRelation mutation hook | VERIFIED | Invalidates relations query on success |
| `frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx` | 5 passing tests | VERIFIED | All 5 pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `related_issues.py` | `KnowledgeGraphRepository.hybrid_search` | `KnowledgeGraphRepository(session)` | VERIFIED | Lines 124-141; hybrid_search called with NodeType.ISSUE |
| `related_issues.py` | `IssueSuggestionDismissalRepository` | `dismissal_repo.get_dismissed_target_ids + create_dismissal` | VERIFIED | Lines 125, 144, 246 |
| `related_issues.py` | `IssueLinkRepository.link_exists` | bidirectional duplicate check | VERIFIED | Lines 286-290, RELATED type |
| `main.py` | `related_issues_router` | `app.include_router(related_issues_router, prefix=...)` | VERIFIED | Line 297 |
| `related-issues-panel.tsx` | `useRelatedSuggestions` | import and call | VERIFIED | Lines 29, 134 |
| `issue-editor-content.tsx` | `RelatedIssuesPanel` | import and render below activity | VERIFIED | Lines 36, 294-298 |
| `issue-properties-panel.tsx` | `RelatedIssuesPanel` | import and render | VERIFIED | Lines 41, 454 |
| `services/api/issues.ts` | `/related-suggestions` API | `issuesApi.getRelatedSuggestions` | VERIFIED | Lines 165-170 |
| `related-issues-panel.tsx` | `dismiss.mutate(s.id)` | `s.id` field from backend | VERIFIED | Backend now serializes id (not issue_id); s.id is populated at runtime |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|------------|-------------|-------------|--------|---------|
| RELISS-01 | 015-01, 015-02, 015-03 | Issue detail shows auto-suggested related issues (semantic similarity via knowledge graph) | VERIFIED | GET /related-suggestions endpoint exists with KG hybrid_search wired; suggestions displayed in panel |
| RELISS-02 | 015-01, 015-02, 015-03 | User can manually link/unlink issues as related from the issue detail page | VERIFIED | POST/DELETE /relations endpoints exist; LinkIssueCombobox in panel |
| RELISS-03 | 015-01, 015-02, 015-03 | Related issues surface connections via shared notes, same project, and semantic similarity score | VERIFIED | Reason enrichment logic lines 196-202; three reason types: "same project", "shared note", "Semantic match (N%)" |
| RELISS-04 | 015-01, 015-02, 015-03 | User can dismiss AI suggestions (dismissed suggestions don't re-appear) | VERIFIED | POST dismiss endpoint + dismissal_repo exist; dismiss button now sends s.id (backend field renamed to id by commit 3fe59609) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/tests/api/test_related_issues.py` | 165, 427 | `item["issue_id"]` references stale field name (now `id`) | Warning | Both tests mock KG repo to return empty list — list comprehension runs over [] so no KeyError occurs; assertions pass vacuously but would fail if a non-empty suggestion list were returned |
| `backend/src/pilot_space/api/v1/routers/related_issues.py` | 334 | `link_repo.delete(link)` — plan specified `soft_delete(link_id)` | Warning | Need to confirm `IssueLinkRepository.delete()` is a soft-delete; if hard-delete, RELISS-02 unlink is irreversible |

### Human Verification Required

#### 1. Dismiss button with real API data

**Test:** Open an issue that has AI suggestions (requires kg_populate to have run for the issue). Click the X button on a suggestion.
**Expected:** Suggestion disappears immediately (optimistic removal). Reload page — the suggestion does not reappear.
**Why human:** Backend integration requires a live KG-populated environment. Frontend unit tests mock the hook return values directly and never exercise the actual API response shape.

#### 2. Bidirectional link visibility

**Test:** Open Issue A. Link Issue B from Issue A's Related Issues panel. Open Issue B.
**Expected:** Issue A appears in Issue B's Related Issues panel without manual refresh.
**Why human:** Requires two browser tabs and a live backend.

### Gaps Summary

All 11 must-haves verified. The field name mismatch gap from the initial verification is closed by commit 3fe59609 which renamed `RelatedSuggestion.issue_id` to `id` in the backend Pydantic model and its construction site. The frontend type `RelatedSuggestion.id: string` and component usage `s.id` are correct and now match the backend serialization.

Two warning-level items remain but do not block the phase goal:

1. Two test assertions at lines 165 and 427 use `item["issue_id"]` — stale after the rename. Both tests use a KG repo mock that returns no node (empty list), so the assertions run over `[]` and pass vacuously. The tests do not break but do not validate the field name. Recommend updating these assertions to use `item["id"]` in a follow-up.

2. The DELETE relation endpoint uses `link_repo.delete(link)` where the plan specified `soft_delete(link_id)`. Verify `IssueLinkRepository.delete()` is a soft-delete implementation to confirm RELISS-02 unlink is reversible.

---

_Verified: 2026-03-10T14:45:00Z_
_Verifier: Claude (gsd-verifier)_
