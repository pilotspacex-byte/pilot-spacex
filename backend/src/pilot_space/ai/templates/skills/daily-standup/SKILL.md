---
name: daily-standup
description: Generate a formatted daily standup report from workspace issue activity
---

# Daily Standup Skill

Generate a ready-to-share standup report by querying issue states and transitions for the requesting user.

## Quick Start

Use this skill when:
- User requests standup (`/daily-standup`, `/standup`)
- User asks "what did I work on yesterday?" or "generate my standup"
- User needs a quick status update for a team meeting

**Example**:
```
User: /daily-standup

## Yesterday (Completed)
- [PS-42] Implement OAuth 2.0 login flow
- [PS-38] Fix pagination on issue list

## Today (In Progress)
- [PS-45] Add ghost text block-type routing
- [PS-51] Write unit tests for standup skill

## Blockers
- [PS-49] Deploy staging environment — blocked by: waiting on DevOps credentials (depends on PS-47)

```

## Workflow

1. **Determine Workday Window**
   - If today is Monday, "yesterday" covers Friday through Sunday (3 days)
   - If today is Tuesday-Friday, "yesterday" covers the previous calendar day
   - Use UTC dates for consistency; the window starts at 00:00 UTC of the first covered day

2. **Query Completed Issues (Yesterday)**
   - Use `list_issues` with state filter `Done`
   - Filter to issues assigned to the requesting user
   - Filter to issues whose state transitioned to `Done` within the workday window
   - Include issue identifier (e.g., PS-42) and title

3. **Query In-Progress Issues (Today)**
   - Use `list_issues` with state filter `In Progress`
   - Filter to issues assigned to the requesting user
   - Include issue identifier and title

4. **Query Blocked Issues (Blockers)**
   - Use `list_issues` with state filter `Blocked`
   - Filter to issues assigned to the requesting user
   - For each blocked issue, use `get_issue` to retrieve dependency context and blocker reason
   - Include issue identifier, title, and blocking reason

5. **Format Output**
   - Use the three-section format: Yesterday, Today, Blockers
   - Each item is a bullet with `[PS-XX] Title`
   - Blockers include a " -- blocked by: {reason}" suffix
   - If a section has no items, include "(No items)" under that heading
   - If all sections are empty, add a suggestion: "No recent activity found. Consider reviewing backlog items."

6. **Output Clean Text**
   - Plain markdown suitable for copy-paste into Slack, Teams, or email
   - No JSON wrapping -- just clean text
   - Keep it concise; no extra commentary

## Output Format

```
## Yesterday (Completed)
- [PS-42] Implement OAuth 2.0 login flow
- [PS-38] Fix pagination on issue list

## Today (In Progress)
- [PS-45] Add ghost text block-type routing

## Blockers
- [PS-49] Deploy staging environment -- blocked by: waiting on DevOps credentials (depends on PS-47)
```

If no activity:
```
## Yesterday (Completed)
(No items)

## Today (In Progress)
(No items)

## Blockers
(No items)

No recent activity found. Consider reviewing backlog items.
```

## MCP Tools Used

- `list_issues` — query issues by state and assignee
- `get_issue` — retrieve issue details for blocker context

## Quality Checklist

- Issue identifiers use workspace prefix format (e.g., PS-42)
- All three sections always present
- Monday standup covers Friday-Sunday
- Output is plain markdown, no JSON
- Empty sections show "(No items)" not blank

## Integration Points

- **Note Canvas**: User can paste standup into a daily note
- **Slack/Teams**: Output is copy-paste ready
- **Approval Flow**: AUTO_EXECUTE (read-only, non-destructive)
