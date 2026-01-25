# Tasks: Pilot Space Phase 3

**Source**: `/specs/003-pilot-space-phase3/`
**Required**: plan.md, spec.md (Phase 3), MVP and Phase 2 complete
**Prerequisite**: All MVP (P0+P1) tasks must be complete

**Generated**: 2026-01-23 | **User Stories**: 3 | **Total Tasks**: 26

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label |

---

## Phase 18: User Story 10 - Search Across Workspace Content (P3)

**Goal**: Enable semantic search with <2s response time
**Verify**: Search query returns relevant results from notes, issues, pages

### AI Agents (US10)

- [ ] T297 [US10] Create SemanticSearchAgent in `backend/src/pilot_space/ai/agents/semantic_search_agent.py`

### Services

- [ ] T298 [US10] Create SemanticSearchService in `backend/src/pilot_space/application/services/search/semantic_search_service.py`
- [ ] T299 [US10] Create HybridSearchService in `backend/src/pilot_space/application/services/search/hybrid_search_service.py` combining vector + full-text

### API Endpoints

- [ ] T300 [US10] Create search schemas in `backend/src/pilot_space/api/v1/schemas/search.py`
- [ ] T301 [US10] Add semantic search endpoint to AI router

### Frontend: Search

- [ ] T302 [US10] Create SearchResults component in `frontend/src/components/search/SearchResults.tsx`
- [ ] T303 [US10] Create SearchFilters component in `frontend/src/components/search/SearchFilters.tsx`

**Checkpoint**: US10 complete - Semantic search.

---

## Phase 19: User Story 11 - Configure Workspace and AI Settings (P3)

**Goal**: Enable workspace admin to configure AI provider keys and settings
**Verify**: Add API keys, validate, configure notification preferences

### Database Models

- [ ] T304 [US11] Create AIConfiguration SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/ai_configuration.py`
- [ ] T305 [US11] Create migration for AIConfiguration in `backend/alembic/versions/015_ai_configuration.py`

### Services

- [ ] T306 [US11] Create SaveAPIKeyService in `backend/src/pilot_space/application/services/settings/save_api_key_service.py` with AES-256 encryption
- [ ] T307 [US11] Create ValidateAPIKeyService in `backend/src/pilot_space/application/services/settings/validate_api_key_service.py`

### API Endpoints

- [ ] T308 [US11] Create settings schemas in `backend/src/pilot_space/api/v1/schemas/settings.py`
- [ ] T309 [US11] Create settings router in `backend/src/pilot_space/api/v1/routers/settings.py`
- [ ] T309a [US11] Document SAML SSO configuration in `docs/operations/saml-setup.md` covering Supabase Dashboard setup and IdP requirements

### Frontend: Settings

- [ ] T310 [US11] Create SettingsLayout component in `frontend/src/components/settings/SettingsLayout.tsx`
- [ ] T311 [US11] Create APIKeySettings component in `frontend/src/components/settings/APIKeySettings.tsx`
- [ ] T312 [US11] Create MemberManagement component in `frontend/src/components/settings/MemberManagement.tsx`
- [ ] T313 [US11] Create ProjectSettings component in `frontend/src/components/settings/ProjectSettings.tsx`

### Frontend: Pages

- [ ] T314 [US11] Create settings page in `frontend/src/app/(workspace)/settings/page.tsx`
- [ ] T315 [US11] Create AI settings page in `frontend/src/app/(workspace)/settings/ai/page.tsx`
- [ ] T316 [US11] Create members settings page in `frontend/src/app/(workspace)/settings/members/page.tsx`

**Checkpoint**: US11 complete - Workspace and AI settings.

---

## Phase 20: User Story 16 - Onboard with Sample Project (P3)

**Goal**: Enable new user onboarding with sample project
**Verify**: New signup creates sample project, can delete with one click

### Services

- [ ] T317 [US16] Create CreateSampleProjectService in `backend/src/pilot_space/application/services/onboarding/create_sample_project_service.py`
- [ ] T318 [US16] Create sample project data fixtures in `backend/src/pilot_space/infrastructure/fixtures/sample_project.py`

### API Endpoints

- [ ] T319 [US16] Create onboarding schemas in `backend/src/pilot_space/api/v1/schemas/onboarding.py`
- [ ] T320 [US16] Add onboarding endpoints to workspaces router

### Frontend: Onboarding

- [ ] T321 [US16] Create OnboardingFlow component in `frontend/src/components/onboarding/OnboardingFlow.tsx`
- [ ] T322 [US16] Create SampleProjectBanner component in `frontend/src/components/onboarding/SampleProjectBanner.tsx`

**Checkpoint**: US16 complete - Sample project onboarding.

---

## Dependencies

### User Story Dependencies

| Story | Depends On | Can Run After |
|-------|------------|---------------|
| US10 | MVP embeddings, Phase 2 knowledge graph | Phase 2 Complete |
| US11 | MVP infrastructure | MVP Complete |
| US16 | All core features | Phase 2 Complete |

### Parallel Opportunities

- US10 and US11 can run in parallel
- US16 should be implemented last (depends on all other features)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 26 |
| US10 (Semantic Search) | 7 |
| US11 (Workspace Settings) | 14 |
| US16 (Sample Project) | 6 |

---

## Related Documentation

- [MVP Tasks](../001-pilot-space-mvp/tasks.md) - Foundation and P0+P1 tasks
- [Phase 2 Tasks](../002-pilot-space-phase2/tasks.md) - P2 enhanced productivity tasks
- [Phase 3 Spec](./spec.md) - User story specifications
- [Phase 3 Plan](./plan.md) - Implementation breakdown
