# PilotSpaceStore Usage Guide

**Version**: 1.0.0 (Wave 2 Frontend)
**Date**: 2026-01-28

## Overview

`PilotSpaceStore` is a unified MobX store for conversational AI agent interactions. It consolidates chat, tasks, approvals, and context management with SSE streaming support.

## Quick Start

```typescript
import { observer } from 'mobx-react-lite';
import { useAIStore } from '@/hooks/useAIStore';

const ChatComponent = observer(() => {
  const { pilotSpace } = useAIStore();

  // Set context
  React.useEffect(() => {
    pilotSpace.setNoteContext({
      noteId: 'note-123',
      selectedText: 'User selected text',
      selectedBlockIds: ['block-1', 'block-2'],
    });
  }, []);

  // Send message
  const handleSend = async (message: string) => {
    await pilotSpace.sendMessage(message);
  };

  return (
    <div>
      {pilotSpace.messages.map(msg => (
        <div key={msg.id}>{msg.content}</div>
      ))}
      {pilotSpace.streamingState.isStreaming && (
        <div>{pilotSpace.streamingState.streamContent}</div>
      )}
    </div>
  );
});
```

## Core Features

### 1. Conversation Management

**Send Message**:

```typescript
await pilotSpace.sendMessage('Extract issues from this note', {
  skillInvoked: 'extract-issues',
});
```

**Access Messages**:

```typescript
pilotSpace.messages; // ChatMessage[]
pilotSpace.streamingState; // StreamingState
pilotSpace.sessionId; // string | null
```

**Clear Conversation**:

```typescript
pilotSpace.clear(); // Clears messages, aborts streaming
```

### 2. Task Tracking

**Active Tasks** (computed):

```typescript
pilotSpace.activeTasks; // TaskState[] (pending or in_progress)
```

**Completed Tasks** (computed):

```typescript
pilotSpace.completedTasks; // TaskState[] (completed)
```

**Manual Task Management**:

```typescript
pilotSpace.addTask('task-123', {
  subject: 'Analyzing code',
  status: 'in_progress',
  progress: 45,
  currentStep: 'Step 2 of 5',
  totalSteps: 5,
});

pilotSpace.updateTaskStatus('task-123', 'completed');
pilotSpace.removeTask('task-123');
```

### 3. Approval Flow (DD-003)

**Pending Approvals**:

```typescript
pilotSpace.pendingApprovals; // ApprovalRequest[]
```

**Approve Request**:

```typescript
await pilotSpace.approveRequest('request-123');
```

**Reject Request**:

```typescript
await pilotSpace.rejectRequest('request-123', 'Not aligned with requirements');
```

**Approval Request Structure**:

```typescript
interface ApprovalRequest {
  requestId: string;
  actionType: string; // 'create_issue', 'modify_issue', etc.
  description: string;
  consequences?: string;
  affectedEntities: Array<{ type: string; id: string; name: string }>;
  urgency: 'low' | 'medium' | 'high';
  proposedContent?: unknown;
  expiresAt: Date;
  confidenceTag?: 'RECOMMENDED' | 'DEFAULT' | 'CURRENT' | 'ALTERNATIVE';
  createdAt: Date;
}
```

### 4. Context Management

**Note Context**:

```typescript
pilotSpace.setNoteContext({
  noteId: 'note-123',
  selectedText: 'Selected content',
  selectedBlockIds: ['block-1', 'block-2'],
  noteTitle: 'Project Requirements',
});
```

**Issue Context**:

```typescript
pilotSpace.setIssueContext({
  issueId: 'issue-456',
  issueTitle: 'Add authentication',
  issueStatus: 'in_progress',
});
```

**Clear Context**:

```typescript
pilotSpace.clearContext(); // Clears both note and issue context
```

**Conversation Context** (computed):

```typescript
pilotSpace.conversationContext;
// Returns: ConversationContext {
//   noteId, issueId, projectId, selectedText, selectedBlockIds
// }
```

## SSE Event Handling

The store handles 8 SSE event types automatically:

| Event Type         | Handler                    | Purpose                |
| ------------------ | -------------------------- | ---------------------- |
| `message_start`    | `handleMessageStart()`     | Initialize new message |
| `text_delta`       | `handleTextDelta()`        | Append streaming text  |
| `tool_use`         | `handleToolUseStart()`     | Record tool invocation |
| `tool_result`      | `handleToolResult()`       | Update tool result     |
| `task_progress`    | `handleTaskUpdate()`       | Update task status     |
| `approval_request` | `handleApprovalRequired()` | Queue approval         |
| `message_stop`     | `handleTextComplete()`     | Finalize message       |
| `error`            | `handleError()`            | Handle errors          |

Events are automatically routed based on type guards from `types/events.ts`.

## Integration with ChatView Components

### MessageList Integration

```typescript
const MessageList = observer(() => {
  const { pilotSpace } = useAIStore();

  return (
    <div>
      {pilotSpace.messages.map(message => (
        <MessageItem key={message.id} message={message} />
      ))}
      {pilotSpace.streamingState.isStreaming && (
        <StreamingIndicator content={pilotSpace.streamingState.streamContent} />
      )}
    </div>
  );
});
```

### TaskPanel Integration

```typescript
const TaskPanel = observer(() => {
  const { pilotSpace } = useAIStore();

  return (
    <div>
      <h3>Active Tasks ({pilotSpace.activeTasks.length})</h3>
      {pilotSpace.activeTasks.map(task => (
        <TaskItem key={task.id} task={task} />
      ))}
    </div>
  );
});
```

### DestructiveApprovalModal Integration

```typescript
const DestructiveApproval = observer(() => {
  const { pilotSpace } = useAIStore();

  if (pilotSpace.pendingApprovals.length === 0) return null;

  const request = pilotSpace.pendingApprovals[0];

  return (
    <DestructiveApprovalModal
      approval={request}
      isOpen={true}
      onApprove={handleApprove}
      onReject={handleReject}
      onClose={handleClose}
        <Button onClick={() => pilotSpace.approveRequest(request.requestId)}>
          Approve
        </Button>
        <Button onClick={() => pilotSpace.rejectRequest(request.requestId)}>
          Reject
        </Button>
      </DialogActions>
    </Dialog>
  );
});
```

## Lifecycle Methods

**Abort Streaming**:

```typescript
pilotSpace.abort(); // Stops SSE connection
```

**Clear State**:

```typescript
pilotSpace.clear(); // Clears messages, tasks, approvals
```

**Reset Store**:

```typescript
pilotSpace.reset(); // Clears all state including context
```

## Type Imports

```typescript
import type {
  ChatMessage,
  MessageRole,
  StreamingState,
  ConversationContext,
  ToolCall,
  TaskState,
  ApprovalRequest,
  NoteContext,
  IssueContext,
  SkillDefinition,
  ConfidenceTag,
} from '@/stores/ai';
```

## Error Handling

**Error State**:

```typescript
pilotSpace.error; // string | null
```

**Example**:

```typescript
if (pilotSpace.error) {
  toast.error(pilotSpace.error);
}
```

## Best Practices

1. **Always use `observer`** for components accessing store state
2. **Set context before sending messages** for context-aware responses
3. **Handle pending approvals** to prevent approval queue buildup
4. **Clear context on unmount** to avoid stale context
5. **Use computed properties** (`activeTasks`, `completedTasks`) instead of filtering manually
6. **Check streaming state** before sending new messages

## Performance Tips

1. **Use `observer` granularly** - Only wrap components that read store state
2. **Leverage computed properties** - MobX caches computed values
3. **Batch updates** - MobX automatically batches state updates
4. **Clear old tasks** - Remove completed tasks to prevent memory leaks

## References

- **Types**: `frontend/src/stores/ai/types/`
- **SSE Client**: `frontend/src/lib/sse-client.ts`
- **MobX Patterns**: `docs/dev-pattern/21c-frontend-mobx-state.md`
- **Approval Rules**: `docs/DESIGN_DECISIONS.md#DD-003`
- **Confidence Tags**: `docs/DESIGN_DECISIONS.md#DD-048`

## Examples

See `frontend/src/features/ai/ChatView/` for complete integration examples.
