---
name: create-note-from-chat
description: Creates a structured note from a homepage chat conversation
trigger: intent_detection
---

# Create Note from Chat Skill

Convert a homepage Compact ChatView conversation into a structured note with TipTap content blocks.

## Quick Start

Use this skill when:
- AI detects 2+ substantive exchanges in homepage chat
- User explicitly requests note creation from chat
- Conversation contains actionable insights worth preserving

## Workflow

1. **Detect Note-Worthy Content**
   - At least 2 substantive exchanges (not greetings or simple questions)
   - Conversation contains actionable items, decisions, or analysis
   - User has engaged with AI suggestions or asked follow-up questions

2. **Extract Key Themes**
   - Generate concise title from main conversation topic
   - Identify distinct discussion points for content blocks

3. **Structure as TipTap Blocks**
   - User messages become blockquotes (attributed context)
   - Assistant analysis becomes paragraphs (refined content)
   - System messages are excluded
   - Preserve chronological order

4. **Create Note via API**
   - Call `POST /notes/from-chat` with structured content
   - Link to source chat session via `source_chat_session_id`
   - Optionally associate with a project

## Output Format

```json
{
  "note_id": "uuid",
  "title": "Auth Refactor Strategy",
  "source_chat_session_id": "uuid"
}
```

## Proactive Suggestion

After 2+ exchanges, the AI may suggest:
"Would you like me to save this conversation as a note? I can structure it with the key points we discussed."

## Integration Points

- **CreateNoteFromChatService**: Backend service for note creation
- **PilotSpaceStore**: Frontend manages chat-to-note UI flow
- **NoteCreationSuggestion**: Frontend component for inline suggestion

## References

- Spec: specs/012-homepage-note/spec.md (Chat-to-Note Endpoint)
- US-19: Homepage Hub feature
