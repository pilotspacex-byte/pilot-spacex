---
name: generate-pm-blocks
description: Generate PM blocks (decision, risk, timeline, RACI, form, dashboard) from natural language description
feature_module: projects
---

# Generate PM Blocks Skill

Generate structured PM blocks from natural language descriptions. Analyzes user input to determine which block types are appropriate and inserts them into the active note.

## Quick Start

Use this skill when:
- User requests PM block creation (`/generate-pm-blocks`)
- Planning sprints, projects, or milestones
- Setting up risk registers, decision records, or RACI matrices
- User describes a workflow that maps to multiple PM block types

**Example**:
```
User: "Set up sprint planning with timeline, risk register, and RACI matrix for our API migration"

AI calls create_pm_block 3 times:
1. create_pm_block(block_type="timeline", data={...}, after_block_id=null)
2. create_pm_block(block_type="risk", data={...}, after_block_id=<prev_block_ref>)
3. create_pm_block(block_type="raci", data={...}, after_block_id=<prev_block_ref>)

AI responds: "[RECOMMENDED] Inserted 3 PM blocks: Timeline with 4 milestones, Risk Register with 3 risks, and RACI Matrix for 3 deliverables."
```

## Workflow

1. **Parse Description**
   - Identify which block types the user needs from keywords:
     - Decision: "decide", "choice", "option", "evaluate", "pros/cons"
     - Form: "survey", "collect", "questionnaire", "feedback", "form"
     - RACI: "responsibility", "accountable", "who does what", "roles", "RACI"
     - Risk: "risk", "mitigation", "threat", "vulnerability", "impact"
     - Timeline: "timeline", "milestones", "schedule", "deadline", "phases"
     - Dashboard: "metrics", "KPIs", "tracking", "progress", "dashboard"
   - If no specific type is mentioned, infer from context (e.g., "sprint planning" implies timeline + risk)

2. **Generate Block Data**
   - For each identified block type, construct the data object following the schemas below
   - Use meaningful, context-specific content derived from the user's description
   - Generate realistic IDs (e.g., `m-1`, `r-1`, `w-1`, `f-1`, `o-1`, `d-1`)

3. **Insert Blocks Sequentially**
   - Call `create_pm_block` for each block type as a SEPARATE tool call
   - Use `after_block_id` from the previous insertion to maintain ordering
   - Users see each block appear progressively

4. **Respond with Summary**
   - Include confidence tag: `RECOMMENDED`, `SUGGESTED`, or `EXPERIMENTAL`
   - List what was created and any suggestions for refinement

## Data Schemas

### Decision Record (`block_type: "decision"`)
```json
{
  "title": "Choose Authentication Provider",
  "status": "open",
  "type": "multi-option",
  "options": [
    {
      "id": "o-1",
      "label": "Supabase Auth",
      "description": "Built-in auth with RLS integration",
      "pros": ["Native RLS", "Free tier"],
      "cons": ["Vendor lock-in"],
      "effort": "low",
      "risk": "low"
    },
    {
      "id": "o-2",
      "label": "Auth0",
      "description": "Enterprise auth provider",
      "pros": ["Enterprise features", "SSO"],
      "cons": ["Cost at scale"],
      "effort": "medium",
      "risk": "low"
    }
  ],
  "linkedIssueIds": []
}
```

### Form (`block_type: "form"`)
```json
{
  "title": "Sprint Retrospective",
  "fields": [
    {"id": "f-1", "label": "What went well?", "type": "textarea", "required": true},
    {"id": "f-2", "label": "What could improve?", "type": "textarea", "required": true},
    {"id": "f-3", "label": "Sprint satisfaction", "type": "rating", "required": false}
  ],
  "responses": {},
  "responseCount": 0
}
```

### RACI Matrix (`block_type: "raci"`)
```json
{
  "title": "API Migration Responsibilities",
  "stakeholders": ["Tech Lead", "Backend Dev", "QA Lead", "PM"],
  "deliverables": ["Database Migration", "API Endpoints", "Integration Tests"],
  "assignments": {
    "Database Migration": {"Tech Lead": "A", "Backend Dev": "R", "QA Lead": "C", "PM": "I"},
    "API Endpoints": {"Tech Lead": "C", "Backend Dev": "A", "QA Lead": "R", "PM": "I"},
    "Integration Tests": {"Tech Lead": "I", "Backend Dev": "C", "QA Lead": "A", "PM": "I"}
  }
}
```
**Rule**: Exactly one `A` (Accountable) per deliverable row.

### Risk Register (`block_type: "risk"`)
```json
{
  "title": "Sprint Risk Assessment",
  "risks": [
    {
      "id": "r-1",
      "title": "API breaking changes",
      "description": "Third-party API may introduce breaking changes",
      "probability": 3,
      "impact": 4,
      "score": 12,
      "mitigation": "mitigate",
      "mitigationPlan": "Pin API version, add integration tests",
      "owner": "Backend Lead",
      "status": "open"
    }
  ]
}
```
**Scoring**: probability (1-5) x impact (1-5). Colors: green (1-6), yellow (7-12), red (13-25).

### Timeline (`block_type: "timeline"`)
```json
{
  "title": "Q1 Project Milestones",
  "milestones": [
    {"id": "m-1", "name": "Design Review", "date": "2026-02-20", "status": "on-track", "dependencies": []},
    {"id": "m-2", "name": "MVP Release", "date": "2026-03-15", "status": "on-track", "dependencies": ["m-1"]},
    {"id": "m-3", "name": "Beta Launch", "date": "2026-03-30", "status": "on-track", "dependencies": ["m-2"]}
  ]
}
```

### Dashboard (`block_type: "dashboard"`)
```json
{
  "title": "Sprint Metrics",
  "widgets": [
    {"id": "w-1", "metric": "Story Points Completed", "value": 0, "trend": "flat", "unit": "pts", "target": 40},
    {"id": "w-2", "metric": "Bug Count", "value": 0, "trend": "flat", "unit": "", "target": 0},
    {"id": "w-3", "metric": "Code Coverage", "value": 80, "trend": "up", "unit": "%", "target": 85}
  ]
}
```

## Output Format

For each block type identified, call the `create_pm_block` MCP tool:

```
create_pm_block(
  note_id=<current_note_id>,
  block_type="<type>",
  data=<data_object>,
  after_block_id=<previous_block_ref or null>
)
```

Then respond in chat with a confidence tag and summary:

```
[RECOMMENDED] Inserted 3 PM blocks for sprint planning:
- Timeline: 4 milestones from Feb 20 to Mar 30
- Risk Register: 3 identified risks (1 high, 2 medium)
- RACI Matrix: 4 stakeholders across 3 deliverables

Suggestions:
- Add a Dashboard block to track sprint velocity
- Consider a Decision Record for the deployment strategy
```

## Examples

### Example 1: Sprint Planning
**Input**: "Set up sprint planning for our API migration project"

**Action**: Insert 3 blocks:
1. `create_pm_block(block_type="timeline", data={title: "API Migration Timeline", milestones: [...]})`
2. `create_pm_block(block_type="risk", data={title: "API Migration Risks", risks: [...]}, after_block_id=<prev>)`
3. `create_pm_block(block_type="raci", data={title: "API Migration RACI", ...}, after_block_id=<prev>)`

**Chat response**:
```
[RECOMMENDED] Inserted 3 PM blocks for API migration sprint planning:
- Timeline with key milestones
- Risk register with migration-specific risks
- RACI matrix for team responsibilities
```

### Example 2: Decision Record
**Input**: "Help us decide between REST and GraphQL for our new API"

**Action**: Insert 1 block:
1. `create_pm_block(block_type="decision", data={title: "REST vs GraphQL", type: "binary", options: [{label: "REST API", ...}, {label: "GraphQL", ...}]})`

**Chat response**:
```
[RECOMMENDED] Inserted Decision Record comparing REST vs GraphQL with pros, cons, effort, and risk for each option.
```

### Example 3: Full Project Setup
**Input**: "Create a complete project management setup for our new mobile app"

**Action**: Insert 5 blocks:
1. Timeline with project phases
2. RACI matrix for team roles
3. Risk register for common mobile dev risks
4. Dashboard for tracking KPIs
5. Decision record for tech stack choice

**Chat response**:
```
[RECOMMENDED] Inserted 5 PM blocks for mobile app project setup:
- Timeline: 5 phases from kickoff to launch
- RACI: 5 stakeholders across 4 deliverables
- Risk Register: 4 risks identified
- Dashboard: 5 KPI widgets
- Decision Record: Native vs Cross-platform

Suggestions:
- Add a Form block for team retrospectives
```

## Integration Points

- **PilotSpaceAgent**: Orchestrator invokes this skill via `/generate-pm-blocks` slash command
- **MCP Tool**: `create_pm_block` from `note_content_server.py` — inserts PM block widgets into note
- **Renderers**: Frontend PM block renderers in `features/notes/editor/extensions/pm-blocks/renderers/`
- **Rules**: `templates/rules/pm_blocks.md` — canonical data schemas and batch insertion rules

## References

- Design Decision: DD-013 (Note-First workflow)
- Design Decision: DD-048 (Confidence Tagging)
- Design Decision: DD-086 (Centralized agent with skills)
- Rules: `backend/src/pilot_space/ai/templates/rules/pm_blocks.md`
