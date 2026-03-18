# Note-First Paradigm

The Note-First paradigm is PilotSpace's core design philosophy (DD-013): **users think in documents, and issues emerge naturally through AI-powered extraction**.

## How It Works

```text
User writes in Note Canvas (TipTap Editor)
  ↓
Ghost Text (500ms pause → inline AI suggestions)
  ↓
Margin Annotations (2s pause → suggestions in sidebar)
  ↓
Issue Extraction (AI discovers actionable items)
  ↓
Issues created with EXTRACTED links back to source blocks
```

No prescriptive forms. The note is the primary artifact.

## TipTap Editor

The note editor uses **TipTap** (ProseMirror-based) with 26 custom extensions:

### Foundation Extensions

- **StarterKit** — Core nodes/marks
- **Markdown** — Markdown I/O
- **TaskList / TaskItem** — Checkbox lists
- **Table** — Table support with row/header/cell

### AI Extensions

- **GhostTextExtension** — Inline AI completions after 500ms typing pause
- **MarginAnnotationExtension** — Annotation indicators in left gutter
- **MarginAnnotationAutoTriggerExtension** — AI annotations after 2s pause
- **AIBlockProcessingExtension** — Visual indicator when AI is modifying a block

### Block Management

- **BlockIdExtension** — Assigns stable UUIDs to every block (used by AI, annotations, scroll sync)
- **ParagraphSplitExtension** — Block separation on Enter
- **CodeBlockExtension** — Syntax-highlighted code with language selector

### Linking & References

- **IssueLinkExtension** — Auto-detect `[PS-XX]` references
- **InlineIssueExtension** — Inline issue badges with state colors
- **NoteLinkExtension** — Cross-note references
- **MentionExtension** — @mentions for users/notes
- **SlashCommandExtension** — /slash commands

## Ghost Text

Real-time inline AI completions that appear as faded text after the cursor.

**Flow**:

1. User types 10+ characters, pauses 500ms
2. GhostTextExtension fires `onTrigger()` callback
3. Frontend calls `POST /api/v1/ai/ghost-text`
4. Response streams suggestion text
5. User accepts: **Tab** (full) or **Right Arrow** (next word)
6. **Escape** to dismiss

**Model**: Claude Haiku (latency-critical, <1.5s SLA)

## Margin Annotations

AI-generated suggestions displayed as colored indicators in the left gutter.

**Trigger**: User pauses 2 seconds with 50+ characters in a block.

**Annotation Types**:

| Type            | Icon          | Color  | Purpose                |
| --------------- | ------------- | ------ | ---------------------- |
| Suggestion      | Lightbulb     | Blue   | Actionable improvement |
| Warning         | AlertTriangle | Amber  | Potential issue        |
| Question        | HelpCircle    | Purple | Needs clarification    |
| Insight         | Sparkles      | Green  | Background context     |
| Reference       | Link2         | Gray   | Related resources      |
| Issue Candidate | CircleDot     | Teal   | Extractable issue      |

**User Actions**: Click annotation → detail popover → Apply / Dismiss / Reject

## Issue Extraction

AI discovers actionable items from note content and creates structured issues.

**Flow**:

1. User clicks "Extract Issues" or AI suggests candidates
2. `POST /notes/{noteId}/extract-issues` (SSE stream)
3. Claude analyzes note content → returns issues with confidence scores
4. User reviews extracted issues in approval panel
5. Approved issues created with `NoteIssueLink(type=EXTRACTED, source_block_id)`

**Confidence Tags**:

- **Recommended** (90-100%): Clear best practice
- **Default** (70-89%): Standard choice
- **Alternative** (50-69%): Valid option, different trade-offs

## Auto-Save

Content persists automatically with a 2-second debounce.

**States**: `idle` → `dirty` → `saving` → `saved` → `idle`

- Max retries: 3 with exponential backoff
- `beforeunload` warning if unsaved changes
- **Cmd+S**: Force-flush via `issue-force-save` DOM event

## Note-Issue Links

Every link between a note and an issue is typed:

| Link Type    | Meaning                               |
| ------------ | ------------------------------------- |
| `EXTRACTED`  | Issue was extracted from this note    |
| `REFERENCED` | Note references this issue            |
| `RELATED`    | General relationship                  |
| `INLINE`     | Issue embedded inline in note content |

Links are bidirectional: navigate from note → issues, or from issue detail → source notes.

## Block Reference System (¶N)

The AI agent uses human-readable block references instead of raw UUIDs:

- Each note block gets a stable UUID via `BlockIdExtension`
- `BlockRefMap` converts UUIDs to `¶1, ¶2, ¶3` for Claude prompts
- Agent references blocks as `¶N` → resolved to UUID before backend dispatch
- Prevents UUID corruption in LLM output

## Knowledge Graph Population

Notes feed into the knowledge graph asynchronously:

```text
Note created/updated
  → Enqueue kg_populate job (pgmq)
  → MemoryWorker processes job
  → Convert TipTap JSON → Markdown → Heading-based chunks
  → Generate embeddings (OpenAI text-embedding-3-large)
  → Create GraphNode entities (NOTE, NOTE_CHUNK)
  → Find similar nodes (cosine similarity ≥ 0.75)
  → Create RELATES_TO edges (max 5 per chunk)
```

This enables semantic search and context expansion across the workspace.

## Version History

Point-in-time snapshots of note content:

- **Triggers**: Auto (periodic), Manual (user), AI_BEFORE/AI_AFTER (AI edits)
- **Optimistic lock**: `version_number` prevents concurrent overwrites
- **Operations**: List versions, restore to version, undo AI changes
- **Retention**: Pinned versions exempt from cleanup
