# Pilot Space → AI Unified Platform: CTO Roadmap

**Version**: 1.1 | **Date**: 2026-03-19 | **Status**: Strategic Draft
**Author**: CTO Office | **Horizon**: 24 months (Q2 2026 – Q2 2028)

---

## Executive Summary

Pilot Space transforms from an AI-augmented SDLC tool into a **domain-agnostic AI Unified Platform** where any team — software, marketing, HRM, CRM, operations — works through a consistent "Note-First" paradigm powered by domain-specific **Workspace Templates** (designed by PilotSpace), **Custom Skills** (built by workspace admins), and autonomous **AI Workers** executing tasks via CLI on worker devices.

The core insight: our existing orchestrator → subagent → skill architecture (DD-086) already abstracts domain logic into composable units. We generalize this from "SDLC skills" to "any-domain skills" while keeping the same security model (RLS), approval workflow (DD-003), and BYOK cost model (DD-011).

---

## 1. Strategic Vision

### 1.1 From SDLC Tool to Universal Work Platform

```
Current State (v1)                    Target State (v2)
─────────────────                     ──────────────────
Workspace                             Workspace
  └── Project (SDLC)                    ├── Domain: Engineering (template)
        ├── Issues                      │     ├── Issues, PRs, Sprints
        ├── Notes                       │     └── Skills: code-review, deploy
        ├── Cycles                      ├── Domain: Marketing (template)
        └── AI Agent (8 skills)         │     ├── Campaigns, Content Calendar
                                        │     └── Skills: seo-audit, copy-gen
                                        ├── Domain: HRM (template)
                                        │     ├── Hiring Pipeline, Reviews
                                        │     └── Skills: jd-writer, interview-prep
                                        └── Domain: CRM (custom)
                                              ├── Deals, Contacts, Pipeline
                                              └── Skills: lead-score, outreach
```

### 1.2 Four Pillars

1. **Template Presets** — PilotSpace-designed domain blueprints (entity schemas, workflows, skills, role templates, MCP tools) that bootstrap a workspace for a specific domain in minutes.

2. **Custom Skills** — Admin-authored or AI-generated skills that extend any domain template. Built through a visual Skill Builder or SKILL.md authoring, stored per-workspace, version-controlled.

3. **AI Workers** — Autonomous CLI agents (`pilot-worker`) running on worker devices (dev machines, CI runners, cloud VMs). Pull tasks from workspace queue, execute in isolated spaces, report results back. Think "OpenClaw meets our existing `pilot implement`."

4. **Domain-Specific LLMs** — Custom fine-tuned models trained on workspace private data for each domain. Each template can have its own specialized model that understands domain terminology, workflows, and patterns at a level general-purpose LLMs cannot. Models are trained within workspace data boundaries (RLS-enforced), deployed per-workspace, and continuously improved through RLHF from user feedback loops.

### 1.3 Design Principles (Extending Current DD-003, DD-086)

| Principle | Description |
|-----------|-------------|
| **Domain-Agnostic Core** | The platform kernel knows entities, workflows, notes, and AI — not "issues" or "sprints." Domain semantics live in templates. |
| **Template as Code** | Every domain template is a declarative manifest (YAML/JSON) that can be versioned, forked, and shared. |
| **Skill Composability** | Skills are the atomic unit of AI capability. They compose into workflows, chain across domains, and are hot-swappable. |
| **Worker Autonomy with Human-in-Loop** | AI Workers execute autonomously but respect the same approval tiers (DD-003): non-destructive auto-approve, destructive requires human sign-off. |
| **BYOK Everywhere** | No domain charges AI cost to PilotSpace. Users bring their own keys, cost tracking per workspace/domain/worker. |
| **Data Flywheel** | Every interaction feeds the domain-specific model training pipeline. Private data never leaves workspace boundaries. Models improve continuously through usage. |

---

## 2. Architecture Evolution

### 2.1 Current Architecture (What We Have)

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Next.js)               │
│  MobX Stores → Features → TipTap Editor          │
├─────────────────────────────────────────────────┤
│                  Backend (FastAPI)                 │
│  API Routers → Services (91) → Repositories       │
├─────────────────────────────────────────────────┤
│              AI Layer (DD-086)                     │
│  PilotSpaceAgent → 2 Subagents + 8 Skills         │
│  33 MCP Tools → 6 Servers                         │
│  Provider Routing (20 task types)                  │
├─────────────────────────────────────────────────┤
│              Infrastructure                        │
│  PostgreSQL+RLS │ Redis │ Supabase Auth            │
├─────────────────────────────────────────────────┤
│              CLI (pilot-cli)                       │
│  login │ implement │ backup                        │
└─────────────────────────────────────────────────┘
```

### 2.2 Target Architecture (AI Unified Platform)

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                          │
│  Domain Switcher → Template Renderer → Universal Note Canvas  │
│  Skill Builder → Worker Dashboard → Marketplace               │
├──────────────────────────────────────────────────────────────┤
│                    API Gateway                                │
│  /api/v2/workspaces/{ws}/domains/{domain}/...                 │
├──────────────────────────────────────────────────────────────┤
│               Domain Template Engine                          │
│  Template Registry │ Schema Compiler │ Workflow Engine         │
│  Entity Factory │ Migration Generator │ Seed Data              │
├──────────────────────────────────────────────────────────────┤
│               AI Orchestration Layer                          │
│  UnifiedAgent (domain-aware routing)                          │
│  ├── Domain Subagents (per-template, multi-turn)              │
│  ├── Skills Registry (platform + workspace + user)            │
│  ├── MCP Tool Factory (generates tools from entity schemas)   │
│  └── Worker Coordinator (task queue, dispatch, results)       │
├──────────────────────────────────────────────────────────────┤
│               Core Platform (domain-agnostic)                 │
│  Entity Store │ Workflow Engine │ Note Engine │ Activity Log   │
│  Permission Engine │ Notification Bus │ Integration Hub        │
├──────────────────────────────────────────────────────────────┤
│               Infrastructure                                  │
│  PostgreSQL+RLS │ Redis │ Supabase Auth │ pgmq Task Queue     │
│  S3/MinIO (artifacts) │ Vector Store (pgvector)               │
├──────────────────────────────────────────────────────────────┤
│               Worker Runtime                                  │
│  pilot-worker CLI │ Space Manager │ Task Executor              │
│  LocalFileSystemSpace │ ContainerSpace │ Sandbox               │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Key Abstractions to Introduce

#### 2.3.1 Generic Entity System (replacing hard-coded Issue/Note/Cycle)

```python
# Current: domain/models/issue.py — tightly coupled
class Issue(WorkspaceScopedModel):
    title: str
    state: IssueState  # Hard-coded enum
    priority: IssuePriority
    project_id: UUID

# Target: domain/models/entity.py — schema-driven
class Entity(WorkspaceScopedModel):
    domain_id: UUID
    entity_type_id: UUID  # References EntityType from template
    data: dict  # JSONB, validated against EntityType.schema
    state: str  # Dynamic, from workflow definition

class EntityType(WorkspaceScopedModel):
    domain_id: UUID
    slug: str  # "issue", "campaign", "deal", "candidate"
    schema: dict  # JSON Schema for data validation
    workflow_id: UUID | None
    icon: str
    color: str
```

**Migration Strategy**: Issue, Note, Cycle become built-in EntityTypes in the "Engineering" template. Existing data migrates to Entity table with `entity_type_id` pointing to the legacy type definitions. Backward-compatible API layer serves both `/issues/{id}` and `/entities/{id}`.

#### 2.3.2 Domain Template Manifest

```yaml
# templates/engineering/manifest.yaml
name: "Engineering"
version: "1.0.0"
author: "PilotSpace"
description: "Full SDLC workflow with issues, sprints, and PR reviews"

entity_types:
  - slug: issue
    schema: ./schemas/issue.json
    workflow: ./workflows/issue-state-machine.yaml
    icon: "circle-dot"
  - slug: sprint
    schema: ./schemas/sprint.json
    workflow: ./workflows/sprint-lifecycle.yaml
    icon: "iterations"
  - slug: note
    schema: ./schemas/note.json
    icon: "file-text"

role_templates:
  - developer
  - product-owner
  - tech-lead
  - qa-engineer

skills:
  - decompose-tasks
  - review-architecture
  - code-review
  - deploy-checklist

mcp_tools:
  - entity_server  # Auto-generated CRUD from entity_types
  - workflow_server  # Transition, assign, comment
  - integration_server  # GitHub, GitLab, Slack

workflows:
  issue-state-machine:
    states: [backlog, todo, in_progress, in_review, done, cancelled]
    transitions:
      - from: backlog, to: todo, trigger: manual
      - from: in_progress, to: in_review, trigger: pr_created
      - from: in_review, to: done, trigger: pr_merged

views:
  - type: board
    group_by: state
    entity_type: issue
  - type: timeline
    entity_type: sprint
  - type: canvas
    entity_type: note

integrations:
  - provider: github
    events: [push, pull_request, issue_comment]
    mappings:
      pull_request.merged → issue.state:done
```

#### 2.3.3 Skill Architecture (Extended)

```
Platform Skills (by PilotSpace, immutable)
  ├── decompose-tasks
  ├── review-architecture
  └── ... (current 8 skills)

Template Skills (bundled with domain template)
  ├── Engineering: code-review, deploy-checklist, sprint-planning
  ├── Marketing: seo-audit, copy-generation, campaign-planner
  ├── HRM: jd-writer, interview-prep, performance-review
  └── CRM: lead-scoring, outreach-sequence, deal-analyzer

Workspace Skills (admin-created, per workspace)
  ├── Custom: "our-deploy-process" (admin skill)
  ├── Custom: "brand-voice-guide" (admin skill)
  └── Generated: AI-created from workspace context

User Skills (per user, portable)
  └── Personal: "my-code-style", "my-review-checklist"
```

**Skill Resolution Order**: User → Workspace → Template → Platform (most specific wins).

#### 2.3.4 AI Worker Architecture

```
                    ┌─────────────────┐
                    │   Workspace      │
                    │   Task Queue     │
                    │   (pgmq)         │
                    └───────┬─────────┘
                            │ pull tasks
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  Worker #1   │ │  Worker #2   │ │  Worker #3   │
    │  (dev laptop)│ │  (CI runner) │ │  (cloud VM)  │
    │              │ │              │ │              │
    │ pilot-worker │ │ pilot-worker │ │ pilot-worker │
    │  ├─ Space    │ │  ├─ Space    │ │  ├─ Space    │
    │  ├─ Executor │ │  ├─ Executor │ │  ├─ Executor │
    │  └─ Reporter │ │  └─ Reporter │ │  └─ Reporter │
    └──────────────┘ └──────────────┘ └──────────────┘
```

**Worker Lifecycle**:

1. `pilot-worker register` — Authenticate, register device capabilities
2. `pilot-worker start` — Poll task queue, claim tasks matching capabilities
3. **Task Execution**: Create Space → inject context (entity data, skills, tools) → execute via Claude Agent SDK → stream progress via SSE
4. **Result Reporting**: Artifacts uploaded → entity state updated → activity logged → human review triggered if destructive
5. `pilot-worker stop` — Graceful drain, complete current task, deregister

**Task Context Injection** (what the worker receives):

```python
class WorkerTaskContext:
    task_id: UUID
    workspace_id: UUID
    domain_id: UUID
    entity: Entity  # The entity this task operates on
    entity_type: EntityType  # Schema + workflow
    skills: list[Skill]  # Resolved skills for this domain
    mcp_tools: list[MCPTool]  # Available tools
    workspace_config: dict  # BYOK keys, approval rules
    artifacts: list[Artifact]  # Input files, previous outputs
    instructions: str  # Human instructions or auto-generated
    constraints: TaskConstraints  # Time limit, cost budget, approval tier
```

---

## 3. Phased Roadmap

### Phase 0: Foundation Hardening (Q2 2026 — 6 weeks)

**Goal**: Stabilize current SDLC platform, extract generalizable primitives.

| Track | Deliverable | Effort |
|-------|-------------|--------|
| **Entity Abstraction** | Extract `EntityType` + `Entity` models from Issue/Note/Cycle. Dual-write migration (old tables + new entity table). Backward-compatible API. | 3 weeks |
| **Domain Context** | Add `domain_id` to workspace-scoped models. Extend RLS policies for domain isolation. Update all 18 repositories. | 2 weeks |
| **Workflow Engine** | Extract issue state machine into declarative YAML workflow engine. Support arbitrary states, transitions, guards, actions. | 2 weeks |
| **Skill Registry** | Move from filesystem auto-discovery to database-backed skill registry with resolution tiers (platform → template → workspace → user). | 1 week |
| **MCP Tool Factory** | Auto-generate CRUD MCP tools from EntityType schemas (replacing hard-coded issue_server, note_server). | 2 weeks |

**Key Decisions**:
- DD-089: Entity Abstraction Strategy (EAV vs JSONB vs hybrid)
  - **Recommendation**: JSONB with JSON Schema validation. Avoids EAV performance cliff, leverages PostgreSQL JSONB indexing, keeps queries simple.
- DD-090: Domain Isolation Model
  - **Recommendation**: `domain_id` column + RLS policy extension. Each domain within a workspace gets its own data partition.

**Quality Gates**: All existing tests pass. Coverage ≥80%. Zero breaking changes to v1 API.

### Phase 1: Template Engine (Q3 2026 — 8 weeks)

**Goal**: Ship domain templates that bootstrap workspaces for non-SDLC use cases.

| Track | Deliverable | Effort |
|-------|-------------|--------|
| **Template Manifest** | YAML manifest parser + validator. Schema compiler (JSON Schema → EntityType + DB indexes). | 3 weeks |
| **Template Registry** | Platform template store (Engineering, Marketing, HRM, CRM as launch templates). Versioned, immutable once published. | 2 weeks |
| **Template Installer** | `POST /workspaces/{ws}/domains` — provisions domain from template: creates entity types, workflows, seeds role templates, installs template skills. | 2 weeks |
| **Migration Generator** | Auto-generate Alembic migrations for new entity type indexes (GIN on JSONB paths used in views/filters). | 1 week |
| **Domain Switcher UI** | Frontend sidebar domain switcher. Domain-scoped views (board, list, timeline, canvas). MobX DomainStore. | 2 weeks |
| **View Engine** | Configurable views per entity type (board, list, timeline, calendar, canvas). Column/grouping/filter configs from template. | 3 weeks |

**Launch Templates** (v1):

| Template | Entity Types | Workflows | Skills |
|----------|-------------|-----------|--------|
| **Engineering** | Issue, Sprint, Note, PR Review | Issue lifecycle, Sprint lifecycle | code-review, decompose-tasks, deploy-checklist, architecture-review |
| **Marketing** | Campaign, Content, Channel, Audience | Campaign lifecycle, Content approval | seo-audit, copy-generation, content-calendar, audience-analysis |
| **HRM** | Candidate, Position, Interview, Review | Hiring pipeline, Performance cycle | jd-writer, interview-prep, resume-screen, review-template |
| **CRM** | Deal, Contact, Company, Activity | Sales pipeline, Deal stages | lead-scoring, outreach-draft, deal-analysis, meeting-prep |

### Phase 2: Custom Skills & Skill Builder (Q3-Q4 2026 — 8 weeks)

**Goal**: Workspace admins can create, test, and deploy custom skills without code.

| Track | Deliverable | Effort |
|-------|-------------|--------|
| **Skill Builder UI** | Visual skill authoring: name, description, system prompt template, MCP tool bindings, input/output schema, test cases. | 4 weeks |
| **Skill Versioning** | Skills stored in DB with version history. Rollback, diff, A/B testing support. | 2 weeks |
| **AI Skill Generator** | Extend `GenerateRoleSkillService`: admin describes intent in natural language → AI generates SKILL.md + test cases. Human reviews and publishes. | 2 weeks |
| **Skill Marketplace** (internal) | Workspace admins can publish skills to org-level marketplace. Other workspaces can install. Rating + usage analytics. | 2 weeks |
| **Skill Chaining** | Compose skills into multi-step workflows: Skill A output → Skill B input. DAG-based execution with error handling. | 2 weeks |
| **Skill Sandbox** | Test skills in isolated environment before publishing. Mock MCP tools, simulated entity data, cost estimation. | 1 week |

**Skill Definition Schema** (extended from current SKILL.md):

```yaml
# skills/custom/lead-scorer/skill.yaml
name: "Lead Scorer"
version: "1.2.0"
domain: "crm"  # optional domain affinity
description: "Score leads based on engagement signals and ICP fit"

triggers:
  - entity_type: deal
    event: created
    auto_run: true  # runs automatically on trigger
  - manual: true  # also available as chat command

inputs:
  - name: deal_data
    source: entity  # pulled from the triggering entity
  - name: icp_profile
    source: workspace_config.crm.ideal_customer_profile

prompt_template: |
  You are a lead scoring analyst. Given the deal data and ICP profile,
  score this lead on a 0-100 scale across these dimensions:
  - Company fit (size, industry, tech stack)
  - Engagement signals (email opens, page visits, demo requests)
  - Budget authority (title, company revenue)

  Deal: {{deal_data}}
  ICP: {{icp_profile}}

output_schema:
  type: object
  properties:
    score: { type: integer, minimum: 0, maximum: 100 }
    breakdown: { type: object }
    recommendation: { type: string, enum: [hot, warm, cold, disqualified] }
    reasoning: { type: string }

tools_required:
  - entity_server.get_entity
  - entity_server.update_entity

side_effects:
  - update_entity:
      field: data.lead_score
      value: "{{output.score}}"
  - update_entity:
      field: data.lead_tier
      value: "{{output.recommendation}}"

approval_tier: auto  # non-destructive
cost_budget: 0.05  # max $0.05 per execution
```

### Phase 3: AI Worker Runtime (Q4 2026 — 10 weeks)

**Goal**: Autonomous AI agents execute tasks from workspace queues on worker devices.

| Track | Deliverable | Effort |
|-------|-------------|--------|
| **pilot-worker CLI** | New CLI package: `register`, `start`, `stop`, `status`, `logs`. Built on existing `pilot-cli` patterns (Typer, config management). | 3 weeks |
| **Task Queue** | pgmq-based task queue with priority, claiming, timeout, retry, dead-letter. Domain-scoped queues. | 2 weeks |
| **Worker Space Manager** | Extend `SpaceInterface` (already exists): `LocalFileSystemSpace` for dev, `ContainerSpace` for cloud. Inject task context (entity, skills, tools). | 2 weeks |
| **Task Executor** | Claude Agent SDK integration: build agent from task context, stream execution, capture artifacts, handle approval gates. | 3 weeks |
| **Worker Dashboard** | Frontend: live worker status, task queue depth, execution logs, cost per worker, approval requests. SSE real-time updates. | 2 weeks |
| **Worker Security** | Worker authentication (mTLS + workspace token). Sandbox constraints (network allowlist, filesystem scope, time/cost limits). Audit logging. | 2 weeks |

**Worker Types** (by deployment):

| Type | Where | Use Case | Space |
|------|-------|----------|-------|
| **Local Worker** | Developer's machine | Code implementation, testing, local deploys | LocalFileSystemSpace |
| **CI Worker** | GitHub Actions / GitLab CI | PR review, automated testing, deployment | ContainerSpace |
| **Cloud Worker** | AWS/GCP VM | Heavy batch processing, report generation | ContainerSpace |
| **Scheduled Worker** | Cron-triggered | Daily digests, metric collection, cleanup | ContainerSpace |

**Task Flow Example** (Engineering domain):

```
1. PM creates issue "Implement OAuth2 login" with acceptance criteria
2. PM clicks "Assign to AI Worker" → task enters queue
3. Worker #1 (dev laptop) claims task
4. Worker creates Space, clones repo, injects issue context
5. Worker executes: analyze codebase → plan → implement → test → PR
6. Worker streams progress via SSE → visible in dashboard
7. PR created → triggers "code-review" skill → human approval gate
8. Human approves → PR merged → issue auto-transitions to "done"
```

**Task Flow Example** (Marketing domain):

```
1. Marketer creates campaign entity "Q4 Product Launch"
2. Marketer adds content entities with briefs
3. Marketer clicks "Generate All Content" → bulk task enters queue
4. Workers claim content tasks in parallel
5. Each worker: read brief → apply brand-voice skill → generate copy
6. Generated content → human review queue (approval_tier: review)
7. Marketer reviews, approves/edits → content marked "approved"
8. "publish" skill auto-posts to connected channels (Slack, CMS)
```

### Phase 4: Platform Maturity (Q1-Q2 2027 — 12 weeks)

**Goal**: Production-grade multi-domain platform with ecosystem.

| Track | Deliverable | Effort |
|-------|-------------|--------|
| **Cross-Domain Intelligence** | AI can reference entities across domains (e.g., CRM deal context when writing marketing copy for that account). Cross-domain skill chaining. | 4 weeks |
| **Template Marketplace** | Public marketplace for community templates. Revenue share model. Template versioning + upgrade paths. | 4 weeks |
| **Skill Marketplace** | Public skill marketplace. Paid skills with usage-based billing. Skill certification program. | 3 weeks |
| **Worker Fleet Management** | Multi-worker orchestration, load balancing, auto-scaling cloud workers, cost optimization. Priority queues per domain. | 3 weeks |
| **Analytics & Insights** | Cross-domain analytics: team velocity, AI ROI, cost per domain, skill effectiveness. Workspace-level dashboards. | 3 weeks |
| **Enterprise Features** | SSO/SCIM, audit logs export, compliance controls, data residency, custom RLS policies per domain. | 4 weeks |
| **SDK & API** | Public REST + WebSocket API for third-party integrations. TypeScript/Python SDKs. Webhook system. | 3 weeks |

### Phase 5: Domain-Specific Custom LLMs (Q3-Q4 2027 — 16 weeks)

**Goal**: Train, deploy, and continuously improve custom LLM models per domain using workspace private data.

| Track | Deliverable | Effort |
|-------|-------------|--------|
| **Data Pipeline** | Automated ETL from workspace entities, notes, skills, activity logs into training-ready datasets. PII anonymization, deduplication, quality scoring. RLS-enforced data isolation — training data never crosses workspace boundaries. | 4 weeks |
| **Training Orchestrator** | Fine-tuning pipeline supporting LoRA/QLoRA adapters on base models (Llama, Mistral, Qwen). Per-domain adapters: engineering-lora, marketing-lora, hrm-lora, crm-lora. GPU cluster management (spot instances for cost). | 4 weeks |
| **Model Registry** | Versioned model store per workspace/domain. A/B testing between model versions. Rollback to previous version. Model performance metrics (accuracy, latency, cost). | 2 weeks |
| **RLHF Feedback Loop** | User thumbs-up/down on AI outputs feeds reward model. Skill execution success/failure as implicit signal. Periodic re-training with accumulated feedback. DPO (Direct Preference Optimization) for alignment. | 3 weeks |
| **Inference Router** | Extend ProviderSelector (DD-011): route to custom model when confidence is high, fallback to general-purpose model for edge cases. Latency-aware routing with SLA guarantees. | 2 weeks |
| **Data Governance Console** | Admin UI: what data is included in training, opt-out controls, data retention policies, export/delete training data (GDPR compliance), audit trail of model training runs. | 3 weeks |

**Custom LLM Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                   DATA COLLECTION LAYER                      │
│                                                              │
│  Entities ──┐                                                │
│  Notes ─────┤    ETL Pipeline     ┌──────────────────┐       │
│  Skills ────┼──► (anonymize, ───►│ Training Dataset  │       │
│  Activity ──┤    deduplicate,     │ Store (S3/MinIO)  │       │
│  Feedback ──┘    quality score)   └────────┬─────────┘       │
│                                            │                 │
│  RLS Boundary: workspace_id + domain_id    │                 │
├────────────────────────────────────────────┼─────────────────┤
│                   TRAINING LAYER           │                 │
│                                            ▼                 │
│  ┌──────────────┐    ┌──────────────────────────┐            │
│  │  Base Model   │    │  Fine-Tuning Pipeline     │            │
│  │  (Llama 3.x / │───►│  LoRA/QLoRA Adapters      │            │
│  │   Mistral /   │    │  DPO Alignment            │            │
│  │   Qwen)       │    │  Domain-specific corpus    │            │
│  └──────────────┘    └──────────┬───────────────┘            │
│                                 │                            │
├─────────────────────────────────┼────────────────────────────┤
│                   MODEL REGISTRY               │              │
│                                 ▼              │              │
│  ┌────────────────────────────────────────┐    │              │
│  │  workspace-123/                        │    │              │
│  │  ├── engineering-lora-v2.3 (active)    │    │              │
│  │  ├── engineering-lora-v2.2 (rollback)  │    │              │
│  │  ├── marketing-lora-v1.5 (active)      │    │              │
│  │  └── crm-lora-v1.0 (A/B test: 30%)    │    │              │
│  └────────────────────────────────────────┘    │              │
│                                                │              │
├────────────────────────────────────────────────┼──────────────┤
│                   INFERENCE LAYER              │              │
│                                                ▼              │
│  ┌───────────────────────────────────────────────────┐       │
│  │  Extended ProviderSelector                         │       │
│  │                                                    │       │
│  │  Route: custom_model (high confidence)             │       │
│  │    ├── engineering → engineering-lora (self-hosted) │       │
│  │    ├── marketing → marketing-lora (self-hosted)    │       │
│  │    └── crm → crm-lora (self-hosted)                │       │
│  │                                                    │       │
│  │  Fallback: general_model (edge cases)              │       │
│  │    └── Anthropic/OpenAI/Google (BYOK)              │       │
│  └───────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Training Data Sources per Domain**:

| Domain | Training Signals | Volume Target |
|--------|-----------------|---------------|
| Engineering | Code reviews, PR comments, architecture decisions, issue descriptions, commit messages, sprint retrospectives | 10K+ examples per workspace |
| Marketing | Campaign briefs, content pieces (approved), brand guidelines, A/B test results, channel performance insights | 5K+ content samples |
| HRM | Job descriptions, interview feedback, performance reviews, offer letters, onboarding materials | 3K+ HR documents |
| CRM | Deal notes, email templates (high-conversion), call transcripts, proposal drafts, win/loss analyses | 5K+ sales interactions |

**Privacy & Security Guarantees**:
- Training data is NEVER shared across workspaces (RLS boundary extends to training pipeline)
- PII anonymization before training (named entity replacement, email/phone masking)
- Admin can exclude specific entities/notes from training via `training_opt_out` flag
- Model weights stored encrypted at rest, decrypted only during inference
- GDPR Article 17: "Right to Erasure" — delete training data triggers model re-training without that data
- Audit log of every training run: data snapshot hash, model version, hyperparameters, evaluation metrics

**Deployment Options**:

| Mode | Where | Cost | Latency | Data Privacy |
|------|-------|------|---------|-------------|
| **PilotSpace Cloud** | Managed GPU cluster | Usage-based | <500ms | Data encrypted, isolated per workspace |
| **Self-Hosted** | Customer's infrastructure | Customer bears | <200ms | Data never leaves customer network |
| **Hybrid** | Base model cloud + adapter local | Split | <400ms | Only adapter weights on customer side |

---

## 4. Technical Deep Dives

### 4.1 Entity Abstraction — Migration Strategy

The biggest risk in this roadmap is migrating from hard-coded Issue/Note/Cycle models to the generic Entity system without breaking existing users.

**Strategy: Dual-Write with Progressive Migration**

```
Phase A (Week 1-2): Add Entity table alongside existing tables
  - Entity table created with JSONB data column
  - Dual-write: every Issue/Note/Cycle write also writes to Entity
  - Read path: unchanged (still uses Issue/Note/Cycle tables)

Phase B (Week 3-4): Shadow read validation
  - Read path: query both old table AND Entity table
  - Log discrepancies (should be zero after dual-write stabilizes)
  - API unchanged

Phase C (Week 5-6): Switch read path
  - Read path: Entity table (with EntityType-based deserialization)
  - Write path: still dual-write for rollback safety
  - v1 API: backward-compatible wrapper over Entity queries
  - v2 API: native Entity endpoints

Phase D (Phase 1+): Deprecate old tables
  - Remove dual-write after 1 release cycle
  - Old tables archived, not dropped (for rollback)
```

### 4.2 RLS Extension for Domain Isolation

```sql
-- Current RLS pattern (workspace only)
CREATE POLICY workspace_isolation ON entities
  USING (workspace_id = current_setting('app.current_workspace_id')::uuid);

-- Extended pattern (workspace + domain)
CREATE POLICY domain_isolation ON entities
  USING (
    workspace_id = current_setting('app.current_workspace_id')::uuid
    AND (
      current_setting('app.current_domain_id', true) IS NULL  -- no domain filter = all domains
      OR domain_id = current_setting('app.current_domain_id', true)::uuid
    )
  );
```

### 4.3 MCP Tool Auto-Generation

```python
class MCPToolFactory:
    """Generate MCP tools from EntityType schemas."""

    def generate_tools(self, entity_type: EntityType) -> list[MCPTool]:
        slug = entity_type.slug  # e.g., "deal"
        tools = [
            self._generate_get_tool(slug, entity_type.schema),
            self._generate_list_tool(slug, entity_type.schema),
            self._generate_create_tool(slug, entity_type.schema),
            self._generate_update_tool(slug, entity_type.schema),
            self._generate_search_tool(slug, entity_type.schema),
        ]
        if entity_type.workflow_id:
            tools.append(self._generate_transition_tool(slug, entity_type.workflow))
        return tools

    # AI agent sees: get_deal, list_deals, create_deal, update_deal,
    #                search_deals, transition_deal_state
```

### 4.4 Worker-to-Platform Communication

```
Worker                          Platform
  │                                │
  ├── POST /workers/register ─────►│  (mTLS + workspace token)
  │◄── 200 {worker_id, config} ───┤
  │                                │
  ├── GET /tasks/claim ────────────►│  (long-poll, domain filter)
  │◄── 200 {task, context} ───────┤
  │                                │
  ├── SSE /tasks/{id}/progress ────►│  (streaming execution logs)
  │                                │
  ├── POST /tasks/{id}/approval ───►│  (needs human sign-off)
  │◄── SSE approval_response ─────┤  (human approves/rejects)
  │                                │
  ├── POST /tasks/{id}/artifacts ──►│  (upload outputs)
  ├── POST /tasks/{id}/complete ───►│  (final status + metrics)
  │                                │
  └── DELETE /workers/{id} ────────►│  (graceful shutdown)
```

### 4.5 Provider Routing Extension (Domain-Aware)

```python
# Current: task-type based routing
ROUTING_TABLE = {
    TaskType.PR_REVIEW: ProviderConfig(primary="anthropic", model="opus"),
    TaskType.GHOST_TEXT: ProviderConfig(primary="google", model="flash"),
}

# Extended: domain + task-type routing with workspace overrides
ROUTING_TABLE = {
    ("engineering", TaskType.CODE_REVIEW): ProviderConfig(primary="anthropic", model="opus"),
    ("engineering", TaskType.GHOST_TEXT): ProviderConfig(primary="google", model="flash"),
    ("marketing", TaskType.CONTENT_GEN): ProviderConfig(primary="anthropic", model="sonnet"),
    ("marketing", TaskType.SEO_ANALYSIS): ProviderConfig(primary="openai", model="gpt-4o"),
    ("crm", TaskType.LEAD_SCORING): ProviderConfig(primary="anthropic", model="haiku"),
    ("*", TaskType.EMBEDDINGS): ProviderConfig(primary="openai", model="text-embedding-3-large"),
}

# Workspace admins can override any routing via settings
# Fallback chain: workspace_override → domain_routing → default_routing
```

---

## 5. Domain Template Specifications

### 5.1 Engineering (Existing, Formalized)

**Entity Types**: Issue, Sprint, Note, PR Review, Module, Epic
**Workflows**: Issue lifecycle (7 states), Sprint lifecycle (4 states), PR review flow
**Skills**: code-review, decompose-tasks, architecture-review, deploy-checklist, test-generator, doc-generator, sprint-planning, retro-facilitator
**Integrations**: GitHub, GitLab, Bitbucket, Slack, Linear (import)
**Views**: Kanban board, Sprint timeline, Note canvas, PR queue

### 5.2 Marketing

**Entity Types**: Campaign, Content Piece, Channel, Audience Segment, Creative Asset, A/B Test
**Workflows**: Content approval (draft → review → approved → published → archived), Campaign lifecycle (planning → active → paused → completed → analyzed)
**Skills**: seo-audit, copy-generation, content-calendar-planner, audience-analysis, competitor-watch, brand-voice-enforcer, performance-report, social-media-scheduler
**Integrations**: Google Analytics, HubSpot, Mailchimp, Hootsuite, Canva, WordPress
**Views**: Content calendar, Campaign dashboard, Channel performance, Asset library

### 5.3 HRM

**Entity Types**: Candidate, Position, Interview, Performance Review, Employee, Onboarding Checklist
**Workflows**: Hiring pipeline (sourced → screened → interviewed → offered → hired/rejected), Performance cycle (self-review → manager-review → calibration → finalized), Onboarding (day-1 → week-1 → month-1 → completed)
**Skills**: jd-writer, resume-screener, interview-prep, interview-debrief, performance-review-template, compensation-analysis, onboarding-checklist-gen, culture-fit-assessment
**Integrations**: Greenhouse, Lever, BambooHR, Workday, LinkedIn
**Views**: Hiring funnel, Interview calendar, Review cycle tracker, Org chart

### 5.4 CRM

**Entity Types**: Deal, Contact, Company, Activity, Quote, Contract
**Workflows**: Sales pipeline (lead → qualified → proposal → negotiation → closed-won/lost), Contract lifecycle (draft → review → sent → signed → active → renewed/expired)
**Skills**: lead-scoring, outreach-draft, deal-analysis, meeting-prep, proposal-generator, contract-review, churn-predictor, upsell-identifier
**Integrations**: Salesforce, HubSpot CRM, Pipedrive, DocuSign, Zoom, Gong
**Views**: Pipeline board, Deal timeline, Contact 360, Revenue forecast

---

## 6. Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Entity abstraction breaks existing SDLC users | High | Medium | Dual-write migration, backward-compatible v1 API, feature flags per workspace |
| Template complexity overwhelms small teams | Medium | High | "Quick Start" wizard, sensible defaults, progressive disclosure. Start with 1 domain, add more later. |
| AI Worker security breach (code execution) | Critical | Low | Sandbox isolation (SpaceInterface), network allowlists, filesystem scoping, cost limits, audit logging, mTLS auth |
| BYOK cost explosion with autonomous workers | High | Medium | Per-task cost budgets, per-domain spending limits, worker cost dashboard, automatic pause at budget threshold |
| Skill quality varies wildly (user-created) | Medium | High | Skill sandbox testing, certification program, rating system, platform-curated "verified" skills |
| Cross-domain data leakage | High | Low | Domain-scoped RLS, explicit cross-domain permission grants, audit trail for cross-domain access |
| Template upgrade breaks customizations | Medium | Medium | Semantic versioning, non-destructive upgrades (additive only), customization overlay that survives template updates |
| Custom model training data poisoning | High | Low | Data quality scoring, anomaly detection, admin review of training batches, adversarial input filtering |
| GPU cost overrun for model training | High | Medium | Spot instance scheduling, LoRA (not full fine-tune) to minimize GPU hours, shared base model across workspaces, training budget caps |
| Custom model hallucination on domain data | Medium | Medium | RAG augmentation alongside fine-tuning, confidence-based routing (low confidence → fallback to general model), human-in-loop for high-stakes outputs |
| GDPR/privacy violation in training pipeline | Critical | Low | PII anonymization at ETL stage, training opt-out per entity, right-to-erasure triggers re-training, data residency enforcement |

---

## 7. Success Metrics

### Phase 0-1 (Foundation + Templates)
- 4 domain templates shipped and functional
- Zero regression in existing SDLC features (100% test pass rate)
- Template installation < 30 seconds
- Entity query performance within 10% of current hard-coded queries

### Phase 2 (Custom Skills)
- 50+ workspace-created skills within 3 months of launch
- Skill creation time < 15 minutes (visual builder)
- AI-generated skill acceptance rate > 60%

### Phase 3 (AI Workers)
- Worker task completion rate > 85%
- Median task execution time < 5 minutes (simple tasks)
- Human approval turnaround < 1 hour
- Zero security incidents in worker sandbox

### Phase 4 (Platform Maturity)
- 10+ community templates in marketplace
- 3+ domains active per enterprise workspace (average)
- AI cost per workspace within 20% of BYOK budget
- NPS > 50 for multi-domain users

### Phase 5 (Custom LLMs)
- Custom model outperforms general-purpose by 25%+ on domain-specific tasks
- Training pipeline processes 10K+ examples per workspace within 24 hours
- Inference latency < 500ms (cloud) / < 200ms (self-hosted)
- Zero cross-workspace data leakage incidents
- RLHF feedback loop improves model accuracy by 5%+ per training cycle
- 40%+ reduction in BYOK API costs through custom model routing

---

## 8. Team & Resource Plan

| Phase | Duration | Backend | Frontend | AI/ML | DevOps | Total |
|-------|----------|---------|----------|-------|--------|-------|
| Phase 0 | 6 weeks | 2 | 1 | 1 | 0.5 | 4.5 |
| Phase 1 | 8 weeks | 2 | 2 | 1 | 0.5 | 5.5 |
| Phase 2 | 8 weeks | 1 | 2 | 2 | 0.5 | 5.5 |
| Phase 3 | 10 weeks | 2 | 1 | 2 | 1 | 6 |
| Phase 4 | 12 weeks | 2 | 2 | 2 | 1 | 7 |
| Phase 5 | 16 weeks | 2 | 1 | 3 | 2 | 8 |

**Key Hires Needed**: 1 Senior AI Engineer (Agent SDK expertise), 1 Platform Engineer (worker runtime, security sandbox), 1 ML Engineer (fine-tuning pipelines, LoRA adapters), 1 ML Ops Engineer (GPU infra, model serving, monitoring).

---

## 9. Appendix: Design Decision Registry (New)

| ID | Decision | Status |
|----|----------|--------|
| DD-089 | Entity Abstraction: JSONB + JSON Schema validation | Proposed |
| DD-090 | Domain Isolation: domain_id + extended RLS | Proposed |
| DD-091 | Template Manifest: YAML declarative format | Proposed |
| DD-092 | Skill Resolution: User → Workspace → Template → Platform | Proposed |
| DD-093 | Worker Authentication: mTLS + workspace-scoped JWT | Proposed |
| DD-094 | Worker Sandbox: SpaceInterface with capability constraints | Proposed |
| DD-095 | MCP Tool Factory: Auto-generate from EntityType schema | Proposed |
| DD-096 | Cross-Domain Access: Explicit permission grants + audit | Proposed |
| DD-097 | Task Queue: pgmq with domain-scoped partitions | Proposed |
| DD-098 | Template Versioning: SemVer with additive-only upgrades | Proposed |
| DD-099 | Custom LLM Training: LoRA/QLoRA adapters per domain per workspace | Proposed |
| DD-100 | Training Data Isolation: RLS boundary extends to ML pipeline | Proposed |
| DD-101 | Inference Router: Custom model first, general-purpose fallback | Proposed |
| DD-102 | RLHF Feedback Loop: DPO alignment from user signals | Proposed |
| DD-103 | Model Registry: Per-workspace versioned model store with A/B testing | Proposed |
