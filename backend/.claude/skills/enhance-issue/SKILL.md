---
name: enhance-issue
description: Enhance issue with AI-suggested labels, priority, and acceptance criteria
---

# Enhance Issue Skill

Automatically enhance issue metadata using AI analysis of title and description.

## Quick Start

Use this skill when:
- User creates minimal issue (only title)
- Issue lacks labels, priority, or acceptance criteria
- User requests AI enhancement (`/enhance-issue`)

**Example**:
```
User creates issue:
Title: "Login not working"

AI enhances:
- Labels: ["bug", "backend", "authentication", "critical"]
- Priority: "critical" (blocks user access)
- Acceptance Criteria:
  - [ ] Users can log in with valid credentials
  - [ ] Error messages are clear for invalid credentials
  - [ ] Session persists after login
```

## Workflow

1. **Analyze Issue Context**
   - Parse title for keywords (fix, implement, bug, feature)
   - Analyze description for technical details
   - Check for urgency markers (critical, urgent, blocking)
   - Identify domain from keywords (auth, api, ui, db)

2. **Suggest Labels**
   - **Type**: bug, feature, enhancement, documentation, chore
   - **Domain**: backend, frontend, infrastructure, security
   - **Technology**: python, typescript, react, postgresql
   - **Status**: needs-investigation, blocked, ready
   - Use RECOMMENDED for clear matches, DEFAULT for inferred

3. **Infer Priority**
   - **Critical**: Security vulnerabilities, data loss, complete feature breakage
   - **High**: Major functionality broken, significant user impact
   - **Medium**: Partial functionality affected, workarounds exist
   - **Low**: Minor issues, cosmetic improvements, nice-to-have features

4. **Generate Acceptance Criteria**
   - Extract implied requirements from description
   - Add standard criteria based on issue type:
     - Bugs: Reproduction steps, expected behavior, error handling
     - Features: Happy path, edge cases, error states
   - Format as checklist for task tracking

## Output Format

```json
{
  "suggested_labels": [
    {"label": "bug", "confidence": "RECOMMENDED", "rationale": "Title contains 'not working'"},
    {"label": "backend", "confidence": "RECOMMENDED", "rationale": "Login is server-side functionality"},
    {"label": "authentication", "confidence": "RECOMMENDED", "rationale": "Login relates to auth"},
    {"label": "critical", "confidence": "RECOMMENDED", "rationale": "Blocks user access"}
  ],
  "suggested_priority": {
    "priority": "critical",
    "confidence": "RECOMMENDED",
    "rationale": "Complete feature breakage preventing user access"
  },
  "acceptance_criteria": [
    {"text": "Users can log in with valid email and password", "confidence": "RECOMMENDED"},
    {"text": "Error messages are displayed for invalid credentials", "confidence": "RECOMMENDED"},
    {"text": "Session persists after successful login", "confidence": "DEFAULT"},
    {"text": "Login form validates input client-side", "confidence": "DEFAULT"}
  ],
  "estimated_complexity": {
    "level": "medium",
    "confidence": "DEFAULT",
    "rationale": "Likely requires debugging auth flow, not full reimplementation"
  }
}
```

## Examples

### Example 1: Bug Issue
**Input**:
```json
{
  "title": "API returns 500 error on user creation",
  "description": "When creating a user with duplicate email, API crashes instead of returning validation error"
}
```

**Output**:
```json
{
  "suggested_labels": [
    {"label": "bug", "confidence": "RECOMMENDED"},
    {"label": "backend", "confidence": "RECOMMENDED"},
    {"label": "api", "confidence": "RECOMMENDED"},
    {"label": "validation", "confidence": "RECOMMENDED"}
  ],
  "suggested_priority": {
    "priority": "high",
    "confidence": "RECOMMENDED",
    "rationale": "Server error but has workaround (client-side validation)"
  },
  "acceptance_criteria": [
    {"text": "API returns 422 error with validation message for duplicate email"},
    {"text": "Server does not crash when duplicate email submitted"},
    {"text": "Error response follows RFC 7807 format"}
  ]
}
```

### Example 2: Feature Request
**Input**:
```json
{
  "title": "Add dark mode support",
  "description": "Users want dark mode for better viewing at night"
}
```

**Output**:
```json
{
  "suggested_labels": [
    {"label": "feature", "confidence": "RECOMMENDED"},
    {"label": "frontend", "confidence": "RECOMMENDED"},
    {"label": "ui", "confidence": "RECOMMENDED"}
  ],
  "suggested_priority": {
    "priority": "medium",
    "confidence": "DEFAULT",
    "rationale": "User request but not critical functionality"
  },
  "acceptance_criteria": [
    {"text": "User can toggle dark mode in settings"},
    {"text": "Dark mode persists across sessions"},
    {"text": "All pages support dark mode theme"},
    {"text": "Color contrast meets WCAG AA standards"}
  ]
}
```

### Example 3: Security Issue
**Input**:
```json
{
  "title": "SQL injection vulnerability in search",
  "description": "Search input is not sanitized, allows arbitrary SQL execution"
}
```

**Output**:
```json
{
  "suggested_labels": [
    {"label": "security", "confidence": "RECOMMENDED"},
    {"label": "bug", "confidence": "RECOMMENDED"},
    {"label": "backend", "confidence": "RECOMMENDED"},
    {"label": "database", "confidence": "RECOMMENDED"}
  ],
  "suggested_priority": {
    "priority": "critical",
    "confidence": "RECOMMENDED",
    "rationale": "OWASP Top 10 vulnerability, potential data breach"
  },
  "acceptance_criteria": [
    {"text": "All search inputs use parameterized queries"},
    {"text": "Security audit confirms no SQL injection vectors"},
    {"text": "Existing data integrity validated after fix"}
  ],
  "estimated_complexity": {
    "level": "low",
    "confidence": "RECOMMENDED",
    "rationale": "Standard fix: use query parameters instead of string concatenation"
  }
}
```

## Integration Points

- **IssueEnhancerAgent**: Primary agent implementing this workflow
- **MCP Tools**: Uses `search_issues` to find similar issues for label suggestions
- **Approval Flow**: Enhancement suggestions are AUTO_EXECUTE (non-destructive)
- **Label Management**: Checks workspace custom labels before suggesting

## References

- Design Decision: DD-048 (Confidence Tagging)
- Design Decision: DD-003 (Auto-execute for suggestions)
- Agent: `backend/src/pilot_space/ai/agents/issue_enhancer_agent_sdk.py`
