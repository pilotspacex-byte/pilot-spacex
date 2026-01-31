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
   - Delay: 300ms after user stops typing (configurable)
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
