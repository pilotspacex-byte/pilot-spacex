---
name: sprint-planning
description: Generate a sprint planning checklist with tasks, assignments, and timeline
feature_module: projects
trigger:
  - "plan sprint"
  - "sprint planning"
  - "plan next iteration"
  - "/sprint-plan"
tools:
  - insert_block
  - search_issues
  - get_project
---

# Sprint Planning Skill

You are helping the user plan a sprint. Follow these steps:

## Steps

1. **Gather context**: Use `get_project` to understand the current project scope and priorities.
2. **Find candidates**: Use `search_issues` to find issues in Backlog or Todo state that are unassigned to a cycle.
3. **Generate checklist**: Create a Smart Checklist (taskList) with the top priority items for the sprint.
4. **Insert into note**: Use `insert_block` to add the checklist to the current note.

## Output Format

Insert a taskList block with items structured as:
- Each taskItem should have:
  - `checked: false` (not started)
  - `assignee`: suggested team member (if known from project context)
  - `priority`: mapped from issue priority
  - `dueDate`: sprint end date
  - Text: issue title with `[PS-XX]` reference

## Example

For a 2-week sprint starting Feb 15:

```json
{
  "type": "taskList",
  "content": [
    {
      "type": "taskItem",
      "attrs": { "checked": false, "priority": "high", "dueDate": "2026-02-28" },
      "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "[PS-42] Implement user authentication" }] }]
    },
    {
      "type": "taskItem",
      "attrs": { "checked": false, "priority": "medium", "dueDate": "2026-02-28" },
      "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "[PS-43] Add role-based access control" }] }]
    }
  ]
}
```

## Rules

- Maximum 15 items per sprint checklist
- Prioritize by: urgent > high > medium > low
- Include effort estimates if available from issues
- Flag any items that have unresolved dependencies
- If no issues found in backlog, suggest the user creates issues first
