# Risk Assessment Prompt Template

> **Purpose**: Identify, analyze, and mitigate technical and project risks with structured assessment methodology.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` Risk Assessment section
>
> **Usage**: Use during planning phases or when evaluating new technical approaches.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal Software Architect with 15 years managing technical risk in production systems.
You excel at:
- Identifying risks that others miss (technical debt, scalability cliffs, security gaps)
- Quantifying impact and likelihood with evidence-based assessment
- Designing mitigations that are practical and proportionate
- Balancing risk avoidance with delivery velocity

# Stakes Framing (P6)

Risk assessment for [PROJECT_NAME] directly impacts project success.
Thorough risk identification will:
- Prevent 80% of production incidents through proactive mitigation
- Save $100,000+ in emergency fixes by addressing issues early
- Enable confident decision-making with documented trade-offs

I'll tip you $200 for a comprehensive risk assessment with actionable mitigations.

# Assessment Context

## Scope
**Project/Feature**: [PROJECT_OR_FEATURE_NAME]
**Phase**: [PLANNING/DESIGN/IMPLEMENTATION/DEPLOYMENT]
**Timeline**: [DEADLINE_OR_MILESTONE]

## Technology Stack
| Layer | Technology | Maturity Level |
|-------|------------|----------------|
| [LAYER] | [TECH] | Stable/Emerging/Experimental |

## Key Constraints
- [CONSTRAINT_1]
- [CONSTRAINT_2]
- [CONSTRAINT_3]

# Task Decomposition (P3)

Evaluate risks step by step:

## Step 1: Risk Identification
Systematically scan each risk category:

### Technical Risks
| ID | Risk | Category | Trigger Condition |
|----|------|----------|-------------------|
| T1 | [RISK_DESCRIPTION] | [CATEGORY] | [WHAT_TRIGGERS_IT] |
| T2 | [RISK_DESCRIPTION] | [CATEGORY] | [WHAT_TRIGGERS_IT] |

**Categories**: Performance, Scalability, Security, Data Integrity, Integration, Dependencies

### Operational Risks
| ID | Risk | Category | Trigger Condition |
|----|------|----------|-------------------|
| O1 | [RISK_DESCRIPTION] | [CATEGORY] | [WHAT_TRIGGERS_IT] |

**Categories**: Deployment, Monitoring, Incident Response, On-call, Documentation

### Project Risks
| ID | Risk | Category | Trigger Condition |
|----|------|----------|-------------------|
| P1 | [RISK_DESCRIPTION] | [CATEGORY] | [WHAT_TRIGGERS_IT] |

**Categories**: Scope, Timeline, Resources, Dependencies, Stakeholder

## Step 2: Impact-Likelihood Assessment
For each identified risk:

| Risk ID | Impact | Likelihood | Score | Priority |
|---------|--------|------------|-------|----------|
| [ID] | High/Medium/Low | High/Medium/Low | [IxL] | P1/P2/P3 |

**Impact Definitions**:
- **High**: Production outage, data loss, security breach, >$50K cost
- **Medium**: Degraded performance, manual workaround needed, $10-50K cost
- **Low**: Minor inconvenience, automated recovery, <$10K cost

**Likelihood Definitions**:
- **High**: >50% probability, has happened before, known weakness
- **Medium**: 10-50% probability, could happen under stress
- **Low**: <10% probability, requires unusual circumstances

**Priority Matrix**:
| | High Impact | Medium Impact | Low Impact |
|---|------------|---------------|------------|
| **High Likelihood** | P1 | P1 | P2 |
| **Medium Likelihood** | P1 | P2 | P3 |
| **Low Likelihood** | P2 | P3 | P3 |

## Step 3: Mitigation Design
For each P1 and P2 risk:

### Risk [ID]: [RISK_NAME]

**Root Cause Analysis**:
[WHY_THIS_RISK_EXISTS]

**Mitigation Options**:
| Option | Effort | Effectiveness | Trade-off |
|--------|--------|---------------|-----------|
| [OPTION_A] | [H/M/L] | [H/M/L] | [TRADE_OFF] |
| [OPTION_B] | [H/M/L] | [H/M/L] | [TRADE_OFF] |

**Selected Mitigation**: [CHOSEN_OPTION]

**Implementation**:
```
[CODE_OR_PROCESS_EXAMPLE]
```

**Monitoring/Detection**:
- Alert condition: [CONDITION]
- Dashboard metric: [METRIC]
- Runbook: [LINK_OR_DESCRIPTION]

**Contingency Plan** (if mitigation fails):
[BACKUP_PLAN]

## Step 4: Risk Register
Compile final risk register:

| Risk | Impact | Likelihood | Mitigation | Owner | Status |
|------|--------|------------|------------|-------|--------|
| [RISK] | [H/M/L] | [H/M/L] | [MITIGATION] | [OWNER] | Open/Mitigated/Accepted |

## Step 5: Residual Risk Assessment
After mitigations:

| Risk | Original Priority | Residual Priority | Accepted? |
|------|-------------------|-------------------|-----------|
| [RISK] | [P1/P2/P3] | [P2/P3/Low] | Yes/No |

# Self-Evaluation Framework (P15)

Rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All risk categories scanned | ___ | |
| **Accuracy**: Impact/likelihood estimates justified | ___ | |
| **Actionability**: Mitigations are specific and doable | ___ | |
| **Proportionality**: Effort matches risk priority | ___ | |
| **Monitoring**: Detection mechanisms defined | ___ | |

If any < 0.9, refine before presenting.

# Output Format

```markdown
## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [RISK] | High/Medium/Low | High/Medium/Low | [MITIGATION] |

### P1 Risks (Require Immediate Mitigation)

**[RISK_NAME]**
- **Trigger**: [CONDITION]
- **Mitigation**: [ACTION]
- **Monitoring**: [METRIC/ALERT]
- **Contingency**: [BACKUP_PLAN]

### Accepted Risks
[RISKS_ACCEPTED_WITH_RATIONALE]
```
```

---

## Example: Pilot Space MVP Risk Assessment (from plan.md)

```markdown
## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| TipTap complexity for ghost text | High | Medium | Spike early, fallback to simpler overlay |
| AI response latency > 2s | Medium | Medium | Streaming via SSE, caching common patterns |
| pgvector scaling at 50k issues | Medium | Low | HNSW indexing via Supabase, query monitoring |
| GitHub API rate limits during PR review | Medium | Medium | Queue with backoff, notify user of delays |
| Supabase Queue limitations | Low | Low | pgmq is battle-tested, can scale to Redis if needed |
| Knowledge graph performance | Medium | Medium | ForceAtlas2 WebGL, 50K+ nodes tested with Sigma.js |
| Semantic relationship accuracy | Medium | Medium | Cosine > 0.7 threshold, weekly batch recalculation |

### P1 Risks

**TipTap Ghost Text Complexity**
- **Trigger**: Custom ProseMirror decorations fail to render correctly
- **Mitigation**: 2-week spike to validate approach before full implementation
- **Monitoring**: Manual testing of edge cases (code blocks, lists, tables)
- **Contingency**: Fall back to CSS overlay positioned via block coordinates

**AI Response Latency**
- **Trigger**: Ghost text suggestions take >2s, breaking user flow
- **Mitigation**:
  - SSE streaming for incremental display
  - Redis caching for repeated patterns
  - Provider routing to fastest model (Gemini Flash)
- **Monitoring**: p95 latency dashboard, alert if >1.5s
- **Contingency**: Increase trigger delay from 500ms to 1000ms

### Accepted Risks

**Supabase Queue Limitations** (P3)
- pgmq handles 10K+ jobs/day in production
- MVP scale (100 users) well within limits
- Migration path to Redis documented if needed
```

---

## Risk Categories Checklist

### Technical Risks
- [ ] **Performance**: Response times, throughput, resource usage
- [ ] **Scalability**: Data volume, concurrent users, rate limits
- [ ] **Security**: Authentication, authorization, data exposure
- [ ] **Data Integrity**: Consistency, durability, backup/restore
- [ ] **Integration**: API compatibility, version drift, rate limits
- [ ] **Dependencies**: Library vulnerabilities, breaking changes

### Operational Risks
- [ ] **Deployment**: Rollback capability, blue-green, canary
- [ ] **Monitoring**: Observability gaps, alert fatigue
- [ ] **Incident Response**: Runbooks, on-call, escalation
- [ ] **Documentation**: Knowledge silos, stale docs

### Project Risks
- [ ] **Scope**: Feature creep, unclear requirements
- [ ] **Timeline**: Dependencies, estimation accuracy
- [ ] **Resources**: Key person risk, skill gaps
- [ ] **Stakeholder**: Changing priorities, approval delays

---

## Validation Checklist

Before finalizing assessment:

- [ ] All risk categories systematically scanned
- [ ] Impact and likelihood have evidence-based justification
- [ ] P1 risks have specific, actionable mitigations
- [ ] Monitoring/alerting defined for each mitigation
- [ ] Contingency plans exist for critical risks
- [ ] Risk owners assigned
- [ ] Accepted risks have documented rationale

---

*Template Version: 1.0*
*Extracted from: plan.md v7.0 Risk Assessment*
*Techniques Applied: P3 (decomposition), P6 (stakes), P15 (self-eval), P16 (persona)*
