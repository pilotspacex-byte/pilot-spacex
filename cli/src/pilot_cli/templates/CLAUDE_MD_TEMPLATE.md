# Current Issue: {{ issue.title }}

> This section was injected by `pilot implement {{ issue.id }}`.
> Do NOT delete it — the pilot CLI reads this file on exit.

## Issue Context

| Field | Value |
|-------|-------|
| **ID** | {{ issue.id }} |
| **Status** | {{ issue.status }} |
| **Priority** | {{ issue.priority }} |
| **Labels** | {{ issue.labels | join(', ') or 'none' }} |

## Description

{{ issue.description or '_No description provided._' }}

## Acceptance Criteria

{% if issue.acceptance_criteria %}
{% for criterion in issue.acceptance_criteria %}
{{ loop.index }}. {{ criterion }}
{% endfor %}
{% else %}
_No acceptance criteria specified._
{% endif %}

## Relevant Notes

{% if linked_notes %}
{% for note in linked_notes %}
### {{ note.note_title }}

{% for block in note.relevant_blocks %}
> {{ block }}

{% endfor %}
{% endfor %}
{% else %}
_No linked notes for this issue._
{% endif %}

## Repository Context

| Field | Value |
|-------|-------|
| **Workspace** | {{ workspace.name }} ({{ workspace.slug }}) |
| **Project** | {{ project.name }} |
| **Repository** | {{ repository.clone_url }} |
| **Default Branch** | {{ repository.default_branch }} |
| **Your Branch** | `{{ suggested_branch }}` |

### Tech Stack Summary

{{ project.tech_stack_summary or '_Not specified._' }}

{% if kg_decisions %}

## Architecture Decisions & Code Patterns (Knowledge Graph)

These decisions and patterns from your workspace's knowledge graph are relevant to this issue:

{% for d in kg_decisions %}
- **{{ d.source_type }}** (score: {{ "%.2f"|format(d.score) }}): {{ d.snippet }}
{% endfor %}
{% endif %}
{% if related_prs %}

## Related Closed Issues & PRs

These previously completed issues and their PRs may serve as implementation reference:

{% for pr in related_prs %}
- {{ pr.issue_identifier }}: {{ pr.issue_title }} — [PR]({{ pr.pr_url }}) ({{ pr.pr_state or 'unknown' }})
{% endfor %}
{% endif %}
{% if sprint_peers %}

## Sprint Peer Issues (Conflict Awareness)

Other issues currently in progress in the same sprint. Avoid modifying the same files if possible:

{% for peer in sprint_peers %}
- **{{ peer.identifier }}** ({{ peer.state }}{% if peer.assignee_name %}, {{ peer.assignee_name }}{% endif %}): {{ peer.title }}
{% endfor %}
{% endif %}

## Your Task

**Implement this issue now.** Work through every acceptance criterion systematically.
Do not stop until all criteria are satisfied and all quality gates pass.

## Implementation Instructions

1. **Follow existing patterns** in `docs/dev-pattern/45-pilot-space-patterns.md`
2. **Run quality gates** before finishing:
   - Backend: `{{ backend_quality_gate }}`
   - Frontend: `{{ frontend_quality_gate }}`
3. **Write tests** for all new code (>80% coverage required)
4. **File size limit**: 700 lines max per code file
5. **Conventional commits**: `feat|fix|refactor(scope): description`
6. **Do NOT create a PR** — the `pilot` CLI will handle that automatically on exit

## Definition of Done

- [ ] All acceptance criteria implemented and tested
- [ ] Quality gates pass (no lint / type / test failures)
- [ ] No TODOs or placeholder code in committed files
- [ ] Commit message follows Conventional Commits format

## Completion Signal

When implementation is complete and all quality gates pass:
1. Stage all changes: `git add -A`
2. Exit Claude Code: type `/exit`
