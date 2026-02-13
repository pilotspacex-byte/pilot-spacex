# Retrospective Skill

## Triggers
- "retrospective", "retro", "sprint review", "/retro"

## Workflow
1. Use `search_issues` to find completed/cancelled issues in the current or recent cycle
2. Analyze velocity, blockers, and patterns
3. Generate a KPI Dashboard PM block with sprint metrics:
   ```json
   {
     "type": "pmBlock",
     "attrs": {
       "blockType": "dashboard",
       "data": "{\"title\":\"Sprint Retrospective\",\"widgets\":[{\"id\":\"w-1\",\"metric\":\"Completed Issues\",\"value\":0,\"trend\":\"flat\",\"unit\":\"\"}]}",
       "version": 1
     }
   }
   ```
4. Optionally insert a Decision Record for key retrospective action items

## Rules
- Include at least 3 KPI widgets: completed issues, velocity trend, blocker count
- Use trend indicators based on comparison with previous sprint
- Suggest actionable improvements, not just observations
- Link dashboard metrics to actual issue data when available
