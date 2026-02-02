# Recommendation Scoring Algorithm

This document explains the scoring system used to recommend options when presenting clarification questions to users.

## Algorithm Overview

```
Total Score (0-100) = Pattern Matching (40) + Simplicity (30) + Security (20) + Performance (10)
```

Each option is scored across four dimensions, with weights reflecting their importance to code quality and maintainability.

---

## Dimension 1: Pattern Matching (40 points maximum)

**Rationale**: Consistency with existing codebase patterns is the strongest predictor of long-term maintainability.

### Scoring Rules

| Criteria | Points | Description |
|----------|--------|-------------|
| **Exact Match** | 40 | Option exactly matches established project pattern |
| **Close Match** | 30 | Similar pattern with minor variations |
| **Related Pattern** | 20 | Uses same technology but different approach |
| **Partially Related** | 10 | Some overlap but significant differences |
| **No Match** | 0 | No existing pattern in codebase |

### How to Score

1. **Identify the pattern category** (authentication, data access, service layer, etc.)
2. **Search codebase** for existing implementations:
   - Use `mcp__serena` tools (find_symbol, search_for_pattern)
   - Look in standard locations (repositories/, services/, middleware/)
3. **Count usage frequency**: How many times is this pattern used?
4. **Assess similarity**: How closely does the option match?

### Examples

**Example 1: Authentication Pattern**
```
Request: "Add authentication to new endpoint"

Option A: JWT with permission-based middleware
- Existing: auth-service/middleware/auth.py (used in 23 endpoints)
- Match Quality: Exact match
- Score: 40/40

Option B: API key authentication
- Existing: worker-auth-client (used in 3 services)
- Match Quality: Related pattern (different use case)
- Score: 20/40

Option C: Basic Auth
- Existing: Not used in project
- Match Quality: No match
- Score: 0/40
```

**Example 2: Data Access Pattern**
```
Request: "Query user permissions"

Option A: Repository pattern with selectinload()
- Existing: base_repository.py (used in 23 repositories)
- Match Quality: Exact match
- Score: 40/40

Option B: Direct SQLAlchemy queries
- Existing: Not used (all data access through repositories)
- Match Quality: No match (violates established pattern)
- Score: 0/40
```

### Pattern Matching Checklist

When scoring pattern matching:
- [ ] **Exact file reference**: Can you point to a specific file implementing this pattern?
- [ ] **Usage frequency**: How many times is the pattern used? (More = stronger signal)
- [ ] **Recency**: Is this an active pattern or legacy code?
- [ ] **Documentation**: Is the pattern documented in CLAUDE.md or dev-pattern docs?
- [ ] **Consistency**: Would choosing this option maintain consistency?

**Special Cases**:
- **Legacy patterns**: If pattern exists but is being phased out, reduce score by 50%
- **Experimental patterns**: If pattern exists but marked as experimental, reduce score by 30%
- **Anti-patterns**: If option violates documented anti-patterns, score = 0

---

## Dimension 2: Simplicity (30 points maximum)

**Rationale**: Simpler solutions are easier to understand, test, and maintain.

### Scoring Rules

| Criteria | Points | Description |
|----------|--------|-------------|
| **Minimal** | 30 | Simplest viable solution, no unnecessary complexity |
| **Standard** | 20 | Moderate complexity, industry-standard approach |
| **Complex** | 10 | Significant complexity, requires expertise |
| **Very Complex** | 0 | Excessive complexity, hard to maintain |

### Simplicity Metrics

Evaluate these factors (each "yes" answer reduces simplicity):
- [ ] Requires new infrastructure? (databases, message queues, caches)
- [ ] Introduces new dependencies? (libraries, frameworks)
- [ ] Requires new configuration? (environment variables, config files)
- [ ] Adds deployment complexity? (new services, containers)
- [ ] Requires specialized knowledge? (advanced patterns, domain expertise)
- [ ] Increases cognitive load? (many moving parts, non-obvious behavior)

**Scoring Formula**:
```
Base Score: 30 points
Subtract 5 points for each "yes" answer above (minimum 0)
```

### Examples

**Example 1: Event Storage**
```
Option A: Add JSONB column to existing table
- New infrastructure: No
- New dependencies: No
- New configuration: No
- Deployment complexity: No
- Specialized knowledge: No (standard SQLAlchemy)
- Cognitive load: Minimal (single table)
- Score: 30/30 (Minimal)

Option B: Separate events table with relationships
- New infrastructure: No
- New dependencies: No
- New configuration: No
- Deployment complexity: No
- Specialized knowledge: No
- Cognitive load: Moderate (relationship management)
- Score: 20/30 (Standard)

Option C: Kafka event stream with CQRS
- New infrastructure: Yes (Kafka)
- New dependencies: Yes (Kafka clients)
- New configuration: Yes (Kafka brokers)
- Deployment complexity: Yes (Kafka cluster)
- Specialized knowledge: Yes (CQRS, event sourcing)
- Cognitive load: High (eventual consistency, event replay)
- Score: 0/30 (Very Complex)
```

**Example 2: Caching Strategy**
```
Option A: In-memory dict with TTL
- Complexity factors: 0 (no infrastructure, no dependencies)
- Score: 30/30 (Minimal)

Option B: Redis cache
- Complexity factors: 3 (new infrastructure, new dependencies, new configuration)
- Score: 15/30 (Complex)
- Rationale: 30 - (3 × 5) = 15
```

### Simplicity Adjustments

**Add bonus points** (up to +5):
- [ ] +5: Reuses existing infrastructure/patterns with zero new dependencies
- [ ] +3: Leverages built-in language/framework features
- [ ] +2: Solution is self-documenting (obvious behavior)

**Subtract penalty points**:
- [ ] -5: Introduces accidental complexity (unnecessary indirection)
- [ ] -10: Solution is "clever" but hard to understand

---

## Dimension 3: Security (20 points maximum)

**Rationale**: Security vulnerabilities are expensive to fix later and can cause serious harm.

### Scoring Rules

| Criteria | Points | Description |
|----------|--------|-------------|
| **Secure by Default** | 20 | No security concerns, follows best practices |
| **Requires Care** | 15 | Secure if implemented correctly, easy to get wrong |
| **Has Risks** | 10 | Known security implications requiring mitigation |
| **Insecure** | 0 | Violates security principles or regulations |

### Security Checklist

Evaluate each option against these security dimensions:

#### 3.1 Input Validation & Injection
- [ ] Protected against SQL injection? (parameterized queries, ORM)
- [ ] Protected against XSS? (escaped output, CSP headers)
- [ ] Protected against command injection? (no shell=True, validated inputs)
- [ ] Input validation at boundary? (Pydantic models, schema validation)

**Scoring**:
- All protected: +5 points
- Mostly protected: +3 points
- Some vulnerabilities: +1 point
- Major vulnerabilities: 0 points

#### 3.2 Authentication & Authorization
- [ ] Requires authentication? (JWT, OAuth, API keys)
- [ ] Proper authorization checks? (permission-based, RBAC)
- [ ] No authentication bypass? (all paths protected)
- [ ] Follows least privilege? (minimal permissions required)

**Scoring**:
- All criteria met: +5 points
- Mostly secure: +3 points
- Gaps exist: +1 point
- Insecure: 0 points

#### 3.3 Data Protection
- [ ] Secrets handled securely? (no hardcoded secrets, env vars, secret management)
- [ ] Sensitive data encrypted? (at rest and in transit)
- [ ] PII anonymized/hashed? (GDPR compliance if applicable)
- [ ] Audit logging present? (who did what when)

**Scoring**:
- All protected: +5 points
- Mostly protected: +3 points
- Some exposure: +1 point
- Data leaks possible: 0 points

#### 3.4 Compliance & Regulatory
- [ ] GDPR compliant? (if applicable: right to be forgotten, data minimization)
- [ ] Industry standards followed? (OWASP Top 10, CWE)
- [ ] Regulatory requirements met? (HIPAA, PCI-DSS if applicable)

**Scoring**:
- Fully compliant: +5 points
- Mostly compliant: +3 points
- Gaps exist: +1 point
- Non-compliant: 0 points

### Examples

**Example 1: License Plate Storage**
```
Option A: Hash at capture (SHA-256 one-way)
- Input validation: N/A (internal data)
- Auth/Authz: N/A (processing pipeline)
- Data protection: ✅ Anonymized, irreversible
- Compliance: ✅ GDPR compliant (right to be forgotten)
- Score: 20/20 (Secure by Default)

Option B: Encrypt with key rotation
- Input validation: N/A
- Auth/Authz: N/A
- Data protection: ⚠️ Reversible (requires key management)
- Compliance: ⚠️ GDPR concern (still PII)
- Score: 10/20 (Has Risks)

Option C: Store raw plates
- Input validation: N/A
- Auth/Authz: N/A
- Data protection: ❌ No protection
- Compliance: ❌ GDPR violation
- Score: 0/20 (Insecure)
```

**Example 2: API Endpoint Authentication**
```
Option A: JWT with permission checks
- Input validation: ✅ Pydantic validation
- Auth/Authz: ✅ JWT + RBAC
- Data protection: ✅ Audit logging
- Compliance: ✅ Follows standards
- Score: 20/20 (Secure by Default)

Option B: No authentication (internal API)
- Input validation: ✅ Pydantic validation
- Auth/Authz: ❌ No protection
- Data protection: ⚠️ Depends on network security
- Compliance: ⚠️ Risky if exposed
- Score: 10/20 (Has Risks)
```

---

## Dimension 4: Performance (10 points maximum)

**Rationale**: Performance is important but often less critical than correctness and security.

### Scoring Rules

| Criteria | Points | Description |
|----------|--------|-------------|
| **Exceeds SLAs** | 10 | Significantly better than required performance |
| **Meets SLAs** | 7 | Comfortably within SLA targets |
| **Close to SLAs** | 4 | Barely meets SLAs, little margin |
| **Below SLAs** | 0 | Does not meet performance requirements |

### Performance Evaluation

#### 4.1 Identify Relevant SLAs

**Common SLA Categories**:
- API response time (e.g., P95 <10ms, P99 <50ms)
- ML inference latency (e.g., <100ms)
- Database query time (e.g., <5ms for simple queries)
- Throughput (e.g., 1000 requests/sec)
- Resource usage (CPU, memory limits)

**How to Find SLAs**:
1. Check CLAUDE.md or docs/performance-slas.md
2. Look at existing monitoring dashboards
3. Review load test results
4. Check CI performance tests

#### 4.2 Estimate Option Performance

For each option, estimate:
- [ ] **Latency impact**: How much time will this add? (network calls, computation, I/O)
- [ ] **Throughput impact**: Can this handle expected load?
- [ ] **Resource usage**: CPU, memory, disk implications
- [ ] **Scalability**: Does this work at 10x current load?

#### 4.3 Compare Against Baselines

**Scoring Formula**:
```
If (estimated_latency < SLA * 0.5): Score = 10 (Exceeds)
If (estimated_latency < SLA * 0.8): Score = 7 (Meets)
If (estimated_latency < SLA): Score = 4 (Close)
If (estimated_latency >= SLA): Score = 0 (Below)
```

### Examples

**Example 1: Database Query Optimization**
```
SLA: API response P95 <10ms
Current baseline: ~8ms

Option A: Repository with selectinload() (eager loading)
- Estimated: 1 query, ~2ms
- Total latency: 8ms + 2ms = 10ms
- Comparison: 10ms ≤ 10ms (barely meets SLA)
- Score: 4/10 (Close to SLAs)

Option B: Multiple sequential queries (N+1)
- Estimated: N queries, ~2ms each, N=10 typical
- Total latency: 8ms + 20ms = 28ms
- Comparison: 28ms > 10ms (violates SLA)
- Score: 0/10 (Below SLAs)

Option C: Single optimized JOIN query
- Estimated: 1 query, ~1ms
- Total latency: 8ms + 1ms = 9ms
- Comparison: 9ms < 10ms * 0.8 (within 80% of SLA)
- Score: 7/10 (Meets SLAs)
```

**Example 2: Caching Strategy**
```
SLA: Dashboard load time <500ms
Current: 450ms (no cache)

Option A: In-memory cache (TTL 60s)
- Estimated: Hit: ~5ms, Miss: 450ms
- Assuming 90% hit rate: 0.9×5 + 0.1×450 = 49.5ms
- Comparison: 49.5ms < 500ms * 0.5 (way under SLA)
- Score: 10/10 (Exceeds SLAs)

Option B: Redis cache
- Estimated: Hit: ~15ms (network), Miss: 450ms
- Assuming 90% hit rate: 0.9×15 + 0.1×450 = 58.5ms
- Comparison: 58.5ms < 500ms * 0.5 (well under SLA)
- Score: 10/10 (Exceeds SLAs)

Option C: Database query optimization (no cache)
- Estimated: 200ms (optimized query)
- Comparison: 200ms < 500ms * 0.8 (within 80% of SLA)
- Score: 7/10 (Meets SLAs)
```

### Performance Anti-Patterns

**Automatic score = 0** if option includes:
- [ ] N+1 queries without justification
- [ ] Blocking I/O in async functions
- [ ] Unbounded loops or recursion
- [ ] Loading large datasets into memory
- [ ] Synchronous external API calls in request path

---

## Complete Scoring Example

### Scenario
**Request**: "Add user permissions checking to camera endpoints"

**Project Context**:
- Auth-service has JWT + RBAC pattern (used in 23 endpoints)
- API SLA: P95 <10ms, currently ~8ms
- GDPR compliance required
- Repository pattern standard (23 repositories)

---

### Option A: Permission-based middleware with repository pattern

**Pattern Matching (40 max)**:
- Matches: auth-service/middleware/auth.py:45-89 (exact match)
- Usage: 23 endpoints use this pattern
- Score: **40/40**

**Simplicity (30 max)**:
- New infrastructure: No
- New dependencies: No
- Reuses existing: Yes (+5 bonus)
- Score: **30/30**

**Security (20 max)**:
- Auth/Authz: ✅ JWT + RBAC (+5)
- Input validation: ✅ Pydantic models (+5)
- Data protection: ✅ Audit logging (+5)
- Compliance: ✅ GDPR compliant (+5)
- Score: **20/20**

**Performance (10 max)**:
- Current: 8ms baseline
- Added latency: ~1ms (single permission query with eager loading)
- Total: 9ms < 10ms * 0.8
- Score: **7/10**

**Total Score: 97/100** ✅ **HIGHLY RECOMMENDED**

---

### Option B: API key authentication

**Pattern Matching (40 max)**:
- Matches: worker-auth-client (related but different use case)
- Usage: 3 services (service-to-service only)
- Not used for user-facing endpoints
- Score: **10/40**

**Simplicity (30 max)**:
- New infrastructure: No
- New dependencies: Yes (API key generation/storage)
- New configuration: Yes (API key rotation)
- Cognitive load: Higher (managing keys vs tokens)
- Formula: 30 - (2 × 5) = **20/30**

**Security (20 max)**:
- Auth/Authz: ⚠️ API keys less secure than JWT (+3)
- Input validation: ✅ Pydantic models (+5)
- Data protection: ⚠️ Key storage concerns (+3)
- Compliance: ⚠️ Audit logging more complex (+2)
- Score: **13/20**

**Performance (10 max)**:
- Added latency: ~0.5ms (key lookup)
- Total: 8.5ms < 10ms * 0.8
- Score: **7/10**

**Total Score: 50/100** ⚠️ **NOT RECOMMENDED** (pattern mismatch)

---

### Option C: No authentication (internal-only)

**Pattern Matching (40 max)**:
- Matches: None (all user-facing endpoints are authenticated)
- Violates established security patterns
- Score: **0/40**

**Simplicity (30 max)**:
- New infrastructure: No
- New dependencies: No
- Simplest option: Yes
- Score: **30/30**

**Security (20 max)**:
- Auth/Authz: ❌ No protection
- Compliance: ❌ GDPR violation (no access control)
- Score: **0/20**

**Performance (10 max)**:
- Added latency: 0ms (no auth check)
- Fastest option
- Score: **10/10**

**Total Score: 40/100** ❌ **STRONGLY NOT RECOMMENDED** (security violation)

---

## Recommendation Presentation Format

When presenting scored options to users:

```markdown
**Which [DECISION] should we follow?**

| Option | Description | Score | Rationale |
|--------|-------------|-------|-----------|
| A | [Description] | 97/100 ⭐ | Exact pattern match, secure by default |
| B | [Description] | 50/100 | Different pattern, less secure |
| C | [Description] | 40/100 ❌ | Security violation |

**Scoring Breakdown (Option A)**:
- Pattern Match: 40/40 (matches auth-service/middleware/auth.py:45-89)
- Simplicity: 30/30 (reuses existing infrastructure)
- Security: 20/20 (JWT + RBAC, GDPR compliant)
- Performance: 7/10 (9ms < 10ms SLA)

**Recommended**: Option A - Exact match with established auth pattern, maintains security and consistency
```

---

## Edge Cases and Special Considerations

### When No Option Scores High

If all options score <60/100:
1. **Explain the trade-offs**: None of the options are ideal
2. **Recommend hybrid approach**: Combine strengths of multiple options
3. **Suggest research**: "Would you like me to research additional approaches?"

### When Multiple Options Score Similarly

If two options within 10 points:
1. **Present both as viable**: "Both options are reasonable"
2. **Highlight differences**: Focus on trade-off dimensions
3. **Let user decide**: Provide context, let user choose based on priorities

### When Security Scores 0

**Always strongly recommend against**, even if total score is high from other dimensions.
- Security violations can't be compensated by simplicity or performance
- Make this explicit in recommendation

### When Performance Scores 0

**Strong recommendation against**, with caveats:
- Explain SLA violation and impact
- Suggest optimization path if pattern match is perfect
- Consider if SLA can be adjusted (rare)
