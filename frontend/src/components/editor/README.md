# Editor Components Architecture

**Scope**: NoteCanvas, TipTap extensions, editor-specific components
**Parent**: [`../README.md`](../README.md)

---

## NoteCanvas Architecture

**Implementation**: `NoteCanvas.tsx`

Central editor component. Props: `noteId`, `content` (TipTap JSON), `readOnly`, `onChange`, `onSave`, `isLoading`, `workspaceId`, `workspaceSlug`, metadata (title, author, dates).

### Layout (65/35 Split)

```
NoteCanvas (responsive)
├── Left (65%): Editor
│   ├── InlineNoteHeader (merged)
│   ├── EditorContent (TipTap) + 13 extensions
│   ├── SelectionToolbar (float on selection)
│   ├── MarginAnnotations (AI hints)
│   └── ThreadedDiscussion (per-block)
├── ResizableHandle (draggable)
└── Right (35%): ChatView
    ├── ChatMessage list
    ├── AI Tool use + results
    └── Approval modals
```

### Responsive Behavior

- **2xl+**: Wider content, larger ChatView
- **xl-2xl**: Standard wide layout
- **lg-xl**: Side-by-side with ChatView
- **md-lg**: ChatView collapsible
- **<md**: Mobile overlay (NoteCanvasMobileLayout)

### State Management

- **TanStack Query**: Note content loading/saving
- **MobX**: Selection state, toolbar visibility, active blocks
- **SSE Streaming**: Real-time content updates from AI

---

## 13 TipTap Extensions

All extensions live in `extensions/` and are independently testable. Instantiated via `createEditorExtensions()` factory.

| #   | Extension                                | Purpose                                   | Key Feature                                     |
| --- | ---------------------------------------- | ----------------------------------------- | ----------------------------------------------- |
| 1   | **BlockIdExtension**                     | Auto-assign unique IDs to blocks          | UUID generation for AI tool references          |
| 2   | **GhostTextExtension**                   | Inline autocomplete on 500ms pause        | Gemini Flash, 50 token max, Tab/Escape handling |
| 3   | **AnnotationMark**                       | Highlight text with annotation marks      | CSS: `annotation-mark`                          |
| 4   | **MarginAnnotationExtension**            | Visual margin hints in left gutter        | Color-coded by type, hover to expand            |
| 5   | **MarginAnnotationAutoTriggerExtension** | Trigger AI annotations after pause        | 2s debounce, 50+ char threshold                 |
| 6   | **IssueLinkExtension**                   | Auto-detect PS-123 syntax                 | Hover preview, state colors, keyboard nav       |
| 7   | **InlineIssueExtension**                 | Inline issue references with state colors | Markdown: `[PS-99](issue:uuid)`                 |
| 8   | **CodeBlockExtension**                   | Syntax-highlighted code blocks            | lowlight integration, copy button               |
| 9   | **MentionExtension**                     | @mentions for users/notes                 | Autocomplete popup, max 10 suggestions          |
| 10  | **SlashCommandExtension**                | /slash commands for formatting            | Command menu, AI commands                       |
| 11  | **ParagraphSplitExtension**              | Double-newline to new paragraph           | Paste transformation                            |
| 12  | **AIBlockProcessingExtension**           | Track blocks being processed by AI        | CSS class for pending blocks                    |
| 13  | **LineGutterExtension**                  | Line numbers + fold buttons               | Nested indentation, foldable headings           |

All extensions follow `Extension.create({ name, addGlobalAttributes?, addProseMirrorPlugins? })` pattern. See individual extension files for implementation.

---

## Auto-Save

No save button -- auto-save only. MobX reaction triggers 2s debounce on content changes. SaveStatus indicator shows idle/saving/saved/error. Error notification with retry on click. Dirty state tracked in MobX.

See `NoteCanvas.tsx` and `NoteStore.ts` for implementation.

---

## Editor Components

| Component                      | Purpose                                       |
| ------------------------------ | --------------------------------------------- |
| **NoteCanvas.tsx**             | Main editor: 65/35 split (canvas + ChatView)  |
| **NoteCanvasMobileLayout.tsx** | Mobile responsive overlay                     |
| **RichNoteHeader.tsx**         | Rich metadata header (title, author, dates)   |
| **InlineNoteHeader.tsx**       | Compact inline header                         |
| **NoteTitleBlock.tsx**         | Title block with sync to note.title           |
| **MarginAnnotations.tsx**      | Margin hints + AI suggestions                 |
| **SelectionToolbar.tsx**       | Floating toolbar on text selection            |
| **ThreadedDiscussion.tsx**     | Threaded AI discussions per block             |
| **AIThreadIndicator.tsx**      | Indicator for AI-assisted blocks              |
| **AskPilotInput.tsx**          | Input for block-level AI actions              |
| **IssueBox.tsx**               | Rainbow-bordered extracted issue box          |
| **OffScreenAIIndicator.tsx**   | Indicator for off-screen AI activity          |
| **AutoTOC.tsx**                | Auto-generated table of contents              |
| **VersionHistoryPanel.tsx**    | Version history + rollback                    |
| **CollapsedChatStrip.tsx**     | Collapsed AI chat indicator                   |
| **NoteMetadata.tsx**           | Metadata: word count, topics, created/updated |

---

## File Organization

```
frontend/src/components/editor/
├── NoteCanvas.tsx                # Main editor (65/35 split)
├── NoteCanvasMobileLayout.tsx    # Mobile responsive overlay
├── RichNoteHeader.tsx            # Rich metadata header
├── InlineNoteHeader.tsx          # Compact inline header
├── NoteTitleBlock.tsx            # Title block
├── MarginAnnotations.tsx         # Margin hints + AI suggestions
├── SelectionToolbar.tsx          # Floating toolbar on selection
├── ThreadedDiscussion.tsx        # Per-block AI discussions
├── AIThreadIndicator.tsx         # AI-assisted block indicator
├── AskPilotInput.tsx             # Block-level AI input
├── IssueBox.tsx                  # Extracted issue box
├── OffScreenAIIndicator.tsx      # Off-screen AI indicator
├── AutoTOC.tsx                   # Auto table of contents
├── VersionHistoryPanel.tsx       # Version history
├── CollapsedChatStrip.tsx        # Collapsed chat indicator
├── NoteMetadata.tsx              # Word count, topics, dates
├── extensions/                   # TipTap extensions (13 total)
├── plugins/                      # ProseMirror plugins
├── hooks/
│   └── useEditorSync.ts
├── index.ts                      # Barrel export
└── __tests__/
```

---

## Related Documentation

- **Parent Components**: [`../README.md`](../README.md)
- **Notes Feature Module**: [`../../features/notes/README.md`](../../features/notes/README.md)
- **AI Stores**: [`../../stores/ai/README.md`](../../stores/ai/README.md)
- **Design Decisions**: DD-067 (ghost text), DD-013 (Note-First)
