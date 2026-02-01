# Pilot Space Business Design Specification

**Version**: 2.0.0
**Date**: 2026-02-01
**Status**: Active
**References**: PROJECT_VISION.md, DESIGN_DECISIONS.md (DD-001 to DD-088), AI_CAPABILITIES.md, spec.md v3.2, feature-story-mapping.md

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Market Positioning Analysis](#2-market-positioning-analysis)
3. [Value Proposition Canvas](#3-value-proposition-canvas)
4. [Target Customer Definition](#4-target-customer-definition)
5. [User Journey Maps](#5-user-journey-maps)
6. [Business Model Design](#6-business-model-design)
7. [Feature-Business Mapping](#7-feature-business-mapping)
8. [Go-to-Market Strategy](#8-go-to-market-strategy)
9. [Success Metrics Framework](#9-success-metrics-framework)
10. [Business Rules Matrix](#10-business-rules-matrix)
11. [Competitive Moat Analysis](#11-competitive-moat-analysis)
12. [Integration Strategy](#12-integration-strategy)
13. [Risk Assessment & Mitigations](#13-risk-assessment--mitigations)
14. [Success Playbook](#14-success-playbook)
15. [Business Model Canvas](#15-business-model-canvas)
16. [Document Cross-References](#16-document-cross-references)

---

## 1. Executive Summary

### Strategic Position

Pilot Space creates a new category: **"AI Writing Partner for Software Development Teams"** -- attacking the fundamental assumption that structure should precede thinking in project management.

### Key Strategic Decisions

| Decision | Choice | Reference |
|----------|--------|-----------|
| **Category** | "AI Writing Partner for Dev Teams" | DD-013 |
| **Pricing Model** | Support Tiers Only (all features free) | DD-010 |
| **AI Orchestration** | 1 PilotSpaceAgent + 3 subagents + 8 skills + 6 MCP Note Tools | DD-086, DD-087, DD-088 |
| **GTM** | Developer community-first PLG | PS-001 |
| **North Star** | Weekly Active Writing Minutes (WAWM) | SC-010 |
| **MVP Scope** | 18 User Stories, 123 FRs | spec.md v3.2 |
| **BYOK Model** | Anthropic + OpenAI required, Gemini recommended | DD-002, DD-058 |

### AI Architecture (DD-086/087/088)

| Component | Count | Purpose |
|-----------|-------|---------|
| PilotSpaceAgent orchestrator | 1 | Multi-turn conversational agent via Claude Agent SDK |
| Subagents | 3 | PRReview, AIContext, DocGenerator (streaming SDK base) |
| Skills | 8 | One-shot structured tasks (extract-issues, improve-writing, etc.) |
| GhostText agent | 1 | Independent fast path, <2s latency |
| MCP Note Tools | 6 | update_note_block, enhance_text, summarize_note, extract_issues, create_issue_from_note, link_existing_issues |

### 90-Day Priority

Validate "Note-First" resonance with 50 teams through closed beta before building sales infrastructure.

---

## 2. Market Positioning Analysis

### 2.1 Competitive Landscape

```
                    HIGH STRUCTURE
                         |
              Jira ------+------ Height
              |          |          |
    ENTERPRISE -----------------------  STARTUP
              |          |          |
           Notion -------+------ Linear
                         |
                    LOW STRUCTURE

    Pilot Space enters: HIGH AI x LOW INITIAL STRUCTURE
```

### 2.2 Competitive Analysis

| Tool | Strengths | Weaknesses | Pilot Space Advantage |
|------|-----------|------------|----------------------|
| **Jira** | Enterprise adoption, extensive features | Complex, expensive, slow | Simpler UX, AI-native, open source |
| **Linear** | Fast, modern UX, developer-focused | Closed source, limited AI | Open source, deeper AI integration |
| **Plane** | Open source, modern, self-hosted | No AI features | AI-first architecture |
| **GitHub Projects** | Tight VCS integration | Limited PM features | Full PM + AI + multi-VCS |
| **Notion** | Flexible docs + tasks | Not built for SDLC | SDLC-specific AI assistance |

### 2.3 Unique Differentiators (Defensibility Analysis)

| Differentiator | Defensibility | Why Hard to Copy |
|----------------|---------------|------------------|
| **Note-First Workflow** | HIGH | Requires complete product rethink, not a feature add-on |
| **Embedded AI Partner** | MEDIUM | Others can add AI, but bolted-on feels different than native |
| **Ghost Text @ 500ms** | HIGH | Deep TipTap integration + context assembly is complex (DD-067) |
| **PilotSpaceAgent Orchestrator** | HIGH | 1 orchestrator + 3 subagents + 8 skills via MCP tools (DD-086) |
| **6 MCP Note Tools** | HIGH | Unified note manipulation layer vs. bolted-on AI (DD-088) |
| **Session Persistence** | HIGH | Multi-turn context builds relationship with AI (DD-086) |

*Reference: DD-013, DD-002, DD-086, DD-087, DD-088*

### 2.4 Category Creation

**Current Categories** (avoid):
- "Project Management" (Jira) -- too broad, commodity
- "Issue Tracker" (Linear) -- too narrow, feature war
- "Team Knowledge" (Notion) -- adjacent, not competitive

**Pilot Space Category**: **"AI Writing Partner for Development Teams"**

This reframes competition entirely:
- Not competing on fields, workflows, integrations
- Competing on *how developers think and create*
- Note Canvas as home, not dashboard (DD-013)

### 2.5 Positioning Statement

> For software development teams (5-100 engineers) frustrated with form-heavy ticketing systems, **Pilot Space is the AI writing partner** that lets you think first and structure later, unlike Linear or Jira which impose templates before you've figured out what to build, because our Note-First workflow with embedded AI turns rough thinking into refined issues automatically.

---

## 3. Value Proposition Canvas

### 3.1 Customer Jobs-to-Be-Done

| Type | Job | Pilot Space Feature |
|------|-----|---------------------|
| **Functional** | Plan sprints, track issues, review PRs | Cycles, Issues, AI PR Review |
| **Functional** | Get implementation context quickly | AI Context (US-12) |
| **Functional** | Refine rough ideas into actionable work | Note-First + extract_issues tool |
| **Emotional** | Feel in control of chaotic projects | Note-First clarity |
| **Emotional** | Reduce anxiety of missing things | AI duplicate detection (find-duplicates skill) |
| **Social** | Look organized to stakeholders | Module progress tracking |
| **Social** | Demonstrate team velocity | Sprint analytics |

### 3.2 Customer Pains & Relievers

| Pain | Severity | Pilot Space Solution | Reference |
|------|----------|---------------------|-----------|
| Form fatigue before thinking | HIGH | Start with blank note, AI suggests structure | DD-013 |
| Context switching | HIGH | Notes -> Issues in same canvas | FR-017, FR-018 |
| AI feels bolted-on | MEDIUM | Ghost text after 500ms, 6 MCP Note Tools | DD-067, DD-088 |
| Ticket graveyards | HIGH | AI flags dormant issues, suggests cleanup | AIContext subagent |
| Duplication | MEDIUM | 70%+ similarity detection via find-duplicates skill | FR-024, DD-087 |

### 3.3 Gain Creators

| Customer Gain | Pilot Space Feature | Metric |
|---------------|---------------------|--------|
| Immediate productivity | Empty canvas, not empty form | SC-001: <2 min issue creation |
| Contextual AI | RAG over project history, code, docs | SC-006: <2s search |
| Single tool | Note-First workflow end-to-end | NFR-014: 2-3 services |
| Fewer meetings | Async AI-enriched docs | SC-005: 30% planning reduction |
| AI trust | Human-in-the-loop approval model | DD-003: Critical-only approval |

---

## 4. Target Customer Definition

### 4.1 Ideal Customer Profile (ICP)

| Attribute | Specification | Rationale |
|-----------|---------------|-----------|
| **Team Size** | 5-100 engineers | Per workspace assumption (spec.md #8) |
| **Issue Volume** | Up to 50,000 issues | MVP scale target (spec.md #9) |
| **Stage** | Series A - C | Budget exists, decisions move fast |
| **Tech Stack** | GitHub-centric | Primary integration (DD-004) |
| **Culture** | Documentation-valued | Note-First requires writing culture |
| **Current Pain** | Jira refugees OR Notion+Linear splitters | Validated frustration |

### 4.2 Buyer Personas

**Sarah -- Engineering Manager (Primary Buyer)**

| Attribute | Detail |
|-----------|--------|
| **Title** | Engineering Manager, 5-15 direct reports |
| **Motivations** | Reduce meeting overhead, demonstrate velocity to leadership |
| **Objections** | "Another tool? My team just learned Linear" |
| **Success Criteria** | Sprint planning in 30% less time (SC-005) |
| **Key Features** | AI task decomposition (decompose-tasks skill), sprint analytics |

**Marcus -- Tech Lead (Champion)**

| Attribute | Detail |
|-----------|--------|
| **Title** | Staff Engineer / Tech Lead |
| **Motivations** | Spend time on architecture, not ticket grooming |
| **Objections** | "AI will suggest wrong things, create cleanup work" |
| **Success Criteria** | AI PR Review saves 50% review time (SC-003: <5 min) |
| **Key Features** | PRReview subagent (DD-006), AIContext subagent (US-12) |

**Elena -- Product Manager (Stakeholder)**

| Attribute | Detail |
|-----------|--------|
| **Title** | Product Manager / Technical PM |
| **Motivations** | Visibility into team progress, async planning |
| **Objections** | "Can I still do sprint planning my way?" |
| **Success Criteria** | Planning time reduced 30%, velocity visible |
| **Key Features** | Cycles, modules, summarize skill, extract-issues skill |

**Dev -- Junior Developer (End User)**

| Attribute | Detail |
|-----------|--------|
| **Title** | Software Engineer, 1-3 years experience |
| **Motivations** | Get implementation guidance, understand codebase |
| **Objections** | "Is the AI actually helpful or just noise?" |
| **Success Criteria** | AI Context provides useful guidance on every issue |
| **Key Features** | AIContext subagent, Claude Code prompts, ghost text |

### 4.3 Anti-Personas (Do Not Target)

| Profile | Why Exclude |
|---------|-------------|
| **Enterprise 500+** | Procurement cycles, legacy integration (Phase 3) |
| **Solo developers** | No collaboration value, free tier abuse |
| **Non-technical teams** | Won't value GitHub integration (DD-004) |
| **Highly regulated** | BYOK + cloud AI = compliance complexity |

---

## 5. User Journey Maps

### 5.1 Sarah (Architect) -- Architecture Decision Flow

| Step | Action | Feature Used | AI Involvement |
|------|--------|-------------|----------------|
| 1 | Opens Pilot Space | Notes home (DD-013) | None |
| 2 | Creates note "API Gateway Decision" | Note canvas | AI greeting + templates (DD-016) |
| 3 | Writes analysis of options | TipTap editor | Ghost text suggests completions (DD-067) |
| 4 | Reviews margin annotations | MarginAnnotationPanel | AI suggests considerations she missed |
| 5 | Shares note, team adds threaded comments | Note collaboration | None (async refinement) |
| 6 | Requests issue extraction | extract_issues MCP tool | AI identifies 3 action items from note |
| 7 | Reviews and approves extracted issues | Issue approval flow | Human-in-the-loop (DD-003) |
| 8 | Opens issue, generates AI Context | AIContext subagent (US-12) | Related docs, code refs, Claude Code prompts |
| 9 | Team submits PR | GitHub integration (US-18) | Auto-linked via commit message |
| 10 | Reviews PR with AI assistance | PRReview subagent (DD-006) | Architecture + security + quality review |

**Outcome**: Architecture decision captured, issues tracked, PR reviewed -- all from a single note.

### 5.2 Marcus (Tech Lead) -- Issue Resolution Flow

| Step | Action | Feature Used | AI Involvement |
|------|--------|-------------|----------------|
| 1 | Opens issue PS-42 "Optimize API latency" | Issue detail view | None |
| 2 | Generates AI Context | AIContext subagent | Related notes, code refs, similar issues |
| 3 | Copies Claude Code prompts | ClaudeCodePromptPanel | Pre-formatted implementation prompts |
| 4 | Decomposes into subtasks | decompose-tasks skill (DD-087) | AI suggests 4 subtasks with estimates |
| 5 | Assigns subtasks to team | Issue management | recommend-assignee skill suggests assignees |
| 6 | Reviews incoming PR | PRReview subagent | Severity-tagged inline comments |
| 7 | Checks sprint burndown | CycleBoard (US-04) | None |
| 8 | PR merged, issue auto-completes | GitHub integration (DD-084) | Auto state transition |

**Outcome**: Complex issue decomposed, delegated, reviewed, and completed with AI assistance at every step.

### 5.3 Elena (PM) -- Sprint Planning Flow

| Step | Action | Feature Used | AI Involvement |
|------|--------|-------------|----------------|
| 1 | Opens note "Sprint 12 Planning" | Note canvas | None |
| 2 | Writes sprint goals and priorities | TipTap editor | Ghost text + improve-writing skill |
| 3 | Extracts issues from planning note | extract_issues MCP tool | AI identifies 8 action items |
| 4 | Moves issues to cycle board | CycleBoard (US-04) | None |
| 5 | Reviews velocity and capacity | VelocityChart | Historical data from last 6 cycles |
| 6 | Generates sprint summary | summarize skill | AI condenses goals for stakeholder update |
| 7 | Shares via Slack | Slack integration (US-09) | Formatted rich block message |

**Outcome**: Sprint planned in 30% less time, stakeholders informed asynchronously.

### 5.4 Dev (Junior) -- Implementation Flow

| Step | Action | Feature Used | AI Involvement |
|------|--------|-------------|----------------|
| 1 | Assigned issue PS-99 "Fix login timeout" | Notification (US-17) | AI-prioritized notification |
| 2 | Opens issue, reads AI Context | AIContext subagent | Related code, docs, similar resolved issues |
| 3 | Copies Claude Code prompts | ClaudeCodePromptPanel | Implementation guidance |
| 4 | Reads linked notes for background | Note -> Issue links | None |
| 5 | Submits PR | GitHub integration | Auto-linked to PS-99 |
| 6 | AI reviews PR automatically | PRReview subagent | Inline feedback with fix suggestions |
| 7 | Addresses review comments, PR merged | GitHub integration | Issue auto-transitions to Completed |

**Outcome**: Junior developer gets senior-level guidance through AI Context, reduces ramp-up time.

---

## 6. Business Model Design

### 6.1 Pricing Philosophy: Support Tiers Only

**Critical Decision (DD-010)**: All features are 100% free. Paid tiers are for **support and SLA only**.

### 6.2 Pricing Tiers

| Tier | Price | Support Level | SLA |
|------|-------|---------------|-----|
| **Community** | Free | GitHub issues, community forums | Best effort |
| **Pro Support** | $10/seat/month | Email support | 48h response |
| **Business Support** | $18/seat/month | Priority support, dedicated Slack | 24h response |
| **Enterprise** | Custom | Dedicated support, consulting | Custom SLA |

### 6.3 BYOK Model Economics

**API Key Requirements (DD-002, DD-058)**:

| Provider | Status | Use Case | Cost per 1M tokens |
|----------|--------|----------|---------------------|
| **Anthropic** | Required | PilotSpaceAgent orchestration, subagents, skills | Opus: $15 in / $75 out; Sonnet: $3/$15; Haiku: $0.25/$1.25 |
| **OpenAI** | Required | Embeddings (3072-dim text-embedding-3-large) | $0.13/1M tokens |
| **Google Gemini** | Recommended | Ghost text, margin annotations (low latency) | Flash: $0.10/1M; Pro: $1.25/1M |

**Estimated AI Cost Per User Per Month (BYOK)**:

| Usage Tier | Monthly AI Cost | Breakdown |
|------------|-----------------|-----------|
| **Light** (5 notes/week, 10 ghost texts/day) | ~$2 | Haiku for skills, Flash for ghost text |
| **Medium** (15 notes/week, 30 ghost texts/day, 2 PR reviews) | ~$8 | Mix of Sonnet + Haiku + Flash |
| **Heavy** (30+ notes/week, 50 ghost texts/day, 5 PR reviews, AIContext daily) | ~$20 | Sonnet-heavy, multiple subagent calls |

**Infrastructure Cost Scaling**:

| Users | Infrastructure/mo | Support/mo | Total Operational/mo | Break-Even MRR |
|-------|-------------------|-----------|----------------------|----------------|
| 100 | $500 | $0 | $500 | 50 paid seats |
| 1,000 | $2,000 | $1,500 | $3,500 | 250 paid seats |
| 5,000 | $6,000 | $4,500 | $10,500 | 750 paid seats |
| 10,000 | $10,000 | $7,500 | $17,500 | 1,250 paid seats |

**BYOK Advantage**: Gross margins remain 80%+ regardless of AI usage intensity. Zero AI API cost exposure.

### 6.4 Revenue Projections (24 Months)

| Quarter | Users | Paid Support | MRR | ARR |
|---------|-------|--------------|-----|-----|
| Q1 (Beta) | 200 | 0 | $0 | $0 |
| Q2 | 500 | 50 | $700 | $8K |
| Q3 | 1,200 | 180 | $2,520 | $30K |
| Q4 | 2,500 | 375 | $5,250 | $63K |
| Q5 | 4,500 | 675 | $9,450 | $113K |
| Q6 | 7,500 | 1,125 | $15,750 | $189K |
| Q7 | 12,000 | 1,800 | $25,200 | $302K |
| Q8 | 18,000 | 2,700 | $37,800 | $454K |

*Assumptions: 5% MoM growth, 15% free-to-paid conversion, $14 blended ARPU*

---

## 7. Feature-Business Mapping

| Feature | Business Value | Metric Impact | Revenue Impact | User Story |
|---------|---------------|---------------|----------------|------------|
| **Note-First Canvas** | Category differentiator | WAWM +40% | Activation +25% | US-01 |
| **Ghost Text** | Productivity booster | Time saved 30% | Retention +15% | US-01 |
| **Issue Extraction** (MCP tool) | Workflow automation | Issues/user +60% | Activation +20% | US-01, US-02 |
| **AI PR Review** (subagent) | Quality assurance | Review time -50% | Expansion +10% | US-03 |
| **AI Context** (subagent) | Implementation velocity | Task completion +35% | Retention +20% | US-12 |
| **Sprint Planning** | Team coordination | Planning time -30% | Team adoption +25% | US-04 |
| **Human-in-the-Loop** | Trust building | AI acceptance +40% | NPS +15 | DD-003 |
| **BYOK Model** | Cost transparency | Margin 80%+ | Enterprise appeal | DD-002 |
| **MCP Note Tools** (6 tools) | Extensibility | Developer adoption +30% | Platform effect | DD-088 |
| **Skill System** (8 skills) | AI depth | Feature coverage +60% | Differentiation | DD-087 |
| **Session Persistence** | Conversation quality | Multi-turn satisfaction +45% | Retention +10% | DD-086 |
| **Knowledge Graph** | Discovery value | Cross-reference usage +50% | Stickiness +20% | US-14 |
| **GitHub Integration** | Developer workflow center | PR automation 95% | Activation +15% | US-18 |
| **Slack Integration** | Team bridge | Notification delivery 99% | Team adoption +10% | US-09 |

---

## 8. Go-to-Market Strategy

### 8.1 Launch Phases

| Phase | Duration | Focus | Success Metric |
|-------|----------|-------|----------------|
| **Private Alpha** | 8 weeks | 10 friendly teams, intense feedback | NPS > 30 |
| **Closed Beta** | 12 weeks | 200 waitlist users, iterate on activation | 25% activation rate |
| **Public Beta** | Ongoing | Open signups, PLG motion | 500 WAU |
| **GA** | Q2 2026 | Support tiers enforced | $5K MRR |

### 8.2 Acquisition Channels

| Channel | CAC Estimate | Priority | Rationale |
|---------|--------------|----------|-----------|
| **Developer content** | $50 | P0 | Builds credibility, evergreen |
| **Twitter/X community** | $30 | P0 | Quick feedback, viral potential |
| **Hacker News launch** | $0 | P0 | High-signal audience |
| **GitHub Marketplace** | $100 | P1 | Integration discovery |
| **Referral program** | $75 | P1 | "Give a month, get a month" |
| **Paid search** | $150 | P2 | Post-PMF scale only |

### 8.3 Activation Metrics

**Aha Moment**: User accepts 3+ ghost text suggestions in first note.

**Activation Criteria** (must hit all within 14 days):
1. Create first note with >500 characters
2. Accept at least 1 ghost text suggestion (DD-067)
3. Create first issue from note (extract_issues or create_issue_from_note MCP tool)
4. Invite 1 teammate

### 8.4 Content Strategy Pillars

| Pillar | Content Types | Cadence |
|--------|---------------|---------|
| **"Note-First" Philosophy** | Blog posts, manifestos | Weekly |
| **AI in Dev Workflow** | Tutorials, demos of skills + subagents | Bi-weekly |
| **Team Stories** | Case studies | Monthly |
| **Technical Deep Dives** | Architecture, MCP tools, OSS | Monthly |

---

## 9. Success Metrics Framework

### 9.1 North Star Metric

**Weekly Active Writing Minutes (WAWM)**

*Why this metric*:
- Directly measures engagement with Note-First (DD-013)
- Leading indicator of retention
- Hard to game without delivering value
- Aligns with 70% AI feature adoption target (SC-010)

### 9.2 Metrics Hierarchy

```
                    WAWM (North Star)
                         |
        +----------------+----------------+
        v                v                v
  Notes Created    Ghost Accepts    Issues Extracted
        |                |                |
        v                v                v
   Signups <---- Activations ----> Team Invites
```

### 9.3 Success Criteria (from spec.md)

| Criterion | Target | Reference |
|-----------|--------|-----------|
| Issue creation time | <2 minutes | SC-001 |
| AI task decomposition | <60 seconds | SC-002 |
| AI PR Review completion | <5 minutes | SC-003 |
| AI label acceptance rate | 80% | SC-004 |
| Sprint planning reduction | 30% | SC-005 |
| Search response time | <2 seconds | SC-006 |
| Page load time | <3 seconds | SC-007 |
| Concurrent users | 100/workspace | SC-008 |
| Issue state change latency | <1 second | SC-009 |
| AI feature weekly usage | 70% of members | SC-010 |
| User satisfaction | 4.0/5.0 | SC-011 |
| PR linking success | 95% | SC-012 |
| Slack notification delivery | 99% | SC-013 |
| Zero data loss (normal ops) | 100% | SC-014 |
| Soft-delete recovery window | 30 days | SC-015 |
| Activity log coverage | 100% | SC-016 |
| RLS enforcement | 100% | SC-019 |

### 9.4 Guardrail Metrics

| Metric | Threshold | Alert If |
|--------|-----------|----------|
| Note quality (avg words) | >200 | <100 = junk notes |
| Ghost text dismissal rate | <60% | >80% = bad suggestions |
| AI label rejection rate | <20% | >40% = poor model (SC-004 inverse) |
| Issue completion rate | >40% | <20% = orphan issues |
| Churn rate | <5%/month | >8% = retention crisis |
| Subagent latency (p95) | <10s | >15s = orchestration bottleneck |
| MCP tool error rate | <2% | >5% = tool reliability issue |

---

## 10. Business Rules Matrix

### 10.1 Issue State Transitions (DD-062)

| From | To | Allowed | Trigger |
|------|----|----|---------|
| unstarted | started | Yes | Manual or PR opened |
| started | completed | Yes | Manual or PR merged (DD-084) |
| completed | started | Yes | Reopen |
| any | cancelled | Yes | Manual |
| cancelled | any | No | Terminal state |
| unstarted | completed | No | Cannot skip started |

### 10.2 AI Approval Thresholds (DD-003)

| Action | Behavior | Configurable | Approval Level |
|--------|----------|--------------|----------------|
| Suggest labels/priority | Auto-apply in UI | Yes | None |
| Auto-transition on PR | Auto + notify | Yes | None |
| Ghost text suggestions | Auto-display | No | None |
| Margin annotations | Auto-display | Yes | None |
| Create sub-issues | Require approval | Yes | User confirmation |
| Extract issues from note | Require approval | No | User confirmation |
| Delete/archive | **Always approval** | No | User + admin |

### 10.3 BYOK Requirements (DD-002, DD-058)

| Provider | Status | If Missing |
|----------|--------|------------|
| Anthropic | **Required** | Core AI features disabled (no subagents, no skills) |
| OpenAI | **Required** | Semantic search disabled, no embeddings |
| Google Gemini | **Recommended** | Ghost text falls back to Haiku (slower) |
| Azure OpenAI | Optional | Enterprise data residency alternative |

### 10.4 Workspace Constraints

| Rule | Limit | Reference |
|------|-------|-----------|
| Max workspace size | 50,000 issues | spec.md Assumption #9 |
| Max note size | 5,000+ blocks (virtual scroll) | DD-046 |
| Rate limit (standard) | 1,000 req/min per workspace | DD-059 |
| Rate limit (AI endpoints) | 100 req/min per workspace | DD-059 |
| Soft deletion recovery | 30 days | DD-062, SC-015 |
| Session TTL | 30 minutes (Redis hot + PostgreSQL persistent) | DD-086 |
| Token budget per session | 8,000 tokens | DD-086 |
| Ghost text max | 1-2 sentences, ~50 tokens | DD-067 |
| Ghost text trigger | 500ms typing pause | DD-067 |
| Word boundary buffering | Buffer until whitespace/punctuation | DD-067 |
| Autosave debounce | 1-2 seconds | DD-049 |
| Embedding regeneration | >20% content diff triggers | DD-070 |

### 10.5 Security & Data Rules

| Rule | Enforcement | Reference |
|------|-------------|-----------|
| RLS workspace isolation | 100% of queries through RLS policies | DD-061, SC-019 |
| API key encryption | AES-256-GCM via Supabase Vault | DD-061 |
| Token rotation | Access 1h + Refresh 7d, rotate on refresh | DD-061 |
| AI cost tracking | Per-provider, per-agent, per-user | DD-086 |
| Activity logging | 100% of state changes logged | SC-016 |

---

## 11. Competitive Moat Analysis

### 11.1 Defensibility Layers

| Layer | Moat Type | Depth | Time to Copy |
|-------|-----------|-------|-------------|
| **Note-First philosophy** | Product architecture | Deep | 12-18 months (requires full product rethink) |
| **1 orchestrator + 3 subagents + 8 skills** | AI depth | Deep | 6-12 months (vs "add AI button" approach) |
| **MCP Tool ecosystem** (6 note tools + DB/GitHub/Search) | Developer platform | Medium | 6-9 months |
| **Session persistence** | Relationship AI | Medium | 3-6 months |
| **Knowledge graph** | Cumulative value | Deep | Grows with usage, never replicable |
| **BYOK model** | Trust architecture | Medium | 3 months to copy, hard to retrofit |

### 11.2 Why Competitors Cannot Easily Respond

**Linear adding AI**: Would need to rebuild around notes, not issues. Their data model is issue-first. Adding ghost text to an issue form is not the same as AI-augmented brainstorming.

**Notion adding SDLC**: Notion is general-purpose. Adding PR review, commit linking, sprint velocity requires deep GitHub integration and SDLC-specific AI training. Their AI is document-generic, not code-aware.

**Jira adding AI**: Atlassian Intelligence exists but is bolted onto a 20-year-old architecture. Note-First requires starting from scratch, which Atlassian cannot do without abandoning their installed base.

**New entrants**: Must build all three layers simultaneously (editor + PM + AI). Building any two is table stakes. The third is the moat.

### 11.3 Cumulative Advantages

| Advantage | Mechanism | Growth Rate |
|-----------|-----------|-------------|
| Knowledge graph density | Every note, issue, PR adds edges | Exponential with team size |
| AI suggestion quality | User feedback loop (accept/dismiss) | Improves per workspace |
| Template library | System + user + AI-generated | Network effect across workspaces |
| MCP tool ecosystem | Third-party tools possible (Phase 3) | Platform effect |

---

## 12. Integration Strategy

### 12.1 MVP Integrations (DD-004)

| Integration | Business Case | User Stories | Revenue Impact |
|-------------|---------------|-------------|----------------|
| **GitHub** | Developer workflow center: commit linking, PR review automation, branch suggestions | US-03, US-18 | Activation +15%, core differentiator |
| **Slack** | Team communication bridge: async notifications, `/pilot` commands, rich messages | US-09, US-17 | Team adoption +10%, reduces context switching |

### 12.2 Phase 2 Integrations

| Integration | Business Case | Target Users |
|-------------|---------------|-------------|
| **GitLab** | Enterprise alternative VCS, expands TAM by 30% | Enterprise teams using GitLab |
| **Discord** | Community-first teams, OSS projects | Startup teams, open source |

### 12.3 Phase 3 Integrations

| Integration | Business Case | Target Users |
|-------------|---------------|-------------|
| **VS Code extension** | IDE integration for AI Context, in-editor issue views | Individual developers |
| **CI/CD display** | Build status on issues, deployment tracking | DevOps-focused teams |

### 12.4 Integration Architecture (DD-088)

All integrations use MCP tool registry pattern:
- GitHub tools: `get_pr_diff`, `get_pr_files`, `link_commit_to_issue`
- Database tools: RLS-enforced CRUD operations
- Search tools: `semantic_search`, `search_codebase`

---

## 13. Risk Assessment & Mitigations

### 13.1 Risk Matrix

| Risk | Probability | Impact | Severity | Mitigation |
|------|-------------|--------|----------|------------|
| **"Note-First" doesn't resonate** | Medium | Critical | HIGH | Templates as scaffolding (DD-033) |
| **AI suggestions generic/wrong** | Medium | High | HIGH | Confidence gating >= 80% (DD-048) |
| **Linear/Notion add AI features** | High | Medium | MEDIUM | Philosophy moat + AI depth |
| **BYOK friction kills activation** | Medium | Medium | MEDIUM | Clear onboarding, key validation |
| **Claude Agent SDK dependency** | Medium | High | HIGH | Abstraction layer, fallback paths |
| **MCP tool complexity vs adoption** | Medium | Medium | MEDIUM | Progressive disclosure, defaults |
| **Session persistence reliability** | Low | High | MEDIUM | Redis + PostgreSQL dual-write |
| **Subagent orchestration latency** | Medium | Medium | MEDIUM | Streaming SSE, token budget (DD-086) |
| **Cost tracking accuracy for BYOK** | Medium | Medium | MEDIUM | Per-call metering, user dashboard |

### 13.2 Risk: Claude Agent SDK Dependency (NEW)

**Scenario**: Anthropic changes SDK terms, pricing, or breaks compatibility.

**Early Warning Signs**:
- SDK deprecation notices
- Pricing increases >50%
- Community reports of instability

**Mitigation Strategy**:
1. **Abstraction layer**: PilotSpaceAgent wraps SDK, not direct coupling
2. **Skill system**: Skills are SDK-independent (structured input/output)
3. **Fallback**: Skills can fall back to direct Anthropic API calls
4. **Multi-provider**: Gemini handles latency-critical paths independently

### 13.3 Risk: Note-First Doesn't Resonate

**Early Warning Signs**: <10% create second note, users bypass notes for issue creation

**Mitigation**:
1. Templates as scaffolding (DD-033): System + User + AI templates
2. Guided onboarding (DD-045): Sample project with realistic content
3. AI greeting (DD-016): Prompt input + recommended templates
4. **Pivot path**: If 60-day data shows <20% Note-First adoption, add "Quick Issue" as co-equal entry point

### 13.4 Risk: AI Suggestions Feel Generic

**Early Warning Signs**: Ghost text accept rate <10%, users disable AI features

**Mitigation**:
1. Progressive context: Current block + 3 previous + sections + user history (DD-067)
2. Confidence gating (DD-048): Only show "Recommended" tag for >= 80%
3. Feedback loop: Accept/dismiss signals improve per workspace
4. **Fallback**: If accept rate <15% after 30 days, default AI off, make opt-in

### 13.5 Risk: Incumbents Add AI Features

**Mitigation**: 1 orchestrator + 3 subagents + 8 skills depth vs. generic "AI assistant". Philosophy moat (Note-First) requires complete product rethink, not feature addition.

---

## 14. Success Playbook

### Days 1-30: Validate Note-First Hypothesis

| Week | Actions | Success Criteria | Deliverables |
|------|---------|------------------|-------------|
| 1-2 | Interview 15 teams using Linear/Notion split | 10+ express Note-First resonance | Interview synthesis doc |
| 2-3 | Build landing page with Note-First positioning | 500 waitlist signups | Landing page live |
| 3-4 | Create 5-min demo: note -> ghost text -> extract issue -> PR review | 1,000 views, 20% completion | Demo video published |
| 4 | Run 3 live demos with waitlist leads | 2+ say "I'd pay for support" | Feedback captured |

### Days 31-60: Alpha with 10 Teams

| Week | Actions | Success Criteria | Deliverables |
|------|---------|------------------|-------------|
| 5-6 | Onboard 10 alpha teams (hand-selected) | 8+ complete BYOK setup | Alpha cohort active |
| 6-7 | Daily feedback calls, rapid iteration | Ship 20+ improvements | Feedback log |
| 7-8 | Measure ghost text accept rate | >15% accept rate | Quality baseline |
| 8 | Measure MCP tool usage (extract_issues, enhance_text) | >30% use Note Tools weekly | Tool adoption metrics |

### Days 61-90: Beta Launch (200 Users)

| Week | Actions | Success Criteria | Deliverables |
|------|---------|------------------|-------------|
| 9-10 | Implement top 5 alpha feedback items | Alpha NPS > 30 | Feature improvements |
| 10-11 | Build referral mechanics | Technical implementation complete | Referral system live |
| 11-12 | Prepare launch assets (blog, changelog, HN draft) | Content reviewed and ready | Launch content |
| 12 | Soft launch to 200 beta users | 100 activated in first week | Beta cohort active |

### Days 91-120: Public Beta, Measure WAWM

| Week | Actions | Success Criteria | Deliverables |
|------|---------|------------------|-------------|
| 13-14 | Open signups, HN launch | 1,000 signups in first week | Public beta live |
| 14-16 | Measure WAWM baseline | >30 min/user/week average | WAWM dashboard |
| 15-16 | Iterate on activation funnel | 25% activation rate | Funnel optimization |
| 16 | Measure AI skill adoption | >50% use 3+ skills | Skill usage report |

### Days 121-150: Support Tier Launch

| Week | Actions | Success Criteria | Deliverables |
|------|---------|------------------|-------------|
| 17-18 | Launch Pro Support tier | 50 paid seats | Billing system live |
| 19-20 | Build case studies from beta teams | 3 published case studies | Marketing content |
| 20 | Launch Business Support tier | 10 business accounts | Enterprise pipeline |

### Days 151-180: First $5K MRR Milestone

| Week | Actions | Success Criteria | Deliverables |
|------|---------|------------------|-------------|
| 21-22 | Scale community (Discord, Office Hours) | 500 Discord members | Community active |
| 23-24 | Double down on highest-converting channel | $5K MRR reached | Revenue milestone |
| 24 | Plan Phase 2 features based on usage data | Phase 2 roadmap published | Product roadmap |

---

## 15. Business Model Canvas

```
+-------------------------------------------------------------------+
|                    PILOT SPACE BUSINESS MODEL                      |
+-----------------+------------------------+------------------------+
| KEY PARTNERS    | KEY ACTIVITIES         | VALUE PROPOSITIONS     |
|                 |                        |                        |
| * Anthropic     | * PilotSpaceAgent      | "Think First,          |
|   (Orchestrator)|   orchestration        |  Structure Later"      |
| * GitHub        | * Editor UX polish     |                        |
|   (Integration) | * MCP tool development | * Note-First (DD-013)  |
| * Supabase      | * Community building   | * 1+3+8 AI system      |
|   (Platform)    | * Content marketing    | * 6 MCP Note Tools     |
|                 |                        | * GitHub-native        |
+-----------------+------------------------+------------------------+
| KEY RESOURCES   | CHANNELS               | CUSTOMER RELATIONSHIPS |
|                 |                        |                        |
| * Claude Agent  | * Developer content    | * Self-serve PLG       |
|   SDK (DD-086)  | * Twitter/X community  | * Discord community    |
| * TipTap/Editor | * Hacker News          | * Office Hours (trust) |
| * Skill System  | * GitHub Marketplace   | * Case study co-create |
|   (DD-087)      | * Referral program     |                        |
| * MCP Registry  |                        |                        |
|   (DD-088)      |                        |                        |
+-----------------+------------------------+------------------------+
| COST STRUCTURE                          | REVENUE STREAMS        |
|                                         |                        |
| * Engineering (60%): 3-5 engineers      | * Support subscriptions |
| * Infrastructure (15%): Supabase        |   - Pro: $10/seat/mo   |
| * Marketing (15%): Content, community   |   - Business: $18/mo   |
| * Support (10%): 1 per 1000 users       |   - Enterprise: Custom |
|                                         |                        |
| BYOK = 0 AI API costs = 80%+ margin    | ALL FEATURES FREE      |
+-----------------------------------------+------------------------+
```

---

## 16. Document Cross-References

| Topic | Document | Key Decisions |
|-------|----------|---------------|
| Core Philosophy | PROJECT_VISION.md | Note-First, 7 Principles |
| Technical Decisions | DESIGN_DECISIONS.md | DD-001 to DD-088 |
| Feature Specs | spec.md v3.2 | 18 Stories, 123 FRs, 20 SCs |
| AI Architecture | AI_CAPABILITIES.md | 1 orchestrator + 3 subagents + 8 skills |
| Agent Architecture | DD-086, DD-087, DD-088 | Conversational, Skills, MCP Tools |
| UI/UX Design | ui-design-spec.md | Component specs |
| Data Model | data-model.md | 21 Entities |
| Feature Mapping | feature-story-mapping.md | 18 US -> architecture components |
| Implementation | plan.md | Phase breakdown |

---

*Document Version: 2.0.0*
*Last Updated: 2026-02-01*
*Author: Pilot Space Strategy Team*
*Changes v2.0: Updated AI architecture from 13 siloed agents to 1+3+8 consolidated system (DD-086/087/088); Added user journey maps for 4 personas; Added business rules matrix; Added feature-business mapping; Added BYOK economics deep dive; Added competitive moat analysis; Added integration strategy; Added success playbook (180-day milestones); Updated risk assessment with SDK dependency and orchestration risks*
*Changes v1.1: Standardized agent count, added SC-001 to SC-020*
*Changes v1.0: Initial version*
