# Phase 42: Command Palette and Breadcrumb Navigation - Research

**Researched:** 2026-03-24
**Domain:** Frontend UI — command palette, breadcrumb navigation, symbol outline panel
**Confidence:** HIGH

## Summary

Phase 42 adds three VS Code-inspired navigation features to the existing Monaco editor environment: a command palette (Cmd+Shift+P), breadcrumb navigation above the editor, and a symbol outline panel (Cmd+Shift+O). All three features are frontend-only, integrating into the existing `EditorLayout` component from Phase 40.

The project already has the core building blocks in place: shadcn's `Command` component (cmdk 1.1.1) is installed and used by `QuickOpen.tsx`, `FileStore` provides active file state for breadcrumbs, and Monaco 0.55.1 supports document symbol providers for the outline panel. The main implementation work is composing these existing primitives into three new feature components with a central `ActionRegistry` for the palette.

**Primary recommendation:** Reuse the existing cmdk/Command pattern from QuickOpen for the command palette; build breadcrumbs as a thin observer component reading FileStore; build the symbol outline using a custom markdown heading parser (for notes) and Monaco's internal OutlineModel API (for code files).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Command palette trigger: Cmd+Shift+P (macOS) / Ctrl+Shift+P (Windows/Linux)
- UI: Full-width overlay at top of editor area (like VS Code), not a modal dialog
- Fuzzy search: Use shadcn Command component (cmdk) -- same pattern as QuickOpen
- Action categories: File, Edit, View, Navigate, Note, AI
- Each action shows: icon, label, category badge, keyboard shortcut
- Actions registered via central `ActionRegistry` -- new actions addable without modifying palette component
- Recently used actions persist in localStorage (cap at 5)
- Breadcrumb position: horizontal bar above editor, below tab bar
- Breadcrumb segments: Workspace > Project > File path segments
- Click behavior: clicking segment opens dropdown showing siblings
- Separator: chevron right icon (Lucide ChevronRight)
- Symbol outline trigger: Cmd+Shift+O toggle
- Position: right sidebar panel, collapsible, 240px default, resizable
- Markdown/notes: extract headings (H1-H6) and PM block markers
- Code files: use Monaco built-in DocumentSymbolProvider
- Tree view with collapsible hierarchy, click-to-navigate, active symbol tracking
- Cmd+G: Go to line (new action + direct shortcut)

### Claude's Discretion
- Action registry implementation details (Map vs array, lazy loading)
- Breadcrumb dropdown animation style
- Symbol outline refresh debounce timing
- Exact icon choices per symbol kind
- Command palette max visible items before scroll

### Deferred Ideas (OUT OF SCOPE)
- Custom keybinding configuration UI (Phase 46)
- Command palette extensions/plugins (Phase 45)
- Multi-file symbol search (workspace-wide)
- Breadcrumb "recent files" dropdown
</user_constraints>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cmdk | 1.1.1 | Command palette fuzzy search | Already used by QuickOpen; shadcn Command wraps it |
| monaco-editor | 0.55.1 | Editor + DocumentSymbolProvider | Already the editor; has symbol APIs built in |
| @monaco-editor/react | 4.7.0 | React wrapper for Monaco | Already used by MonacoNoteEditor |
| lucide-react | 0.562.0 | Icons for actions, symbols, breadcrumbs | Already the icon library |
| mobx / mobx-react-lite | 6.15.0 | Reactive state (FileStore, potential EditorStore) | Already the state management choice |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Command | - | Pre-styled cmdk wrapper | Command palette UI |
| shadcn/ui Popover | - | Breadcrumb segment dropdowns | Clicking breadcrumb segments |
| shadcn/ui ScrollArea | - | Symbol outline scrollable tree | Outline panel content |
| @/components/ui/resizable | - | Outline panel resize | Right sidebar resizable panel |

### No New Dependencies Required
All features can be built with existing packages. No npm installs needed.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/features/
├── command-palette/
│   ├── components/
│   │   └── CommandPalette.tsx        # The overlay UI (cmdk-based)
│   ├── hooks/
│   │   └── useCommandPalette.ts      # Open/close state, keyboard handler
│   ├── registry/
│   │   └── ActionRegistry.ts         # Central action registration
│   └── actions/
│       ├── fileActions.ts            # File category actions
│       ├── editActions.ts            # Edit category actions
│       ├── viewActions.ts            # View category actions
│       ├── navigateActions.ts        # Navigate category actions
│       ├── noteActions.ts            # Note category actions
│       └── aiActions.ts              # AI category actions
├── breadcrumbs/
│   ├── components/
│   │   ├── BreadcrumbBar.tsx         # Horizontal breadcrumb bar
│   │   └── BreadcrumbSegment.tsx     # Individual segment with dropdown
│   └── hooks/
│       └── useBreadcrumbs.ts         # Derive segments from active file
├── symbol-outline/
│   ├── components/
│   │   ├── SymbolOutlinePanel.tsx    # Right sidebar panel
│   │   └── SymbolTreeItem.tsx        # Individual tree node
│   ├── hooks/
│   │   └── useSymbolOutline.ts       # Extract symbols, track active
│   └── parsers/
│       └── markdownSymbols.ts        # Heading + PM block extraction
```

### Pattern 1: ActionRegistry (Map-based singleton)
**What:** A central registry where actions are registered by ID. The palette reads from this registry, and any module can register actions without coupling to the palette UI.
**When to use:** Command palette action management.
**Recommendation (Claude's discretion):** Use a `Map<string, PaletteAction>` keyed by action ID. Simpler than a class -- just a module-level Map with register/unregister/getAll functions. No lazy loading needed; all actions are lightweight data objects (no heavy imports).

```typescript
// ActionRegistry.ts
export interface PaletteAction {
  id: string;
  label: string;
  category: 'file' | 'edit' | 'view' | 'navigate' | 'note' | 'ai';
  icon: React.ComponentType<{ className?: string }>;
  shortcut?: string; // Display string: "Cmd+S"
  execute: () => void;
  /** Lower = higher priority in results */
  priority?: number;
}

const registry = new Map<string, PaletteAction>();

export function registerAction(action: PaletteAction): () => void {
  registry.set(action.id, action);
  return () => registry.delete(action.id); // Returns unregister fn
}

export function getAllActions(): PaletteAction[] {
  return Array.from(registry.values());
}
```

### Pattern 2: Breadcrumb Derivation from FileStore
**What:** Breadcrumbs are computed from `FileStore.activeFile.path` by splitting on `/` and resolving siblings from the file tree.
**When to use:** BreadcrumbBar component.

```typescript
// useBreadcrumbs.ts
interface BreadcrumbSegment {
  label: string;
  path: string;       // Full path up to this segment
  isLast: boolean;
  siblings: { id: string; name: string; path: string }[];
}

// Split activeFile.path into segments, look up siblings from fileTreeItems
function deriveBreadcrumbs(
  activeFile: OpenFile | undefined,
  fileTreeItems: FileTreeItem[]
): BreadcrumbSegment[] { ... }
```

### Pattern 3: Symbol Extraction (dual strategy)
**What:** For markdown/note files, parse headings and PM blocks from content text. For code files, use Monaco's internal OutlineModel API.
**When to use:** Symbol outline panel.

For markdown files (custom parser -- lightweight):
```typescript
// markdownSymbols.ts
export interface DocumentSymbol {
  name: string;
  kind: 'heading' | 'pm-block' | 'function' | 'class' | 'variable' | 'interface';
  line: number;       // 1-based
  level: number;      // nesting depth (heading level or 0 for flat)
  children: DocumentSymbol[];
}

export function parseMarkdownSymbols(content: string): DocumentSymbol[] {
  // Extract ## headings (H1-H6) and ```pm:type blocks
  // Build hierarchy: H2 nests under H1, H3 under H2, etc.
}
```

For code files (Monaco internal API):
```typescript
// useSymbolOutline.ts -- code file path
import { StandaloneServices } from 'monaco-editor/esm/vs/editor/standalone/browser/standaloneServices.js';
import { ILanguageFeaturesService } from 'monaco-editor/esm/vs/editor/common/services/languageFeatures.js';
import { OutlineModel } from 'monaco-editor/esm/vs/editor/contrib/documentSymbols/browser/outlineModel.js';

async function getCodeSymbols(model: monaco.editor.ITextModel): Promise<DocumentSymbol[]> {
  const { documentSymbolProvider } = StandaloneServices.get(ILanguageFeaturesService);
  const outline = await OutlineModel.create(documentSymbolProvider, model);
  return outline.asListOfDocumentSymbols();
}
```

### Pattern 4: Keyboard Shortcut Registration
**What:** Global keyboard shortcuts registered via `useEffect` + `addEventListener('keydown')` -- same pattern used by `useQuickOpen`.
**When to use:** All three features need keyboard triggers.

```typescript
// Existing pattern from useQuickOpen.ts -- reuse exactly
useEffect(() => {
  function handleKeyDown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'p') {
      e.preventDefault();
      togglePalette();
    }
  }
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [togglePalette]);
```

### Anti-Patterns to Avoid
- **Importing Monaco internals at module level:** OutlineModel, ILanguageFeaturesService, StandaloneServices are internal APIs that must be dynamically imported inside `useEffect` or async functions to avoid SSG build failures. Same pattern as all other Monaco features in this codebase.
- **Making ActionRegistry a MobX store:** Actions are static data registered at mount time. No need for reactivity on the registry itself -- the palette reads actions when opened, not continuously.
- **Wrapping CommandPalette in `observer()`:** If it only reads from ActionRegistry (non-MobX), no observer needed. Only breadcrumbs and outline need observer (they read FileStore).
- **Nesting breadcrumb dropdowns in the same stacking context as Monaco:** Monaco has high z-index; use Radix Portal (via Popover) for dropdowns.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy search matching | Custom scoring algorithm | cmdk built-in filtering | cmdk handles fuzzy match, ranking, and keyboard nav |
| Keyboard navigation in lists | Arrow key handlers | cmdk CommandList | Built into Command component |
| Dropdown positioning | Manual absolute positioning | Radix Popover (via shadcn) | Handles viewport collision, portal, focus trap |
| Resizable panels | Custom drag handlers | shadcn ResizablePanel | Already used for file tree; consistent behavior |

**Key insight:** The existing QuickOpen + cmdk pattern handles 80% of the command palette work. The main new code is the ActionRegistry data layer and the breadcrumb/outline UI components.

## Common Pitfalls

### Pitfall 1: Monaco Internal API Instability
**What goes wrong:** `OutlineModel` and `ILanguageFeaturesService` are internal Monaco APIs (not in public typings). Path may change between Monaco versions.
**Why it happens:** Monaco does not officially expose symbol extraction as a public API.
**How to avoid:** Pin import paths to the exact paths verified for Monaco 0.55.1. Add a comment with the Monaco version. If symbols fail to load, fall back gracefully to empty state.
**Warning signs:** TypeScript errors on import paths after Monaco upgrade.

### Pitfall 2: Keyboard Shortcut Conflicts with Monaco
**What goes wrong:** Cmd+Shift+P and Cmd+Shift+O are also Monaco built-in shortcuts (command palette and "go to symbol"). When focus is inside Monaco editor, the editor captures the event before the React handler.
**Why it happens:** Monaco registers its own keyboard handlers with high priority.
**How to avoid:** Register a Monaco keybinding override that calls the custom palette/outline instead of Monaco's built-in. Use `editor.addCommand()` or `editor.addAction()` to intercept within Monaco context. The global `window` listener handles when focus is outside Monaco.
**Warning signs:** Shortcut works when clicking outside editor but not when editor is focused.

### Pitfall 3: Breadcrumb Dropdown Stacking Under Monaco
**What goes wrong:** Popover content renders behind the Monaco editor overlay.
**Why it happens:** Monaco uses high z-index values for its internal layers.
**How to avoid:** Use Radix Popover (via shadcn) which portals to `document.body`. Ensure the breadcrumb bar is positioned outside the Monaco container DOM, not inside it.
**Warning signs:** Dropdown flickers or is invisible when opened.

### Pitfall 4: Symbol Outline Excessive Re-computation
**What goes wrong:** Parsing symbols on every keystroke causes jank.
**Why it happens:** Content changes fire continuously during typing.
**How to avoid:** Debounce symbol extraction. **Recommendation (Claude's discretion):** 500ms debounce for markdown heading parser, 1000ms for Monaco OutlineModel (which is async and heavier). Use `requestIdleCallback` if available.
**Warning signs:** Typing lag, especially in large files.

### Pitfall 5: SSG Build Failure from Monaco Imports
**What goes wrong:** Importing Monaco internal modules at module level breaks Next.js static generation.
**Why it happens:** Monaco requires browser APIs (DOM, Web Workers) not available during SSG.
**How to avoid:** All Monaco imports must be dynamic (`import()` inside useEffect or async functions). This is the established pattern -- see `MonacoNoteEditor` using `next/dynamic` with `ssr: false`.
**Warning signs:** Build fails with "window is not defined" or similar.

### Pitfall 6: Recently Used Actions localStorage Race
**What goes wrong:** Multiple tabs overwrite each other's recently-used list.
**Why it happens:** Each tab reads stale localStorage on open, writes without merging.
**How to avoid:** Read localStorage fresh each time the palette opens (not cached in state). Write-through on action execution. 5-item cap naturally limits divergence impact. Not worth adding `storage` event listener for this.

## Code Examples

### Command Palette Integration in EditorLayout
```typescript
// EditorLayout.tsx -- add CommandPalette alongside QuickOpen
// Palette mounts at workspace level (above all panels)
return (
  <div className={className}>
    <ResizablePanelGroup orientation="horizontal">
      {/* ... file tree panel ... */}
      <ResizablePanel defaultSize={80} minSize={40}>
        <div className="flex flex-col h-full">
          <TabBar />
          <BreadcrumbBar /> {/* NEW: between TabBar and editor */}
          {/* ... editor content ... */}
        </div>
      </ResizablePanel>
      {/* Optional: SymbolOutlinePanel as third resizable panel */}
    </ResizablePanelGroup>
    <QuickOpen items={fileTreeItems} />
    <CommandPalette /> {/* NEW: overlay, not in panel flow */}
  </div>
);
```

### Breadcrumb Segment with Popover Dropdown
```typescript
// BreadcrumbSegment.tsx
import { ChevronRight } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

function BreadcrumbSegment({ segment, onNavigate }: Props) {
  return (
    <>
      {!segment.isFirst && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />}
      <Popover>
        <PopoverTrigger asChild>
          <button
            className={cn(
              'text-sm px-1 py-0.5 rounded hover:bg-muted transition-colors truncate max-w-[160px]',
              segment.isLast ? 'font-semibold text-foreground' : 'text-muted-foreground'
            )}
          >
            {segment.label}
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-56 p-1">
          {segment.siblings.map(sibling => (
            <button key={sibling.id} onClick={() => onNavigate(sibling)} ...>
              {sibling.name}
            </button>
          ))}
        </PopoverContent>
      </Popover>
    </>
  );
}
```

### Active Symbol Tracking
```typescript
// useSymbolOutline.ts -- track which symbol contains cursor
function findActiveSymbol(
  symbols: DocumentSymbol[],
  cursorLine: number
): DocumentSymbol | null {
  let best: DocumentSymbol | null = null;
  function walk(items: DocumentSymbol[]) {
    for (const sym of items) {
      if (sym.line <= cursorLine) {
        best = sym; // Latest symbol before or at cursor
      }
      walk(sym.children);
    }
  }
  walk(symbols);
  return best;
}

// Listen to editor cursor position changes
useEffect(() => {
  if (!editor) return;
  const disposable = editor.onDidChangeCursorPosition((e) => {
    const active = findActiveSymbol(symbols, e.position.lineNumber);
    setActiveSymbolId(active?.name ?? null);
  });
  return () => disposable.dispose();
}, [editor, symbols]);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `getDocumentSymbols()` function | `OutlineModel.create()` via `StandaloneServices` | Monaco 0.34.1 (2022) | Must use internal API path for symbol extraction |
| cmdk 0.x | cmdk 1.x (breaking change) | 2024 | Different API; project already on 1.1.1 |
| Custom keyboard shortcut manager | Browser `addEventListener` + Monaco `addCommand` | Established | Dual registration needed: global + Monaco-internal |

**Deprecated/outdated:**
- `monaco-editor/esm/vs/editor/contrib/documentSymbols/documentSymbols.js` -- old path, moved to `browser/outlineModel.js`
- cmdk 0.x API -- project is on 1.x; no migration needed

## Open Questions

1. **Monaco Internal API Type Safety**
   - What we know: `OutlineModel` and `StandaloneServices` imports work at runtime but lack official TypeScript declarations
   - What's unclear: Whether Monaco 0.55.1 has moved these paths again since 0.34.1
   - Recommendation: Verify exact import paths at implementation time; wrap in try/catch with graceful fallback

2. **Outline Panel Layout Integration**
   - What we know: EditorLayout uses `ResizablePanelGroup` with file tree (left) and editor (center)
   - What's unclear: Whether adding a third resizable panel (right) for the outline will require refactoring the two-panel group
   - Recommendation: Add outline as a conditionally-rendered third `ResizablePanel` inside the existing group. When hidden, editor panel gets full width. This is how `ResizablePanelGroup` is designed to work.

3. **Action Execute Context**
   - What we know: Actions need references to FileStore, editor instance, etc. to execute
   - What's unclear: How to inject context into action execute() functions without tight coupling
   - Recommendation: Actions are registered at component mount time with closures over store references. When the palette executes an action, the closure already has the needed context.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.x + jsdom |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && pnpm test -- --run --reporter=verbose` |
| Full suite command | `cd frontend && pnpm test` |

### Phase Requirements -> Test Map

Since no formal requirement IDs are assigned, tests map to the three features:

| Feature | Behavior | Test Type | Automated Command | File Exists? |
|---------|----------|-----------|-------------------|-------------|
| ActionRegistry | Register, unregister, getAll, fuzzy filter | unit | `cd frontend && pnpm test -- --run src/features/command-palette/registry/ActionRegistry.test.ts` | No - Wave 0 |
| CommandPalette | Opens on Cmd+Shift+P, searches, executes action | unit | `cd frontend && pnpm test -- --run src/features/command-palette/components/CommandPalette.test.tsx` | No - Wave 0 |
| useBreadcrumbs | Derives segments from file path, resolves siblings | unit | `cd frontend && pnpm test -- --run src/features/breadcrumbs/hooks/useBreadcrumbs.test.ts` | No - Wave 0 |
| markdownSymbols | Extracts headings + PM blocks, builds hierarchy | unit | `cd frontend && pnpm test -- --run src/features/symbol-outline/parsers/markdownSymbols.test.ts` | No - Wave 0 |
| useSymbolOutline | Active symbol tracking, debounced refresh | unit | `cd frontend && pnpm test -- --run src/features/symbol-outline/hooks/useSymbolOutline.test.ts` | No - Wave 0 |
| Recently used | localStorage persist, cap at 5, read on open | unit | `cd frontend && pnpm test -- --run src/features/command-palette/hooks/useRecentActions.test.ts` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && pnpm test -- --run --reporter=verbose`
- **Per wave merge:** `cd frontend && pnpm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/features/command-palette/registry/ActionRegistry.test.ts` -- registry CRUD + filter
- [ ] `src/features/command-palette/components/CommandPalette.test.tsx` -- render + keyboard interaction
- [ ] `src/features/breadcrumbs/hooks/useBreadcrumbs.test.ts` -- path splitting, sibling resolution
- [ ] `src/features/symbol-outline/parsers/markdownSymbols.test.ts` -- heading hierarchy, PM blocks
- [ ] `src/features/symbol-outline/hooks/useSymbolOutline.test.ts` -- active tracking, debounce

## Sources

### Primary (HIGH confidence)
- Existing codebase: `QuickOpen.tsx`, `useQuickOpen.ts`, `command.tsx` -- verified cmdk 1.1.1 pattern
- Existing codebase: `FileStore.ts`, `EditorLayout.tsx`, `TabBar.tsx` -- verified integration points
- Existing codebase: `MonacoNoteEditor.tsx`, `useMonacoNote.ts` -- verified editor/monaco instance access pattern
- Existing codebase: `pmBlockMarkers.ts` -- verified PM block parsing pattern
- [Monaco DocumentSymbolProvider API](https://microsoft.github.io/monaco-editor/typedoc/interfaces/languages.DocumentSymbolProvider.html)
- [Monaco registerDocumentSymbolProvider](https://microsoft.github.io/monaco-editor/typedoc/functions/languages.registerDocumentSymbolProvider.html)

### Secondary (MEDIUM confidence)
- [Monaco getDocumentSymbols removal issue #2959](https://github.com/microsoft/monaco-editor/issues/2959) -- OutlineModel.create() approach verified by community
- [Monaco DocumentSymbol interface](https://microsoft.github.io/monaco-editor/typedoc/interfaces/languages.DocumentSymbol.html)

### Tertiary (LOW confidence)
- Monaco internal import paths (`StandaloneServices`, `OutlineModel`) -- these are internal APIs subject to change; verified for ~0.34.1+ but exact paths need runtime validation against 0.55.1

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages already installed, patterns verified in codebase
- Architecture: HIGH -- follows established patterns (cmdk, MobX observer, Monaco hooks)
- Pitfalls: MEDIUM -- Monaco internal API paths are the main uncertainty; keyboard conflict handling needs runtime testing
- Breadcrumbs: HIGH -- straightforward string splitting + FileStore observation
- Symbol outline: MEDIUM -- markdown parser is simple but Monaco OutlineModel path needs verification

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no fast-moving dependencies)
