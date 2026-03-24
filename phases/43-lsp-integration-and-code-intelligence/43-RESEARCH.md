# Phase 43: LSP Integration and Code Intelligence - Research

**Researched:** 2026-03-24
**Domain:** Monaco editor language services, TypeScript worker API, Pyright WASM, diagnostics UI
**Confidence:** HIGH

## Summary

Phase 43 adds code intelligence features to the Monaco editor: autocomplete, hover info, go-to-definition, find references, signature help, and diagnostics for TypeScript/JavaScript (primary) and Python (secondary). JSON/CSS/HTML intelligence is already provided by Monaco's built-in language services and requires no additional work.

The TypeScript language service is built into `monaco-editor` 0.55.1 (already installed). It requires only configuration: setting compiler options, diagnostic options, and optionally adding type definitions via `addExtraLib`. No additional packages needed. The Python story is more complex: `@typefox/pyright-browser` (1.1.299) and `monaco-pyright-lsp` (0.1.7) exist but are low-activity packages. The CONTEXT.md marks Pyright WASM bundle strategy as Claude's Discretion; recommendation is to use `monaco-pyright-lsp` loaded lazily via dynamic import when a `.py` file opens, with a fallback to basic syntax highlighting if the worker fails.

The diagnostics panel is a custom React component that reads Monaco markers via `monaco.editor.onDidChangeMarkers` and `monaco.editor.getModelMarkers()`. This is standard Monaco API with no additional libraries needed.

**Primary recommendation:** Focus on TypeScript configuration first (zero new dependencies, highest impact), then build the diagnostics panel UI, then add Python support as a lazy-loaded enhancement.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **TypeScript/JavaScript** (primary) -- Monaco's built-in TypeScript language service. Full IntelliSense: autocomplete, hover types, go-to-definition, find references, signature help, diagnostics with inline squiggles.
- **Python** (secondary) -- Pyright WASM build running in a Web Worker. Limited cross-file resolution.
- **JSON/CSS/HTML** -- Monaco's built-in language services (already working out of the box).
- **Markdown** -- No LSP (notes use custom decorations from Phase 40).
- **Browser-hosted via Web Workers** -- no backend language server processes.
- **No socket-based LSP protocol** -- use Monaco's native language registration APIs.
- **Workers loaded lazily** per language on first file open of that type.
- **Diagnostics Panel** -- collapsible panel below editor area, badge count, click-to-navigate, error/warning/info filters.
- **Platform Differences** -- Web: TS + JSON/CSS/HTML + Python (if bundle OK). Tauri: same + cross-file go-to-definition.
- **Pyright WASM ~5-8MB** -- must be lazy-loaded, show loading indicator.

### Claude's Discretion
- Pyright WASM bundle strategy (CDN vs bundled vs on-demand)
- TypeScript lib definitions loading (which lib.d.ts files to include)
- Diagnostics panel exact layout and animation
- Hover tooltip max width and content truncation
- Auto-import suggestion strategy
- Debounce timing for diagnostics refresh

### Deferred Ideas (OUT OF SCOPE)
- Cross-file go-to-definition on web
- Full Python project analysis (requires server-side Pyright)
- Go, Rust, Java, C# language support
- Auto-import suggestions
- Code actions / quick fixes
- Linting integration (ESLint, Ruff)
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| monaco-editor | 0.55.1 | Editor + built-in TS/JS/JSON/CSS/HTML language services | Already installed, built-in TypeScript worker |
| @monaco-editor/react | 4.7.0 | React wrapper with onValidate callback | Already installed, provides marker events |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| monaco-pyright-lsp | 0.1.7 | Pyright WASM for Python intelligence | Lazy-loaded on first .py file open |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| monaco-pyright-lsp | @typefox/pyright-browser + monaco-languageclient | Full LSP protocol stack but heavier (~10.7.0 languageclient), more complex setup. monaco-pyright-lsp is simpler for our use case |
| Custom diagnostics panel | monaco-marker-data-provider | Only helps with marker data flow, not UI. We need custom UI anyway |

**Installation:**
```bash
cd frontend && pnpm add monaco-pyright-lsp
```

**No new dependencies needed for TypeScript/JavaScript intelligence.** Monaco 0.55.1 already includes everything.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/features/editor/
  hooks/
    useTypeScriptDefaults.ts   # TS compiler + diagnostic options config
    usePythonLanguage.ts       # Pyright WASM lazy loader + provider registration
    useDiagnosticsPanel.ts     # Marker subscription + diagnostic state
  components/
    DiagnosticsPanel.tsx       # Problems panel UI below editor
    DiagnosticRow.tsx          # Single diagnostic entry (icon + file + line + message)
  language/
    typescript-config.ts       # CompilerOptions, DiagnosticsOptions constants
    python-worker.ts           # Pyright Web Worker initialization
```

### Pattern 1: TypeScript Language Service Configuration
**What:** Configure Monaco's built-in TypeScript worker with appropriate compiler options and diagnostic settings.
**When to use:** On Monaco mount, before any TypeScript file is loaded.
**Example:**
```typescript
// Source: Monaco Editor API docs
import type * as monacoNs from 'monaco-editor';

export function configureTypeScriptDefaults(monaco: typeof monacoNs): void {
  const tsDefaults = monaco.languages.typescript.typescriptDefaults;

  // Compiler options
  tsDefaults.setCompilerOptions({
    target: monaco.languages.typescript.ScriptTarget.ESNext,
    module: monaco.languages.typescript.ModuleKind.ESNext,
    moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
    jsx: monaco.languages.typescript.JsxEmit.ReactJSX,
    allowJs: true,
    checkJs: false,
    strict: true,
    noEmit: true,
    esModuleInterop: true,
    allowNonTsExtensions: true,
    lib: ['esnext', 'dom', 'dom.iterable'],
  });

  // Enable all diagnostics
  tsDefaults.setDiagnosticsOptions({
    noSemanticValidation: false,
    noSyntaxValidation: false,
    noSuggestionDiagnostics: false,
  });

  // Also configure JavaScript defaults
  const jsDefaults = monaco.languages.typescript.javascriptDefaults;
  jsDefaults.setDiagnosticsOptions({
    noSemanticValidation: false,
    noSyntaxValidation: false,
  });
}
```

### Pattern 2: Marker Subscription for Diagnostics Panel
**What:** Subscribe to Monaco marker changes to populate a diagnostics panel.
**When to use:** When the diagnostics panel component mounts.
**Example:**
```typescript
// Source: Monaco Editor API - editor.onDidChangeMarkers
import type * as monacoNs from 'monaco-editor';

export interface Diagnostic {
  severity: 'error' | 'warning' | 'info' | 'hint';
  message: string;
  source: string;
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  modelUri: string;
  fileName: string;
}

function severityToString(severity: monacoNs.MarkerSeverity): Diagnostic['severity'] {
  switch (severity) {
    case 8: return 'error';
    case 4: return 'warning';
    case 2: return 'info';
    default: return 'hint';
  }
}

export function subscribeToDiagnostics(
  monaco: typeof monacoNs,
  onUpdate: (diagnostics: Diagnostic[]) => void
): monacoNs.IDisposable {
  return monaco.editor.onDidChangeMarkers((uris) => {
    const allMarkers = monaco.editor.getModelMarkers({});
    const diagnostics: Diagnostic[] = allMarkers.map((m) => ({
      severity: severityToString(m.severity),
      message: m.message,
      source: m.source ?? '',
      startLineNumber: m.startLineNumber,
      startColumn: m.startColumn,
      endLineNumber: m.endLineNumber,
      endColumn: m.endColumn,
      modelUri: m.resource.toString(),
      fileName: m.resource.path.split('/').pop() ?? '',
    }));
    onUpdate(diagnostics);
  });
}
```

### Pattern 3: Lazy Pyright Worker Loading
**What:** Load Pyright WASM only when a Python file is first opened.
**When to use:** On language detection of `.py` file in FileStore.
**Example:**
```typescript
let pyrightLoaded = false;

export async function ensurePythonLanguage(monaco: typeof monacoNs): Promise<void> {
  if (pyrightLoaded) return;
  pyrightLoaded = true;

  // Dynamic import to avoid bundling upfront
  const { MonacoPyrightProvider } = await import('monaco-pyright-lsp');
  const provider = new MonacoPyrightProvider();
  // Register with Monaco
  await provider.init(monaco);
}
```

### Pattern 4: Hook Pattern for Language Providers (Consistent with Codebase)
**What:** useEffect-based provider registration with IDisposable cleanup.
**When to use:** All language feature hooks follow this pattern (matches useMonacoTheme, useMonacoGhostText).
**Example:**
```typescript
export function useTypeScriptDefaults(monaco: typeof monacoNs | null): void {
  useEffect(() => {
    if (!monaco) return;
    configureTypeScriptDefaults(monaco);
    // No cleanup needed -- TS defaults are global singleton
  }, [monaco]);
}
```

### Anti-Patterns to Avoid
- **Registering providers per-editor instance:** Language providers are global to the Monaco instance, not per-editor. Register once, not in each MonacoFileEditor mount.
- **Synchronous Pyright import:** Never import monaco-pyright-lsp at module level. Always use dynamic import().
- **Polling for markers:** Use `onDidChangeMarkers` event, not setInterval polling.
- **Wrapping DiagnosticsPanel in observer():** If it only consumes local React state from marker events, keep it as a plain component (consistent with React 19 patterns in this codebase).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TypeScript autocomplete | Custom completion provider | Monaco built-in TS worker | Already provides VS Code-level IntelliSense |
| TypeScript hover info | Custom hover provider | Monaco built-in TS worker | Full type info + JSDoc extraction built-in |
| TypeScript go-to-definition | Custom definition provider | Monaco built-in TS worker | Within-file + cross-model navigation built-in |
| TypeScript diagnostics | Custom linter/checker | Monaco built-in TS worker | Semantic + syntax validation with squiggles |
| TypeScript signature help | Custom signature provider | Monaco built-in TS worker | Parameter hints on `(` trigger built-in |
| Python type checking | Custom type checker | Pyright WASM | Type inference is enormously complex |
| Marker change detection | Custom diffing | `editor.onDidChangeMarkers` | Native event, efficient, correct |

**Key insight:** For TypeScript, Monaco's built-in language service IS the VS Code TypeScript experience. Configuration is the only work needed. For Python, Pyright is the only viable browser-side type checker.

## Common Pitfalls

### Pitfall 1: TypeScript Defaults Must Be Set Before Model Creation
**What goes wrong:** Compiler options set after a model is created don't apply retroactively to that model's worker.
**Why it happens:** The TypeScript worker reads defaults at model creation time.
**How to avoid:** Call `configureTypeScriptDefaults()` in a `beforeMount` callback or early useEffect before any Editor components render.
**Warning signs:** First opened TS file has no IntelliSense but subsequent files work.

### Pitfall 2: getModelMarkers Timing with onDidChangeModelContent
**What goes wrong:** Calling `getModelMarkers()` inside `onDidChangeModelContent` returns stale markers (the TS worker hasn't re-validated yet).
**Why it happens:** Marker updates are async -- the TS worker processes changes and sets markers after a delay.
**How to avoid:** Use `onDidChangeMarkers` event instead. It fires AFTER the worker has updated markers.
**Warning signs:** Diagnostics panel shows stale errors that disappear on next keystroke.

### Pitfall 3: Multiple Models Share One TypeScript Worker
**What goes wrong:** Type errors in one file show up in another, or imports resolve unexpectedly.
**Why it happens:** Monaco's TS worker maintains a single project context across all models. `addExtraLib` definitions are global.
**How to avoid:** Use unique file URIs for each model. Be intentional about what's added via `addExtraLib`. Consider using `monaco.Uri.parse('file:///path/to/file.ts')` for models.
**Warning signs:** Phantom errors in files that were clean before opening another file.

### Pitfall 4: Pyright WASM Bundle Size Blocks Initial Load
**What goes wrong:** If Pyright is eagerly loaded, it adds 5-8MB to initial bundle, destroying load performance.
**Why it happens:** Pyright WASM is large because it includes the full type checker.
**How to avoid:** Lazy-load via `import()` only when first `.py` file is opened. Show a loading indicator (spinner in suggest widget or status bar message "Loading Python IntelliSense...").
**Warning signs:** Lighthouse performance score drops, initial load time increases significantly.

### Pitfall 5: Pyright Cross-File Imports Don't Work in Browser
**What goes wrong:** Python files importing from other Python files get `reportMissingImports` errors.
**Why it happens:** Pyright WASM has no filesystem access -- it can only analyze the single file provided.
**How to avoid:** Accept this limitation (documented in CONTEXT.md as deferred). Suppress or lower severity of import-related diagnostics for Python files. Document this as a known limitation.
**Warning signs:** Every Python file with imports shows red squiggles.

### Pitfall 6: Registering Providers Globally vs Per-Language
**What goes wrong:** Custom providers for Python accidentally override Monaco's built-in TS providers.
**Why it happens:** Provider registration uses language ID selectors. If selector is too broad ('*' or wrong language), it conflicts.
**How to avoid:** Always specify exact language ID: `'python'` for Python providers, never `'*'`.
**Warning signs:** TypeScript autocomplete stops working after opening a Python file.

### Pitfall 7: onValidate Fires Per-Editor, onDidChangeMarkers Fires Globally
**What goes wrong:** Using `@monaco-editor/react`'s `onValidate` prop gives markers for one editor; using `onDidChangeMarkers` gives markers for ALL models.
**Why it happens:** `onValidate` is scoped to the editor's model; `onDidChangeMarkers` is a global event.
**How to avoid:** For the diagnostics panel (shows ALL file diagnostics), use `onDidChangeMarkers`. For per-file status indicators, `onValidate` is simpler.
**Warning signs:** Diagnostics panel only shows errors from the active file.

## Code Examples

### TypeScript Worker Access (Verified API)
```typescript
// Source: Monaco Editor API - languages.typescript
// Access the TypeScript worker to get rich diagnostics
async function getTypeScriptDiagnostics(
  monaco: typeof monacoNs,
  model: monacoNs.editor.ITextModel
): Promise<void> {
  const worker = await monaco.languages.typescript.getTypeScriptWorker();
  const client = await worker(model.uri);

  const semanticDiagnostics = await client.getSemanticDiagnostics(model.uri.toString());
  const syntacticDiagnostics = await client.getSyntacticDiagnostics(model.uri.toString());
  // These are already reflected as markers, but useful for custom processing
}
```

### Register Go-to-Definition in Command Palette
```typescript
// Extends existing navigateActions.ts pattern
import { Locate, ListTree } from 'lucide-react';

interface LSPNavigateActionsContext {
  goToDefinition?: () => void;
  findReferences?: () => void;
}

export function registerLSPNavigateActions(context: LSPNavigateActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'navigate:go-to-definition',
      label: 'Go to Definition',
      category: 'navigate',
      icon: Locate,
      shortcut: 'F12',
      execute: () => context.goToDefinition?.(),
      priority: 43,
    },
    {
      id: 'navigate:find-references',
      label: 'Find All References',
      category: 'navigate',
      icon: ListTree,
      shortcut: 'Shift+F12',
      execute: () => context.findReferences?.(),
      priority: 44,
    },
  ];
  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
```

### Diagnostics Panel Component Structure
```typescript
// Source: Custom implementation following VS Code PROBLEMS pattern
interface DiagnosticsPanelProps {
  diagnostics: Diagnostic[];
  onNavigate: (uri: string, line: number, column: number) => void;
  className?: string;
}

// Filter state: 'all' | 'errors' | 'warnings'
// Badge: "{N} errors, {M} warnings"
// Each row: severity icon + fileName + ":" + line + " " + message
// Click row -> onNavigate(uri, line, column) -> editor.revealLineInCenter + setPosition
```

### Theme Diagnostic Colors (Add to pilotSpaceTheme.ts)
```typescript
// Colors to add to both light and dark themes
// Light theme additions:
{
  'editorError.foreground': '#ef4444',       // red-500
  'editorWarning.foreground': '#f59e0b',     // amber-500
  'editorInfo.foreground': '#3b82f6',        // blue-500
  'editorHint.foreground': '#6b7280',        // gray-500
  'editorError.border': '#fecaca',           // red-200
  'editorWarning.border': '#fde68a',         // amber-200
}

// Dark theme additions:
{
  'editorError.foreground': '#f87171',       // red-400
  'editorWarning.foreground': '#fbbf24',     // amber-400
  'editorInfo.foreground': '#60a5fa',        // blue-400
  'editorHint.foreground': '#9ca3af',        // gray-400
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Socket-based LSP (WebSocket) | In-browser Web Workers for TS/Pyright | 2023+ | No backend dependency for language services |
| monaco-languageclient for TS | Built-in TS worker (zero config) | Always | No extra package needed for TS |
| Manual completion providers | Let Monaco's built-in TS service handle it | Always | Full IntelliSense with no custom code |
| getModelMarkers polling | onDidChangeMarkers event | Monaco 0.34+ | Event-driven, no polling needed |

**Deprecated/outdated:**
- `monaco-typescript` npm package (v4.10.0, 4 years old): Now integrated directly into `monaco-editor`. Do not install separately.
- `freeInlineCompletions`: Replaced by `disposeInlineCompletions` in Monaco 0.55.1 (already noted in Phase 40-04 decisions).

## Open Questions

1. **Pyright WASM package maturity**
   - What we know: `monaco-pyright-lsp` (0.1.7) has 229 weekly downloads, last release ~1 year ago. `@typefox/pyright-browser` (1.1.299) has 1,293 weekly downloads, also low activity.
   - What's unclear: Whether these packages work reliably with Monaco 0.55.1 and Next.js dynamic imports.
   - Recommendation: Implement Python support behind a feature flag. If Pyright WASM causes issues, fall back to syntax highlighting only. Test bundle size impact during implementation.

2. **Cross-file go-to-definition scope**
   - What we know: Deferred for web. Tauri desktop can read local files via `tauri-plugin-fs`.
   - What's unclear: How to populate Monaco's TS worker with cross-file context on Tauri.
   - Recommendation: Defer Tauri cross-file support to a future phase. Within-file go-to-definition works with zero config via built-in TS worker.

3. **TypeScript lib definitions loading**
   - What we know: Monaco includes standard lib.d.ts files. The `lib` compiler option controls which are loaded.
   - What's unclear: Exact bundle size impact of loading `['esnext', 'dom', 'dom.iterable']` vs minimal set.
   - Recommendation: Start with `['esnext', 'dom', 'dom.iterable']` (matches VS Code default). Monaco already bundles these.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (jsdom environment) |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && pnpm test -- --run` |
| Full suite command | `cd frontend && pnpm test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| (none assigned) | TS compiler options configured correctly | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/typescriptConfig.test.ts` | Wave 0 |
| (none assigned) | Diagnostics subscription produces correct Diagnostic[] | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/diagnosticsPanel.test.ts` | Wave 0 |
| (none assigned) | DiagnosticsPanel renders errors/warnings with counts | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/DiagnosticsPanel.test.tsx` | Wave 0 |
| (none assigned) | LSP navigate actions register in palette | unit | `cd frontend && pnpm vitest run src/features/command-palette/__tests__/lspNavigateActions.test.ts` | Wave 0 |
| (none assigned) | Python language lazy-loads on .py file open | unit | `cd frontend && pnpm vitest run src/features/editor/__tests__/pythonLanguage.test.ts` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && pnpm vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && pnpm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/features/editor/__tests__/typescriptConfig.test.ts` -- TS defaults configuration
- [ ] `src/features/editor/__tests__/diagnosticsPanel.test.ts` -- marker subscription logic
- [ ] `src/features/editor/__tests__/DiagnosticsPanel.test.tsx` -- panel component rendering
- [ ] `src/features/command-palette/__tests__/lspNavigateActions.test.ts` -- action registration
- [ ] `src/features/editor/__tests__/pythonLanguage.test.ts` -- lazy loading behavior

Note: Monaco editor APIs will need mocking in unit tests (jsdom has no real Monaco). Focus tests on: configuration objects are correct, React component rendering, action registration, and lazy-loading logic.

## Sources

### Primary (HIGH confidence)
- [Monaco Editor API - TypeScript](https://microsoft.github.io/monaco-editor/typedoc/functions/languages.typescript.getTypeScriptWorker.html) - TypeScript worker API
- [Monaco Editor API - DiagnosticsOptions](https://microsoft.github.io/monaco-editor/typedoc/interfaces/languages.typescript.DiagnosticsOptions.html) - Diagnostic configuration
- [Monaco Editor API - registerDefinitionProvider](https://microsoft.github.io/monaco-editor/typedoc/functions/languages.registerDefinitionProvider.html) - Language provider registration
- [Monaco Editor API - registerCompletionItemProvider](https://microsoft.github.io/monaco-editor/typedoc/functions/languages.registerCompletionItemProvider.html) - Completion provider API
- Existing codebase: `MonacoFileEditor.tsx`, `EditorLayout.tsx`, `pilotSpaceTheme.ts`, `useSymbolOutline.ts`, `ActionRegistry.ts`

### Secondary (MEDIUM confidence)
- [@monaco-editor/react npm](https://www.npmjs.com/package/@monaco-editor/react) - onValidate callback documentation
- [Monaco Editor GitHub Issues #906, #607](https://github.com/microsoft/monaco-editor/issues/906) - getModelMarkers + onDidChangeMarkers behavior
- [TypeFox/monaco-languageclient](https://github.com/TypeFox/monaco-languageclient) - Pyright browser integration patterns

### Tertiary (LOW confidence)
- [monaco-pyright-lsp npm](https://socket.dev/npm/package/monaco-pyright-lsp) - Package exists but low download count, needs validation during implementation
- [@typefox/pyright-browser npm](https://www.npmjs.com/package/@typefox/pyright-browser) - Alternative Pyright package, version 1.1.299, low activity

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Monaco 0.55.1 built-in TS support is well-documented and already in use
- Architecture: HIGH - Follows existing hook patterns (useMonacoTheme, useMonacoGhostText) with standard Monaco APIs
- Pitfalls: HIGH - Well-known issues documented in Monaco GitHub issues
- Python support: LOW - Pyright WASM packages have low adoption and may have compatibility issues

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain, Monaco 0.55.1 is current)
