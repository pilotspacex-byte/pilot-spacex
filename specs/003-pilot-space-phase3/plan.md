# Implementation Plan: Pilot Space Phase 3

**Branch**: `003-pilot-space-phase3` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Dependency**: Requires completion of `001-pilot-space-mvp` and `002-pilot-space-phase2`
**Scope**: P3 Features - Discovery & Onboarding (3 User Stories)

## Summary

Phase 3 completes the Pilot Space feature set with discovery and onboarding capabilities. This phase builds on the MVP and Phase 2 foundation to add semantic search, workspace configuration, and sample project onboarding.

**Prerequisites**:
- MVP (001-pilot-space-mvp) complete and stable
- Phase 2 (002-pilot-space-phase2) complete
- pgvector embedding infrastructure operational
- Supabase Vault configured for key encryption

## Technical Context

**Inherits from MVP/Phase 2**: Python 3.12+ (Backend), TypeScript 5.x (Frontend), Supabase platform
**Key Dependencies**:
- pgvector with HNSW indexing (from MVP)
- OpenAI text-embedding-3-large (embeddings)
- Claude Haiku 4.5 (summary generation)
- Supabase Vault (API key encryption)

## User Stories (3 Total)

| Priority | Story | Description | Dependencies |
|----------|-------|-------------|--------------|
| P3 | US-10 | Semantic Search | MVP embeddings, Phase 2 knowledge graph |
| P3 | US-11 | Workspace Settings | MVP infrastructure |
| P3 | US-16 | Sample Project | All core features |

---

## User Story Implementation Breakdown

### US-10: Semantic Search (P3)

**Spec Reference**: User Story 10 | **Priority**: P3 | **Acceptance Scenarios**: 4

**Clarifications Applied**:
```toon
US10clarify[5]{question,answer,impact}:
  What search results include?,Document structure + LLM summaries at document/section level,Multi-level extraction
  When to extract structure?,On save via async background job,Supabase Queue job
  What summary granularity?,Document + sections (H1/H2) No paragraph-level,Heading-based chunking
  How to store code AST?,Function/class signatures + docstrings,Top-level symbols
  Which LLM for summaries?,Fast model (Claude Haiku 4.5),Provider routing
```

**Data Model Entities**: Embedding, SearchIndex, DocumentSummary
**Key Components**: `SearchService`, `EmbeddingIndexer`, `SemanticSearchAPI`

**Implementation Tasks**:
1. Create DocumentSummary entity for section summaries
2. Build structure extraction service (headings, code symbols)
3. Implement summary generation with Claude Haiku 4.5
4. Create hybrid search endpoint (vector + full-text + filters)
5. Build search results ranking algorithm
6. Add background job for incremental indexing
7. Build SearchResults component with relevance highlighting
8. Implement fallback to keyword search when no semantic matches

---

### US-11: Workspace Settings (P3)

**Spec Reference**: User Story 11 | **Priority**: P3 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US11clarify[1]{question,answer,impact}:
  How to validate API keys?,Test API call to provider on save,Async validation error display
```

**Data Model Entities**: AIConfiguration, Workspace, WorkspaceMember
**Key Components**: `AISettingsForm.tsx`, `MemberManagement.tsx`, `ProjectSettings.tsx`

**Implementation Tasks**:
1. Create AIConfiguration management API
2. Implement API key encryption with Supabase Vault
3. Build API key validation service (test calls)
4. Create AISettingsForm component with provider selection
5. Build MemberManagement component with role assignment
6. Create ProjectSettings component for custom states/labels
7. Implement settings persistence with audit logging

---

### US-16: Sample Project (P3)

**Spec Reference**: User Story 16 | **Priority**: P3 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US16clarify[1]{question,answer,impact}:
  How to handle sample project deletion?,Permanent delete (no soft delete),Hard delete for sample data
```

**Data Model Entities**: Project (is_sample flag)
**Key Components**: Sample data seeder, onboarding flow, `SampleProjectBanner.tsx`

**Implementation Tasks**:
1. Create sample data fixtures (JSON/YAML)
2. Build sample project seeder service
3. Add is_sample flag to Project entity
4. Create onboarding flow with sample project option
5. Build SampleProjectBanner with delete action
6. Implement hard delete for sample projects
7. Add skip option during workspace creation

**Sample Data Content**:
- Project: "Product Launch" with description
- 5-10 Issues: Various states (backlog, in-progress, done)
- 3 Notes: Feature brainstorm, meeting notes, decision log
- 1 Cycle: "Sprint 1" with sample velocity
- Example AI threads demonstrating assistant capabilities

---

## Implementation Priority Order

Phase 3 features should be implemented in this order:

```toon
phase3order[3]{order,story,deps,deliverable}:
  1,US-10: Semantic Search,MVP embeddings,Content discovery
  2,US-11: Workspace Settings,Infrastructure,Admin configuration
  3,US-16: Sample Project,All core features,User onboarding
```

---

## Risk Assessment

```toon
phase3risks[3]{risk,impact,likelihood,mitigation}:
  Semantic search latency,Medium,Medium,Pre-compute embeddings async; cache common queries
  API key validation failures,Low,Medium,Clear error messages with retry option
  Sample project data quality,Low,Low,Curate realistic data that demonstrates features
```

---

## Success Criteria

Upon Phase 3 completion:
- Semantic search returns relevant results in <2s for 10k items
- API keys validated before save with clear success/error feedback
- New users can explore sample project within 30 seconds of signup
- All P0+P1+P2+P3 features operational (18 user stories total)

---

## Related Documentation

- [MVP Specification](../001-pilot-space-mvp/spec.md) - Foundation features (P0 + P1)
- [MVP Plan](../001-pilot-space-mvp/plan.md) - Foundation implementation plan
- [Phase 2 Specification](../002-pilot-space-phase2/spec.md) - Enhanced Productivity features
- [Phase 2 Plan](../002-pilot-space-phase2/plan.md) - Phase 2 implementation plan
- [Architecture Docs](../../docs/architect/README.md) - Technical architecture
