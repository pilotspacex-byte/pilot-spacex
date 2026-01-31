# Issue Handling Rules

## When creating issues:

1. **Always include required fields**:
   - `title`: Clear, concise description (≤100 chars)
   - `description`: Detailed explanation with context
   - `priority`: One of: critical, high, medium, low
   - `labels`: Project-specific labels (backend, frontend, bug, feature, etc.)

2. **Set state to "triage" by default**:
   - New issues start in triage state
   - Allows team to review and prioritize before assignment
   - State machine: triage → backlog → todo → in_progress → in_review → done → canceled

3. **Link to related notes when applicable**:
   - If issue extracted from note, preserve `source_block_id`
   - Creates bidirectional link between issue and note block
   - Enables traceability from issue back to original context

4. **Use project-specific label conventions**:
   - **Type labels**: bug, feature, enhancement, refactor, docs, test
   - **Domain labels**: backend, frontend, infrastructure, ai, integrations
   - **Priority labels**: p0 (critical), p1 (high), p2 (medium), p3 (low)
   - **Special labels**: security, performance, accessibility, breaking-change

## When updating issues:

1. **Preserve existing assignees unless explicitly changed**:
   - If updating other fields, don't clear assignee_id
   - Only modify assignee when explicitly requested by user or AI recommendation

2. **Track state transitions for analytics**:
   - Record state changes in activities table
   - Include transition metadata (actor_id, timestamp, reason)
   - Enables velocity tracking and cycle time metrics

3. **Add comment explaining AI-driven changes**:
   - When AI modifies issue (labels, priority, description):
     - Create activity record with `action_type: "ai_updated"`
     - Include rationale in comment field
     - Tag with confidence level (RECOMMENDED/DEFAULT/ALTERNATIVE)
   - Example: "AI updated priority to 'high' (RECOMMENDED): Issue blocks user authentication, mentioned in 3 related notes"

## Validation Rules:

1. **Title validation**:
   - Non-empty string
   - Maximum 100 characters
   - Should start with action verb (Implement, Fix, Add, Update, etc.) or be descriptive

2. **State transition validation**:
   - Cannot skip states (e.g., triage → in_progress requires backlog → todo first)
   - Cannot move done → in_progress without explicit reopen action
   - Canceled is terminal state (requires new issue to reopen)

3. **Assignment validation**:
   - Assignee must be workspace member
   - Cannot assign to deactivated users
   - Recommend assignee based on expertise and workload (use recommend-assignee skill)

## AI Confidence Tagging:

All AI suggestions for issue creation/updates MUST include confidence tags per DD-048:

- **RECOMMENDED**: Clear best practice, strong semantic match
  - Example: Extracting "Fix login bug" from note explicitly mentioning bug
- **DEFAULT**: Standard choice, safe option
  - Example: Setting priority to "medium" when no urgency markers present
- **CURRENT**: Existing state, no change suggested
  - Example: Issue already has appropriate labels
- **ALTERNATIVE**: Valid option with different tradeoffs
  - Example: Suggesting assignee when multiple qualified team members exist

## Integration Points:

- **IssueExtractorAgent**: Uses these rules when extracting from notes
- **IssueEnhancerAgent**: Uses label conventions when enhancing issues
- **AssigneeRecommenderAgent**: Uses assignment validation rules
- **DuplicateDetectorAgent**: Checks before creating new issues

## References:

- Design Decision: DD-013 (Note-First Workflow)
- Design Decision: DD-048 (Confidence Tagging)
- Design Decision: DD-003 (Human-in-the-loop Approval)
- Data Model: `specs/001-pilot-space-mvp/data-model.md` (Issue entity)
