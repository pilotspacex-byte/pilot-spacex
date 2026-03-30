'use client';

/**
 * CommandPalette - Global Cmd+K / Cmd+P search modal (T-019)
 *
 * Opens via uiStore.commandPaletteOpen. Searches notes and issues
 * with a 5-result cap per group via server-side search query.
 * Keyboard-navigable with cmdk.
 *
 * Mode prefixes:
 *   >  Commands mode  — editor/UI command list
 *   #  Symbols mode   — (deferred) symbol search placeholder
 *   :  Go-to-line mode — jump to a line number in the active editor
 *   (no prefix) — default notes/issues search
 *
 * Cmd+P opens palette (alias for Cmd+K — identical behavior).
 */

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { FileText, Ticket, Search, Terminal, Hash, CornerDownLeft } from 'lucide-react';

import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '@/components/ui/command';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { observer } from 'mobx-react-lite';
import { useUIStore, useWorkspaceStore } from '@/stores';
import { notesApi } from '@/services/api/notes';
import { issuesApi } from '@/services/api/issues';
import type { Note } from '@/types/note';
import type { Issue } from '@/types/issue';

const MAX_RESULTS_PER_GROUP = 5;
const DEBOUNCE_MS = 250;

// ─── Palette modes ───────────────────────────────────────────────────────────

type PaletteMode = 'search' | 'commands' | 'symbols' | 'goto-line';

function detectMode(query: string): PaletteMode {
  if (query.startsWith('>')) return 'commands';
  if (query.startsWith('#')) return 'symbols';
  if (query.startsWith(':')) return 'goto-line';
  return 'search';
}

function effectiveQuery(mode: PaletteMode, query: string): string {
  return mode !== 'search' ? query.slice(1).trim() : query;
}

// ─── Built-in commands list ───────────────────────────────────────────────────

interface Command {
  id: string;
  label: string;
  description?: string;
  action: () => void;
}

// ─── Search results ───────────────────────────────────────────────────────────

interface SearchResults {
  notes: Note[];
  issues: Issue[];
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function NoteResultItem({ note }: { note: Note }) {
  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="truncate text-sm font-medium">{note.title || 'Untitled'}</span>
    </div>
  );
}

function IssueResultItem({ issue }: { issue: Issue }) {
  const stateName = issue.state?.name ?? '';
  const stateColor = issue.state?.color;

  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <Ticket className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="font-mono text-xs text-muted-foreground shrink-0">{issue.identifier}</span>
      <span className="truncate text-sm font-medium flex-1">{issue.name ?? issue.title}</span>
      {stateName && (
        <Badge
          variant="secondary"
          className="text-xs shrink-0 font-normal"
          style={stateColor ? { borderColor: stateColor, color: stateColor } : undefined}
        >
          {stateName}
        </Badge>
      )}
    </div>
  );
}

function ResultSkeleton() {
  return (
    <div className="px-2 py-1.5 space-y-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded shrink-0" />
          <Skeleton className="h-4 flex-1 rounded" />
        </div>
      ))}
    </div>
  );
}

// ─── Mode hint bar ────────────────────────────────────────────────────────────

function ModeHintBar({ mode }: { mode: PaletteMode }) {
  return (
    <div className="flex items-center gap-3 px-3 py-1.5 border-t text-[11px] text-muted-foreground bg-muted/30">
      <span className={cn('flex items-center gap-1', mode === 'commands' && 'text-foreground font-medium')}>
        <kbd className="font-mono">&gt;</kbd> Commands
      </span>
      <span className={cn('flex items-center gap-1', mode === 'symbols' && 'text-foreground font-medium')}>
        <kbd className="font-mono">#</kbd> Symbols
      </span>
      <span className={cn('flex items-center gap-1', mode === 'goto-line' && 'text-foreground font-medium')}>
        <kbd className="font-mono">:</kbd> Go to Line
      </span>
    </div>
  );
}

// ─── Commands mode ────────────────────────────────────────────────────────────

interface CommandsModeProps {
  query: string;
  onClose: () => void;
}

/**
 * CommandsModeInline — rendered outside cmdk's CommandList to bypass the
 * built-in filter which uses the raw input value (including ">" prefix).
 */
function CommandsModeInline({ query, onClose }: CommandsModeProps) {
  const commands: Command[] = [
    {
      id: 'toggle-source-control',
      label: 'Toggle Source Control Panel',
      description: 'Ctrl+Shift+G',
      action: () => {
        const e = new KeyboardEvent('keydown', {
          key: 'G',
          shiftKey: true,
          ctrlKey: true,
          bubbles: true,
        });
        window.dispatchEvent(e);
        onClose();
      },
    },
    {
      id: 'toggle-file-tree',
      label: 'Toggle File Tree',
      description: 'Ctrl+B',
      action: () => {
        window.dispatchEvent(new CustomEvent('code-editor:toggle-file-tree'));
        onClose();
      },
    },
    {
      id: 'format-document',
      label: 'Format Document',
      description: 'Shift+Alt+F',
      action: () => {
        window.dispatchEvent(new CustomEvent('code-editor:format-document'));
        onClose();
      },
    },
    {
      id: 'change-language-mode',
      label: 'Change Language Mode',
      action: () => {
        window.dispatchEvent(new CustomEvent('code-editor:change-language'));
        onClose();
      },
    },
  ];

  const filtered = query
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  if (filtered.length === 0) {
    return (
      <div className="px-3 py-4 text-sm text-muted-foreground text-center">
        No commands match &ldquo;{query}&rdquo;
      </div>
    );
  }

  return (
    <div role="group" aria-label="Commands" className="px-1 py-1">
      <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Commands
      </p>
      {filtered.map((cmd) => (
        <button
          key={cmd.id}
          type="button"
          role="option"
          className="flex items-center gap-2 w-full px-2 py-2 rounded-sm text-sm hover:bg-accent cursor-pointer text-left"
          onClick={cmd.action}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              cmd.action();
            }
          }}
        >
          <Terminal className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="flex-1">{cmd.label}</span>
          {cmd.description && (
            <span className="text-xs text-muted-foreground font-mono shrink-0">
              {cmd.description}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// ─── Symbols mode ─────────────────────────────────────────────────────────────

function SymbolsMode() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 px-4 text-center">
      <Hash className="h-6 w-6 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">
        Symbol search available in a future update
      </p>
      <p className="text-xs text-muted-foreground">
        Monaco outline API integration coming soon
      </p>
    </div>
  );
}

// ─── Go to line mode ──────────────────────────────────────────────────────────

interface GotoLineModeProps {
  query: string;
  onClose: () => void;
}

/**
 * GotoLineModeInline — rendered outside cmdk's CommandList to bypass the
 * built-in filter which uses the raw input value (including ":" prefix).
 */
function GotoLineModeInline({ query, onClose }: GotoLineModeProps) {
  const lineNumber = parseInt(query, 10);
  const isValid = !isNaN(lineNumber) && lineNumber > 0;

  const handleGoto = useCallback(() => {
    if (!isValid) return;
    window.dispatchEvent(
      new CustomEvent('code-editor:goto-line', { detail: { lineNumber } })
    );
    onClose();
  }, [isValid, lineNumber, onClose]);

  return (
    <div className="px-3 py-4">
      <p className="text-sm text-muted-foreground mb-2">
        {query === '' ? (
          'Type a line number to navigate'
        ) : isValid ? (
          <>
            Go to line <span className="font-mono font-medium text-foreground">{lineNumber}</span>
          </>
        ) : (
          <span className="text-destructive">Enter a valid line number</span>
        )}
      </p>
      {isValid && (
        <button
          type="button"
          className="flex items-center gap-2 w-full px-2 py-2 rounded-sm text-sm hover:bg-accent cursor-pointer text-left"
          onClick={handleGoto}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleGoto();
            }
          }}
        >
          <CornerDownLeft className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="text-sm">
            Go to line <span className="font-mono font-medium">{lineNumber}</span>
          </span>
        </button>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export const CommandPalette = observer(function CommandPalette() {
  const uiStore = useUIStore();
  const workspaceStore = useWorkspaceStore();
  const router = useRouter();
  const params = useParams<{ workspaceSlug: string }>();

  // Read open state directly from MobX (component is observer())
  const open = uiStore.commandPaletteOpen;
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResults>({ notes: [], issues: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Mode detection from query prefix
  const mode = detectMode(query);
  const eQuery = effectiveQuery(mode, query);

  // When dialog closes (by cmdk or Escape), sync back to store
  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        uiStore.closeCommandPalette();
        setQuery('');
        setResults({ notes: [], issues: [] });
        setFetchError(null);
      }
    },
    [uiStore]
  );

  const workspaceSlug = params?.workspaceSlug;
  const workspaceId =
    workspaceStore.currentWorkspace?.id ??
    (workspaceSlug ? workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id : undefined) ??
    workspaceStore.currentWorkspaceId;

  // Debounced search — only active in 'search' mode
  useEffect(() => {
    if (!open) return;
    if (mode !== 'search') return;
    if (!workspaceId) return;

    // Clear results when query is empty
    if (!eQuery.trim()) {
      setResults({ notes: [], issues: [] });
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    const timer = setTimeout(async () => {
      try {
        // Pass query to backend for server-side filtering so results are not
        // limited to the first page of items.
        const [notesRes, issuesRes] = await Promise.all([
          notesApi.list(workspaceId, { search: eQuery }, 1, MAX_RESULTS_PER_GROUP),
          issuesApi.list(workspaceId, { search: eQuery }, 1, MAX_RESULTS_PER_GROUP),
        ]);

        setResults({
          notes: notesRes.items.slice(0, MAX_RESULTS_PER_GROUP),
          issues: issuesRes.items.slice(0, MAX_RESULTS_PER_GROUP),
        });
      } catch {
        setFetchError('Search failed. Try again.');
      } finally {
        setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [eQuery, open, workspaceId, mode]);

  // Register Cmd+P as alias for Cmd+K (opens palette)
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const platform =
        (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
          ?.platform ?? navigator.platform;
      const isMac = /mac/i.test(platform);
      const modifier = isMac ? event.metaKey : event.ctrlKey;

      if (modifier && event.key === 'p') {
        const activeTag = document.activeElement?.tagName.toLowerCase();
        const isEditorFocused =
          document.activeElement?.closest('.ProseMirror') !== null ||
          activeTag === 'input' ||
          activeTag === 'textarea';
        if (isEditorFocused) return;

        event.preventDefault();
        uiStore.openCommandPalette();
      }
    }

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [uiStore]);

  const handleSelectNote = useCallback(
    (noteId: string) => {
      if (workspaceSlug) router.push(`/${workspaceSlug}/notes/${noteId}`);
      handleOpenChange(false);
    },
    [router, workspaceSlug, handleOpenChange]
  );

  const handleSelectIssue = useCallback(
    (issueId: string) => {
      if (workspaceSlug) router.push(`/${workspaceSlug}/issues/${issueId}`);
      handleOpenChange(false);
    },
    [router, workspaceSlug, handleOpenChange]
  );

  const hasResults = results.notes.length > 0 || results.issues.length > 0;
  const hasQuery = query.trim().length > 0;

  // Placeholder for default search mode (no query)
  const showDefaultPlaceholder = !hasQuery && mode === 'search';

  return (
    <CommandDialog
      open={open}
      onOpenChange={handleOpenChange}
      title="Command Palette"
      description="Search notes, issues, run commands, or navigate"
      className="max-w-xl"
      showCloseButton={false}
    >
      <CommandInput
        placeholder={
          mode === 'commands' ? 'Search commands...' :
          mode === 'symbols' ? 'Search symbols...' :
          mode === 'goto-line' ? 'Enter line number...' :
          'Search notes and issues...'
        }
        value={query}
        onValueChange={setQuery}
        autoFocus
      />

      {/* ── Modes ── */}

      {/* Commands mode (> prefix)
          Rendered outside CommandList to bypass cmdk's internal filter
          (cmdk filters by raw input value which includes ">") */}
      {mode === 'commands' && (
        <div className="max-h-[400px] overflow-y-auto" role="listbox" aria-label="Commands">
          <CommandsModeInline query={eQuery} onClose={() => handleOpenChange(false)} />
        </div>
      )}

      {/* Symbols mode (# prefix) */}
      {mode === 'symbols' && (
        <SymbolsMode />
      )}

      {/* Go-to-line mode (: prefix) */}
      {mode === 'goto-line' && (
        <div className="max-h-[200px] overflow-y-auto">
          <GotoLineModeInline query={eQuery} onClose={() => handleOpenChange(false)} />
        </div>
      )}

      {/* Default search mode (no prefix) */}
      {mode === 'search' && (
        <>
          <CommandList className={cn('max-h-[400px]', !hasQuery && 'hidden')}>
            {/* Loading state */}
            {isLoading && <ResultSkeleton />}

            {/* Error state */}
            {fetchError && !isLoading && (
              <div role="alert" className="px-3 py-4 text-sm text-destructive text-center">
                {fetchError}
              </div>
            )}

            {/* Empty state */}
            {!isLoading && !fetchError && hasQuery && !hasResults && (
              <CommandEmpty>No results for &ldquo;{query}&rdquo;</CommandEmpty>
            )}

            {/* Notes group */}
            {!isLoading && results.notes.length > 0 && (
              <>
                <CommandGroup heading="Notes">
                  {results.notes.map((note) => (
                    <CommandItem
                      key={note.id}
                      value={`note-${note.id}-${note.title}`}
                      onSelect={() => handleSelectNote(note.id)}
                    >
                      <NoteResultItem note={note} />
                    </CommandItem>
                  ))}
                </CommandGroup>
                {results.issues.length > 0 && <CommandSeparator />}
              </>
            )}

            {/* Issues group */}
            {!isLoading && results.issues.length > 0 && (
              <CommandGroup heading="Issues">
                {results.issues.map((issue) => (
                  <CommandItem
                    key={issue.id}
                    value={`issue-${issue.id}-${issue.identifier}-${issue.name ?? issue.title}`}
                    onSelect={() => handleSelectIssue(issue.id)}
                  >
                    <IssueResultItem issue={issue} />
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>

          {/* Placeholder when no query */}
          {showDefaultPlaceholder && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Search className="h-4 w-4" />
              <span>Start typing to search notes and issues</span>
            </div>
          )}
        </>
      )}

      {/* Mode hint bar — always visible */}
      <ModeHintBar mode={mode} />
    </CommandDialog>
  );
});
