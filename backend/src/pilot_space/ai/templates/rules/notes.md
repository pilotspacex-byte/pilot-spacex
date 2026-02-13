# Note Handling Rules

## Ghost Text:

1. **Match user's writing style and tone**:
   - Analyze previous paragraphs for:
     - Formality level (casual vs professional)
     - Sentence length (short vs long-form)
     - Technical depth (high-level vs detailed)
   - Mirror vocabulary choices (technical jargon vs plain language)
   - Preserve point-of-view (first-person, second-person, third-person)

2. **Never suggest more than 3 sentences at once**:
   - Keep suggestions concise to avoid overwhelming user
   - Focus on completing current thought, not writing entire sections
   - If longer content needed, stop at natural break point (paragraph end)

3. **Respect selected text boundaries**:
   - If user has text selected, ghost text should complete/enhance selection
   - Don't suggest text that would overwrite existing content
   - For mid-sentence selection, ensure grammatical continuation

4. **Timing and triggers**:
   - Delay: 500ms after user stops typing (DD-067)
   - Max tokens: 50 tokens per suggestion
   - Model: Gemini 2.0 Flash (lowest latency per DD-011)
   - Cancel on any user input (typing, deletion, cursor movement)

5. **Acceptance behavior**:
   - `Tab` key: Accept full suggestion
   - `→` (right arrow): Accept word-by-word
   - `Esc`: Dismiss ghost text
   - Any typing: Dismiss and show new suggestion after delay

## Margin Annotations:

1. **Include actionable suggestions only**:
   - **Good**: "Consider breaking this into subtasks" (provides action)
   - **Bad**: "This is interesting" (no actionable guidance)
   - **Good**: "Extract this as issue: 'Implement user auth'" (clear action)
   - **Bad**: "You mentioned authentication" (just observation)

2. **Link to specific note blocks by ID**:
   - Each annotation must reference `block_id` (paragraph/list UUID)
   - Enables precise highlighting in right margin
   - Preserves annotation-block relationship across edits

3. **Categorize annotations**:
   - **improvement**: Suggests enhancement to writing or structure
     - Example: "Add more context about why JWT was chosen over sessions"
   - **question**: Raises clarifying question
     - Example: "Should this support SSO providers (Google, GitHub)?"
   - **action-item**: Suggests creating issue or task
     - Example: "Create issue: Implement JWT refresh token rotation"
   - **warning**: Highlights potential problem
     - Example: "This conflicts with security requirements in previous note"

4. **Confidence tagging for action-items**:
   - All action-item annotations MUST include confidence tag (DD-048)
   - Example:
     ```json
     {
       "type": "action-item",
       "confidence": "RECOMMENDED",
       "rationale": "Clear implementation task with security implications"
     }
     ```

## Note Block Structure:

1. **Block types**:
   - `paragraph`: Text block
   - `heading`: Section header (h1-h6)
   - `list`: Bullet or numbered list (contains list_items)
   - `code`: Code block with language syntax
   - `quote`: Blockquote

2. **Block metadata**:
   - `id`: UUID for linking (annotations, issues)
   - `order`: Sequence number within note
   - `created_at`: Timestamp
   - `updated_at`: Timestamp

3. **Block linking**:
   - Issues can link to source blocks via `source_block_id`
   - Annotations link to blocks via `block_id`
   - Enables "show in note" navigation from issue view

## PM Block Types:

1. **Diagrams** (mermaid code blocks):
   - Insert via `insert_block` with markdown containing ` ```mermaid ` fenced code
   - 10 supported types: flowchart, sequence, gantt, class, ER, state, C4, pie, mindmap, git graph
   - Frontend auto-renders SVG preview below code block
   - Max 100 nodes per diagram for performance

2. **Smart Checklist** (enhanced taskList):
   - Insert via `insert_block` with taskList JSON content
   - Each taskItem supports: assignee, dueDate, priority (none/low/medium/high/urgent), isOptional, conditionalParentId
   - Optional items excluded from progress bar denominator
   - Conditional items greyed out when parent unchecked

3. **Decision Record** (pmBlock type: decision):
   - Insert via `insert_block` with pmBlock JSON: `{ "type": "pmBlock", "attrs": { "blockType": "decision", "data": "..." } }`
   - Status: open → decided → superseded
   - Options: each with label, description, pros[], cons[], effort, risk
   - Always include at least 2 options for binary decisions

4. **Form Block** (pmBlock type: form):
   - 10 field types: text, textarea, number, date, select, multiselect, checkbox, rating, email, url
   - Include validation rules (required, min, max, pattern)

5. **RACI Matrix** (pmBlock type: raci):
   - Rows = deliverables, columns = stakeholders
   - Exactly one Accountable (A) per deliverable (constraint)

6. **Risk Register** (pmBlock type: risk):
   - Each risk: description, probability (1-5), impact (1-5), score = P × I
   - Color coding: green (1-6), yellow (7-12), red (13-25)
   - Mitigation strategies: avoid, mitigate, transfer, accept

7. **Timeline** (pmBlock type: timeline):
   - Milestones with dates, dependencies, status (on-track/at-risk/blocked)

8. **KPI Dashboard** (pmBlock type: dashboard):
   - Widgets with metric name, current value, trend (up/down/flat)

## PM Block TipTap JSON Format:

When inserting PM blocks via `insert_block`, use this TipTap JSON structure:

```json
{
  "type": "pmBlock",
  "attrs": {
    "blockType": "decision",
    "data": "{\"title\":\"Choose DB\",\"options\":[...]}",
    "version": 1
  }
}
```

**Important**: The `data` field MUST be a JSON-encoded string, not a raw object.
The frontend parses it via `JSON.parse()` in the renderer.

Supported `blockType` values: `decision`, `form`, `raci`, `risk`, `timeline`, `dashboard`.

For `insert_pm_block` content_update operations, provide `pmBlockData`:
```json
{
  "operation": "insert_pm_block",
  "pmBlockData": {
    "blockType": "decision",
    "data": "{\"title\":\"...\",\"status\":\"open\",\"options\":[...]}",
    "version": 1
  },
  "afterBlockId": "target-block-id"
}
```

For `update_pm_block`, provide `blockId` and updated `pmBlockData`:
```json
{
  "operation": "update_pm_block",
  "blockId": "existing-pm-block-id",
  "pmBlockData": {
    "blockType": "decision",
    "data": "{\"title\":\"...\",\"status\":\"decided\",...}",
    "version": 1
  }
}
```

**Edit guard (FR-048)**: `update_pm_block` respects the user edit guard.
If a user has manually edited a PM block, the agent MUST NOT update it.
Instead, create a new block with the revised content.

## Batch Writing Strategy:

When the user asks to write, draft, or document content longer than 3 paragraphs,
split the output into multiple sequential tool calls (2-4 paragraphs each).

**Why**: Users see content appear progressively, giving real-time streaming feedback
instead of a long wait followed by a sudden content dump.

**Pattern**:
1. First batch: `write_to_note(note_id, markdown)` — appends 2-4 paragraphs at the end.
2. Read the newly created block references (¶N) from the tool result.
3. Subsequent batches: `insert_block(note_id, content_markdown, after_block_id=¶N)` —
   where ¶N is the last block from the previous batch.
4. Break at natural boundaries: after a heading, after a list, after a code block,
   or at the end of a logical section.

**Example** — user asks "Write an architecture overview":
- Batch 1: `write_to_note` with `# Architecture Overview\n\n## Goals\n\nParagraph about goals...`
- Batch 2: `insert_block` after ¶3 with `## Components\n\nComponent description...`
- Batch 3: `insert_block` after ¶6 with `## Data Flow\n\nFlow description...\n\n## Summary\n\n...`

**Short content** (≤3 paragraphs): Use a single `write_to_note` call — no batching needed.

**Updating existing blocks**: Use `update_note_block(block_id, new_content_markdown)` for
single-block replacements. For multi-block rewrites, replace each block individually with
sequential `update_note_block` calls (one per block being changed).

## AI Context for Notes:

1. **When generating ghost text**:
   - Context window: Current paragraph + previous 2 paragraphs
   - Include note metadata: title, labels, workspace context
   - Don't include unrelated notes or issues

2. **When creating margin annotations**:
   - Context window: Current block + full note content
   - Include related notes (semantic search, max 3 results)
   - Include workspace context (project labels, team expertise)

3. **Token budget**:
   - Ghost text: 500 tokens max context, 50 tokens max output
   - Margin annotations: 2000 tokens max context, 200 tokens max output

## Validation Rules:

1. **Note title**:
   - Non-empty string
   - Maximum 200 characters
   - Unique within workspace (soft constraint, warn on duplicates)

2. **Block content**:
   - Maximum 10,000 characters per block
   - Code blocks: Maximum 5,000 lines
   - Total note size: Maximum 1MB

3. **Annotation limits**:
   - Maximum 50 annotations per note
   - Maximum 10 pending (unresolved) annotations per block
   - Annotations auto-resolve after 30 days if not interacted with

## Integration Points:

- **GhostTextExtension**: TipTap extension implementing ghost text UI
- **MarginAnnotationExtension**: TipTap extension for margin suggestions
- **NoteStore**: MobX store managing note state
- **GhostTextAgent**: Generates contextual suggestions
- **MarginAnnotationAgent**: Creates actionable annotations

## References:

- Design Decision: DD-013 (Note-First Workflow)
- Design Decision: DD-011 (Model Selection for Latency)
- Design Decision: DD-048 (Confidence Tagging)
- User Story: US-01 (AI Ghost Text)
- User Story: US-02 (Margin Annotations)
- Frontend: `frontend/src/features/notes/editor/extensions/`
