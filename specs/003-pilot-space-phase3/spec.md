# Feature Specification: Pilot Space Phase 3

**Feature Branch**: `003-pilot-space-phase3`
**Created**: 2026-01-23
**Status**: Draft
**Dependency**: Requires completion of `001-pilot-space-mvp` and `002-pilot-space-phase2`
**Scope**: P3 Features - Discovery & Onboarding

## Summary

Phase 3 completes the Pilot Space feature set with discovery and onboarding features: semantic search across workspace content, workspace configuration settings, and a sample project for new user onboarding.

**Prerequisites**:
- MVP (001-pilot-space-mvp) must be complete and stable
- Phase 2 (002-pilot-space-phase2) must be complete
- Embedding infrastructure from MVP operational

## User Stories (3 Total)

| Priority | User Story | Description |
|----------|------------|-------------|
| P3 | US-10 | Semantic Search |
| P3 | US-11 | Workspace Settings |
| P3 | US-16 | Sample Project |

---

## Clarifications (from MVP Sessions)

### US-10 - Semantic Search
- Q: What should search results include? → A: Extract document structure (tree-based for docs, AST for code) with LLM summaries at document/section level. Store relationships in knowledge graph for context-aware search.
- Q: When to extract structure? → A: On save via async background job. Results available within 30s.
- Q: What summary granularity? → A: Document + sections (H1/H2 headings). No paragraph-level for MVP.
- Q: How to store code AST? → A: Function/class signatures + docstrings. Top-level symbols in searchable format.
- Q: Which LLM for summaries? → A: Fast model (Claude Haiku 4.5) for bulk processing.

### US-11 - Workspace Settings
- Q: How to validate API keys? → A: Test API call to provider on save, show success/error before persisting.

### US-16 - Sample Project
- Q: How to handle sample project deletion? → A: Permanent delete (no soft delete, it's just sample data).

---

## User Scenarios & Testing

### User Story 10 - Search Across Workspace Content (Priority: P3)

A user searches for information across issues, pages, and documentation using natural language queries and receives contextually relevant results.

**Why this priority**: Semantic search enhances discoverability but basic filtering suffices for smaller workspaces.

**Independent Test**: Can be tested by indexing workspace content and executing search queries to verify relevant results are returned.

**Acceptance Scenarios**:

1. **Given** a user enters a search query, **When** results are returned, **Then** they see matching issues, pages, and comments ranked by relevance
2. **Given** search is performed, **When** results display, **Then** response time is under 2 seconds for workspaces under 10,000 items
3. **Given** natural language query, **When** searching, **Then** semantic matching finds relevant content even without exact keyword matches
4. **Given** search results, **When** clicking an item, **Then** the user navigates directly to that content

---

### User Story 11 - Configure Workspace and AI Settings (Priority: P3)

A workspace admin configures AI provider keys, project settings, integrations, and member permissions to customize the platform for their team.

**Why this priority**: Configuration is necessary but typically done once during setup.

**Independent Test**: Can be tested by modifying workspace settings, adding API keys, and verifying AI features activate correctly.

**Acceptance Scenarios**:

1. **Given** a user is workspace admin, **When** they access settings, **Then** they can configure AI provider API keys
2. **Given** API keys are added, **When** saved, **Then** keys are encrypted and AI features become available
3. **Given** GitHub integration section, **When** connecting, **Then** OAuth flow completes and repositories are listed
4. **Given** member management, **When** inviting users, **Then** admin can assign roles (Owner/Admin/Member/Guest)
5. **Given** project settings, **When** configuring, **Then** admin can set custom states, labels, and workflow preferences

---

### User Story 16 - Onboard with Sample Project (Priority: P3)

A new user explores Pilot Space capabilities through a pre-populated sample project that demonstrates realistic workflows and AI features.

**Why this priority**: Onboarding reduces time-to-value for new users but is not blocking for core functionality.

**Reference**: DD-045 (Sample Project Onboarding)

**Acceptance Scenarios**:

1. **Given** a new user signs up, **When** they complete workspace creation, **Then** a "Product Launch" sample project is automatically created
2. **Given** the sample project exists, **When** the user explores it, **Then** they find realistic notes, issues, cycles, and AI-generated threads
3. **Given** sample AI threads exist, **When** viewing them, **Then** the user sees example AI conversations demonstrating assistant capabilities
4. **Given** the user understands the product, **When** they want to start fresh, **Then** they can delete the sample project with one click
5. **Given** multiple workspaces exist, **When** creating a new workspace, **Then** the user can choose to skip sample project creation

---

## Functional Requirements

### Semantic Search (from MVP FR-030)

- **FR-030**: System MUST provide semantic search across workspace content (issues, pages, notes, comments)

**Implementation Notes**:
- Uses pgvector extension with HNSW indexing (from MVP infrastructure)
- Embeddings generated via OpenAI text-embedding-3-large (3072 dimensions)
- Hybrid search: vector similarity + full-text + metadata filters
- Background job extracts document structure and generates summaries

### Workspace Settings

- **FR-S01**: System MUST allow workspace admins to configure AI provider API keys (OpenAI, Anthropic, Google, Azure)
- **FR-S02**: System MUST encrypt API keys using AES-256-GCM with Supabase Vault
- **FR-S03**: System MUST validate API keys via test call before persisting
- **FR-S04**: System MUST allow workspace admins to manage member roles (Owner/Admin/Member/Guest)
- **FR-S05**: System MUST allow project-level custom states, labels, and workflow configuration

### Sample Project Onboarding (from MVP FR-087)

- **FR-087**: System MUST provide pre-populated sample project ("Product Launch") for new users with realistic notes, issues, and AI threads

**Implementation Notes**:
- Minimal seed: 5-10 issues, 3 notes, 1 cycle
- Hard delete (no soft delete) for sample data
- Option to skip during workspace creation

---

## Edge Cases

- What happens when AI provider API key is invalid or expired? System should gracefully disable AI features with clear error message and allow manual operations.
- What happens when semantic search returns no results? Fall back to full-text search and display "No semantic matches, showing keyword results."
- What happens when sample project deletion fails? Show error and allow retry; sample data is not critical.

---

## Related Documentation

- [MVP Specification](../001-pilot-space-mvp/spec.md) - Foundation features (P0 + P1)
- [Phase 2 Specification](../002-pilot-space-phase2/spec.md) - Enhanced Productivity features (P2)
- [Implementation Plan](./plan.md) - Phase 3 implementation breakdown
- [Design Decisions](../../docs/DESIGN_DECISIONS.md) - Architectural decision records
