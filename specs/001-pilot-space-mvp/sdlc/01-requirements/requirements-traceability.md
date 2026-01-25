# Requirements Traceability Matrix (RTM)

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This document provides bidirectional traceability between business objectives, user stories, functional requirements, design decisions, and test cases for the Pilot Space MVP.

---

## Traceability Hierarchy

```
Business Objectives (O1-O7)
    └── User Stories (US-01 to US-18)
        └── Functional Requirements (FR-001 to FR-123)
            └── Design Decisions (DD-001 to DD-085)
                └── Test Cases (TC-xxx)
                    └── Implementation (Components)
```

---

## Business Objective → User Story Mapping

| Objective | Description | User Stories |
|-----------|-------------|--------------|
| **O1** | Reduce requirement-to-ticket time | US-01, US-02 |
| **O2** | Improve issue quality | US-02, US-07, US-12 |
| **O3** | Accelerate code review | US-03, US-18 |
| **O4** | Enable AI-assisted development | US-01, US-02, US-03, US-07, US-08, US-10, US-12 |
| **O5** | Reduce context switching | US-10, US-12, US-13, US-14 |
| **O6** | Improve sprint planning accuracy | US-04, US-05 |
| **O7** | Support distributed teams | US-06, US-09, US-17 |

---

## User Story → Functional Requirements Mapping

### P0: Foundation

#### US-01: Note-First Collaborative Writing
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-001 | Note canvas as default home view | P0 | DD-013, DD-067 | Planned |
| FR-002 | Ghost text suggestions after 500ms pause | P0 | DD-067 | Planned |
| FR-003 | Tab accepts full suggestion, → accepts word | P0 | DD-067 | Planned |
| FR-004 | AI margin annotations with clarifying questions | P0 | DD-013 | Planned |
| FR-005 | Threaded AI discussions per block | P0 | DD-013 | Planned |
| FR-006 | Issue extraction with rainbow boxes | P0 | DD-013 | Planned |
| FR-007 | Bidirectional note-issue linking | P0 | DD-013 | Planned |
| FR-008 | AI categorization (🔴 Explicit, 🟡 Implicit, 🟢 Related) | P0 | DD-013 | Planned |
| FR-009 | Selection toolbar with AI actions | P1 | DD-013 | Planned |
| FR-010 | Virtualized rendering for 1000+ blocks | P0 | DD-065 | Planned |
| FR-011 | Auto-generated table of contents | P2 | DD-067 | Planned |
| FR-012 | Autosave with "Saved" indicator | P0 | - | Planned |
| FR-013 | Extended undo stack including AI changes | P1 | - | Planned |
| FR-014 | Note pinning to sidebar | P2 | - | Planned |
| FR-015 | Resizable margin panel (150-350px) | P2 | - | Planned |
| FR-016 | Note metadata (created, edited, author, word count) | P2 | - | Planned |
| FR-017 | Word boundary handling in ghost text streaming | P0 | DD-067 | Planned |

### P1: Core Workflow

#### US-02: AI Issue Creation
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-020 | AI suggests enhanced title within 2s | P1 | DD-002 | Planned |
| FR-021 | AI expands description with acceptance criteria | P1 | DD-002 | Planned |
| FR-022 | AI recommends labels, priority, assignees | P1 | DD-002, DD-048 | Planned |
| FR-023 | Duplicate detection with >70% similarity score | P1 | DD-070 | Planned |
| FR-024 | Accept/modify/reject AI suggestions independently | P1 | DD-003 | Planned |
| FR-025 | Confidence tags (Recommended, Default, Alternative) | P1 | DD-048 | Planned |
| FR-026 | Bulk AI actions on selected issues | P2 | - | Planned |
| FR-027 | AI context menu suggestions | P2 | - | Planned |

#### US-03: AI PR Review
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-030 | Auto-trigger AI review on PR open (webhook) | P1 | DD-006 | Planned |
| FR-031 | Inline PR comments with line references | P1 | DD-006 | Planned |
| FR-032 | Unified review (architecture, security, quality, performance) | P1 | DD-006 | Planned |
| FR-033 | Severity markers (Critical/Warning/Suggestion) | P1 | DD-006 | Planned |
| FR-034 | Rationale and documentation links per comment | P1 | DD-006 | Planned |
| FR-035 | Review completion within 5 minutes | P1 | DD-006 | Planned |

#### US-04: Sprint Planning
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-040 | Create cycle with start/end date and goals | P1 | - | Planned |
| FR-041 | Add issues to cycle, display on sprint board | P1 | - | Planned |
| FR-042 | Drag-and-drop issue state transitions | P1 | - | Planned |
| FR-043 | Cycle metrics (completion %, velocity, burndown) | P1 | - | Planned |
| FR-044 | Cycle rollover or return to backlog | P1 | - | Planned |

### P2: Enhanced Features

#### US-05: Modules/Epics
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-050 | Create module with name and description | P2 | - | Planned |
| FR-051 | Module progress reflects completed issues | P2 | - | Planned |
| FR-052 | Module list with issue count, progress, target date | P2 | - | Planned |
| FR-053 | Module detail view with linked issues | P2 | - | Planned |

#### US-06: Documentation Pages
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-055 | Rich text formatting (headers, lists, code, tables) | P2 | - | Planned |
| FR-056 | Autosave within 5 seconds | P2 | - | Planned |
| FR-057 | AI documentation generation from code/feature | P2 | DD-002 | Planned |
| FR-058 | Edit/approve/regenerate AI content | P2 | DD-003 | Planned |
| FR-059 | Last-saved version display (no co-editing) | P2 | DD-005 | Planned |

#### US-07: Task Decomposition
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-060 | AI generates subtasks from feature description | P2 | DD-002 | Planned |
| FR-061 | Subtasks include type (frontend/backend/QA) and estimates | P2 | - | Planned |
| FR-062 | AI identifies task dependencies | P2 | - | Planned |
| FR-063 | Accept all/modify/regenerate subtasks | P2 | DD-003 | Planned |
| FR-064 | Sub-issues linked to parent feature | P2 | - | Planned |

#### US-08: Architecture Diagrams
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-065 | AI generates Mermaid diagram from description | P2 | DD-012 | Planned |
| FR-066 | Visual diagram rendering in editor | P2 | DD-012 | Planned |
| FR-067 | Edit diagram code directly | P2 | DD-012 | Planned |
| FR-068 | Support sequence, class, flowchart, ERD, C4 types | P2 | DD-012 | Planned |
| FR-069 | Insert diagram into documentation page | P2 | - | Planned |

#### US-09: Slack Integration
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-070 | Post notification on issue creation within 30s | P2 | DD-004 | Planned |
| FR-071 | Notification shows title, assignee, priority, link | P2 | DD-004 | Planned |
| FR-072 | `/pilot create` command for issue creation | P2 | DD-004 | Planned |
| FR-073 | Link unfurl with rich preview | P2 | DD-004 | Planned |
| FR-074 | Configurable notification preferences | P2 | DD-004 | Planned |

### P3: Supporting Features

#### US-10: Semantic Search
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-075 | Search across issues, notes, pages | P3 | DD-070 | Planned |
| FR-076 | Typo-tolerant search | P3 | DD-070 | Planned |
| FR-077 | LLM-generated summaries in results | P3 | DD-070 | Planned |
| FR-078 | Document structure extraction on save | P3 | DD-070 | Planned |

#### US-11: Workspace Settings
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-080 | BYOK API key configuration | P3 | DD-002 | Planned |
| FR-081 | API key validation on save | P3 | DD-002 | Planned |
| FR-082 | Workspace member management | P3 | DD-007 | Planned |
| FR-083 | Role-based permissions | P3 | DD-007 | Planned |

#### US-12: AI Context
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-085 | Aggregate related docs and code for issues | P3 | DD-055 | Planned |
| FR-086 | AST analysis for code file discovery | P3 | DD-055 | Planned |
| FR-087 | Claude Code prompt generation | P3 | DD-055 | Planned |
| FR-088 | On-demand context refresh | P3 | DD-056 | Planned |

#### US-13: Command Palette
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-090 | Cmd+K opens command palette | P3 | - | Planned |
| FR-091 | Fuzzy search for commands | P3 | - | Planned |
| FR-092 | Context-aware AI suggestions | P3 | - | Planned |
| FR-093 | Recent items and navigation | P3 | - | Planned |

#### US-14: Knowledge Graph
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-095 | Visual graph of entity relationships | P3 | DD-068 | Planned |
| FR-096 | Sigma.js WebGL rendering | P3 | DD-068 | Planned |
| FR-097 | ForceAtlas2 auto-layout | P3 | DD-068 | Planned |
| FR-098 | Semantic relationship detection | P3 | DD-068 | Planned |

#### US-15: Templates
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-100 | AI-generated templates from patterns | P3 | - | Planned |
| FR-101 | Workspace-level template library | P3 | - | Planned |
| FR-102 | Smart placeholder detection | P3 | - | Planned |

#### US-16: Sample Project
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-105 | Pre-populated sample project on signup | P3 | - | Planned |
| FR-106 | Guided tour of features | P3 | - | Planned |
| FR-107 | Permanent delete (no soft delete) | P3 | - | Planned |

#### US-17: Notifications
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-110 | In-app notification center | P3 | - | Planned |
| FR-111 | AI-determined notification priority | P3 | - | Planned |
| FR-112 | Mark as read/unread | P3 | - | Planned |

#### US-18: GitHub Integration
| FR ID | Requirement | Priority | DD Reference | Status |
|-------|-------------|----------|--------------|--------|
| FR-115 | Link GitHub repository to project | P3 | DD-004 | Planned |
| FR-116 | Auto-link commits via issue ID pattern | P3 | DD-004 | Planned |
| FR-117 | PR webhook triggers AI review | P3 | DD-004, DD-006 | Planned |
| FR-118 | PR merge auto-transitions issue to Completed | P3 | DD-004 | Planned |
| FR-119 | Branch naming suggestions | P3 | - | Planned |

---

## Design Decision → Functional Requirement Mapping

| DD ID | Decision | Impacted FRs |
|-------|----------|--------------|
| DD-001 | FastAPI replaces Django | All backend FRs |
| DD-002 | BYOK + Claude SDK orchestration | FR-020-027, FR-030-035, FR-057, FR-060, FR-065, FR-080-081 |
| DD-003 | Critical-only AI approval | FR-024, FR-058, FR-063 |
| DD-004 | MVP: GitHub + Slack only | FR-070-074, FR-115-119 |
| DD-005 | No real-time collaboration | FR-059 |
| DD-006 | Unified AI PR Review | FR-030-035 |
| DD-007 | Basic RBAC | FR-082-083 |
| DD-012 | Multi-format diagrams | FR-065-069 |
| DD-013 | Note-First workflow | FR-001-017 |
| DD-048 | AI confidence tags | FR-025 |
| DD-055 | AI Context architecture | FR-085-088 |
| DD-056 | AI Context updates: on-demand | FR-088 |
| DD-065 | Frontend architecture patterns | FR-010 |
| DD-067 | Note Canvas implementation | FR-001-017 |
| DD-068 | Knowledge Graph architecture | FR-095-098 |
| DD-070 | Embedding & Search configuration | FR-023, FR-075-078 |

---

## Non-Functional Requirements

| NFR ID | Category | Requirement | Target | Related FRs |
|--------|----------|-------------|--------|-------------|
| NFR-001 | Performance | API read latency (p95) | <500ms | All API FRs |
| NFR-002 | Performance | API write latency (p95) | <1s | All API FRs |
| NFR-003 | Performance | Ghost text response | <2s | FR-002 |
| NFR-004 | Performance | PR review completion | <5min | FR-035 |
| NFR-005 | Performance | Search latency (10K items) | <2s | FR-075-078 |
| NFR-006 | Performance | Note canvas 60fps | 1000+ blocks | FR-010 |
| NFR-007 | Availability | Uptime SLA | 99.5% | All FRs |
| NFR-008 | Availability | Recovery time objective | 4 hours | All FRs |
| NFR-009 | Scalability | Concurrent users | 100 per workspace | All FRs |
| NFR-010 | Scalability | Issues per workspace | 50,000 | All issue FRs |
| NFR-011 | Security | Encryption at rest | AES-256 | All data FRs |
| NFR-012 | Security | Encryption in transit | TLS 1.3 | All API FRs |
| NFR-013 | Security | API rate limiting | 1000 req/min | All API FRs |
| NFR-014 | Security | AI rate limiting | 100 req/min | All AI FRs |
| NFR-015 | Accessibility | WCAG compliance | 2.1 AA | All UI FRs |
| NFR-016 | Accessibility | Keyboard navigation | Full support | All UI FRs |
| NFR-017 | Accessibility | Screen reader support | Full support | All UI FRs |

---

## Test Coverage Matrix

| User Story | Unit Tests | Integration Tests | E2E Tests | Status |
|------------|------------|-------------------|-----------|--------|
| US-01 | Planned | Planned | Planned | Not Started |
| US-02 | Planned | Planned | Planned | Not Started |
| US-03 | Planned | Planned | Planned | Not Started |
| US-04 | Planned | Planned | Planned | Not Started |
| US-05 | Planned | Planned | Planned | Not Started |
| US-06 | Planned | Planned | Planned | Not Started |
| US-07 | Planned | Planned | Planned | Not Started |
| US-08 | Planned | Planned | Planned | Not Started |
| US-09 | Planned | Planned | Planned | Not Started |
| US-10 | Planned | Planned | Planned | Not Started |
| US-11 | Planned | Planned | Planned | Not Started |
| US-12 | Planned | Planned | Planned | Not Started |
| US-13 | Planned | Planned | Planned | Not Started |
| US-14 | Planned | Planned | Planned | Not Started |
| US-15 | Planned | Planned | Planned | Not Started |
| US-16 | Planned | Planned | Planned | Not Started |
| US-17 | Planned | Planned | Planned | Not Started |
| US-18 | Planned | Planned | Planned | Not Started |

---

## Appendix: Full Requirement Cross-Reference

For complete functional requirement details, see:
- [spec.md](../../spec.md) - Full user story specifications
- [DESIGN_DECISIONS.md](../../../../docs/DESIGN_DECISIONS.md) - Architecture decision records
- [acceptance-criteria-catalog.md](./acceptance-criteria-catalog.md) - Testable acceptance criteria
