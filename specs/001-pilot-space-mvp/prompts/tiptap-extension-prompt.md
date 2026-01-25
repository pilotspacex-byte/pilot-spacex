# TipTap Extension Development Prompt Template

> **Purpose**: Design and implement production-ready TipTap/ProseMirror extensions for rich text editing with AI integration.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` US-01, US-06 TipTap extension specifications
>
> **Usage**: Use when implementing TipTap extensions for note canvas, documentation pages, or AI-enhanced editing features.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Senior Frontend Engineer with 12 years specializing in rich text editors.
You excel at:
- ProseMirror schema design and TipTap extension architecture
- Real-time collaborative editing patterns and conflict resolution
- Performance optimization for editors with 1000+ blocks
- Accessibility-first extension design with keyboard navigation

# Stakes Framing (P6)

This TipTap extension is critical to [PROJECT_NAME]'s core editing experience.
A well-designed extension will:
- Provide seamless AI integration without disrupting writing flow
- Maintain 60fps performance with 1000+ blocks via virtualization
- Enable accessibility-first editing for all users
- Support future extensibility for additional features

I'll tip you $200 for a production-ready extension that passes all quality gates.

# Task Context

## Extension Overview
**Extension Name**: [EXTENSION_NAME]
**Purpose**: [ONE_SENTENCE_PURPOSE]
**Trigger**: [WHAT_ACTIVATES_THIS_EXTENSION]
**UI Manifestation**: [HOW_IT_APPEARS_IN_EDITOR]

## User Story Reference
**Story ID**: US-[XX]
**Acceptance Criteria**: [KEY_CRITERIA_FROM_SPEC]

## UI Design Reference
**Spec Section**: [UI_SPEC_SECTION]
**Visual Specs**: [KEY_VISUAL_REQUIREMENTS]

# Task Decomposition (P3)

Design the TipTap extension step by step:

## Step 1: Extension Classification
Determine the extension type:

| Type | Use Case | Example |
|------|----------|---------|
| **Node** | Block-level content (code block, image, mention) | `CodeBlockExtension` |
| **Mark** | Inline formatting (bold, link, highlight) | `HighlightMark` |
| **Extension** | Behavior without schema (keyboard shortcuts, history) | `GhostTextExtension` |
| **Plugin** | Low-level ProseMirror plugin (decorations, state) | `MarginAnnotationPlugin` |

**Classification Decision**:
- [ ] Node - Creates new block type
- [ ] Mark - Adds inline formatting
- [ ] Extension - Adds behavior (most AI features)
- [ ] Plugin - Low-level decoration/state management

## Step 2: Schema Design (if Node/Mark)
Define the ProseMirror schema:

```typescript
// For Node extensions
const nodeSpec: NodeSpec = {
  group: '[inline|block]',
  content: '[content_expression]',
  atom: [true|false],
  attrs: {
    [attr_name]: { default: [value] },
  },
  parseDOM: [{ tag: '[selector]', getAttrs: (dom) => ({}) }],
  toDOM: (node) => ['[tag]', { ...node.attrs }, 0],
}

// For Mark extensions
const markSpec: MarkSpec = {
  inclusive: [true|false],
  excludes: '[mark_names]',
  attrs: {
    [attr_name]: { default: [value] },
  },
  parseDOM: [{ tag: '[selector]' }],
  toDOM: (mark) => ['[tag]', { ...mark.attrs }],
}
```

## Step 3: Extension Configuration
Define TipTap extension structure:

```typescript
import { Extension } from '@tiptap/core'

export interface [ExtensionName]Options {
  [option_name]: [type]
}

export const [ExtensionName] = Extension.create<[ExtensionName]Options>({
  name: '[extension-name]',

  addOptions() {
    return {
      [option_name]: [default_value],
    }
  },

  addCommands() {
    return {
      [commandName]: (args) => ({ commands }) => {
        // Command implementation
      },
    }
  },

  addKeyboardShortcuts() {
    return {
      '[shortcut]': () => this.editor.commands.[command](),
    }
  },

  addInputRules() {
    return [
      // Input rules for auto-formatting
    ]
  },

  addProseMirrorPlugins() {
    return [
      // Low-level plugins
    ]
  },
})
```

## Step 4: Decoration Strategy (if visual overlay)
For extensions with visual elements that don't modify document:

```typescript
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

const pluginKey = new PluginKey('[plugin-name]')

const decorationPlugin = new Plugin({
  key: pluginKey,

  state: {
    init: () => DecorationSet.empty,
    apply: (tr, decorationSet) => {
      // Update decorations based on transaction
      const decorations: Decoration[] = []

      // Widget decoration (inline element)
      decorations.push(
        Decoration.widget(pos, (view) => {
          const el = document.createElement('[tag]')
          // Configure element
          return el
        })
      )

      // Node decoration (wrap existing node)
      decorations.push(
        Decoration.node(from, to, { class: '[class]' })
      )

      return DecorationSet.create(tr.doc, decorations)
    },
  },

  props: {
    decorations: (state) => pluginKey.getState(state),
  },
})
```

## Step 5: Event Handling
Define user interaction handlers:

```typescript
addProseMirrorPlugins() {
  return [
    new Plugin({
      props: {
        handleKeyDown: (view, event) => {
          // Handle key events
          if (event.key === 'Tab' && this.isGhostTextVisible()) {
            this.acceptGhostText()
            return true // Handled
          }
          return false // Pass to next handler
        },

        handleDOMEvents: {
          blur: (view, event) => {
            // Handle blur
            return false
          },
        },
      },
    }),
  ]
}
```

**Key Priority Rules** (per plan.md decision #9):
1. Code block context → indent
2. Ghost text visible → accept
3. Default → next field

## Step 6: AI Integration (if applicable)
Define AI connection patterns:

**Trigger Mechanism**:
| Trigger | Timing | Debounce |
|---------|--------|----------|
| [TRIGGER_TYPE] | [WHEN] | [MS] |

**SSE Connection**:
```typescript
class AIIntegrationHandler {
  private abortController: AbortController | null = null

  async requestSuggestion(context: EditorContext) {
    // Cancel previous request
    this.abortController?.abort()
    this.abortController = new AbortController()

    const response = await fetch('/api/v1/ai/[endpoint]', {
      method: 'POST',
      body: JSON.stringify(context),
      signal: this.abortController.signal,
    })

    // Handle SSE stream
    const reader = response.body?.getReader()
    // ... process stream
  }

  cleanup() {
    this.abortController?.abort()
  }
}
```

**Context Window**:
| Component | Tokens | Priority |
|-----------|--------|----------|
| [CONTEXT_1] | ~[N] | P[X] |
| [CONTEXT_2] | ~[N] | P[X] |

## Step 7: Accessibility Requirements
Define a11y compliance:

**Keyboard Navigation**:
| Shortcut | Action |
|----------|--------|
| [KEY] | [ACTION] |

**ARIA Requirements**:
```typescript
// ARIA live region for AI suggestions
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
>
  {aiSuggestion}
</div>

// Screen reader announcement
function announceToScreenReader(message: string) {
  const announcement = document.createElement('div')
  announcement.setAttribute('aria-live', 'polite')
  announcement.textContent = message
  document.body.appendChild(announcement)
  setTimeout(() => announcement.remove(), 1000)
}
```

**Motion Preferences**:
```css
.ghost-text {
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 150ms, transform 150ms;
}

.ghost-text.visible {
  opacity: 0.4;
  transform: translateX(0);
}

@media (prefers-reduced-motion: reduce) {
  .ghost-text {
    transition: none;
  }
}
```

## Step 8: Testing Requirements

**Unit Tests**:
```typescript
describe('[ExtensionName]', () => {
  it('should [expected_behavior]', () => {
    const editor = new Editor({
      extensions: [[ExtensionName]],
      content: '<p>Test content</p>',
    })

    // Test implementation
    expect(editor.getHTML()).toContain('[expected]')
  })
})
```

**Integration Tests**:
- [ ] Extension loads without errors
- [ ] Commands execute correctly
- [ ] Keyboard shortcuts work
- [ ] AI integration handles errors gracefully

**Accessibility Tests**:
- [ ] Keyboard-only navigation works
- [ ] Screen reader announces changes
- [ ] Focus management is correct
- [ ] Motion preferences respected

# Chain-of-Thought Guidance (P12)

For each section, evaluate:
1. **What's the interaction model?** - Keyboard, mouse, touch, voice?
2. **What's the performance impact?** - Re-renders, DOM operations, network?
3. **What could go wrong?** - Cursor position, selection, concurrent edits?
4. **How does it affect a11y?** - Focus, announcements, keyboard nav?

# Self-Evaluation Framework (P15)

After designing, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Schema Design**: Correct ProseMirror patterns | ___ | |
| **Performance**: No unnecessary re-renders | ___ | |
| **Accessibility**: WCAG 2.2 AA compliant | ___ | |
| **AI Integration**: Proper cancellation/cleanup | ___ | |
| **Key Handling**: Correct priority ordering | ___ | |
| **Testing**: Comprehensive coverage | ___ | |

**Refinement Threshold**: If any score < 0.9, identify gap and refine.

# Output Format

```markdown
## TipTap Extension: [EXTENSION_NAME]

### Overview
| Attribute | Value |
|-----------|-------|
| **Type** | Node / Mark / Extension / Plugin |
| **Purpose** | [ONE_LINER] |
| **Trigger** | [EVENT/ACTION] |
| **UI Spec Section** | [REFERENCE] |

### Schema (if applicable)
\`\`\`typescript
// Schema definition
\`\`\`

### Extension Implementation
\`\`\`typescript
// Full extension code
\`\`\`

### Keyboard Shortcuts
| Shortcut | Action | Priority |
|----------|--------|----------|
| [KEY] | [ACTION] | [N] |

### AI Integration (if applicable)
| Aspect | Detail |
|--------|--------|
| **Trigger** | [WHEN] |
| **Debounce** | [MS] |
| **Context** | [WHAT_SENT] |
| **Cancellation** | AbortController |

### Accessibility
| Requirement | Implementation |
|-------------|----------------|
| Keyboard nav | [DETAILS] |
| Screen reader | [ARIA_PATTERN] |
| Motion | [CSS_HANDLING] |

### Test Matrix
- Unit: [COUNT] tests
- Integration: [COUNT] tests
- a11y: [COUNT] tests

---
*Extension Version: 1.0*
*Story Reference: US-[XX]*
```
```

---

## Quick-Fill Variants

### Variant A: Ghost Text Extension (US-01)

```markdown
**Extension Name**: GhostTextExtension
**Purpose**: Display inline AI writing suggestions during typing pause
**Trigger**: 500ms pause in typing
**UI Manifestation**: Semi-transparent italic text after cursor

**Type**: Extension (with ProseMirror plugin for decorations)

**Key Specifications** (ui-design-spec.md Section 8.2):
- 40% opacity, italic style
- 150ms fade-in animation
- Tab to accept full suggestion
- Right Arrow to accept word-by-word
- Escape to dismiss
- Max length: ~50 tokens

**Context Window**:
- Current block: ~100 tokens
- 3 previous blocks: ~300 tokens
- Section summary: ~100 tokens

**Keyboard Priority**:
1. Code block → Tab inserts indent
2. Ghost text visible → Tab accepts
3. Default → Tab moves focus
```

### Variant B: Margin Annotation Extension (US-01)

```markdown
**Extension Name**: MarginAnnotationExtension
**Purpose**: Display AI suggestions in right margin alongside blocks
**Trigger**: AI analysis of block content
**UI Manifestation**: Floating panel in right margin

**Type**: Plugin (decoration-based positioning)

**Key Specifications** (ui-design-spec.md Section 7.3):
- 200px default width, resizable 150-350px
- AI muted background color
- 3px left border indicator
- Vertical stack with scroll overflow

**Positioning**: CSS Anchor Positioning API (Chrome 125+)
- Fallback: position: absolute with calculated offsets

**ARIA Pattern**:
- role="complementary" for margin region
- aria-labelledby linking to block
- aria-live="polite" for new annotations
```

### Variant C: Issue Extraction Extension (US-01)

```markdown
**Extension Name**: IssueExtractionExtension
**Purpose**: Detect and highlight potential issues in note content
**Trigger**: Content analysis on save/focus-loss
**UI Manifestation**: Rainbow-bordered box around detected issues

**Type**: Extension (with Mark for highlighting)

**Key Specifications** (ui-design-spec.md Section 7.4):
- 2px rainbow gradient border (hue-rotate animation)
- Hover: scale 2%, elevated shadow
- Click: opens issue creation modal
- State: Strikethrough + "Deleted" badge for removed issues

**Detection Patterns**:
- Action verbs: "implement", "fix", "add", "update", "remove"
- Entity references: quoted strings, code blocks
- Task indicators: TODO, FIXME, HACK

**ARIA Pattern**:
- role="button" for clickable issue boxes
- aria-describedby for issue preview
```

---

## Validation Checklist

Before implementing extension:

- [ ] Extension type correctly identified (Node/Mark/Extension/Plugin)
- [ ] Schema follows ProseMirror conventions
- [ ] Keyboard shortcuts don't conflict with existing shortcuts
- [ ] AI integration uses AbortController for cancellation
- [ ] Decorations are efficiently updated (no full re-render)
- [ ] Accessibility requirements documented and testable
- [ ] Performance impact assessed for 1000+ blocks
- [ ] Motion preferences respected

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `specs/001-pilot-space-mvp/ui-design-spec.md` | Visual specifications |
| `specs/001-pilot-space-mvp/plan.md` | Implementation decisions |
| `docs/architect/frontend-architecture.md` | Frontend patterns |
| [TipTap Documentation](https://tiptap.dev/docs) | Official TipTap docs |
| [ProseMirror Guide](https://prosemirror.net/docs/guide/) | ProseMirror fundamentals |

---

*Template Version: 1.0*
*Extracted from: plan.md v7.2 US-01, US-06 specifications*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*
