# AI Confidence Tagging Rules (DD-048)

## Overview

All AI suggestions in PilotSpace MUST include exactly one confidence tag. This establishes clear expectations about AI certainty and enables users to make informed decisions about accepting recommendations.

**Design Decision Reference**: DD-048 (AI Confidence Tags)

## Tag Definitions

### RECOMMENDED
**Meaning**: Strongest suggestion, backed by clear evidence or best practices

**When to use**:
- Clear semantic match to user intent
- Follows established best practices
- Supported by multiple data points
- High confidence from underlying model (>0.8 if scored)

**Examples**:
```json
{
  "suggestion": "Create issue: Fix email login bug",
  "confidence": "RECOMMENDED",
  "rationale": "Explicit bug mention with user impact, clear action required"
}
```

```json
{
  "assignee": "alice@example.com",
  "confidence": "RECOMMENDED",
  "rationale": "Primary backend engineer, authored related authentication code, available capacity"
}
```

```json
{
  "label": "security",
  "confidence": "RECOMMENDED",
  "rationale": "Issue mentions JWT tokens and authentication, clear security implications"
}
```

### DEFAULT
**Meaning**: Standard choice, safe fallback when no special criteria apply

**When to use**:
- Most common pattern for this scenario
- No strong indicators for alternative choices
- Safe choice that won't cause issues
- Moderate confidence from model (0.5-0.8)

**Examples**:
```json
{
  "priority": "medium",
  "confidence": "DEFAULT",
  "rationale": "No urgency markers (critical/urgent) or deferral indicators (nice-to-have/eventually)"
}
```

```json
{
  "state": "triage",
  "confidence": "DEFAULT",
  "rationale": "Standard initial state for new issues, allows team review before assignment"
}
```

```json
{
  "annotation_type": "improvement",
  "confidence": "DEFAULT",
  "rationale": "Suggestion enhances clarity without raising critical concerns"
}
```

### CURRENT
**Meaning**: Reflects existing value, no change proposed

**When to use**:
- Documenting current state
- AI agrees with existing value
- No modification suggested
- Used in update operations to show "keep as-is"

**Examples**:
```json
{
  "assignee": "bob@example.com",
  "confidence": "CURRENT",
  "rationale": "Existing assignee is appropriate, no change needed"
}
```

```json
{
  "priority": "high",
  "confidence": "CURRENT",
  "rationale": "Priority correctly reflects issue criticality based on user impact"
}
```

```json
{
  "labels": ["backend", "api"],
  "confidence": "CURRENT",
  "rationale": "Existing labels accurately categorize issue scope"
}
```

### ALTERNATIVE
**Meaning**: Valid option with different tradeoffs, user decision required

**When to use**:
- Multiple valid approaches exist
- Tradeoffs between options
- Requires domain knowledge or preference
- Low confidence from model (<0.5) or high uncertainty

**Examples**:
```json
{
  "suggestion": "Evaluate caching strategy",
  "confidence": "ALTERNATIVE",
  "rationale": "Tentative suggestion (maybe, could), needs team discussion on Redis vs in-memory"
}
```

```json
{
  "assignee": "carol@example.com",
  "confidence": "ALTERNATIVE",
  "rationale": "Alternative assignee with relevant skills, but less experience in this area than primary choice"
}
```

```json
{
  "approach": "Implement as microservice",
  "confidence": "ALTERNATIVE",
  "rationale": "Alternative to monolith extension, better isolation but higher operational complexity"
}
```

## Usage Guidelines

### 1. Exactly One Tag Per Suggestion

**Required**: Every AI suggestion must include exactly one confidence tag.

```json
// ✅ CORRECT: Single confidence tag
{
  "suggestion": "Add error handling",
  "confidence": "RECOMMENDED",
  "rationale": "Critical path lacks exception handling"
}

// ❌ INCORRECT: No confidence tag
{
  "suggestion": "Add error handling"
}

// ❌ INCORRECT: Multiple tags
{
  "suggestion": "Add error handling",
  "confidence": ["RECOMMENDED", "DEFAULT"]
}
```

### 2. Always Include Rationale

**Required**: Explain reasoning briefly (1-2 sentences max).

```json
// ✅ CORRECT: Clear rationale
{
  "label": "performance",
  "confidence": "RECOMMENDED",
  "rationale": "Issue mentions slow response times and timeout errors"
}

// ❌ INCORRECT: Missing rationale
{
  "label": "performance",
  "confidence": "RECOMMENDED"
}

// ❌ INCORRECT: Vague rationale
{
  "label": "performance",
  "confidence": "RECOMMENDED",
  "rationale": "This seems right"
}
```

### 3. Tag Each Entity Separately

**When affecting multiple entities**: Tag each independently.

```json
// ✅ CORRECT: Separate tags for different fields
{
  "issue_updates": {
    "priority": {
      "value": "high",
      "confidence": "RECOMMENDED",
      "rationale": "Blocks user login, critical path"
    },
    "assignee": {
      "value": "alice@example.com",
      "confidence": "DEFAULT",
      "rationale": "Primary backend engineer, standard assignment"
    },
    "labels": {
      "value": ["backend", "security"],
      "confidence": "RECOMMENDED",
      "rationale": "Authentication issue with security implications"
    }
  }
}
```

## Implementation Examples

### Issue Extraction

```python
@dataclass
class ExtractedIssue:
    """Issue extracted from note with confidence tagging."""
    name: str
    description: str
    confidence: Literal["RECOMMENDED", "DEFAULT", "CURRENT", "ALTERNATIVE"]
    rationale: str
    source_block_id: str
    labels: list[str]
    priority: str | None = None

# Example output
issue = ExtractedIssue(
    name="Implement JWT authentication",
    description="Add JWT-based auth with refresh tokens",
    confidence="RECOMMENDED",
    rationale="Clear implementation task with specific requirements (JWT, refresh tokens)",
    source_block_id="block-abc123",
    labels=["backend", "security"],
    priority="high",
)
```

### Assignee Recommendation

```python
@dataclass
class AssigneeRecommendation:
    """Recommended assignee with confidence score."""
    user_id: UUID
    user_email: str
    confidence: Literal["RECOMMENDED", "DEFAULT", "CURRENT", "ALTERNATIVE"]
    rationale: str
    expertise_match: float  # 0.0-1.0
    workload: int  # Current assigned issues

# Example output
recommendation = AssigneeRecommendation(
    user_id=UUID("..."),
    user_email="alice@example.com",
    confidence="RECOMMENDED",
    rationale="Primary backend engineer, authored 80% of auth module, available capacity (2 current issues)",
    expertise_match=0.92,
    workload=2,
)
```

### Margin Annotation

```python
@dataclass
class MarginAnnotation:
    """Annotation for note block with confidence tagging."""
    block_id: str
    type: Literal["improvement", "question", "action-item", "warning"]
    content: str
    confidence: Literal["RECOMMENDED", "DEFAULT", "CURRENT", "ALTERNATIVE"]
    rationale: str
    action: dict[str, Any] | None = None

# Example output
annotation = MarginAnnotation(
    block_id="block-def456",
    type="action-item",
    content="Create issue: Implement rate limiting",
    confidence="RECOMMENDED",
    rationale="Explicit security requirement, standard API protection",
    action={
        "type": "create_issue",
        "issue_name": "Implement API rate limiting",
        "labels": ["backend", "security"],
        "priority": "high",
    },
)
```

## Frontend Display

### Visual Indicators

```typescript
// Tag to icon/color mapping
const CONFIDENCE_DISPLAY = {
  RECOMMENDED: { icon: '⭐', color: 'green', label: 'Recommended' },
  DEFAULT: { icon: '🔵', color: 'blue', label: 'Default' },
  CURRENT: { icon: '✓', color: 'gray', label: 'Current' },
  ALTERNATIVE: { icon: '🔀', color: 'yellow', label: 'Alternative' },
};

// Example UI component
<div className="ai-suggestion">
  <span className={`badge badge-${CONFIDENCE_DISPLAY[confidence].color}`}>
    {CONFIDENCE_DISPLAY[confidence].icon} {CONFIDENCE_DISPLAY[confidence].label}
  </span>
  <p>{suggestion}</p>
  <small className="rationale">{rationale}</small>
</div>
```

## Testing Requirements

### Unit Tests

```python
def test_confidence_tag_validation():
    """All AI suggestions must include valid confidence tag."""
    issue = extract_issue_from_note(note_content)

    assert issue.confidence in ["RECOMMENDED", "DEFAULT", "CURRENT", "ALTERNATIVE"]
    assert issue.rationale is not None
    assert len(issue.rationale) > 0

def test_confidence_rationale_quality():
    """Rationale should be specific and actionable."""
    annotation = generate_annotation(block_content)

    # Bad rationales to avoid
    bad_rationales = ["seems good", "probably right", "AI thinks so"]
    assert annotation.rationale.lower() not in bad_rationales

    # Should contain evidence
    assert len(annotation.rationale.split()) >= 5  # At least 5 words
```

## Anti-Patterns

### ❌ DON'T: Use numeric confidence scores

```json
// ❌ INCORRECT
{
  "suggestion": "Add validation",
  "confidence": 0.87,
  "confidence_percentage": "87%"
}

// ✅ CORRECT
{
  "suggestion": "Add validation",
  "confidence": "RECOMMENDED",
  "rationale": "Input field lacks validation, security best practice"
}
```

### ❌ DON'T: Use vague terms

```json
// ❌ INCORRECT
{
  "suggestion": "Fix the bug",
  "confidence": "likely",  // Not a valid tag
  "rationale": "Probably a good idea"
}

// ✅ CORRECT
{
  "suggestion": "Fix the bug",
  "confidence": "RECOMMENDED",
  "rationale": "Exception thrown on null input, affects 20% of users"
}
```

### ❌ DON'T: Omit rationale

```json
// ❌ INCORRECT
{
  "priority": "high",
  "confidence": "RECOMMENDED"
}

// ✅ CORRECT
{
  "priority": "high",
  "confidence": "RECOMMENDED",
  "rationale": "Blocks critical user workflow, mentioned in 3 support tickets"
}
```

## References

- **Design Decision**: DD-048 (AI Confidence Tagging)
- **Architecture**: `docs/architect/ai-layer.md` (Confidence Scoring)
- **Skills**: All skills in `backend/.claude/skills/*/SKILL.md` use confidence tagging
- **Agents**: All agents in `backend/src/pilot_space/ai/agents/*_sdk_agent.py` implement tagging
