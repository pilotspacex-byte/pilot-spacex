# TipTap Markdown Extension Usage

The TipTap Markdown extension (`tiptap-markdown`) has been integrated into the NoteCanvas editor to provide native bidirectional Markdown ↔ TipTap JSON conversion.

## Features

### 1. Native Markdown Parsing

The editor can now parse markdown strings directly:

```typescript
editor.commands.setContent('# Heading\n\nSome **bold** text.');
```

### 2. Markdown Serialization

Get the current editor content as markdown:

```typescript
const markdownString = editor.storage.markdown.getMarkdown();
```

### 3. Insert Markdown Content

Insert markdown at the current cursor position:

```typescript
editor.commands.insertContent('## Section Title\n\nParagraph text.');
```

### 4. Custom InlineIssue Markdown Syntax

The InlineIssue extension supports custom markdown syntax:

**Syntax:**

```markdown
[PS-99](issue:uuid 'Issue title')
```

**Parsing:**

```typescript
// This markdown:
'Check out [PS-99](issue:123e4567-e89b-12d3-a456-426614174000 "Fix login bug")'

// Becomes this TipTap node:
{
  type: 'inlineIssue',
  attrs: {
    issueId: '123e4567-e89b-12d3-a456-426614174000',
    issueKey: 'PS-99',
    title: 'Fix login bug',
    type: 'task',
    state: 'backlog',
    priority: 'medium'
  }
}
```

**Serialization:**

```typescript
// This TipTap node:
{
  type: 'inlineIssue',
  attrs: {
    issueId: '123e4567-e89b-12d3-a456-426614174000',
    issueKey: 'PS-99',
    title: 'Fix login bug',
    // ...
  }
}

// Becomes this markdown:
'[PS-99](issue:123e4567-e89b-12d3-a456-426614174000 "Fix login bug")'
```

## Backend SSE Integration

The frontend can now parse markdown sent from backend SSE events directly:

```typescript
// Backend sends SSE event with markdown content:
event: text_delta
data: {"delta": "## Suggested Section\n\nHere's some content with [PS-99](issue:uuid \"title\")"}

// Frontend handler:
const handleTextDelta = (delta: string) => {
  // The markdown is automatically parsed when inserted
  editor.commands.insertContent(delta);
};
```

## Configuration

The Markdown extension is configured in `createEditorExtensions.ts`:

```typescript
import { Markdown } from 'tiptap-markdown';

extensions.push(
  Markdown.configure({
    html: true, // Allow HTML in markdown (for block ID comments)
    tightLists: true, // No <p> inside <li>
    breaks: false, // Don't convert \n to <br>
    linkify: false, // Don't auto-create links from URLs
    transformPastedText: false, // Don't transform pasted text
    transformCopiedText: false, // Don't transform copied text
  })
);
```

## Testing

See `__tests__/markdown-integration.test.ts` for comprehensive test coverage of:

- Markdown parsing to TipTap JSON
- TipTap JSON serialization to markdown
- InlineIssue custom syntax parsing
- InlineIssue custom syntax serialization
- `insertContent()` with markdown strings

## Benefits

1. **No Backend Conversion**: The backend can send raw markdown in SSE events without converting to TipTap JSON
2. **Simplified API**: Single `insertContent()` call works for both markdown and JSON
3. **Copy/Paste**: Users can copy markdown from external sources and paste directly
4. **Export**: Easy export to markdown format via `getMarkdown()`
5. **Custom Extensions**: Support for custom markdown syntax (like InlineIssue)

## API Reference

### Commands

- `editor.commands.setContent(markdown)` - Replace all content with markdown
- `editor.commands.insertContent(markdown)` - Insert markdown at cursor
- `editor.commands.insertContentAt(pos, markdown)` - Insert markdown at position

### Storage

- `editor.storage.markdown.getMarkdown()` - Get current content as markdown

### Options

See `tiptap-markdown` [documentation](https://github.com/aguingand/tiptap-markdown) for all available configuration options.
