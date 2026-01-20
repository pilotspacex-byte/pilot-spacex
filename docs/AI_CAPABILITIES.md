# Pilot Space - AI Capabilities Architecture

## Overview

Pilot Space integrates AI as a first-class platform capability, designed to augment human expertise across the software development lifecycle. This document details the AI features, architecture, and implementation strategy.

> **Important**: Pilot Space uses a **BYOK (Bring Your Own Key)** model. Users must provide their own API keys for LLM providers (OpenAI, Anthropic, or Azure OpenAI). There are no limits on AI usage when valid API keys are configured.

---

## AI Philosophy

### Human-in-the-Loop Principle

Every AI interaction in Pilot Space follows a consistent pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI INTERACTION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Trigger │ → │    AI    │ → │  Human   │ → │  Action  │  │
│  │         │    │ Analysis │    │  Review  │    │          │  │
│  └─────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │              │               │               │         │
│       ▼              ▼               ▼               ▼         │
│   User action    Suggestion      Accept/Modify    Execute      │
│   or event      with rationale    /Reject        or Cancel     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### AI Confidence Levels

AI suggestions include confidence indicators:

| Level | Indicator | Behavior |
|-------|-----------|----------|
| **High** (>90%) | Green | Suggestion prominent, one-click accept |
| **Medium** (70-90%) | Yellow | Suggestion visible, review recommended |
| **Low** (<70%) | Orange | Flagged for human attention, requires review |
| **Uncertain** | Gray | AI cannot determine, human input required |

### Transparency Requirements

All AI-generated content is clearly labeled:
- `✨ AI-assisted` badge on suggestions
- Expandable rationale section explaining AI reasoning
- Link to source data used for generation
- Ability to view alternative suggestions

---

## AI Agent Framework

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATOR                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    TASK ROUTER                             │ │
│  │  • Analyzes incoming request                               │ │
│  │  • Selects appropriate agent(s)                            │ │
│  │  • Manages agent coordination                              │ │
│  │  • Handles fallbacks and retries                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐ │
│  │                    CONTEXT MANAGER                         │ │
│  │  • Workspace context (projects, members, settings)         │ │
│  │  • Project context (states, labels, conventions)           │ │
│  │  • User context (role, preferences, history)               │ │
│  │  • Codebase context (architecture, patterns, style)        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐ │
│  │                    AGENT POOL                              │ │
│  │                                                            │ │
│  │  Critical Agents (Human Confirmation Required)             │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │ │
│  │  │ Arch Review│ │Code Review │ │ Security   │            │ │
│  │  │   Agent    │ │   Agent    │ │   Agent    │            │ │
│  │  └────────────┘ └────────────┘ └────────────┘            │ │
│  │                                                            │ │
│  │  Autonomous Agents (Human-in-the-Loop)                     │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │ │
│  │  │    Doc     │ │   Task     │ │  Diagram   │            │ │
│  │  │ Generator  │ │  Planner   │ │ Generator  │            │ │
│  │  └────────────┘ └────────────┘ └────────────┘            │ │
│  │                                                            │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │ │
│  │  │  Pattern   │ │  Retro     │ │ Knowledge  │            │ │
│  │  │  Matcher   │ │  Analyst   │ │   Search   │            │ │
│  │  └────────────┘ └────────────┘ └────────────┘            │ │
│  │                                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Definitions

#### 1. Architecture Review Agent

**Purpose**: Analyze code changes for architectural compliance and suggest improvements.

**Triggers**:
- Pull request created/updated
- Manual review request
- Scheduled architecture audit

**Capabilities**:
```yaml
inputs:
  - Pull request diff
  - Codebase structure
  - Architecture documentation
  - Project conventions

outputs:
  - Compliance score (0-100)
  - Pattern violations list
  - Improvement suggestions
  - Related ADRs

actions:
  - Add PR comment with review
  - Create issue for violations
  - Update architecture docs
  - Suggest refactoring tasks
```

**Example Output**:
```markdown
## 🏗️ Architecture Review

### Compliance Score: 78/100

### Findings

#### ⚠️ Pattern Violations (2)
1. **Direct database access in controller** (Line 45-52)
   - Recommendation: Move to repository layer
   - Related: ADR-0023 Repository Pattern

2. **Missing input validation** (Line 89)
   - Recommendation: Add DTO validation decorator
   - Pattern: Input Validation at Boundaries

#### ✅ Good Practices Detected
- Proper dependency injection usage
- Clear separation of concerns in services

### Suggested Actions
- [ ] Refactor DB access to repository
- [ ] Add input validation
```

#### 2. Code Review Agent

**Purpose**: Provide automated code review focusing on quality, security, and maintainability.

**Triggers**:
- Pull request created
- Code push to protected branch
- Manual review request

**Capabilities**:
```yaml
inputs:
  - Code diff
  - Test coverage data
  - Linting results
  - Historical patterns

outputs:
  - Code quality score
  - Security findings
  - Performance suggestions
  - Test coverage gaps

actions:
  - Inline PR comments
  - Request changes
  - Approve with suggestions
  - Create follow-up issues
```

#### 3. Documentation Generator Agent

**Purpose**: Generate and maintain documentation from code and discussions.

**Triggers**:
- Issue completion
- PR merge
- Manual doc request
- Scheduled doc refresh

**Capabilities**:
```yaml
inputs:
  - Source code
  - Code comments
  - Issue discussions
  - Existing documentation

outputs:
  - API documentation
  - README updates
  - Architecture diagrams
  - Changelog entries

actions:
  - Create/update Pages
  - Generate Mermaid diagrams
  - Update API specs
  - Create release notes
```

**Documentation Types**:

| Type | Source | Format | Trigger |
|------|--------|--------|---------|
| API Reference | Code + OpenAPI | Markdown + Swagger | PR merge |
| Architecture Diagram | Code structure | Mermaid C4 | Weekly/On-demand |
| Component Doc | Code + Comments | Markdown | File change |
| Decision Record | Issue + Discussion | ADR Template | Decision tag |
| Release Notes | Commits + Issues | Changelog | Release event |

#### 4. Task Planner Agent

**Purpose**: Decompose features into actionable tasks with estimates.

**Triggers**:
- Epic/Feature creation
- User request "Plan this feature"
- Sprint planning session

**Capabilities**:
```yaml
inputs:
  - Feature description
  - Acceptance criteria
  - Historical similar tasks
  - Team velocity data

outputs:
  - Task breakdown
  - Story point estimates
  - Dependencies map
  - Risk assessment

actions:
  - Create sub-issues
  - Set dependencies
  - Assign estimates
  - Add to backlog
```

**Example Interaction**:

```
User: Plan the "User Authentication" feature

AI Task Planner Response:

## Feature: User Authentication

### Proposed Task Breakdown

| # | Task | Type | Points | Dependencies |
|---|------|------|--------|--------------|
| 1 | Design auth database schema | Design | 2 | - |
| 2 | Implement user registration API | Backend | 3 | 1 |
| 3 | Implement login/logout API | Backend | 3 | 1 |
| 4 | Add JWT token management | Backend | 3 | 2, 3 |
| 5 | Create registration form UI | Frontend | 3 | 2 |
| 6 | Create login form UI | Frontend | 2 | 3 |
| 7 | Add auth state management | Frontend | 3 | 4, 5, 6 |
| 8 | Write integration tests | QA | 5 | All |

**Total Estimate**: 24 story points
**Confidence**: 85% (based on 12 similar features)

### Risks Identified
- OAuth integration may add 5-8 additional points
- Email verification adds 3 points if required

[Accept All] [Modify] [Reject]
```

#### 5. Diagram Generator Agent

**Purpose**: Create architectural and technical diagrams from descriptions or code.

**Supported Diagram Types**:

| Type | Use Case | Format |
|------|----------|--------|
| **Sequence** | API flows, interactions | Mermaid |
| **Class** | Domain models, relationships | Mermaid |
| **Component** | System architecture | C4 Model |
| **Entity-Relationship** | Database schema | Mermaid ERD |
| **Flowchart** | Process flows | Mermaid |
| **Architecture** | System overview | ArchiMate |

**Example Generation**:

```
User: Generate a sequence diagram for user login

AI Response:

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as Auth API
    participant DB as Database
    participant Redis as Session Store

    U->>FE: Enter credentials
    FE->>API: POST /auth/login
    API->>DB: Validate credentials
    DB-->>API: User record
    API->>API: Generate JWT
    API->>Redis: Store session
    API-->>FE: JWT + refresh token
    FE->>FE: Store tokens
    FE-->>U: Redirect to dashboard
```

[Copy Mermaid] [Edit] [Insert into Page]
```

#### 6. Pattern Matcher Agent

**Purpose**: Identify recurring patterns and suggest standardization.

**Capabilities**:
- Detect code patterns across codebase
- Identify anti-patterns
- Suggest pattern libraries
- Track pattern adoption

**Pattern Categories**:

| Category | Examples |
|----------|----------|
| **Architecture** | Repository, Service Layer, Event Sourcing |
| **Design** | Factory, Strategy, Observer, Decorator |
| **API** | RESTful conventions, Error handling, Pagination |
| **Testing** | Arrange-Act-Assert, Test doubles, Fixtures |
| **Security** | Input validation, Authentication, Authorization |

#### 7. Retrospective Analyst Agent

**Purpose**: Analyze sprint data and generate insights for retrospectives.

**Triggers**:
- Sprint completion
- Manual analysis request
- Scheduled weekly digest

**Outputs**:
```yaml
sprint_summary:
  velocity: 42 points (↑15% from avg)
  completion_rate: 87%
  carryover: 3 issues

insights:
  - "Testing tasks took 40% longer than estimated"
  - "Frontend tasks consistently under-estimated"
  - "Code review cycle time improved by 25%"

recommendations:
  - "Consider adding QA buffer for integration tasks"
  - "Pair programming showed 30% fewer defects"
  - "Morning standups correlated with faster blocker resolution"

metrics:
  cycle_time_avg: "2.3 days"
  pr_review_time: "4.2 hours"
  bug_injection_rate: "0.12 per feature"
```

#### 8. Knowledge Search Agent

**Purpose**: Semantic search across all workspace content.

**Searchable Content**:
- Issues and comments
- Pages and documentation
- Code and commits
- Slack/Discord messages (if integrated)
- External linked documents

**Features**:
- Natural language queries
- Context-aware results
- Related content suggestions
- Answer synthesis from multiple sources

**Example Query**:
```
User: "How do we handle rate limiting in our API?"

AI Response:

## Rate Limiting Implementation

Based on workspace knowledge:

### Current Implementation
Rate limiting is implemented in `api/middleware/rate_limit.py` using
Redis-based token bucket algorithm. (Source: API Architecture Doc)

### Configuration
- Default: 60 requests/minute per user
- Authenticated: 120 requests/minute
- Admin: Unlimited

### Related Resources
1. [ADR-0015: Rate Limiting Strategy](link)
2. [Issue #234: Add rate limit headers](link)
3. [Page: API Guidelines - Rate Limiting Section](link)

### Code Reference
`api/middleware/rate_limit.py:45-78`
```

---

## AI Feature Details

### Issue AI Assistance

#### Smart Issue Creation

When creating an issue, AI assists with:

| Feature | Trigger | AI Action |
|---------|---------|-----------|
| **Title Enhancement** | User types title | Suggest clearer, searchable title |
| **Description Expansion** | Partial description | Generate acceptance criteria, steps to reproduce |
| **Label Suggestion** | Issue content | Recommend relevant labels |
| **Priority Inference** | Keywords, similar issues | Suggest appropriate priority |
| **Assignee Recommendation** | Content, code ownership | Suggest based on expertise |
| **Duplicate Detection** | Issue creation | Flag potential duplicates |

#### Issue Decomposition

```
┌─────────────────────────────────────────────────────────────────┐
│                    ISSUE DECOMPOSITION FLOW                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Epic/Feature Description                                       │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │   AI Analysis   │                                           │
│  │  • Parse intent │                                           │
│  │  • Identify scope│                                          │
│  │  • Find similar │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │  Suggest Tasks  │ ──→ │  User Refines   │                   │
│  │  • Subtasks     │     │  • Add/Remove   │                   │
│  │  • Estimates    │     │  • Modify       │                   │
│  │  • Dependencies │     │  • Approve      │                   │
│  └─────────────────┘     └────────┬────────┘                   │
│                                   │                             │
│                                   ▼                             │
│                          Create Sub-Issues                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Documentation AI

#### Auto-Documentation Pipeline

```
Code Change
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Extract   │ ──→ │   Generate  │ ──→ │   Review    │
│   Context   │     │    Draft    │     │   & Edit    │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
• Function signature  • Description        • Human approval
• Existing comments   • Parameters         • Modifications
• Usage patterns      • Return values      • Publication
• Test cases          • Examples
```

#### Living Documentation

AI maintains documentation freshness:

| Check | Frequency | Action |
|-------|-----------|--------|
| Code-Doc Sync | On PR merge | Flag outdated sections |
| Broken Links | Daily | Fix or flag for removal |
| Usage Analytics | Weekly | Archive unused docs |
| Completeness | On-demand | Identify missing docs |

### Code Review AI

#### Review Dimensions

```
┌─────────────────────────────────────────────────────────────────┐
│                    CODE REVIEW DIMENSIONS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Architecture│  │  Security   │  │Performance │            │
│  │  Compliance │  │   Analysis  │  │  Impact    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│        │               │                │                      │
│        ▼               ▼                ▼                      │
│   • Pattern use    • OWASP checks   • Complexity           │
│   • Layer bounds   • Input valid.   • N+1 queries          │
│   • Dependencies   • Auth/AuthZ     • Memory leaks         │
│                    • Secrets        • Async issues          │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Quality   │  │   Testing   │  │Documentation│            │
│  │   Metrics   │  │   Coverage  │  │   Quality   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│        │               │                │                      │
│        ▼               ▼                ▼                      │
│   • Readability    • Coverage %     • Comment clarity       │
│   • Maintainability• Edge cases     • API docs              │
│   • Code smells    • Test quality   • README updates        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Review Output Format

```markdown
## 🤖 AI Code Review

### Summary
- **Files Changed**: 12
- **Lines Added**: 234
- **Lines Removed**: 89
- **Overall Score**: 82/100

### Critical Issues (Must Fix)
1. **SQL Injection Risk** - `user_controller.py:67`
   ```python
   # Current (vulnerable)
   query = f"SELECT * FROM users WHERE id = {user_id}"

   # Suggested fix
   query = "SELECT * FROM users WHERE id = %s"
   cursor.execute(query, (user_id,))
   ```

### Warnings (Should Fix)
1. **Missing error handling** - `payment_service.py:123`
2. **Potential memory leak** - `cache_manager.py:45`

### Suggestions (Nice to Have)
1. Consider extracting method at line 89-120
2. Add type hints for public methods

### Testing Gaps
- [ ] Missing test for edge case: empty input
- [ ] No integration test for payment flow

### Documentation Impact
- [ ] Update API docs for new endpoint
- [ ] Add changelog entry
```

### Sprint Planning AI

#### Velocity Prediction

```
Historical Data
      │
      ├── Sprint velocities (last 6 sprints)
      ├── Team capacity changes
      ├── Issue complexity scores
      └── External factors (holidays, etc.)
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VELOCITY PREDICTION MODEL                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Features:                                                      │
│  • Rolling average velocity                                     │
│  • Capacity adjustment factor                                   │
│  • Carryover penalty                                            │
│  • Complexity distribution                                       │
│                                                                 │
│  Output:                                                        │
│  • Predicted velocity: 38 points                                │
│  • Confidence interval: 35-42 points                            │
│  • Risk factors: 2 team members on PTO                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Sprint Composition Suggestions

```
AI Sprint Planning Assistant

Based on your backlog and team capacity:

## Recommended Sprint Composition

### Must Include (Business Priority)
- AUTH-234: Password reset flow (5 pts) - P0
- API-567: Rate limiting fix (3 pts) - P0

### Recommended (Balanced Load)
- FE-890: Dashboard redesign (8 pts) - P1
- BE-123: Cache optimization (5 pts) - P1

### Risk Items (Uncertainty)
- INTEG-456: Third-party API migration (13 pts)
  ⚠️ High uncertainty - consider spike first

### Capacity Analysis
| Member | Available | Assigned | Skills Match |
|--------|-----------|----------|--------------|
| Alice  | 100%      | 13 pts   | ✅ Backend   |
| Bob    | 80%       | 10 pts   | ✅ Frontend  |
| Carol  | 50%       | 5 pts    | ⚠️ New to codebase |

Total: 28/38 points allocated

[Auto-fill Remaining] [Adjust] [Finalize]
```

---

## RAG (Retrieval-Augmented Generation) Pipeline

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAG PIPELINE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    INDEXING LAYER                        │   │
│  │                                                          │   │
│  │  Sources:                  Processing:                   │   │
│  │  ┌──────────┐             ┌──────────┐                  │   │
│  │  │  Issues  │────────────→│  Chunker │                  │   │
│  │  │  Pages   │             │  (512tok)│                  │   │
│  │  │  Code    │             └────┬─────┘                  │   │
│  │  │  Commits │                  │                        │   │
│  │  │  Docs    │                  ▼                        │   │
│  │  └──────────┘             ┌──────────┐                  │   │
│  │                           │Embeddings│                  │   │
│  │                           │ (Local)  │                  │   │
│  │                           └────┬─────┘                  │   │
│  │                                │                        │   │
│  │                                ▼                        │   │
│  │                           ┌──────────┐                  │   │
│  │                           │ pgvector │                  │   │
│  │                           │  Store   │                  │   │
│  │                           └──────────┘                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    RETRIEVAL LAYER                       │   │
│  │                                                          │   │
│  │  Query                     Retrieval                     │   │
│  │  ┌──────────┐             ┌──────────┐                  │   │
│  │  │  User    │────────────→│ Semantic │                  │   │
│  │  │  Query   │             │  Search  │                  │   │
│  │  └──────────┘             └────┬─────┘                  │   │
│  │                                │                        │   │
│  │                                ▼                        │   │
│  │                           ┌──────────┐                  │   │
│  │                           │ Re-Rank  │                  │   │
│  │                           │ (Top-K)  │                  │   │
│  │                           └────┬─────┘                  │   │
│  │                                │                        │   │
│  │                                ▼                        │   │
│  │                           ┌──────────┐                  │   │
│  │                           │ Context  │                  │   │
│  │                           │ Assembly │                  │   │
│  │                           └──────────┘                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    GENERATION LAYER                      │   │
│  │                                                          │   │
│  │  ┌──────────┐     ┌──────────┐     ┌──────────┐        │   │
│  │  │ Context  │ ──→ │   LLM    │ ──→ │ Response │        │   │
│  │  │+ Query   │     │  + Prompt│     │+ Sources │        │   │
│  │  └──────────┘     └──────────┘     └──────────┘        │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Embedding Models

Embeddings are generated using the configured LLM provider's embedding API:

| Model | Provider | Dimensions | Use Case |
|-------|----------|------------|----------|
| `text-embedding-3-small` | OpenAI | 1536 | Default, cost-effective |
| `text-embedding-3-large` | OpenAI | 3072 | Higher quality retrieval |
| `voyage-code-2` | Anthropic | 1536 | Code-specific embeddings |

**Note**: Embeddings are stored in PostgreSQL using the pgvector extension.

### Index Update Strategy

| Content Type | Update Trigger | Index Strategy |
|--------------|----------------|----------------|
| Issues | Create/Update | Real-time |
| Pages | Save | Debounced (30s) |
| Code | PR Merge | Batch (nightly) |
| Comments | Create | Real-time |

---

## LLM Provider Configuration

### BYOK (Bring Your Own Key) Model

Pilot Space requires users to provide their own API keys for LLM providers. This approach:
- Gives users full control over AI costs
- Eliminates complex metering and billing
- Allows users to leverage existing API credits
- Ensures data flows directly to user's chosen provider

### Supported Providers

```yaml
# User configuration (workspace settings or environment variables)

providers:
  openai:
    api_key: ${OPENAI_API_KEY}  # User-provided
    models:
      - gpt-4o           # Recommended for code review
      - gpt-4o-mini      # Cost-effective for suggestions
    default_model: gpt-4o

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}  # User-provided
    models:
      - claude-sonnet-4-20250514  # Excellent for code analysis
      - claude-3-5-haiku-20241022  # Fast, cost-effective
    default_model: claude-sonnet-4-20250514

  azure_openai:
    api_key: ${AZURE_OPENAI_KEY}  # User-provided
    endpoint: ${AZURE_OPENAI_ENDPOINT}  # User-provided
    deployment_name: gpt-4
    # Enterprise preferred for compliance requirements

# Task-to-provider routing (configurable)
routing:
  code_review:
    preferred: [anthropic, openai]
    model: claude-sonnet-4-20250514

  documentation:
    preferred: [openai, anthropic]
    model: gpt-4o-mini

  issue_enhancement:
    preferred: [openai, anthropic]
    model: gpt-4o-mini

  semantic_search:
    preferred: [openai]
    model: text-embedding-3-small
```

### Cost Optimization

| Strategy | Implementation |
|----------|----------------|
| **Tiered Models** | Use gpt-4o-mini/haiku for simple tasks, gpt-4o/sonnet for complex |
| **Caching** | Cache embeddings and common query responses (Redis) |
| **Batching** | Batch similar requests where possible |
| **Smart Routing** | Route to cheapest capable model per task type |

### Provider Comparison

| Provider | Strengths | Best For | Cost |
|----------|-----------|----------|------|
| **OpenAI** | Fast, reliable, good all-around | Documentation, search | $$ |
| **Anthropic** | Excellent code understanding | Code review, architecture | $$$ |
| **Azure OpenAI** | Enterprise compliance, private endpoints | Enterprise deployments | $$ |

---

## AI Trigger Points

### Autonomy Model: Critical-Only Approval

AI actions follow a tiered autonomy model (configurable per project):

| Action Type | Default Behavior | Requires Approval |
|-------------|------------------|-------------------|
| **Suggestions** (labels, priority) | Show in UI | No (user accepts/rejects) |
| **State Transitions** (PR events) | Auto-execute + notify | No (configurable) |
| **PR Comments** (review feedback) | Auto-post | No |
| **Issue Creation** (from decomposition) | Require approval | Yes |
| **Documentation Updates** | Require approval | Yes |
| **Destructive Actions** (delete, archive) | Always require | Yes (not configurable) |

### Automatic Triggers

| Event | AI Action | Notification |
|-------|-----------|--------------|
| Issue Created | Label/Priority suggestion | Inline in UI |
| PR Opened | Code + architecture review | PR comment |
| PR Merged | Update linked issue state | Activity log |
| Sprint Completed | Generate retrospective insights | Notification |

### On-Demand Triggers (AI-Assisted)

| User Action | AI Response |
|-------------|-------------|
| `/ai review` | Comprehensive code review |
| `/ai plan <feature>` | Task decomposition |
| `/ai doc <file>` | Documentation generation |
| `/ai diagram <type>` | Diagram generation |
| `/ai explain` | Code/decision explanation |
| `/ai search <query>` | Semantic knowledge search |

### Comment Triggers

AI responds to special comment patterns:

```markdown
@pilot-ai review architecture
@pilot-ai suggest tests
@pilot-ai explain this function
@pilot-ai generate docs
@pilot-ai find similar issues
```

---

## Privacy & Security

### Data Handling

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA FLOW CONTROLS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Data                     AI Processing                    │
│  ┌──────────┐                 ┌──────────┐                     │
│  │Workspace │                 │ Context  │                     │
│  │  Data    │─────────────────│ Builder  │                     │
│  └──────────┘                 └────┬─────┘                     │
│       │                            │                            │
│       ▼                            ▼                            │
│  ┌──────────┐                 ┌──────────┐                     │
│  │   PII    │                 │  Prompt  │                     │
│  │ Filtering│                 │ Assembly │                     │
│  └──────────┘                 └────┬─────┘                     │
│       │                            │                            │
│       ▼                            ▼                            │
│  ┌──────────┐                 ┌──────────┐                     │
│  │Anonymized│                 │   LLM    │                     │
│  │ Context  │────────────────▶│   API    │                     │
│  └──────────┘                 └────┬─────┘                     │
│                                    │                            │
│                               No data retained                  │
│                               by LLM provider                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Privacy Controls

| Setting | Default | Options |
|---------|---------|---------|
| PII Masking | Enabled | Per workspace toggle |
| Code Sharing with AI | Enabled | Per project toggle |
| Telemetry | Opt-in | Disable all |

### Data Privacy Considerations

Since Pilot Space uses BYOK (external LLM providers):

1. **Data flows to your chosen LLM provider** - Review their data policies
2. **OpenAI/Anthropic API agreements** - Enterprise plans offer zero data retention
3. **Azure OpenAI** - Data stays within your Azure tenant (enterprise recommended)
4. **PII Masking** - Enable to scrub sensitive data before sending to LLM

**For maximum privacy (Enterprise)**:
- Use Azure OpenAI with private endpoints
- Enable PII masking at workspace level
- Review and configure data retention policies with your LLM provider
- Enable audit logging for all AI operations

---

## Configuration & Settings

### Workspace-Level AI Settings

```yaml
workspace:
  ai:
    enabled: true
    default_provider: openai  # openai | anthropic | azure_openai

    # API Keys (encrypted at rest)
    credentials:
      openai_api_key: "sk-..."      # User-provided
      anthropic_api_key: "sk-..."   # User-provided (optional)
      azure_endpoint: "https://..." # User-provided (optional)

    features:
      auto_label: true
      auto_priority: true
      duplicate_detection: true

    review:
      auto_review_prs: true
      review_types: [architecture, security, quality]

    documentation:
      auto_generate: false
      update_on_merge: true
      diagram_format: mermaid

    agents:
      pr_review: enabled
      task_planner: enabled
      doc_generator: enabled
      knowledge_search: enabled
```

### Project-Level Overrides

```yaml
project:
  ai:
    # Override workspace settings
    auto_review_prs: false  # Disable for this project

    # Custom patterns
    architecture_patterns:
      - name: "Service Layer"
        path: "src/services/**"
        rules: ["no-direct-db-access", "inject-dependencies"]

    # Custom prompts
    review_instructions: |
      Focus on Python type hints and async patterns.
      Flag any blocking I/O in async functions.
```

---

## Metrics & Observability

### AI Usage Metrics

| Metric | Description | Dashboard |
|--------|-------------|-----------|
| Suggestions/day | AI suggestions generated | Usage |
| Acceptance rate | % of suggestions accepted | Quality |
| Response time | AI response latency | Performance |
| Token usage | LLM token consumption | Cost |
| Error rate | Failed AI operations | Reliability |

### Quality Metrics

| Metric | Measurement |
|--------|-------------|
| Review accuracy | Human override rate |
| Doc quality | User edits after generation |
| Prediction accuracy | Estimate vs actual |
| Search relevance | Click-through rate |

---

*Document Version: 1.0*
*Last Updated: 2026-01-20*
*Author: Pilot Space Team*
