# Phase 40: WebGPU Note Canvas + IDE File Editor - Research

**Researched:** 2026-03-23
**Domain:** Monaco Editor migration, IDE file editing, markdown preview, spring physics scrolling
**Confidence:** HIGH

## Summary

This phase migrates the note editor from TipTap/ProseMirror (DOM-based) to Monaco Editor (Canvas-based rendering) and adds IDE-like file editing capabilities. Monaco Editor is the same engine powering VS Code, providing GPU-accelerated Canvas rendering, native inline completions (ghost text), CompletionItemProvider (slash commands), and view zones/widgets for embedding custom React renderers (PM blocks).

The project currently uses React 19.2.3 + Next.js 16.1.4. The `@monaco-editor/react` v4.7.0 is the stable React wrapper with React 19 peer dependency support. Yjs collaboration rebinds from `y-prosemirror` to `y-monaco` v0.1.6 (compatible with existing yjs 13.6.29). The existing `SupabaseYjsProvider` transport layer is reused unchanged.

**Primary recommendation:** Use `@monaco-editor/react` 4.7.0 as the React wrapper, load Monaco via `next/dynamic` with `ssr: false`, map all 10 PM block types to Monaco view zones with React portals, use Monaco's native `InlineCompletionsProvider` for ghost text and `CompletionItemProvider` with `/` and `@` trigger characters for slash commands and mentions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Monaco Editor is the base rendering layer, replacing TipTap/ProseMirror's DOM rendering
- TipTap's block-based features render INSIDE Monaco's canvas viewport as Monaco widgets/view zones
- Document model: Monaco text model is source of truth. Notes stored as markdown text. PM blocks stored as special markdown markers (e.g., ```pm:decision ... ```) that Monaco detects and renders as view zone widgets
- Yjs collaboration connects through Monaco's text model using y-monaco binding (not y-prosemirror)
- Slash commands (/) and mentions (@) use Monaco's native CompletionItemProvider suggest widget
- Ghost text AI uses Monaco's native inline completions API
- All 10 PM block types (RACI, decision, risk, dependency, etc.) become Monaco view zone widgets with their existing React renderers
- Rich formatting (bold, italic, headings, lists) applied via Monaco decorations on the markdown text
- Four file sources: (1) artifact files via S3 signed URLs, (2) local repo files via tauri-plugin-fs, (3) note content as markdown files, (4) remote repo files via GitHub/GitLab API
- Remote repo files are read-only browsing
- File navigation: VS Code-style file tree sidebar + Cmd+P fuzzy quick open
- Tab system for open files -- multiple files open simultaneously
- Auto-save with 2s debounce for all file types
- GPU acceleration via Monaco's Canvas rendering
- Spring physics scrolling in editor viewport, file tree, and note list sidebar
- Crossfade transitions (200-300ms) for mode switches, panel open/close, file tree expand/collapse
- Toggle mode for markdown preview (edit vs preview, not side-by-side)
- Full extended markdown: GFM + Mermaid + KaTeX + footnotes + definition lists + custom containers
- Web-first, Tauri bonus for local repo browsing
- No collaboration on file editing -- single-user only

### Claude's Discretion
- Markdown preview engine choice (react-markdown stack vs Monaco-native vs other)
- Spring physics scroll implementation (custom vs library)
- PM block markdown marker format (exact syntax for encoding blocks in text)
- Monaco theme and color scheme (should match Pilot Space design system)
- File tree component implementation (custom vs existing library)
- Tab management UX details (max tabs, tab overflow, close behavior)

### Deferred Ideas (OUT OF SCOPE)
- Collaborative file editing (Yjs on code files)
- Remote repo file editing + commit via API
- Split-pane markdown preview (side-by-side)
- LSP/IntelliSense/autocomplete for code files
- Git blame/annotate in the editor
- Multiple terminal tabs/splits (DESK-03)
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `monaco-editor` | 0.55.1 | Code editor engine (Canvas-based) | Powers VS Code; GPU-accelerated Canvas rendering, built-in tokenization for 70+ languages |
| `@monaco-editor/react` | 4.7.0 | React wrapper for Monaco | Stable React 19 support (peer dep ^19.0.0); handles lifecycle, loader, theming |
| `y-monaco` | 0.1.6 | Yjs <-> Monaco binding | Official Yjs binding; maps Y.Text to Monaco model, renders remote cursors via Awareness |
| `lenis` | 1.3.20 | Spring physics smooth scrolling | Industry standard for smooth scroll; built-in React bindings via `lenis/react`; lerp-based momentum |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `react-markdown` | 10.1.0 (existing) | Markdown preview rendering | Toggle preview mode for notes and markdown files |
| `remark-gfm` | 4.0.1 (existing) | GFM tables, strikethrough, autolinks | Always on for markdown preview |
| `remark-math` | 6.0.0 | Math syntax parsing ($inline$, $$block$$) | Markdown preview with math equations |
| `rehype-katex` | 7.0.1 | KaTeX math rendering | Renders parsed math in preview mode |
| `katex` | 0.16.40 | Math typesetting engine | Required by rehype-katex |
| `remark-directive` | 4.0.0 | Custom container/admonition syntax | ::: containers in markdown preview |
| `rehype-raw` | 7.0.0 | Pass raw HTML through rehype | Required for some remark plugin outputs |
| `mermaid` | 11.12.2 (existing) | Diagram rendering | Reuse existing MermaidPreview component |
| `dompurify` | 3.3.1 (existing) | HTML sanitization | Sanitize rendered markdown preview output |
| `yjs` | 13.6.29 (existing) | CRDT framework | Keep existing; y-monaco peer dep ^13.3.1 compatible |
| `y-indexeddb` | 9.0.12 (existing) | Local Yjs persistence | Keep existing; offline support |
| `react-virtuoso` | 4.18.1 (existing) | Virtualized lists | File tree virtualization for large directories |
| `lowlight` | 3.2.0 (existing) | Syntax highlighting | Preview mode code block highlighting (Monaco handles edit mode natively) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `lenis` | Custom spring physics | Lenis is battle-tested, 8KB gzipped, handles edge cases (touch, trackpad, keyboard scroll) |
| `react-markdown` for preview | Monaco's built-in markdown preview | Monaco has no built-in rich preview; react-markdown is already in the project and extensible |
| Custom file tree | `react-arborist` | react-virtuoso already in project; custom tree with virtuoso avoids new dep and matches design system |
| `monacopilot` for AI completions | Custom InlineCompletionsProvider | monacopilot couples to Codestral/external API; Pilot Space has BYOK AI backend; custom provider is simpler |

**Installation:**
```bash
cd frontend && pnpm add monaco-editor @monaco-editor/react y-monaco lenis remark-math rehype-katex katex remark-directive rehype-raw
```

**Version verification:** All versions verified via `npm view` on 2026-03-23.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── features/
│   ├── editor/                    # New Monaco-based editor
│   │   ├── MonacoNoteEditor.tsx   # Main note editor component (replaces NoteCanvasEditor)
│   │   ├── MonacoFileEditor.tsx   # File editing component (code, artifacts)
│   │   ├── hooks/
│   │   │   ├── useMonacoNote.ts   # Note-specific Monaco setup (decorations, view zones)
│   │   │   ├── useMonacoGhostText.ts  # InlineCompletionsProvider registration
│   │   │   ├── useMonacoSlashCmd.ts   # CompletionItemProvider for / and @
│   │   │   ├── useMonacoCollab.ts     # y-monaco binding + SupabaseYjsProvider
│   │   │   ├── useMonacoTheme.ts      # Pilot Space theme definition
│   │   │   └── useMonacoViewZones.ts  # PM block view zone management
│   │   ├── view-zones/
│   │   │   ├── PMBlockViewZone.tsx    # Generic view zone host (React portal)
│   │   │   └── ViewZoneManager.ts     # Tracks view zones, handles add/remove/resize
│   │   ├── decorations/
│   │   │   ├── markdownDecorations.ts # Bold, italic, heading, list decorations
│   │   │   └── entityHighlight.ts     # Entity highlighting (migrated)
│   │   ├── markers/
│   │   │   └── pmBlockMarkers.ts      # Detect/parse PM block markdown markers
│   │   └── themes/
│   │       └── pilotSpaceTheme.ts     # Monaco theme matching design system
│   ├── file-browser/              # IDE file navigation
│   │   ├── components/
│   │   │   ├── FileTree.tsx       # VS Code-style tree sidebar
│   │   │   ├── FileTreeNode.tsx   # Individual tree node
│   │   │   ├── QuickOpen.tsx      # Cmd+P fuzzy finder dialog
│   │   │   └── TabBar.tsx         # Open file tabs
│   │   ├── hooks/
│   │   │   ├── useFileTree.ts     # Tree state (expand/collapse, selection)
│   │   │   └── useQuickOpen.ts    # Fuzzy search logic
│   │   └── stores/
│   │       └── FileStore.ts       # MobX store: open tabs, active file, dirty state
│   ├── markdown-preview/          # Toggle preview mode
│   │   ├── MarkdownPreview.tsx    # Full-featured preview renderer
│   │   └── plugins/
│   │       ├── remarkAdmonition.ts   # Custom container plugin
│   │       └── rehypeMermaid.ts      # Mermaid diagram rendering
│   └── notes/
│       ├── editor/extensions/pm-blocks/renderers/  # KEEP: existing 10 renderers
│       └── collab/SupabaseYjsProvider.ts           # KEEP: unchanged transport
├── stores/
│   └── FileStore.ts               # Or register in RootStore
└── components/
    └── editor/
        └── NoteCanvasEditor.tsx    # DEPRECATED (keep for rollback during migration)
```

### Pattern 1: Monaco View Zone with React Portal
**What:** Render React components (PM block renderers) inside Monaco's canvas viewport using view zones + `createPortal`
**When to use:** Every PM block (RACI, decision, risk, dependency, etc.)
**Example:**
```typescript
// Source: Monaco Editor API docs + React Portal pattern
import { createPortal } from 'react-dom';

interface ViewZoneEntry {
  zoneId: string;
  domNode: HTMLDivElement;
  afterLineNumber: number;
}

function useMonacoViewZones(
  editor: monaco.editor.IStandaloneCodeEditor | null,
  blocks: PMBlockMarker[]
) {
  const [zones, setZones] = useState<ViewZoneEntry[]>([]);

  useEffect(() => {
    if (!editor) return;

    editor.changeViewZones((accessor) => {
      // Remove old zones
      zones.forEach(z => accessor.removeZone(z.zoneId));

      // Add new zones
      const newZones = blocks.map(block => {
        const domNode = document.createElement('div');
        domNode.style.width = '100%';

        const zoneId = accessor.addZone({
          afterLineNumber: block.endLine,
          heightInPx: 200, // initial; ResizeObserver updates
          domNode,
          suppressMouseDown: false,
        });

        return { zoneId, domNode, afterLineNumber: block.endLine };
      });

      setZones(newZones);
    });
  }, [editor, blocks]);

  // Render React components into view zone DOM nodes via portals
  return zones.map((zone, i) =>
    createPortal(
      <PMBlockRenderer type={blocks[i].type} data={blocks[i].data} />,
      zone.domNode
    )
  );
}
```

### Pattern 2: Monaco InlineCompletionsProvider for Ghost Text
**What:** Register a custom inline completions provider that calls Pilot Space AI backend
**When to use:** Ghost text AI suggestions in note editing
**Example:**
```typescript
// Source: Monaco Editor API - InlineCompletionsProvider
import type * as monaco from 'monaco-editor';

function registerGhostTextProvider(
  monacoInstance: typeof monaco,
  fetchCompletion: (context: GhostTextContext) => Promise<string>
) {
  return monacoInstance.languages.registerInlineCompletionsProvider('markdown', {
    provideInlineCompletions: async (model, position, context, token) => {
      const textBeforeCursor = model.getValueInRange({
        startLineNumber: 1,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      });

      const suggestion = await fetchCompletion({
        textBeforeCursor,
        textAfterCursor: model.getValueInRange({
          startLineNumber: position.lineNumber,
          startColumn: position.column,
          endLineNumber: model.getLineCount(),
          endColumn: model.getLineMaxColumn(model.getLineCount()),
        }),
        cursorPosition: model.getOffsetAt(position),
        blockId: '',
      });

      if (token.isCancellationRequested || !suggestion) {
        return { items: [] };
      }

      return {
        items: [{
          insertText: suggestion,
          range: new monacoInstance.Range(
            position.lineNumber, position.column,
            position.lineNumber, position.column
          ),
        }],
      };
    },
    freeInlineCompletions: () => {},
  });
}
```

### Pattern 3: Monaco Dynamic Import in Next.js
**What:** Lazy-load Monaco (~3MB) to avoid blocking initial page load
**When to use:** All Monaco editor components
**Example:**
```typescript
// Source: Next.js dynamic import + @monaco-editor/react docs
'use client';

import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';

const MonacoNoteEditor = dynamic(
  () => import('@/features/editor/MonacoNoteEditor'),
  {
    ssr: false,
    loading: () => <Skeleton className="h-full w-full" />,
  }
);

export default function NoteEditorWrapper(props: NoteEditorProps) {
  return <MonacoNoteEditor {...props} />;
}
```

### Pattern 4: PM Block Markdown Markers
**What:** Encode PM blocks as fenced code blocks with `pm:` prefix in markdown text
**When to use:** Storing PM block data in Monaco's text model
**Recommended format:**
```
  ```pm:decision
  {
    "id": "dec-001",
    "title": "Use Monaco for editor",
    "status": "approved",
    "owner": "user-123"
  }
  ```
```
**Why this format:**
- Standard markdown fenced code block syntax -- renders gracefully in any markdown viewer
- `pm:` prefix namespace avoids collision with regular code blocks
- JSON body is human-readable and parseable
- Monaco's built-in tokenizer detects fenced code blocks; custom monarch rules can highlight `pm:*` blocks
- View zone replaces the entire fenced block range with the rich React renderer

### Pattern 5: File Store (MobX)
**What:** MobX store managing open files, tabs, and dirty state
**When to use:** File browser feature
**Example:**
```typescript
// Source: Project pattern from RootStore + MobX conventions
import { makeAutoObservable, computed } from 'mobx';

interface OpenFile {
  id: string;
  name: string;
  path: string;
  source: 'artifact' | 'local' | 'note' | 'remote';
  language: string;
  content: string;
  isDirty: boolean;
}

class FileStore {
  openFiles: Map<string, OpenFile> = new Map();
  activeFileId: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  get activeFile(): OpenFile | undefined {
    return this.activeFileId ? this.openFiles.get(this.activeFileId) : undefined;
  }

  get tabs(): OpenFile[] {
    return Array.from(this.openFiles.values());
  }

  openFile(file: Omit<OpenFile, 'isDirty'>) {
    if (!this.openFiles.has(file.id)) {
      this.openFiles.set(file.id, { ...file, isDirty: false });
    }
    this.activeFileId = file.id;
  }

  closeFile(id: string) {
    this.openFiles.delete(id);
    if (this.activeFileId === id) {
      const remaining = Array.from(this.openFiles.keys());
      this.activeFileId = remaining[remaining.length - 1] ?? null;
    }
  }
}
```

### Anti-Patterns to Avoid
- **Wrapping view zone React renderers in `observer()`**: Same React 19 `flushSync` issue as TipTap NodeView renderers -- use plain components + context bridge pattern (documented in project memory)
- **Importing monaco-editor at module level**: Causes SSR crash in Next.js. Always use dynamic import or `@monaco-editor/react`'s built-in loader
- **Creating new Monaco models on every render**: Monaco models are heavyweight; create once, update content. Store model references in FileStore
- **Mixing TipTap and Monaco in the same view**: Clean migration -- replace entire editor, don't try to embed one inside the other

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inline AI completions (ghost text) | Custom decoration + widget overlay | Monaco `InlineCompletionsProvider` | Native ghost text rendering, Tab/Escape/Arrow handling built in |
| Autocomplete menu (slash, mentions) | Custom popup + keyboard handling | Monaco `CompletionItemProvider` | Native suggest widget with fuzzy matching, keyboard nav, documentation panel |
| Syntax highlighting in editor | Custom tokenizer | Monaco's built-in TextMate/Monarch grammars | 70+ languages out of the box |
| Smooth scroll physics | Custom `requestAnimationFrame` loop | `lenis` 1.3.20 | Handles touch, trackpad, keyboard, accessibility; 8KB gzipped |
| Markdown rendering pipeline | Custom markdown parser | `react-markdown` + remark/rehype plugins | Already in project; extensible plugin ecosystem |
| Math typesetting | Custom math renderer | `rehype-katex` + `katex` | Industry standard; server-side rendering possible |
| CRDT collaboration | Custom OT/CRDT | `yjs` + `y-monaco` | Already using yjs; y-monaco is official binding |
| Diff viewer | Custom diff renderer | Monaco `DiffEditor` component | Built-in side-by-side and inline diff with syntax highlighting |

**Key insight:** Monaco provides nearly all the low-level editor features needed (ghost text, autocomplete, decorations, view zones, themes, diff). The main custom work is the PM block view zone integration and the file browser UI.

## Common Pitfalls

### Pitfall 1: Monaco SSR Crash in Next.js
**What goes wrong:** Importing `monaco-editor` at the top level crashes server-side rendering because Monaco accesses `window` and `document`.
**Why it happens:** Monaco is browser-only; Next.js App Router pre-renders on server.
**How to avoid:** Always use `next/dynamic` with `ssr: false`. The `@monaco-editor/react` loader handles Monaco initialization, but the component itself must not be server-rendered. Place the dynamic import in a `'use client'` file.
**Warning signs:** `ReferenceError: window is not defined` during build or SSR.

### Pitfall 2: Monaco Bundle Size (~3MB)
**What goes wrong:** Monaco adds ~3MB to the JavaScript bundle, causing slow initial loads.
**Why it happens:** Monaco includes language grammars, themes, and the full editor engine.
**How to avoid:** (1) Dynamic import with loading skeleton. (2) Use `@monaco-editor/react`'s CDN loader (default) or configure webpack/turbopack to tree-shake unused languages. (3) Only register languages actually needed (markdown, json, typescript, python, etc.).
**Warning signs:** First Load JS jumps dramatically in `next build` output.

### Pitfall 3: View Zone Height Synchronization
**What goes wrong:** PM block React components inside view zones have dynamic height (user expands/collapses sections), but Monaco allocates a fixed `heightInPx` for each view zone.
**Why it happens:** Monaco's view zone API requires explicit height; it doesn't auto-size from DOM content.
**How to avoid:** Use `ResizeObserver` on each view zone's `domNode`. When observed height changes, call `editor.changeViewZones()` to update the zone's `heightInPx`. Debounce updates to avoid layout thrashing.
**Warning signs:** View zones clip content or leave gaps below rendered components.

### Pitfall 4: React Portal Cleanup in View Zones
**What goes wrong:** Memory leaks and stale React trees when view zones are removed.
**Why it happens:** `createPortal` renders into a DOM node, but Monaco's `changeViewZones` removes the DOM node directly. React doesn't get a chance to unmount.
**How to avoid:** Track all portal roots. When a view zone is removed, call `root.unmount()` (for `createRoot` portals) or remove from portal state before Monaco removes the DOM node. Use an effect cleanup that removes zones first, then unmounts React.
**Warning signs:** Console warnings about unmounted components; increasing memory usage over time.

### Pitfall 5: y-monaco Awareness Cursor Colors
**What goes wrong:** Remote cursor colors are random or clash with the UI theme.
**Why it happens:** y-monaco uses awareness `user.color` field for cursor styling but doesn't enforce a palette.
**How to avoid:** Set awareness `user.color` from a predefined palette when joining the session. Store color in workspace member profile for consistency.
**Warning signs:** Ugly or invisible cursor colors against the editor background.

### Pitfall 6: Monaco Model Disposal
**What goes wrong:** "Model already disposed" errors when switching tabs or navigating.
**Why it happens:** Monaco models are disposable resources. If a model is disposed while still bound to an editor or y-monaco, operations throw.
**How to avoid:** Manage model lifecycle in FileStore. Only dispose when closing a tab. When switching tabs, detach the old model (`editor.setModel(newModel)`) before touching the old one. Never dispose a model that has an active y-monaco binding.
**Warning signs:** Errors referencing disposed models; editor goes blank on tab switch.

### Pitfall 7: observer() in View Zone Renderers (React 19 flushSync)
**What goes wrong:** Wrapping PM block view zone renderers in MobX `observer()` causes nested `flushSync` errors in React 19.
**Why it happens:** Same root cause as TipTap NodeView -- MobX `useSyncExternalStore` + React's synchronous rendering in portals triggers nested sync updates.
**How to avoid:** Use plain React components for view zone renderers. Pass data via React context (same pattern as `IssueNoteContext` documented in project memory). Only wrap outer container components in `observer()`.
**Warning signs:** "flushSync was called from inside a lifecycle method" console errors.

### Pitfall 8: Lenis + Monaco Scroll Conflict
**What goes wrong:** Lenis intercepts scroll events that Monaco's internal scroll handling needs.
**Why it happens:** Lenis wraps the scroll container; Monaco has its own virtual scroll for the editor viewport.
**How to avoid:** Exclude Monaco editor DOM elements from Lenis using the `[data-lenis-prevent]` attribute. Apply Lenis only to the outer containers (file tree, note list sidebar), not the editor viewport itself. Monaco handles its own scroll.
**Warning signs:** Editor scrolling feels laggy, jumpy, or doesn't respond to scroll events.

## Code Examples

### Monaco Editor with Custom Theme
```typescript
// Source: Monaco Editor API + Pilot Space design system
import type * as monaco from 'monaco-editor';

export function defineTheme(monacoInstance: typeof monaco) {
  monacoInstance.editor.defineTheme('pilot-space', {
    base: 'vs', // light theme base
    inherit: true,
    rules: [
      { token: 'heading', fontStyle: 'bold', foreground: '1a1a2e' },
      { token: 'emphasis', fontStyle: 'italic' },
      { token: 'strong', fontStyle: 'bold' },
      { token: 'keyword', foreground: '6366f1' }, // indigo-500
      { token: 'string', foreground: '059669' },   // emerald-600
      { token: 'comment', foreground: '9ca3af', fontStyle: 'italic' },
    ],
    colors: {
      'editor.background': '#FAFAFA',
      'editor.foreground': '#1a1a2e',
      'editor.lineHighlightBackground': '#F3F4F6',
      'editor.selectionBackground': '#C7D2FE',
      'editorCursor.foreground': '#6366F1',
      'editorGhostText.foreground': '#9CA3AF',
    },
  });
}
```

### y-monaco Collaboration Binding
```typescript
// Source: y-monaco docs + SupabaseYjsProvider pattern
import * as Y from 'yjs';
import { MonacoBinding } from 'y-monaco';
import type { editor as MonacoEditor } from 'monaco-editor';
import type { Awareness } from 'y-protocols/awareness';
import { SupabaseYjsProvider } from '@/features/notes/collab/SupabaseYjsProvider';

export function setupCollaboration(
  editor: MonacoEditor.IStandaloneCodeEditor,
  model: MonacoEditor.ITextModel,
  ydoc: Y.Doc,
  awareness: Awareness,
) {
  const ytext = ydoc.getText('monaco'); // Y.Text shared type

  const binding = new MonacoBinding(
    ytext,
    model,
    new Set([editor]),
    awareness,
  );

  return {
    binding,
    destroy: () => binding.destroy(),
  };
}
```

### Markdown Preview with Full Plugin Stack
```typescript
// Source: react-markdown + remark/rehype plugin docs
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkDirective from 'remark-directive';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeHighlight from 'rehype-highlight';
import DOMPurify from 'dompurify';
import { MermaidPreview } from '@/features/notes/editor/extensions/pm-blocks/MermaidPreview';
import 'katex/dist/katex.min.css';

const components = {
  code({ className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '');
    if (match?.[1] === 'mermaid') {
      return <MermaidPreview chart={String(children)} />;
    }
    return <code className={className} {...props}>{children}</code>;
  },
};

export function MarkdownPreview({ content }: { content: string }) {
  const sanitized = DOMPurify.sanitize(content);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath, remarkDirective]}
      rehypePlugins={[rehypeRaw, rehypeKatex, rehypeHighlight]}
      components={components}
    >
      {sanitized}
    </ReactMarkdown>
  );
}
```

### Lenis Smooth Scroll (Excluding Monaco)
```typescript
// Source: lenis docs + React integration
'use client';

import { ReactLenis } from 'lenis/react';

export function SmoothScrollProvider({ children }: { children: React.ReactNode }) {
  return (
    <ReactLenis
      root
      options={{
        lerp: 0.1,         // Smooth interpolation
        duration: 1.2,     // Scroll duration
        smoothWheel: true,
        touchMultiplier: 2,
      }}
    >
      {children}
    </ReactLenis>
  );
}

// In MonacoNoteEditor -- prevent Lenis from intercepting:
// <div data-lenis-prevent className="editor-container">
//   <Editor ... />
// </div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TipTap/ProseMirror DOM rendering | Monaco Canvas rendering | This migration | 60fps scroll, no DOM layout jank for large documents |
| y-prosemirror for collab | y-monaco for collab | This migration | Simpler binding, Monaco-native cursor rendering |
| Custom ghost text ProseMirror plugin | Monaco InlineCompletionsProvider | This migration | Native ghost text UX (Tab accept, word-by-word, dismiss) |
| Custom slash command ProseMirror plugin | Monaco CompletionItemProvider | This migration | Native suggest widget with fuzzy matching |
| DOM-based scrolling | Lenis spring physics (non-editor areas) | This migration | Polished, native-app feel with momentum scrolling |
| `@monaco-editor/react` 4.6.x | 4.7.0 | 2025 | React 19 peer dependency support |

**Deprecated/outdated:**
- `react-monaco-editor` (separate package): Less maintained than `@monaco-editor/react`; lacks loader management
- `@studio-freight/react-lenis` (0.0.47): Deprecated; lenis now exports React bindings natively via `lenis/react`

## Discretion Recommendations

### Markdown Preview Engine: react-markdown stack
**Recommendation:** Use the existing `react-markdown` 10.1.0 + remark/rehype plugin chain.
**Rationale:** Already in the project. Extensible via plugins (remark-math, remark-directive, rehype-katex). Renders to React components (easy to style with design system). Mermaid integration via existing `MermaidPreview` component.
**Confidence:** HIGH

### Spring Physics Scrolling: Lenis
**Recommendation:** Use `lenis` 1.3.20 with `lenis/react` export.
**Rationale:** Industry standard (used by top agencies/studios). 8KB gzipped. Handles all input types (wheel, touch, keyboard). React bindings built-in. Apply to outer containers only; exclude Monaco editor viewport with `data-lenis-prevent`.
**Confidence:** HIGH

### PM Block Markdown Marker Format
**Recommendation:** Fenced code blocks with `pm:` prefix: ` ```pm:decision\n{json}\n``` `
**Rationale:** (1) Valid markdown -- renders as code block in any viewer. (2) Monaco tokenizer already handles fenced blocks. (3) JSON body is parseable and human-readable. (4) Easy regex detection: `/^```pm:(\w+)/`. (5) View zone replaces the entire fenced block range.
**Confidence:** MEDIUM -- may need iteration on the exact format once implemented

### Monaco Theme
**Recommendation:** Custom `pilot-space` theme extending `vs` (light) base with design system colors.
**Rationale:** Match the warm, calm aesthetic. Use indigo accent for cursor and selection (consistent with brand). Subtle line highlight. Ghost text in muted gray. Dark theme variant extending `vs-dark` for future.
**Confidence:** HIGH

### File Tree Component
**Recommendation:** Custom component using `react-virtuoso` for virtualization.
**Rationale:** `react-virtuoso` is already in the project. Custom tree allows full design system integration (icons, spacing, animations). No need for `react-arborist` or similar -- the tree is a simple recursive structure with expand/collapse.
**Confidence:** HIGH

### Tab Management
**Recommendation:** Max 12 tabs visible, horizontal scroll for overflow, close on middle-click, close all/close others context menu. Modified indicator (dot) during auto-save debounce window.
**Rationale:** Matches VS Code conventions familiar to developers. 12-tab limit prevents tab bar from becoming unusable.
**Confidence:** MEDIUM -- UX preference; adjustable based on testing

## Open Questions

1. **PM Block Data Migration**
   - What we know: Notes are currently stored as TipTap JSON (ProseMirror document format)
   - What's unclear: How to migrate existing notes with PM blocks from TipTap JSON to markdown with PM block markers. This is a data migration concern.
   - Recommendation: Build a `tiptapJsonToMarkdown` converter that runs once per note on first load. Store converted markdown back. Keep TipTap JSON as backup in a separate field for rollback.

2. **Monaco Worker Configuration in Next.js/Turbopack**
   - What we know: Monaco uses web workers for language services. `@monaco-editor/react`'s loader defaults to CDN-hosted workers.
   - What's unclear: Whether self-hosted workers work correctly with Next.js 16 + Turbopack.
   - Recommendation: Start with CDN loader (default). If offline/Tauri support is needed, investigate `monaco-editor-webpack-plugin` equivalent for Turbopack later.

3. **View Zone Performance with 10+ PM Blocks**
   - What we know: View zones with React portals work for individual blocks.
   - What's unclear: Performance impact when a note has 10+ PM blocks each with complex React renderers.
   - Recommendation: Profile during implementation. Virtualize view zones if needed (only render portals for visible zones). Use `IntersectionObserver` on view zone DOM nodes.

4. **Crossfade Transitions**
   - What we know: 200-300ms crossfade for mode switches.
   - What's unclear: Best approach for smooth transition between Monaco editor and markdown preview (they are different DOM trees).
   - Recommendation: Use CSS `opacity` transition with absolute positioning. Fade old view out while fading new view in. Keep both mounted briefly during transition.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.x + jsdom |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && pnpm test -- --run` |
| Full suite command | `cd frontend && pnpm test` |

### Phase Requirements -> Test Map

No formal requirement IDs assigned yet (TBD). Key behaviors to validate:

| Behavior | Test Type | Automated Command | Notes |
|----------|-----------|-------------------|-------|
| Monaco editor mounts without SSR error | unit | `pnpm test -- --run src/features/editor/__tests__/MonacoNoteEditor.test.tsx` | Mock monaco-editor |
| PM block markers parse correctly | unit | `pnpm test -- --run src/features/editor/__tests__/pmBlockMarkers.test.ts` | Pure function test |
| Ghost text provider returns completions | unit | `pnpm test -- --run src/features/editor/__tests__/ghostText.test.ts` | Mock AI API |
| Slash command provider lists commands | unit | `pnpm test -- --run src/features/editor/__tests__/slashCmd.test.ts` | Mock CompletionItemProvider |
| FileStore open/close/switch tabs | unit | `pnpm test -- --run src/features/file-browser/__tests__/FileStore.test.ts` | MobX store test |
| Markdown preview renders GFM + math + mermaid | unit | `pnpm test -- --run src/features/markdown-preview/__tests__/MarkdownPreview.test.tsx` | Snapshot test |
| View zone height syncs with ResizeObserver | integration | `pnpm test -- --run src/features/editor/__tests__/viewZones.test.tsx` | jsdom + mock Monaco |
| Tab management (max tabs, overflow, close) | unit | `pnpm test -- --run src/features/file-browser/__tests__/TabBar.test.tsx` | Component test |

### Sampling Rate
- **Per task commit:** `cd frontend && pnpm test -- --run --reporter=verbose`
- **Per wave merge:** `cd frontend && pnpm test && pnpm type-check && pnpm lint`
- **Phase gate:** Full quality gates green before verify

### Wave 0 Gaps
- [ ] `frontend/src/features/editor/__tests__/` -- test directory for new editor tests
- [ ] `frontend/src/features/file-browser/__tests__/` -- test directory for file browser tests
- [ ] `frontend/src/features/markdown-preview/__tests__/` -- test directory for preview tests
- [ ] Monaco mock setup in vitest (mock `monaco-editor` module for jsdom environment)

## Sources

### Primary (HIGH confidence)
- [Monaco Editor API docs](https://microsoft.github.io/monaco-editor/typedoc/) - InlineCompletionsProvider, CompletionItemProvider, view zones, IViewZone
- [@monaco-editor/react npm](https://www.npmjs.com/package/@monaco-editor/react) - v4.7.0, React 19 support, loader config
- [y-monaco GitHub](https://github.com/yjs/y-monaco) - v0.1.6, MonacoBinding API, peer deps
- [Yjs Monaco docs](https://docs.yjs.dev/ecosystem/editor-bindings/monaco) - Binding setup, awareness
- [Lenis GitHub](https://github.com/darkroomengineering/lenis) - v1.3.20, React export, options
- npm registry - All versions verified via `npm view` on 2026-03-23

### Secondary (MEDIUM confidence)
- [Monaco Editor Discussions #4477](https://github.com/microsoft/monaco-editor/discussions/4477) - View zone React rendering patterns
- [Monacopilot docs](https://monacopilot.dev/) - InlineCompletionsProvider patterns (used as reference, not as dependency)
- [Liveblocks Monaco+Yjs guide](https://liveblocks.io/docs/guides/how-to-create-a-collaborative-code-editor-with-monaco-yjs-nextjs-and-liveblocks) - Next.js + Monaco + Yjs integration patterns
- [Deno Monaco+Next.js blog](https://deno.com/blog/monaco-nextjs) - SSR workarounds

### Tertiary (LOW confidence)
- None -- all claims verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages verified on npm, peer deps checked, existing project deps confirmed compatible
- Architecture: HIGH - Monaco APIs well-documented; view zone + React portal pattern verified in community examples
- Pitfalls: HIGH - Based on documented issues (SSR crashes, bundle size) and project-specific knowledge (React 19 flushSync issue)
- Discretion recommendations: HIGH for most (react-markdown, lenis, file tree); MEDIUM for PM block format (needs implementation validation)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days -- stable ecosystem, no major breaking changes expected)
