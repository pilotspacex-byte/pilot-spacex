# Product Requirements Document (PRD)

## Pilot Space MVP - AI-Augmented SDLC Platform

**Document Version**: 1.0 | **Status**: Approved | **Date**: 2026-01-23
**Product Owner**: Tin Dang | **Feature Branch**: `001-pilot-space-mvp`

---

## Executive Summary

Pilot Space is an AI-augmented Software Development Lifecycle (SDLC) platform that revolutionizes how teams capture, clarify, and track development work through a **Note-First** workflow. Unlike traditional issue trackers that force structure upfront, Pilot Space enables collaborative thinking where AI expert agents help extract explicit, actionable issues from implicit, rough ideas.

### The Problem

| Traditional Tools | Pain Point |
|-------------------|------------|
| Jira, Linear, Asana | Force upfront structure with rigid forms |
| Notion, Confluence | Good for notes but disconnected from execution |
| GitHub Issues | Developer-centric, missing PM workflows |

**Core Insight**: Teams spend significant time translating vague stakeholder requests into structured tickets. This translation loses context, creates miscommunication, and delays delivery.

### The Solution

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PILOT SPACE: NOTE-FIRST WORKFLOW                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. WRITE              2. CLARIFY              3. EXTRACT    4. EXECUTE │
│  ─────────             ──────────              ───────────   ────────── │
│  Rough ideas      →    AI asks probing    →   Root issues   → Trackable │
│  (implicit)            questions              surface         work items│
│                                               (explicit)                 │
│                                                                          │
│  "We need to          "What's driving        • Security vuln • Sprint   │
│   change auth"         this? Security?        • Compliance    • Board   │
│                        Compliance?"           • Migration     • Review  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Business Objectives

### Primary Objectives

| Objective | Success Metric | Target |
|-----------|----------------|--------|
| **O1**: Reduce requirement-to-ticket time | Time from initial request to structured issue | 50% reduction |
| **O2**: Improve issue quality | Issues reopened due to unclear requirements | <10% reopen rate |
| **O3**: Accelerate code review | PR review turnaround time | <30 min average |
| **O4**: Enable AI-assisted development | % of issues with AI-generated metadata | >80% coverage |

### Secondary Objectives

| Objective | Success Metric | Target |
|-----------|----------------|--------|
| **O5**: Reduce context switching | Time spent searching for related info | 40% reduction |
| **O6**: Improve sprint planning accuracy | Velocity variance sprint-over-sprint | <15% variance |
| **O7**: Support distributed teams | User satisfaction with async workflows | >4.0/5.0 rating |

---

## User Personas

### Primary Personas

#### 1. Alex - Tech Lead (Primary)
| Attribute | Detail |
|-----------|--------|
| **Role** | Tech Lead / Senior Developer |
| **Team Size** | 5-15 engineers |
| **Pain Points** | Context switching, unclear requirements, PR review bottleneck |
| **Goals** | Ship quality code faster, maintain architectural standards |
| **Key Features** | AI PR Review, AI Context, Task Decomposition |

#### 2. Sarah - Product Manager (Primary)
| Attribute | Detail |
|-----------|--------|
| **Role** | Product Manager |
| **Team Size** | Cross-functional team of 8-20 |
| **Pain Points** | Translating stakeholder requests, tracking dependencies |
| **Goals** | Clear requirements, predictable sprints, stakeholder alignment |
| **Key Features** | Note-First Canvas, Issue Extraction, Sprint Planning |

#### 3. Marcus - Full-Stack Developer (Primary)
| Attribute | Detail |
|-----------|--------|
| **Role** | Software Developer |
| **Team Size** | Works in 3-5 person feature teams |
| **Pain Points** | Understanding issue context, finding related code |
| **Goals** | Quick context acquisition, focused implementation |
| **Key Features** | AI Context, Ghost Text, GitHub Integration |

### Secondary Personas

#### 4. Dana - Engineering Manager
| Attribute | Detail |
|-----------|--------|
| **Role** | Engineering Manager |
| **Team Size** | 15-30 engineers across 3-5 teams |
| **Pain Points** | Cross-team visibility, resource allocation |
| **Goals** | Team productivity metrics, bottleneck identification |
| **Key Features** | Sprint Metrics, Knowledge Graph, Search |

---

## Feature Scope

### MVP Feature Summary

| Priority | User Story | Business Value |
|----------|------------|----------------|
| **P0** | US-01: Note-First Collaborative Writing | Core differentiator |
| **P1** | US-02: AI Issue Creation | Quality improvement |
| **P1** | US-03: AI PR Review | Code review acceleration |
| **P1** | US-04: Sprint Planning | Agile workflow support |
| **P2** | US-05: Modules/Epics | Feature organization |
| **P2** | US-06: Documentation Pages | Knowledge management |
| **P2** | US-07: Task Decomposition | Planning efficiency |
| **P2** | US-08: Architecture Diagrams | Technical documentation |
| **P2** | US-09: Slack Integration | Team communication |
| **P3** | US-10: Semantic Search | Information retrieval |
| **P3** | US-11: Workspace Settings | Configuration |
| **P3** | US-12: AI Context | Developer context |
| **P3** | US-13: Command Palette | Power user navigation |
| **P3** | US-14: Knowledge Graph | Relationship visualization |
| **P3** | US-15: Templates | Workflow standardization |
| **P3** | US-16: Sample Project | Onboarding |
| **P3** | US-17: Notifications | Awareness |
| **P3** | US-18: GitHub Integration | Development workflow |

### MVP Exclusions (DD-054)

| Feature | Reason | Phase |
|---------|--------|-------|
| Real-time collaboration | Complexity, DD-005 | Phase 2 |
| GitLab/Bitbucket | Focus on GitHub first | Phase 2 |
| Custom AI agents | Complexity, DD-008 | Phase 2+ |
| Advanced analytics | MVP simplicity | Phase 2 |
| Mobile apps | Web-first approach | Phase 3 |
| LDAP/Active Directory | Enterprise tier | Phase 3 |
| AI cost tracking per workspace | Users use provider dashboards | Phase 2 |

---

## Success Metrics

### North Star Metric

**Weekly Active Notes Created per User** - Measures adoption of Note-First workflow

### Leading Indicators

| Metric | Definition | Target | Measurement |
|--------|------------|--------|-------------|
| Note→Issue Conversion | % of notes that generate issues | >40% | Weekly |
| AI Suggestion Acceptance | % of AI suggestions accepted | >60% | Daily |
| Time-to-First-Issue | Time from note creation to first issue | <15 min | Weekly |
| Ghost Text Usage | % of typing sessions with ghost text | >30% | Daily |

### Lagging Indicators

| Metric | Definition | Target | Measurement |
|--------|------------|--------|-------------|
| User Retention | 30-day retention | >70% | Monthly |
| NPS Score | Net Promoter Score | >50 | Quarterly |
| Issue Reopen Rate | Issues reopened due to unclear requirements | <10% | Monthly |
| PR Merge Time | Time from PR open to merge | <4 hours | Weekly |

### Technical KPIs

| Metric | Target | SLA |
|--------|--------|-----|
| API Availability | 99.5% | Monthly |
| API Latency (p95) | <500ms reads, <1s writes | Daily |
| AI Response Time | <2s ghost text, <5min PR review | Per-request |
| Search Latency | <2s for 10K items | Daily |

---

## Technical Requirements Summary

### Platform Architecture

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Backend** | FastAPI + SQLAlchemy 2.0 (async) | Modern async, better AI workload (DD-001) |
| **Frontend** | Next.js 14 + React 18 + MobX | App router, server components |
| **Database** | PostgreSQL 16 + pgvector | RLS, vector search |
| **Platform** | Supabase (Auth, Storage, Queues) | Unified platform (DD-060) |
| **AI** | Claude Agent SDK + BYOK | Provider routing (DD-002) |
| **Cache** | Redis | AI response caching |
| **Search** | Meilisearch | Typo-tolerant search |

### AI Architecture

| Component | Provider | Use Case |
|-----------|----------|----------|
| Orchestration | Claude Agent SDK | Agentic tasks with MCP tools |
| Code Analysis | Claude (Opus/Sonnet) | PR review, task decomposition |
| Low Latency | Google Gemini Flash | Ghost text, annotations |
| Embeddings | OpenAI text-embedding-3-large | Semantic search, RAG |

### Infrastructure

| Aspect | Specification |
|--------|---------------|
| **Services** | 2-3 (Supabase + FastAPI + Next.js) |
| **Deployment** | Containerized, Supabase hosted |
| **Scale** | 5-100 members per workspace, 50K issues |
| **Availability** | 99.5% uptime, 4-hour RTO |

---

## Constraints & Dependencies

### Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| BYOK-only AI | Users must have API keys | Clear onboarding, key validation |
| No real-time collaboration | Last-write-wins conflicts | Conflict notification (DD-005) |
| GitHub + Slack only | No GitLab/Discord in MVP | Clear scope communication |
| WCAG 2.1 AA | Accessibility requirements | Design system compliance |

### Dependencies

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| Supabase Platform | Infrastructure | Vendor lock-in | Abstraction layer |
| Claude Agent SDK | AI | API changes | Version pinning |
| GitHub API | Integration | Rate limits | Queue with backoff |
| OpenAI Embeddings | AI | Cost | Batch processing |

---

## Timeline & Milestones

### MVP Development Phases

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **Phase 0** | Research & Design | 2 weeks | Technical research, architecture decisions |
| **Phase 1** | Foundation | 3 weeks | Auth, database, basic UI |
| **Phase 2** | Core Features | 4 weeks | Note canvas, issues, AI integration |
| **Phase 3** | Enhanced Features | 3 weeks | PR review, search, integrations |
| **Phase 4** | Polish & Launch | 2 weeks | Testing, documentation, deployment |

### Go-to-Market

| Milestone | Date | Criteria |
|-----------|------|----------|
| Alpha | TBD | Internal testing with 5-10 users |
| Beta | TBD + 4 weeks | Limited beta with 50-100 users |
| GA | TBD + 8 weeks | Public launch |

---

## Risks & Mitigations

### High Priority Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| AI cost exceeds user expectations | Medium | High | Clear BYOK cost documentation |
| Ghost text latency issues | Medium | High | Gemini Flash, response caching |
| User adoption of Note-First | Medium | Critical | Onboarding flow, sample project |
| Supabase outages | Low | High | Multi-region, graceful degradation |

### Medium Priority Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GitHub rate limits | Medium | Medium | Queue with exponential backoff |
| Complex TipTap implementation | Medium | Medium | Incremental feature delivery |
| MobX learning curve | Low | Medium | Team training, patterns documentation |

---

## Stakeholder Sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| Product Owner | Tin Dang | 2026-01-23 | Pending |
| Tech Lead | TBD | - | Pending |
| Engineering Manager | TBD | - | Pending |

---

## Appendix

### A. Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Feature Specification | [spec.md](../../spec.md) | 18 user stories, 123 FRs |
| Design Decisions | [DESIGN_DECISIONS.md](../../../../docs/DESIGN_DECISIONS.md) | 85 ADRs |
| Architecture Index | [docs/architect/README.md](../../../../docs/architect/README.md) | Architecture documentation |
| Constitution | [constitution.md](../../../../.specify/memory/constitution.md) | Project principles |

### B. Glossary

| Term | Definition |
|------|------------|
| **Note-First** | Workflow starting with collaborative notes, not forms |
| **Ghost Text** | AI-generated inline suggestions while typing |
| **BYOK** | Bring Your Own Key - users provide LLM API keys |
| **AI Context** | Aggregated context (code, docs, issues) for development |
| **Margin Annotations** | AI suggestions appearing in document margins |
| **Issue Extraction** | Converting note content to structured issues |

### C. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-23 | Claude | Initial PRD creation |
