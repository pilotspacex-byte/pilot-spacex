# ChatView - PilotSpace AI Conversational Interface

> **Architecture Reference**: `docs/architect/agent-architecture-remediation-plan.md` Phase 4.2
> **Version**: 1.0.0
> **Date**: 2026-01-27

## Overview

ChatView is the unified conversational AI interface for PilotSpace, implementing the centralized agent architecture from `pilotspace-agent-architecture.md` v1.5.0. It provides a seamless chat experience with skill invocation, agent spawning, task tracking, and human-in-the-loop approvals.

## Component Tree

```
ChatView/
├── ChatView.tsx                  # Main container with store integration
├── ChatHeader.tsx                # Title, status, task badges, session info
├── MessageList/
│   ├── MessageList.tsx           # Auto-scrolling conversation container
│   ├── MessageGroup.tsx          # Groups consecutive messages by role
│   ├── UserMessage.tsx           # User message bubble
│   ├── AssistantMessage.tsx      # AI message bubble with markdown
│   ├── ToolCallList.tsx          # Expandable tool call displays
│   └── StreamingContent.tsx      # Animated streaming indicator
├── TaskPanel/
│   ├── TaskPanel.tsx             # Collapsible task tracking panel
│   ├── TaskList.tsx              # Tabbed list (active/pending/completed)
│   ├── TaskItem.tsx              # Individual task card
│   └── TaskSummary.tsx           # Progress bar and counts
├── ApprovalOverlay/
│   ├── ApprovalOverlay.tsx       # Floating indicator + queue manager
│   ├── ApprovalDialog.tsx        # Approval/reject dialog
│   ├── IssuePreview.tsx          # Issue data preview
│   ├── ContentDiff.tsx           # Before/after comparison
│   └── GenericJSON.tsx           # Fallback JSON display
└── ChatInput/
    ├── ChatInput.tsx             # Auto-resizing textarea + toolbar
    ├── ContextIndicator.tsx      # Active context badges
    ├── SkillMenu.tsx             # Searchable skill selector
    └── AgentMenu.tsx             # Searchable agent selector
```

## Key Features

### 1. Conversational Interface

- **Auto-scrolling messages** with scroll-to-bottom button
- **Streaming content** with animated cursor
- **Message grouping** by role for better visual hierarchy
- **Tool call displays** with collapsible input/output
- **Markdown support** for rich text responses

### 2. Skill & Agent Invocation

- **Slash commands** (`\skill-name`) for skill invocation
- **At mentions** (`@agent-name`) for agent spawning
- **Searchable menus** with keyboard navigation (Command pattern)
- **Categorized skills** (writing, notes, issues, code, documentation, planning)
- **Agent capabilities** displayed in menu

### 3. Task Tracking

- **Real-time progress** with active/pending/completed tabs
- **Task metadata** (subject, description, skill/subagent)
- **Progress summary** with completion percentage
- **Status indicators** (pending, in_progress, completed, failed)

### 4. Human-in-the-Loop Approvals (DD-003)

- **Floating indicator** with approval count
- **Approval queue** with auto-advance
- **Specialized previews** for issues, diffs, generic JSON
- **Expiration timer** for time-sensitive approvals
- **Rejection reasons** captured for feedback

### 5. Context Management

- **Note context** (selected text, block IDs, cursor position)
- **Issue context** (issue ID, title, description)
- **Project context** (project ID, name)
- **Dismissible badges** for clearing context

## Usage

### Basic Usage

```tsx
import { ChatView } from '@/features/ai/ChatView';
import { usePilotSpaceStore } from '@/stores/ai';

function MyComponent() {
  const store = usePilotSpaceStore();

  return <ChatView store={store} userName="John Doe" userAvatar="/avatars/john.png" />;
}
```

### With Note Context

```tsx
// Set context before opening chat
store.setNoteContext({
  noteId: 'note-123',
  selectedText: 'This is the selected text',
  selectedBlockIds: ['block-1', 'block-2'],
});

// User can then ask: "Extract issues from this selection"
```

### With Issue Context

```tsx
store.setIssueContext({
  issueId: 'issue-456',
  projectId: 'project-789',
  title: 'Fix login bug',
  description: 'Users cannot login with SSO',
});

// User can then ask: "Generate AI context for this issue"
```

### Skill Invocation

Users can type `\` to trigger the skill menu:

```
User: \extract-issues
AI: [Executes extract-issues skill, streams results]
```

### Agent Invocation

Users can type `@` to trigger the agent menu:

```
User: @pr-review the latest changes
AI: [Spawns pr-review subagent, streams analysis]
```

## Store Interface

ChatView expects a store implementing `IPilotSpaceStore`:

```typescript
interface IPilotSpaceStore {
  // Conversation
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
  sessionId: string | null;
  error: string | null;

  // Tasks
  tasks: Map<string, AgentTask>;
  activeTasks: AgentTask[];
  completedTasks: AgentTask[];

  // Approvals
  pendingApprovals: ApprovalRequest[];
  hasUnresolvedApprovals: boolean;

  // Context
  noteContext: NoteContext | null;
  issueContext: IssueContext | null;
  projectContext: ProjectContext | null;
  activeSkill: string | null;
  skillArgs: string | null;
  mentionedAgents: string[];

  // Actions
  sendMessage(content: string): Promise<void>;
  setNoteContext(ctx: NoteContext | null): void;
  setIssueContext(ctx: IssueContext | null): void;
  setProjectContext(ctx: ProjectContext | null): void;
  setActiveSkill(skill: string, args?: string): void;
  addMentionedAgent(agent: string): void;
  approveAction(id: string, modifications?: Record<string, unknown>): Promise<void>;
  rejectAction(id: string, reason: string): Promise<void>;
  abort(): void;
  clearConversation(): void;
}
```

## Accessibility

All components follow WCAG 2.2 AA standards:

- **Keyboard navigation** for all interactive elements
- **Focus indicators** with 2px solid outline
- **ARIA labels** for icon-only buttons
- **Touch targets** ≥44x44px on mobile
- **Screen reader** support with semantic HTML
- **Reduced motion** respected for animations

## Styling

Components use shadcn/ui patterns with Tailwind CSS:

- **Color system** via CSS variables (`--background`, `--foreground`, etc.)
- **Dark mode** support with `dark:` variants
- **Responsive design** with mobile-first approach
- **Smooth transitions** with `transition-colors` and `animate-*` classes

## Performance

- **Memo wrapping** for all components to prevent unnecessary re-renders
- **MobX observer** for reactive updates
- **Virtualization** ready (ScrollArea component)
- **Debounced input** for skill/agent detection
- **Lazy loading** for large message lists

## Testing

### Unit Tests

```bash
pnpm test ChatView
```

### E2E Tests

```bash
pnpm test:e2e features/ai/chat
```

Key test scenarios:

- ✅ Send message and receive response
- ✅ Invoke skill via slash command
- ✅ Invoke agent via at mention
- ✅ Track task progress
- ✅ Approve/reject actions
- ✅ Clear conversation
- ✅ Manage context (note, issue, project)

## Integration Points

### Backend API

ChatView integrates with `/api/v1/ai/chat` endpoint:

```typescript
POST /api/v1/ai/chat
Body: {
  "message": "string",
  "context": {
    "note_id": "uuid | null",
    "issue_id": "uuid | null",
    "project_id": "uuid | null",
    "selected_text": "string | null",
    "selected_block_ids": ["string"]
  },
  "session_id": "string | null"
}

Response: SSE stream with events:
- message_start
- content_block_start
- text_delta
- tool_use (skill/subagent invocation)
- approval_request
- task_progress
- message_stop
```

### NoteCanvas Integration

ChatView can be integrated into NoteCanvas as a sidebar:

```tsx
<NoteCanvas>
  <Sidebar>
    <ChatView store={store} />
  </Sidebar>
</NoteCanvas>
```

## Future Enhancements

- [ ] Message editing and regeneration
- [ ] Conversation forking
- [ ] Export conversation to markdown
- [ ] Voice input support
- [ ] Multi-modal attachments (images, files)
- [ ] Real-time collaboration indicators
- [ ] Custom skill creation UI
- [ ] Agent performance metrics

## References

- **Architecture**: `docs/architect/pilotspace-agent-architecture.md`
- **Remediation Plan**: `docs/architect/agent-architecture-remediation-plan.md`
- **Design Decisions**: `docs/DESIGN_DECISIONS.md` (DD-003, DD-048)
- **shadcn/ui AI Patterns**: https://shadcn.io/ai
