---
name: request-clarification-analyzer
description: This skill should be used when user requests are ambiguous, incomplete, or require contextual understanding. It analyzes the current project (tech stack, architecture, patterns, domain) to generate intelligent, context-aware clarification questions with recommended options. Use this proactively when requests lack critical details, have multiple interpretations, or when existing project patterns can inform the implementation approach.
---

# Request Clarification Analyzer

This skill transforms ambiguous user requests into clear, actionable requirements by analyzing the current project context and generating intelligent clarification questions.

## When to Use This Skill

**Proactive triggers** (use automatically when ANY apply):

- Scope boundaries unclear ("add feature" without specifying where)
- Multiple valid approaches exist (new service vs extend existing)
- Breaking changes possible (API modifications)
- Security implications (permissions, auth requirements)
- Missing technical details (data types, relationships, constraints)
- User request contains vague terms ("add authentication", "improve performance", "fix bug")
- Request conflicts with existing patterns or architecture
- Domain-specific context needed to understand intent

**Reactive triggers** (use when asked):

- User explicitly asks for clarification or options
- User seems unsure about implementation approach
- User provides incomplete requirements
- User asks "what do you need to know?"

**Skip clarification when ALL true**:

- User provided explicit, complete requirements
- Task is well-defined (specific file path, clear bug with repro)
- User explicitly said "just do it" or "proceed"
- Single obvious implementation approach

## Quick Mode vs Full Mode

**Quick Mode** (1-2 questions, ~1 minute):
- Simple feature additions with clear scope
- Bug fixes needing minor clarification
- Output: Direct AskUserQuestion with 2-3 options

**Full Mode** (3-5 questions, ~3-5 minutes):
- Complex features touching multiple layers
- Architecture decisions with trade-offs
- New entities requiring schema design
- Output: Progressive clarification with scoring

## Tool Integration

This skill leverages specific tools for effective clarification:

### Required Tools

**For Project Analysis** (use `mcp__serena` tools):
```
mcp__serena__get_symbols_overview  → Understand file structure
mcp__serena__find_symbol           → Locate specific classes/functions
mcp__serena__search_for_pattern    → Find usage patterns
mcp__serena__find_referencing_symbols → Trace dependencies
mcp__serena__list_dir              → Explore directory structure
```

**For Question Presentation** (use `AskUserQuestion` tool):
```python
# Present clarification questions with concrete options
AskUserQuestion(
    questions=[{
        "question": "Which authentication pattern should we use?",
        "header": "Auth Pattern",
        "options": [
            {"label": "JWT + RBAC (Recommended)", "description": "Matches existing auth-service pattern"},
            {"label": "API Key", "description": "For service-to-service communication"},
            {"label": "OAuth2", "description": "For external integrations"}
        ],
        "multiSelect": False
    }]
)
```

**For Progress Tracking** (use `TodoWrite` tool):
- Track clarification questions asked
- Mark questions as answered
- Build refined requirements progressively

### Tool Usage Flow

```
1. Receive ambiguous request
   ↓
2. Use mcp__serena tools to analyze project context
   ↓
3. Identify ambiguities and generate questions
   ↓
4. Present questions via AskUserQuestion (max 4 questions per call)
   ↓
5. Integrate answers and refine requirements
   ↓
6. Hand off to downstream skills (SDD, backend-payload-api, etc.)
```

---

## Core Capabilities

### 1. Project Context Analysis

Systematically analyze the current project to inform clarification questions.

#### Analysis Dimensions

**Tech Stack Discovery**:

- Languages & versions (Python 3.12, TypeScript 5.x, etc.)
- Frameworks (FastAPI, React, Next.js, etc.)
- Databases (PostgreSQL, DuckDB, Redis, etc.)
- Key libraries & their purposes
- Infrastructure (Docker, K8s, cloud providers)

**Architecture Patterns**:

- Repository pattern, Service layer, MVC, etc.
- Three-tier, microservices, monolith, etc.
- Event-driven, REST, GraphQL, etc.
- Authentication/authorization approach
- State management patterns

**Existing Features**:

- Core domain entities
- User types & roles
- Business logic boundaries
- Integration points
- API endpoints & contracts

**Code Conventions**:

- Naming conventions
- File structure patterns
- Testing approaches
- Error handling strategies
- Documentation standards

**Domain Context**:

- Business domain (e-commerce, ITS, healthcare, etc.)
- Industry standards (GDPR, HIPAA, traffic regulations, etc.)
- User personas
- Key workflows
- Terminology & glossary

#### Discovery Process (with Tool Calls)

```
1. Scan repository structure:
   - mcp__serena__list_dir(relative_path=".", recursive=False)
   - Read: pyproject.toml, package.json, CLAUDE.md
   - Identify: Primary languages, frameworks, build tools

2. Analyze architecture:
   - Read: README.md, docs/architecture.md, CLAUDE.md
   - mcp__serena__list_dir(relative_path="apps", recursive=False)
   - mcp__serena__list_dir(relative_path="libs", recursive=False)
   - Identify: Microservices, shared libraries, configuration

3. Extract domain knowledge:
   - mcp__serena__find_symbol(name_path_pattern="*Entity", depth=1)
   - mcp__serena__get_symbols_overview(relative_path="apps/{service}/src/ubits/{service}/dto/")
   - Identify: Core entities, relationships, business rules

4. Study existing patterns:
   - mcp__serena__search_for_pattern(substring_pattern="class.*Repository")
   - mcp__serena__find_symbol(name_path_pattern="*Service", include_body=False)
   - Sample: 2-3 similar features/endpoints for pattern extraction

5. Build context summary:
   - Tech Stack: Languages, frameworks, databases
   - Architecture: Patterns, structure, communication
   - Domain: Entities, workflows, terminology
   - Conventions: Naming, file structure, testing
```

#### Example Output

```markdown
## Project Context Summary

**Tech Stack**:
- Python 3.12 with FastAPI
- PostgreSQL + DuckDB (time-series)
- Redis (caching), Kafka (events)
- YOLO11 + TensorRT (ML inference)

**Architecture**:
- Three-tier isolation (Edge → Worker → Data Center)
- Repository + Service layer pattern
- Event-driven with Kafka
- Async/await throughout

**Domain**:
- Intelligent Transportation System (ITS)
- Camera-based traffic monitoring
- Vehicle detection, license plate recognition
- Real-time analytics with 30-day retention

**Key Entities**:
- Camera, CameraConfig, CameraEvent
- User, Tenant, Permission
- Vehicle, LicensePlate, DetectionEvent

**Conventions**:
- Namespace: `ubits.*` (never `src.*`)
- File size: ≤700 lines
- Tests: >95% coverage, TDD approach
- Async: All I/O operations
```

### 2. Ambiguity Detection

Identify unclear, incomplete, or ambiguous aspects of user requests.

#### Detection Categories

**Vague Terms**:

- "Authentication" → Which method? (JWT, OAuth2, session, API key)
- "Performance" → Which metric? (latency, throughput, memory, CPU)
- "Database" → Which one? (existing, new, which type)
- "API" → REST, GraphQL, gRPC, WebSocket?
- "Dashboard" → For whom? (admin, user, analytics)

**Missing Scope**:

- "Add user management" → CRUD only? Roles? Permissions? Profile? Password reset?
- "Fix bug" → Which component? What behavior? Expected vs actual?
- "Improve caching" → Which data? What duration? Invalidation strategy?

**Multiple Interpretations**:

- "Add notifications" → Email? Push? In-app? SMS? All?
- "Export data" → Which format? (CSV, JSON, PDF, Excel) Which data? Full or filtered?
- "Real-time updates" → WebSocket? SSE? Polling? What latency requirement?

**Architecture Conflicts**:

- Request implies direct DB access in three-tier architecture (violates tiers)
- Request suggests synchronous where async is required
- Request conflicts with existing authentication pattern

**Domain Gaps**:

- Request uses incorrect terminology for the domain
- Request misunderstands business rules
- Request unclear about user types/roles

#### Detection Process

```
1. Parse user request:
   - Extract: Main action, target component, constraints
   - Identify: Technical terms, domain terms, vague terms

2. Check against project context:
   - Does request align with architecture?
   - Does terminology match domain glossary?
   - Does approach match existing patterns?

3. Identify ambiguities:
   - List vague terms with multiple meanings
   - Note missing critical details
   - Flag multiple valid interpretations
   - Detect potential conflicts

4. Prioritize by impact:
   - CRITICAL: Ambiguity affects architecture/scope
   - HIGH: Ambiguity affects security/performance
   - MEDIUM: Ambiguity affects UX/maintainability
   - LOW: Ambiguity is cosmetic/preference
```

### 3. Context-Aware Question Generation

Generate clarification questions informed by project context and existing patterns.

#### Question Types

**Pattern-Based Questions**:

Use existing project patterns to offer concrete options.

```markdown
**Example**: User asks "Add authentication"

**Generated Question**:
This project uses JWT tokens with role-based permissions (see auth-service).

**Which authentication pattern should we follow?**

| Option | Description | Existing Example |
|--------|-------------|------------------|
| A | JWT with role-based access (standard pattern) | auth-service/middleware/auth.py |
| B | API key for service-to-service | worker-auth-client pattern |
| C | OAuth2 client credentials | External integrations |

**Recommended**: Option A - Matches existing user-facing auth pattern
```

**Architecture-Aware Questions**:

Consider architectural constraints when generating options.

```markdown
**Example**: User asks "Add real-time camera feed viewer"

**Generated Question**:
This project uses three-tier architecture (Edge → Worker → Data Center).
Data Center tier NEVER accesses raw camera streams (security constraint).

**Which tier should handle this feature?**

| Option | Description | Implications |
|--------|-------------|--------------|
| A | Edge tier (direct camera access) | Requires edge deployment, local viewing only |
| B | Process at Worker, stream to Data Center | Respects three-tier, requires video encoding |
| C | Store snapshots at Worker, view at Data Center | Simplest, not "real-time" (5s delay) |

**Recommended**: Option C - Balances requirements with architecture constraints

**Note**: Option A requires explicit justification for breaking tier isolation.
```

**Domain-Informed Questions**:

Leverage domain knowledge to clarify business requirements.

```markdown
**Example**: User asks "Add traffic violation detection"

**Generated Question**:
ITS domain has standard violation types (speeding, red light, illegal turn, etc.).

**Which violations should be detected?**

| Option | Violation Types | ML Model Complexity | Legal Requirements |
|--------|----------------|---------------------|-------------------|
| A | Speeding only | Simple (existing speed detection) | Requires calibrated cameras |
| B | Red light violations | Medium (needs traffic signal data) | Requires signal integration |
| C | Comprehensive (5+ types) | High (multiple ML models) | Requires legal compliance audit |

**Recommended**: Option A - Leverages existing capabilities, lowest complexity

**Domain Context**: Traffic violations require specific legal compliance (varies by region).
Consider consulting legal requirements before implementation.
```

**Constraint-Discovery Questions**:

Uncover hidden requirements through targeted questions.

```markdown
**Example**: User asks "Store video recordings"

**Generated Question**:
Video storage has multiple dimensions requiring clarification:

**Q1: Retention Policy**
- How long should recordings be kept?
- Industry standard: 30 days (general), 90 days (incidents), 7 years (legal hold)

**Q2: Privacy Requirements**
- GDPR compliance needed? (license plate blurring, data minimization)
- This project already implements license plate hashing at Worker tier

**Q3: Storage Volume**
- Expected camera count? Video quality? Compression?
- Calculation: 100 cameras × 1080p × H.265 × 24h = ~5TB/day

**Recommended Approach**:
- Retention: 30 days rolling (balances cost & utility)
- Privacy: Use existing license plate hashing (GDPR compliant)
- Storage: Implement tiered storage (hot: 7 days, cold: 23 days)
```

#### Question Generation Process

```
1. Identify ambiguous aspect from detection phase

2. Load relevant project context:
   - Existing patterns for this feature type
   - Architecture constraints
   - Domain knowledge
   - Similar implementations

3. Generate 2-4 concrete options:
   - Option A: Most aligned with existing patterns (RECOMMENDED)
   - Option B: Alternative approach with tradeoffs
   - Option C: Advanced/comprehensive approach
   - Option D: Minimal/simple approach (if applicable)

4. For each option, document:
   - Description (what it means)
   - Implications (consequences)
   - Existing example (if any)
   - Pros/cons or tradeoffs

5. Provide recommendation:
   - Based on: Existing patterns, architecture, complexity
   - Reasoning: Why this option is recommended
   - Alternatives: When other options might be better

6. Add contextual notes:
   - Domain considerations
   - Legal/compliance requirements
   - Performance implications
   - Security concerns
```

### 4. Interactive Clarification Flow

Guide users through clarification with progressive disclosure.

#### Flow Structure

```
Initial Request
     ↓
Analyze Project Context (automatic)
     ↓
Detect Ambiguities (1-5 critical items)
     ↓
Generate Questions (one at a time)
     ↓
Present Question with Options
     ↓
Wait for User Response
     ↓
Integrate Answer
     ↓
Next Question or Proceed
```

#### Progressive Disclosure

**Present one question at a time** to avoid overwhelming:

```markdown
## Clarification Needed (1 of 3)

**Context**: You asked to "add authentication"

[Question with options as table]

**You can respond with**:
- Letter (A, B, C)
- "recommended" (uses Option A)
- Custom answer (describe your preference)
```

**After answer received**:

```markdown
✓ Authentication approach: JWT with role-based access

## Clarification Needed (2 of 3)

**Context**: JWT authentication requires user storage

[Next question with options]
```

#### Maximum Questions Rule

- **Limit**: 5 questions maximum per request
- **Prioritization**: By impact (critical → high → medium → low)
- **Bundling**: Related questions can be combined if logical
- **User control**: User can say "skip remaining" to proceed with defaults

#### Answer Integration

After each answer:

```
1. Record answer in context:
   - Store as structured data (not just text)
   - Link to relevant project components
   - Track dependencies on other answers

2. Update requirement understanding:
   - Refine scope based on answer
   - Adjust subsequent questions if needed
   - Drop questions that became irrelevant

3. Build implementation context:
   - Map answers to specific files/patterns
   - Identify required changes
   - Generate task implications
```

### 5. Smart Recommendations

Provide intelligent recommendations based on:

- **Project patterns**: What already exists
- **Best practices**: Industry standards
- **Complexity**: Prefer simple over complex
- **Maintainability**: Prefer consistent over novel
- **Performance**: Known optimization patterns
- **Security**: Proven security patterns

#### Recommendation Algorithm

```
For each question:
  Score each option (0-100):
    +30: Matches existing project pattern
    +20: Follows project architecture
    +15: Uses established technologies in project
    +10: Simple to implement
    +10: Secure by default
    +10: Good performance characteristics
    +5:  Well-documented approach

  Recommend highest-scoring option
  If score difference <10: Present as equal alternatives
  If score difference >30: Strong recommendation
```

#### Recommendation Presentation

```markdown
**Recommended**: Option A - JWT with role-based access (Score: 85)

**Why recommended**:
- Matches existing auth pattern (see auth-service/middleware/auth.py)
- Already has User/Role/Permission models in database
- Test utilities exist (tests/fixtures/auth.py)
- Team familiar with this approach

**When to choose alternatives**:
- Option B if service-to-service (no user context)
- Option C if integrating with external OAuth provider
```

### 6. Conflict Resolution

Detect and resolve conflicts between user requests and project constraints.

#### Conflict Types

**Architecture Violations**:

```markdown
**Conflict Detected**: Request violates three-tier isolation

**User Request**: "Data Center should directly access camera streams"

**Project Constraint**: Three-tier architecture prohibits Data Center → Edge communication

**Resolution Options**:

A. **Redesign request** - Process at Worker tier, send metadata to Data Center (RECOMMENDED)
   - Maintains architecture integrity
   - Worker already has camera access
   - Data Center gets results via Kafka events

B. **Justify exception** - Document why tier violation is necessary
   - Requires explicit approval
   - Must document security implications
   - Add to technical debt register

C. **Clarify misunderstanding** - User may not need raw stream
   - What's the actual goal? (monitoring, alerts, analytics)
   - Alternative solutions available?
```

**Pattern Mismatches**:

```markdown
**Conflict Detected**: Request suggests pattern inconsistent with project

**User Request**: "Add REST endpoint for real-time updates"

**Project Pattern**: Real-time features use Kafka events + WebSocket (see camera-service)

**Suggested Clarification**:

"This project uses event-driven architecture for real-time features. REST endpoints are used for CRUD operations, not real-time updates.

**Did you mean**:
A. Add CRUD endpoint for configuration (REST) + real-time updates via WebSocket (RECOMMENDED)
B. Add SSE (Server-Sent Events) endpoint for one-way updates
C. Actually need request/response, not real-time (use REST)

**Existing Example**: camera-service/api/websocket.py for real-time camera events"
```

**Domain Misunderstandings**:

```markdown
**Conflict Detected**: Request uses incorrect domain terminology

**User Request**: "Add parking violation detection for moving vehicles"

**Domain Issue**: "Parking violation" implies stationary vehicles, conflicts with "moving"

**Clarification**:

"In ITS domain:
- **Parking violations**: Illegal parking (stationary)
- **Moving violations**: Speeding, red light, illegal turn (moving)

**Which type do you need**:
A. Parking violations (stationary vehicle detection)
B. Moving violations (traffic law enforcement)
C. Both (comprehensive violation detection)

**Current Capabilities**: Project already detects vehicles and tracks speed (moving violations simpler)"
```

## Workflow Examples

### Example 1: Vague Feature Request

**User Request**: "Add user dashboard"

**Analysis**:

```
1. Detect ambiguities:
   - Which user type? (admin, regular user, tenant)
   - What data? (personal, system, analytics)
   - What actions? (view-only, interactive)
   - What tech? (React, Next.js, server-rendered)

2. Load project context:
   - Tech: FastAPI backend, separate frontend planned
   - Users: Regular users, admins, tenants with isolation
   - Data: Cameras, events, detections, analytics
   - Pattern: API endpoints at Data Center tier

3. Prioritize questions:
   - CRITICAL: User type (affects data access & permissions)
   - HIGH: Data to display (affects API design)
   - MEDIUM: Interaction level (affects complexity)
   - LOW: Tech stack (defer to existing patterns)
```

**Generated Questions**:

```markdown
## Clarification: User Dashboard (1 of 2)

**Context**: Project has three user types with different access levels

**Q1: Which user type is this dashboard for?**

| Option | User Type | Access Level | Existing Example |
|--------|-----------|--------------|------------------|
| A | Regular users (view own data) | Tenant-scoped | camera-service endpoints |
| B | Tenant admins (manage tenant) | Multi-user tenant scope | /api/v1/users |
| C | System admins (full access) | Cross-tenant | admin endpoints |

**Recommended**: Option A - Most common use case, simplest data access

---

## Clarification: User Dashboard (2 of 2)

**Context**: Based on "Regular users" selection

**Q2: What data should the dashboard display?**

| Category | Data Points | Complexity | API Endpoint Needed |
|----------|-------------|------------|---------------------|
| A | Camera status + recent events | Simple | Existing endpoints |
| B | Analytics + trends (charts) | Medium | New analytics endpoint |
| C | Comprehensive (live feeds + analytics + config) | High | Multiple new endpoints |

**Recommended**: Option A - Start with core functionality, iterate based on feedback

**Implementation Note**: All data already available via existing APIs, just needs frontend.
```

### Example 2: Conflicting Request

**User Request**: "Store all camera raw video for 6 months"

**Analysis**:

```
1. Detect conflicts:
   - Storage cost: ~900TB for 100 cameras × 6 months
   - Architecture: Edge processes, doesn't store long-term
   - Privacy: GDPR requires data minimization
   - Business rule: Current retention is 30 days

2. Calculate implications:
   - Storage: 100 cameras × 5TB/day × 180 days = 90 petabytes
   - Cost: ~$2M/month (AWS S3 Standard)
   - Bandwidth: Continuous upload from edge
   - Privacy: Risk of PII exposure

3. Identify real need:
   - Compliance? (legal hold)
   - Forensics? (incident investigation)
   - Quality assurance? (ML model training)
   - Audit trail? (system behavior verification)
```

**Generated Clarification**:

```markdown
## ⚠️ Request Requires Clarification

**User Request**: Store all camera raw video for 6 months

**Detected Issues**:

1. **Storage Volume**: 90 petabytes (~$2M/month)
2. **Privacy Conflict**: GDPR requires data minimization (current: 30 days)
3. **Architecture**: Not designed for long-term edge storage

**Before proceeding, need to understand the actual requirement**:

### What problem are you trying to solve?

| Use Case | Alternative Solution | Cost | Privacy Compliant |
|----------|---------------------|------|-------------------|
| Legal compliance | Store metadata + reconstruction capability | $5K/month | ✓ Yes |
| Incident investigation | Store flagged incidents only (90 days) | $50K/month | ✓ Yes |
| ML training | Store representative samples (rotating) | $10K/month | ✓ Yes |
| Full archival | Compressed + tiered storage | $200K/month | ✗ Requires legal review |

**Recommended**: Clarify use case first - likely solvable without full raw video

**Domain Context**: ITS systems typically store:
- Metadata: Indefinite (small footprint)
- Incidents: 90 days (legal requirement)
- Raw video: 7-30 days (operational needs)

**Would you like to explore an alternative that achieves your goal at lower cost/risk?**
```

### Example 3: Missing Context

**User Request**: "Fix the bug"

**Analysis**:

```
1. Missing information:
   - Which component?
   - What's broken?
   - Expected vs actual behavior?
   - How to reproduce?
   - Error messages/logs?

2. Cannot proceed without:
   - Component identification
   - Clear description of issue
```

**Generated Response**:

```markdown
## Insufficient Information: Need Bug Details

To fix the bug, I need more information:

### Q1: Which component has the bug?

| Component | Description |
|-----------|-------------|
| auth-service (Port 8001) | User authentication & authorization |
| camera-service (Port 8002) | Camera management & configuration |
| ml-inference (Worker tier) | Object detection & classification |
| event-processor (Worker tier) | Event streaming & processing |
| analytics-service (Port 8003) | Data aggregation & reporting |
| API Gateway | Request routing & rate limiting |
| Frontend | User interface |
| Other | Specify: __________ |

### Q2: What is the bug?

**Please provide**:
- Current behavior: What happens now?
- Expected behavior: What should happen?
- Steps to reproduce: How to trigger it?
- Error messages: Any logs or stack traces?
- Environment: Local, staging, production?

### Q3: When did this start?

- Just noticed (might be old)
- After recent deployment (regression)
- Always been there (original implementation issue)

**Example of good bug description**:

> Component: camera-service
> Issue: GET /api/v1/cameras returns 500 error
> Expected: Should return camera list
> Reproduce: Call endpoint as authenticated user
> Error: KeyError: 'tenant_id' in logs
> Started: After deployment of PR #123 yesterday
```

## Integration with Other Skills

This skill works **before** other implementation skills:

```
User Request (ambiguous)
     ↓
request-clarification-analyzer
     ├→ Analyze project context
     ├→ Detect ambiguities
     ├→ Generate questions
     ├→ Collect answers
     └→ Build clear requirement
     ↓
specification-driven-development
     ↓
Implementation Skills (backend-payload-api, etc.)
```

**Example Flow**:

```
User: "Add authentication"
  ↓
Clarification: JWT vs OAuth2 vs API Key?
User: "JWT with roles"
  ↓
Clarification: Which roles? New or use existing?
User: "Use existing User/Role models"
  ↓
Clear Requirement Generated:
  "Implement JWT authentication middleware using existing
   User/Role/Permission models from auth-service database.
   Apply to camera-service endpoints per permission matrix."
  ↓
SDD Specification Phase
  ↓
Implementation
```

## Best Practices

### Do

- ✅ Analyze project context before asking questions
- ✅ Provide recommended options based on existing patterns
- ✅ Limit to 5 questions maximum
- ✅ Present one question at a time
- ✅ Show examples from current codebase
- ✅ Calculate implications (cost, complexity, risk)
- ✅ Flag conflicts with architecture/domain
- ✅ Offer to skip remaining questions

### Don't

- ❌ Ask generic questions without context
- ❌ Present more than 4 options per question
- ❌ Ask questions whose answers are in the codebase
- ❌ Dump all questions at once
- ❌ Provide recommendations without reasoning
- ❌ Ignore existing project patterns
- ❌ Continue asking after user says "proceed"

## Success Indicators

**You're using this skill effectively when**:

- ✅ Questions reference existing project patterns
- ✅ Recommendations align with architecture
- ✅ User understands tradeoffs clearly
- ✅ Conflicts detected before implementation
- ✅ Final requirement is unambiguous
- ✅ Implementation path is clear

**You're NOT using this skill effectively if**:

- ❌ Questions could apply to any project
- ❌ No analysis of current codebase
- ❌ Recommendations without justification
- ❌ User confused by too many options
- ❌ Requirement still ambiguous after clarification
- ❌ Implementation approach unclear

## Integration with /dev Workflow

This skill is designed to be invoked from the `/dev` command workflow (Phase 1.3: Smart Clarification).

### Invocation from /dev

When `/dev` detects ambiguous requests, it invokes this skill:

```text
/dev add user profile feature
     ↓
Parse request → Scope unclear? → Invoke skill: request-clarification-analyzer
     ↓
Analyze project context → Generate questions → User answers
     ↓
Refined requirements → Continue /dev Phase 2 (Load Context)
```

### Clarification Triggers from /dev

The `/dev` command invokes this skill when ANY apply:
- Scope boundaries unclear ("add feature" without specifying where)
- Multiple valid approaches exist (new service vs extend existing)
- Breaking changes possible (API modifications)
- Security implications (permissions, auth requirements)
- Missing technical details (data types, relationships, constraints)

### Skip Clarification from /dev

The `/dev` command skips this skill when ALL true:
- User provided explicit, complete requirements
- Task is well-defined (specific file path, clear bug with repro)
- User explicitly said "just do it" or "proceed"
- Single obvious implementation approach

### Output Format for /dev

After clarification completes, provide structured output:

```markdown
## Clarification Complete

**Original Request**: [user's vague request]

**Refined Requirements**:
- [Clarified requirement 1]
- [Clarified requirement 2]

**Clarifications Made**:
1. [Question] → [User's answer] (Score: XX/100)
2. [Question] → [User's answer] (Score: XX/100)

**Project Patterns Applied**:
- Auth: [pattern + file reference]
- Data Access: [pattern + file reference]

**Ready for**: /dev Phase 2 (Load Context) or downstream skill
```

---

## Reference

For supporting documentation, see:

- **`references/question-templates.md`** - Reusable question patterns for 6 ambiguity types (scope, technical decisions, constraints, conflicts, priority, domain-specific) with customizable templates and real-world examples
- **`references/project-analysis-checklist.md`** - Systematic 6-phase project discovery process (structure → tech stack → architecture → domain → patterns → synthesis) for context-aware analysis
- **`references/scoring-algorithm.md`** - Complete explanation of 0-100 scoring system across 4 dimensions (Pattern Matching 40pts, Simplicity 30pts, Security 20pts, Performance 10pts) with calculation examples
- **`references/integration-patterns.md`** - How this skill integrates with specification-driven-development and domain-specific skills (backend-payload-api, service-repository-pattern, etc.) including handoff protocols and orchestration workflows
