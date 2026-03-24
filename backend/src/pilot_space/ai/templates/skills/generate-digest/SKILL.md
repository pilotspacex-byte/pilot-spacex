---
name: generate-digest
description: Analyzes workspace state and generates actionable insights
feature_module: notes
trigger: scheduled
---

# Generate Digest Skill

Analyze workspace activity and generate categorized, actionable suggestions for the AI Digest panel.

## Quick Start

Use this skill when:
- Hourly background job triggers digest generation
- User manually refreshes the digest panel
- System detects significant workspace state changes

## Workflow

1. **Receive Workspace Context**
   - Recent issues (last 7 days): state, assignee, priority, activity
   - Recent notes (last 7 days): annotations, extraction status
   - Active cycles: progress metrics, burndown
   - Issue links and dependencies

2. **Analyze for Actionable Insights**
   Categories to check:
   - `stale_issues`: Issues not updated in 3+ days while in active state
   - `unlinked_notes`: Notes with no linked issues (potential extraction candidates)
   - `review_needed`: Issues in review state for 2+ days
   - `blocked_dependencies`: Issues blocked by unresolved dependencies
   - `cycle_risk`: Cycles at risk of missing targets (>70% time, <50% done)
   - `overdue_items`: Issues past target date
   - `unassigned_priority`: High/urgent priority issues with no assignee
   - `duplicate_candidates`: Issues with high semantic similarity
   - `stale_prs`: PRs open for 3+ days without review
   - `annotation_pending`: Notes with unaddressed AI annotations
   - `inactive_members`: Team members with no activity in 5+ days
   - `documentation_gaps`: Features without linked documentation notes

3. **Score Relevance**
   For each suggestion, score 0.0-1.0 based on:
   - Ownership: Is the user the owner/assignee? (+0.3)
   - Recency: How recently did the user interact with related items? (+0.2)
   - Priority: Is the related item high/urgent priority? (+0.2)
   - Impact: Does this affect active cycles or deadlines? (+0.3)

4. **Return Structured Output**

## Output Format

```json
{
  "suggestions": [
    {
      "id": "uuid",
      "category": "stale_issues",
      "title": "3 issues haven't been updated this week",
      "description": "PS-42, PS-55, PS-61 are in progress but have no activity since Monday",
      "entity_id": "uuid",
      "entity_type": "issue",
      "action_url": "/workspace/issues?filter=stale",
      "relevance_score": 0.85
    }
  ],
  "summary": "Generated 8 suggestions across 5 categories",
  "tokens_used": {
    "input": 950,
    "output": 420
  }
}
```

## Constraints

- Context must stay under 4000 tokens
- Maximum 20 suggestions per digest
- Each suggestion must have a unique (entity_id, category) pair
- Relevance scores must be between 0.0 and 1.0

## Integration Points

- **DigestContextBuilder**: Builds SQL aggregate context (<4000 tokens)
- **DigestJobHandler**: Orchestrates the job, stores results
- **WorkspaceDigest model**: Stores suggestions as JSONB
- **Queue**: LOW priority (`ai_low`), 60s timeout, 3 retries

## References

- Spec: specs/012-homepage-note/spec.md (Background Job Specification)
- US-19: Homepage Hub feature
