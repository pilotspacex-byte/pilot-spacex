# Question Templates for Request Clarification

This reference provides reusable question patterns for different types of ambiguities detected in user requests.

## Template Structure

Each template follows this format:

```markdown
**Ambiguity Type**: [Category]
**Trigger Keywords**: [List of keywords that indicate this ambiguity]
**Question Pattern**: [Template with placeholders]
**Example**: [Real-world usage]
```

---

## 1. Scope Ambiguities

### 1.1 Feature Scope Undefined

**Ambiguity Type**: Missing boundaries or extent of functionality

**Trigger Keywords**: "add", "implement", "create", "build" (without specific details)

**Question Pattern**:
```
The request mentions "[FEATURE]" but the scope isn't fully defined.

**Which aspects should be included?**

| Aspect | Description | Existing Pattern (if any) |
|--------|-------------|---------------------------|
| A | [Minimal scope] | [Reference to similar feature] |
| B | [Medium scope] | [Reference to similar feature] |
| C | [Full scope] | [Reference to similar feature] |

**Recommended**: Option [X] - [Rationale based on project context]
```

**Example**:
```
The request mentions "authentication" but the scope isn't fully defined.

**Which aspects should be included?**

| Aspect | Description | Existing Pattern |
|--------|-------------|------------------|
| A | JWT token validation only | auth-service/middleware/jwt_validator.py |
| B | JWT + role-based permissions | auth-service/middleware/auth.py:45-89 |
| C | Full OAuth2 with refresh tokens | External integrations pattern |

**Recommended**: Option B - Matches standard user-facing auth pattern in this project
```

### 1.2 Integration Points Unclear

**Ambiguity Type**: Missing information about system boundaries and communication

**Trigger Keywords**: "integrate", "connect", "sync", "communicate with"

**Question Pattern**:
```
The request involves integration with [SYSTEM], but integration details are unclear.

**Which integration pattern should we follow?**

| Pattern | Protocol | Auth | Existing Example |
|---------|----------|------|------------------|
| A | [Pattern 1] | [Auth method] | [File reference] |
| B | [Pattern 2] | [Auth method] | [File reference] |
| C | [Pattern 3] | [Auth method] | [File reference] |

**Recommended**: Option [X] - [Rationale]
```

**Example** (Three-Tier Architecture):
```
The request involves camera data processing, but tier placement is unclear.

**Which tier should handle this processing?**

| Tier | Responsibility | Communication | Existing Pattern |
|------|----------------|---------------|------------------|
| A | Edge (K3s) | Publishes to Kafka only | camera-processor/edge/ |
| B | Worker (GPU) | Consumes/publishes Kafka | ml-inference/worker/ |
| C | Data Center | Consumes from Kafka, serves API | analytics-service/ |

**Recommended**: Option B - ML processing requires GPU resources (Worker tier)
**Constraint**: Edge NEVER does inference, Data Center NEVER accesses raw video
```

---

## 2. Technical Decision Ambiguities

### 2.1 Technology Choice Unspecified

**Ambiguity Type**: Multiple valid technical approaches available

**Trigger Keywords**: "store", "cache", "queue", "process" (without technology specification)

**Question Pattern**:
```
The request requires [CAPABILITY], but technology choice isn't specified.

**Which technology matches our stack?**

| Option | Technology | Trade-offs | Current Usage |
|--------|-----------|------------|---------------|
| A | [Tech 1] | [Pros/Cons] | [Where used] |
| B | [Tech 2] | [Pros/Cons] | [Where used] |
| C | [Tech 3] | [Pros/Cons] | [Where used] |

**Recommended**: Option [X] - [Rationale based on consistency/performance/expertise]
```

**Example**:
```
The request requires event streaming, but technology choice isn't specified.

**Which technology matches our stack?**

| Option | Technology | Trade-offs | Current Usage |
|--------|-----------|------------|---------------|
| A | Kafka | High throughput, complex setup, proven at scale | All inter-tier communication |
| B | RabbitMQ | Easier setup, lower throughput | Not currently used |
| C | Redis Streams | Simple, limited durability | Used for caching only |

**Recommended**: Option A - Kafka is standard for all event streaming in this project
```

### 2.2 Data Model Design

**Ambiguity Type**: Schema structure or relationships undefined

**Trigger Keywords**: "store", "save", "persist", "database"

**Question Pattern**:
```
The request involves storing [ENTITY], but schema design is unclear.

**How should [ENTITY] be modeled?**

| Approach | Relationships | Tables/Collections | Existing Pattern |
|----------|---------------|-------------------|------------------|
| A | [Model 1] | [Structure] | [Similar entity] |
| B | [Model 2] | [Structure] | [Similar entity] |
| C | [Model 3] | [Structure] | [Similar entity] |

**Recommended**: Option [X] - [Consistency with existing models]
```

**Example**:
```
The request involves storing user preferences, but schema design is unclear.

**How should user preferences be modeled?**

| Approach | Relationships | Tables | Existing Pattern |
|----------|---------------|--------|------------------|
| A | JSON column in users table | 1 table | camera_config (JSONB in cameras) |
| B | Separate preferences table | 2 tables (users, user_preferences) | permissions (separate table) |
| C | Key-value store | External Redis | Not used for user data |

**Recommended**: Option A - Matches camera_config pattern, simpler for sparse data
```

---

## 3. Constraint Clarifications

### 3.1 Performance Requirements

**Ambiguity Type**: SLAs or performance expectations undefined

**Trigger Keywords**: "fast", "real-time", "optimize", "performance"

**Question Pattern**:
```
The request mentions [PERFORMANCE_TERM], but specific SLAs are unclear.

**What are the performance requirements?**

| Metric | Target | Current Baseline | Feasibility |
|--------|--------|------------------|-------------|
| A | [Conservative] | [Current value] | Easy |
| B | [Standard] | [Current value] | Standard |
| C | [Aggressive] | [Current value] | Challenging |

**Project SLAs**: [List relevant SLAs from docs]
**Recommended**: Option [X] - [Rationale]
```

**Example**:
```
The request mentions "real-time analytics", but specific SLAs are unclear.

**What are the performance requirements?**

| Metric | Target | Current Baseline | Feasibility |
|--------|--------|------------------|-------------|
| A | <1 second response | API: ~8ms P95 | Easy (async processing) |
| B | <100ms response | API: ~8ms P95 | Standard (cached results) |
| C | <10ms response | API: ~8ms P95 | Very challenging (requires optimization) |

**Project SLAs**: API P95 <10ms, ML inference <100ms
**Recommended**: Option B - Balances real-time UX with feasible implementation
```

### 3.2 Security/Privacy Constraints

**Ambiguity Type**: Data handling or access control requirements unclear

**Trigger Keywords**: "user data", "permissions", "access", "security", "privacy"

**Question Pattern**:
```
The request involves [SENSITIVE_OPERATION], but security requirements are unclear.

**What security constraints apply?**

| Requirement | Implementation | Existing Pattern | Compliance |
|-------------|----------------|------------------|------------|
| A | [Security level 1] | [How to implement] | [Standard] |
| B | [Security level 2] | [How to implement] | [Standard] |
| C | [Security level 3] | [How to implement] | [Standard] |

**Regulatory Context**: [GDPR/HIPAA/PCI-DSS if applicable]
**Recommended**: Option [X] - [Compliance rationale]
```

**Example** (GDPR context):
```
The request involves storing license plate data, but privacy requirements are unclear.

**What security constraints apply?**

| Requirement | Implementation | Existing Pattern | GDPR Compliance |
|-------------|----------------|------------------|-----------------|
| A | Store raw plates | Direct storage | ❌ Violates right to be forgotten |
| B | Hash at capture | SHA-256 one-way | ✅ Anonymized, irreversible |
| C | Encrypt with key rotation | AES-256 | ⚠️ Requires key management, still reversible |

**Regulatory Context**: GDPR applies (EU customers)
**Recommended**: Option B - Matches tier-2 hashing pattern (ml-inference/worker/)
**Constraint**: MUST hash at Tier 2 before sending to Data Center
```

---

## 4. Conflict Resolution Questions

### 4.1 Architecture Violation Detection

**Ambiguity Type**: Request conflicts with established architectural patterns

**Trigger Keywords**: Detect patterns like "Tier 3 accessing cameras", "HTTP between tiers", "blocking I/O in async"

**Question Pattern**:
```
⚠️ **Potential Architecture Violation Detected**

The request suggests [VIOLATING_PATTERN], which conflicts with [ARCHITECTURE_RULE].

**How should we proceed?**

| Option | Approach | Trade-offs |
|--------|----------|------------|
| A | Follow established pattern: [CORRECT_PATTERN] | [Benefits] |
| B | Modify architecture with justification | [Requires approval, rationale needed] |
| C | Clarify requirement (possible misunderstanding) | [May not be needed] |

**Architecture Context**: [Relevant architecture principle]
**Recommended**: Option [X] - [Strong rationale for compliance]
```

**Example** (Three-Tier Violation):
```
⚠️ **Potential Architecture Violation Detected**

The request suggests "Data Center accessing camera streams", which conflicts with three-tier isolation.

**How should we proceed?**

| Option | Approach | Trade-offs |
|--------|----------|------------|
| A | Edge publishes frames → Kafka → Data Center consumes | Standard pattern, adds latency |
| B | Allow Data Center → Camera direct access | ❌ Violates security boundary, breaks tier isolation |
| C | Clarify: Do you need live frames or processed events? | May be misunderstanding |

**Architecture Context**: Tier 3 (Data Center) NEVER accesses raw camera streams (security + scalability)
**Recommended**: Option A (if live frames needed) or C (if processed events sufficient)
```

### 4.2 Pattern Mismatch

**Ambiguity Type**: Request uses different pattern than project standard

**Trigger Keywords**: Code patterns that don't match project conventions

**Question Pattern**:
```
The request suggests [PATTERN_A], but this project uses [PATTERN_B].

**Which pattern should we follow?**

| Pattern | Description | Project Usage | Migration Cost |
|---------|-------------|---------------|----------------|
| A | [Suggested pattern] | [Usage count] | [Cost to standardize] |
| B | [Existing pattern] | [Usage count] | [Cost to add exception] |

**Consistency Impact**: [Analysis of inconsistency costs]
**Recommended**: Option [X] - [Consistency rationale]
```

**Example**:
```
The request suggests "direct SQLAlchemy queries in endpoints", but this project uses the repository pattern.

**Which pattern should we follow?**

| Pattern | Description | Project Usage | Migration Cost |
|---------|-------------|---------------|----------------|
| A | Direct SQLAlchemy in endpoints | 0 endpoints (not used) | High (breaks abstraction) |
| B | Repository pattern | 23 repositories (standard) | Low (add 1 repository) |

**Consistency Impact**: Breaking repository pattern makes testing harder, violates DI principles
**Recommended**: Option B - Create new repository following libs/database/repositories/base.py
```

---

## 5. Priority and Phasing Questions

### 5.1 MVP Scope

**Ambiguity Type**: Full feature requested without phasing

**Trigger Keywords**: Large feature requests with multiple sub-components

**Question Pattern**:
```
The request describes [LARGE_FEATURE] with multiple components.

**Should we phase this implementation?**

| Phase | Scope | Value | Complexity |
|-------|-------|-------|------------|
| P1 (MVP) | [Minimal] | [Core value] | [Low/Med/High] |
| P2 (Enhancement) | [Added value] | [Nice-to-have] | [Low/Med/High] |
| P3 (Future) | [Complete] | [Polish] | [Low/Med/High] |

**Recommended MVP**: Phase P1 - [Rationale for smallest valuable increment]
```

**Example**:
```
The request describes "user dashboard with analytics, export, real-time updates, and customization".

**Should we phase this implementation?**

| Phase | Scope | Value | Complexity |
|-------|-------|-------|------------|
| P1 (MVP) | Basic dashboard with static analytics | Core value, testable | Low |
| P2 (Enhancement) | Add CSV export | User convenience | Medium |
| P3 (Future) | Real-time updates + full customization | Polish, complex infrastructure | High |

**Recommended MVP**: Phase P1 - Validates user need before infrastructure investment
```

---

## 6. Domain-Specific Questions

### 6.1 Business Logic Ambiguity

**Ambiguity Type**: Business rules or domain logic unclear

**Trigger Keywords**: Domain terms without definition

**Question Pattern**:
```
The request mentions [DOMAIN_TERM], but the business logic is unclear.

**How should [DOMAIN_TERM] behave?**

| Option | Business Rule | Edge Cases | Example |
|--------|---------------|------------|---------|
| A | [Rule 1] | [Handling] | [Concrete example] |
| B | [Rule 2] | [Handling] | [Concrete example] |
| C | [Rule 3] | [Handling] | [Concrete example] |

**Domain Context**: [Relevant business context from project]
**Recommended**: Option [X] - [Business rationale]
```

**Example** (ITS domain):
```
The request mentions "vehicle classification", but the business logic is unclear.

**How should vehicle classification behave?**

| Option | Business Rule | Edge Cases | Example |
|--------|---------------|------------|---------|
| A | Simple (car, truck, motorcycle) | All other → "other" | Fast, lower accuracy |
| B | Detailed (8 categories) | Bicycles, buses separate | Slower, higher accuracy |
| C | Custom per camera | Configurable rules | Most flexible, complex |

**Domain Context**: Traffic analytics for municipality (spec: incident detection priority)
**Recommended**: Option B - Municipality needs bus lane monitoring (per requirement doc)
```

---

## Usage Guidelines

### When to Use Which Template

1. **Start with Ambiguity Detection** (main skill process)
2. **Identify ambiguity category** from request analysis
3. **Select appropriate template(s)** from this reference
4. **Customize with project context**:
   - Fill in existing patterns from codebase
   - Reference specific files and line numbers
   - Include current metrics/baselines
5. **Apply scoring algorithm** to options
6. **Present maximum 5 questions** (prioritize CRITICAL/HIGH)

### Template Customization

Each template should be customized with:
- **Existing patterns**: Reference actual files (e.g., `auth-service/middleware/auth.py:45-89`)
- **Current metrics**: Use real baseline numbers (e.g., "API P95: ~8ms")
- **Domain context**: Include business context from README, docs, or domain models
- **Architecture constraints**: Reference CLAUDE.md or architecture docs

### Scoring Integration

After customizing a template, apply scoring algorithm (see `scoring-algorithm.md`):
- Pattern matching: +40 points if option matches existing pattern
- Simplicity: +30 points for simplest viable option
- Security: +20 points for secure-by-default
- Performance: +10 points for meeting SLAs

Present options with scores and recommend highest-scoring option.
