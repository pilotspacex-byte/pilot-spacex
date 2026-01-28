# Data TestID Requirements for E2E Tests

**Generated**: 2026-01-28

This document maps E2E test requirements to component implementations and identifies missing `data-testid` attributes.

## Status Legend
- ❌ Missing - Attribute does not exist
- ⚠️ Partial - Some instances exist, others missing
- ✅ Complete - Attribute exists and correctly implemented

## Component Mapping

### ChatView.tsx
**Location**: `frontend/src/features/ai/ChatView/ChatView.tsx`

| Test ID | Status | Line | Required For |
|---------|--------|------|--------------|
| `data-testid="chat-view"` | ❌ Missing | Root div (line 170) | All chat tests - container detection |

**Fix Required**:
```tsx
// Line 170
<div className={cn('flex flex-col h-full bg-background', className)} data-testid="chat-view">
```

### ChatInput.tsx
**Location**: `frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx`

| Test ID | Status | Line | Required For |
|---------|--------|------|--------------|
| `data-testid="chat-input"` | ❌ Missing | Textarea (line 144) | Message input tests |
| `data-testid="send-button"` | ❌ Missing | Submit button (line 206) | Send message tests |
| `data-testid="abort-button"` | ❌ Missing | Abort button (line 195) | Streaming abort tests |

**Fix Required**:
```tsx
// Line 144
<Textarea
  data-testid="chat-input"
  ref={textareaRef}
  value={value}
  // ... rest of props
/>

// Line 195 (abort button)
<Button
  data-testid="abort-button"
  type="button"
  variant="destructive"
  size="icon"
  onClick={onAbort}
  className="shrink-0"
>

// Line 206 (send button)
<Button
  data-testid="send-button"
  type="button"
  size="icon"
  onClick={handleSubmitClick}
  disabled={!canSubmit}
  className="shrink-0"
>
```

### MessageList.tsx
**Location**: `frontend/src/features/ai/ChatView/MessageList/MessageList.tsx`

| Test ID | Status | Line | Required For |
|---------|--------|------|--------------|
| `data-testid="message-user"` | ❌ Missing | User message container | User message verification |
| `data-testid="message-assistant"` | ❌ Missing | AI message container | AI response verification |
| `data-testid="streaming-indicator"` | ❌ Missing | Streaming badge/spinner | Streaming state tests |

**Fix Required** (in MessageGroup.tsx or Message component):
```tsx
// For each message in MessageGroup
<div data-testid={`message-${message.role}`} className="...">
  {message.content}
</div>
```

### ChatHeader.tsx
**Location**: `frontend/src/features/ai/ChatView/ChatHeader.tsx`

| Test ID | Status | Line | Required For |
|---------|--------|------|--------------|
| `data-testid="chat-header"` | ❌ Missing | Header container (line 49) | Header verification |
| `data-testid="streaming-indicator"` | ❌ Missing | Streaming badge (line 61) | Streaming state tests |
| `data-testid="new-session-button"` | ❌ Missing | New session button (line 97) | Session creation tests |
| `data-testid="session-dropdown"` | ❌ Missing | Session dropdown trigger (line 86) | Session switching tests |
| `data-testid="session-item"` | ❌ Missing | Session dropdown items (line 106+) | Session selection tests |
| `data-testid="clear-conversation-button"` | ❌ Missing | Clear button (line ~115) | Clear conversation tests |

**Fix Required**:
```tsx
// Line 49
<div className={cn('border-b bg-background', className)} data-testid="chat-header">

// Line 61 (streaming badge)
<Badge variant="secondary" className="gap-1.5 text-xs" data-testid="streaming-indicator">

// Line 86 (session dropdown)
<DropdownMenuTrigger asChild data-testid="session-dropdown">

// Line 97 (new session button)
<DropdownMenuItem onClick={onNewSession} className="gap-2" data-testid="new-session-button">

// Session items (need to check full file for line numbers)
<DropdownMenuItem onClick={() => onSelectSession?.(session.sessionId)} data-testid="session-item">
```

### ApprovalOverlay.tsx
**Location**: `frontend/src/features/ai/ChatView/ApprovalOverlay/ApprovalOverlay.tsx`

| Test ID | Status | Line | Required For |
|---------|--------|------|--------------|
| `data-testid="approval-overlay"` | ❌ Missing | Overlay container (line 72) | Approval detection |
| `data-testid="approval-title"` | ❌ Missing | Dialog title | Approval content verification |
| `data-testid="approval-action"` | ❌ Missing | Action description | Action details display |
| `data-testid="approval-reasoning"` | ❌ Missing | Reasoning text | Reasoning display |
| `data-testid="approve-button"` | ❌ Missing | Approve button | Approval action tests |
| `data-testid="reject-button"` | ❌ Missing | Reject button | Rejection action tests |

**Fix Required** (need to check ApprovalDialog.tsx):
```tsx
// Line 72 (floating indicator)
<div className={cn('fixed bottom-4 left-4 z-50', className)} data-testid="approval-overlay">

// In ApprovalDialog.tsx
<DialogTitle data-testid="approval-title">Approval Required</DialogTitle>

<Button onClick={approve} data-testid="approve-button">Approve</Button>
<Button onClick={reject} data-testid="reject-button">Reject</Button>
```

### Navigation (App Layout)
**Location**: `frontend/src/app/layout.tsx` or navigation component

| Test ID | Status | Line | Required For |
|---------|--------|------|--------------|
| `data-testid="nav-ai-chat"` | ❌ Missing | AI chat navigation link | Chat navigation |
| `data-testid="nav-issues"` | ❌ Missing | Issues navigation link | Issue navigation |

**Fix Required**:
```tsx
<Link href="/chat" data-testid="nav-ai-chat">AI Chat</Link>
<Link href="/issues" data-testid="nav-issues">Issues</Link>
```

## Priority Task Breakdown

### P4-026: Add data-testid to ChatView Core Components (HIGH PRIORITY)
**Estimate**: 30 minutes

**Files**:
- `ChatView.tsx` - Add root container testid
- `MessageList.tsx` - Add message container testids
- Need to check `MessageGroup.tsx` or create `Message.tsx` component

**Acceptance Criteria**:
- ✅ Chat view container is testable
- ✅ User messages have data-testid="message-user"
- ✅ Assistant messages have data-testid="message-assistant"
- ✅ Tests can detect and verify messages

### P4-027: Add data-testid to ChatInput and Controls (HIGH PRIORITY)
**Estimate**: 20 minutes

**Files**:
- `ChatInput.tsx` - Add input, send button, abort button testids

**Acceptance Criteria**:
- ✅ Chat input textarea is testable
- ✅ Send button is testable
- ✅ Abort button is testable
- ✅ Tests can interact with input controls

### P4-028: Add data-testid to ChatHeader and Session Controls (MEDIUM PRIORITY)
**Estimate**: 30 minutes

**Files**:
- `ChatHeader.tsx` - Add header, streaming indicator, session controls testids

**Acceptance Criteria**:
- ✅ Streaming indicator is testable
- ✅ Session dropdown is testable
- ✅ New session button is testable
- ✅ Session list items are testable
- ✅ Clear conversation button is testable

### P4-029: Add data-testid to ApprovalOverlay Components (MEDIUM PRIORITY)
**Estimate**: 30 minutes

**Files**:
- `ApprovalOverlay.tsx` - Add overlay container testid
- `ApprovalDialog.tsx` - Add dialog content testids

**Acceptance Criteria**:
- ✅ Approval overlay is detectable
- ✅ Approval dialog title is testable
- ✅ Action description is testable
- ✅ Approve/reject buttons are testable
- ✅ Tests can interact with approval workflow

### P4-030: Add data-testid to Navigation Links (LOW PRIORITY)
**Estimate**: 15 minutes

**Files**:
- App layout or navigation component

**Acceptance Criteria**:
- ✅ AI chat link is testable
- ✅ Issues link is testable
- ✅ Tests can navigate between sections

## Testing Best Practices

### Naming Convention
Use descriptive, semantic names:
- Container elements: `{component}-{element}` (e.g., `chat-view`, `approval-overlay`)
- Interactive elements: `{action}-button` (e.g., `send-button`, `approve-button`)
- Content elements: `{role}-{type}` (e.g., `message-user`, `message-assistant`)
- State indicators: `{state}-indicator` (e.g., `streaming-indicator`, `loading-indicator`)

### Dynamic Content
For repeated elements (messages, tasks, sessions):
```tsx
// Good: Unique per instance
<div data-testid={`message-${message.role}`} key={message.id}>

// Better: Even more specific
<div data-testid={`message-${message.role}-${message.id}`} key={message.id}>

// For queries: Use general selector
page.locator('[data-testid^="message-user"]') // All user messages
```

### Avoid Anti-Patterns
❌ Don't use data-testid for styling
❌ Don't duplicate testids
❌ Don't use overly generic names (e.g., `button-1`, `div-container`)
❌ Don't change testids frequently (breaks tests)

✅ Use semantic, stable identifiers
✅ Keep testids separate from implementation
✅ Document testid purpose in code comments

## Verification Checklist

After adding data-testid attributes, verify:

- [ ] All E2E tests can locate elements
- [ ] No duplicate testids in same DOM tree
- [ ] Testids follow naming convention
- [ ] Dynamic content has unique identifiers
- [ ] Tests pass without flakiness
- [ ] Playwright DevTools can find elements

## Running Tests After Implementation

```bash
# Check if elements are found
cd frontend
pnpm test:e2e --debug chat-conversation.spec.ts

# Run all tests
pnpm test:e2e

# Check test report
pnpm exec playwright show-report
```

## Expected Impact

**Before fixes**: 0% test success (all tests fail on element not found)
**After fixes**: 60-80% test success (depending on backend implementation)

Remaining failures will be due to:
- Backend API not fully implemented
- Missing SSE streaming endpoint
- Missing approval request handling
- Session persistence not wired up

Those issues are tracked separately in backend implementation tasks.
