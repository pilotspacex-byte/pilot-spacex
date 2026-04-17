'use client';

/**
 * CommandPalette - Global Cmd+K / Cmd+P search modal (v3)
 *
 * Opens via uiStore.commandPaletteOpen. Keyboard-navigable with cmdk.
 *
 * Mode prefixes (v3):
 *   #  Issues mode    — search issues (title, identifier, state)
 *   @  People mode    — search workspace members (name, email)
 *   /  Pages mode     — search notes/pages (title)
 *   >  Commands mode  — editor/UI command list
 *   :  Go-to-line     — jump to a line number in the active editor (demoted)
 *   (no prefix)       — unified search across notes + issues
 *
 * Cmd+P opens palette (alias for Cmd+K — identical behavior).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  FileText,
  Ticket,
  Search,
  Terminal,
  CornerDownLeft,
  User as UserIcon,
} from 'lucide-react';

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
import type { WorkspaceMember } from '@/types/workspace';

const MAX_RESULTS_PER_GROUP = 5;
const DEBOUNCE_MS = 250;
const PREFIX_CHARS = ['#', '@', '/', '>', ':'] as const;

// ─── Palette modes ───────────────────────────────────────────────────────────

type PaletteMode =
  | 'search'
  | 'issues'
  | 'people'
  | 'pages'
  | 'commands'
  | 'goto-line';

function detectMode(query: string): PaletteMode {
  if (query.startsWith('#')) return 'issues';
  if (query.startsWith('@')) return 'people';
  if (query.startsWith('/')) return 'pages';
  if (query.startsWith('>')) return 'commands';
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
      <span className="truncate text-sm font-medium flex-1">
        {note.title || 'Untitled'}
      </span>
      {note.projectId && (
        <Badge variant="secondary" className="text-xs shrink-0 font-normal">
          Project
        </Badge>
      )}
    </div>
  );
}

function IssueResultItem({ issue }: { issue: Issue }) {
  const stateName = issue.state?.name ?? '';
  const stateColor = issue.state?.color;

  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <Ticket className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="font-mono text-xs text-muted-foreground shrink-0">
        {issue.identifier}
      </span>
      <span className="truncate text-sm font-medium flex-1">
        {issue.name ?? issue.title}
      </span>
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

function MemberResultItem({ member }: { member: WorkspaceMember }) {
  const name = member.user?.name ?? 'Unknown';
  const email = member.user?.email ?? '';
  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <UserIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="truncate text-sm font-medium flex-1">{name}</span>
      {email && (
        <span className="truncate text-xs text-muted-foreground shrink-0 max-w-[180px]">
          {email}
        </span>
      )}
      {member.role && (
        <Badge variant="secondary" className="text-xs shrink-0 font-normal capitalize">
          {member.role}
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

// ─── Prefix legend footer ─────────────────────────────────────────────────────

interface PrefixChip {
  prefix: string;
  label: string;
}

const PREFIX_CHIPS: readonly PrefixChip[] = [
  { prefix: '#', label: 'issues' },
  { prefix: '@', label: 'people' },
  { prefix: '/', label: 'pages' },
  { prefix: '>', label: 'commands' },
];

function PrefixLegend({
  currentMode,
  onPick,
}: {
  currentMode: PaletteMode;
  onPick: (prefix: string) => void;
}) {
  const activeByMode: Record<PaletteMode, string | null> = {
    issues: '#',
    people: '@',
    pages: '/',
    commands: '>',
    'goto-line': ':',
    search: null,
  };
  const activePrefix = activeByMode[currentMode];

  return (
    <div className="flex items-center gap-1 px-2 py-1.5 border-t text-[11px] text-muted-foreground bg-muted/30">
      {PREFIX_CHIPS.map((chip, idx) => {
        const isActive = chip.prefix === activePrefix;
        return (
          <span key={chip.prefix} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onPick(chip.prefix)}
              className={cn(
                'inline-flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors',
                'hover:bg-accent hover:text-accent-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isActive && 'bg-accent text-accent-foreground font-medium'
              )}
              aria-label={`Switch to ${chip.label} mode`}
              aria-pressed={isActive}
            >
              <kbd className="font-mono text-[11px]">{chip.prefix}</kbd>
              <span>{chip.label}</span>
            </button>
            {idx < PREFIX_CHIPS.length - 1 && (
              <span aria-hidden="true" className="text-muted-foreground/60">
                ·
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}

// ─── Commands mode ────────────────────────────────────────────────────────────

/**
 * useCommands — returns the built-in command list for the commands mode.
 */
function useCommands(onClose: () => void): Command[] {
  return useMemo<Command[]>(
    () => [
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
    ],
    [onClose]
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
  const [issueResults, setIssueResults] = useState<Issue[]>([]);
  const [pageResults, setPageResults] = useState<Note[]>([]);
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
        setIssueResults([]);
        setPageResults([]);
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

  // Members: prefer store-loaded list; fall back to fetching on open
  const rawMembers = workspaceStore.currentMembers;
  const allMembers = useMemo<WorkspaceMember[]>(() => rawMembers ?? [], [rawMembers]);
  useEffect(() => {
    if (!open || !workspaceId) return;
    if (allMembers.length > 0) return;
    // Guard: `fetchMembers` may be absent in test mocks
    if (typeof workspaceStore.fetchMembers === 'function') {
      void workspaceStore.fetchMembers(workspaceId);
    }
  }, [open, workspaceId, allMembers, workspaceStore]);

  // Debounced search — unified 'search' mode (notes + issues)
  useEffect(() => {
    if (!open) return;
    if (mode !== 'search') return;
    if (!workspaceId) return;

    if (!eQuery.trim()) {
      setResults({ notes: [], issues: [] });
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    let cancelled = false;

    const timer = setTimeout(async () => {
      try {
        const [notesRes, issuesRes] = await Promise.all([
          notesApi.list(workspaceId, { search: eQuery }, 1, MAX_RESULTS_PER_GROUP),
          issuesApi.list(workspaceId, { search: eQuery }, 1, MAX_RESULTS_PER_GROUP),
        ]);
        if (cancelled) return;

        setResults({
          notes: notesRes.items.slice(0, MAX_RESULTS_PER_GROUP),
          issues: issuesRes.items.slice(0, MAX_RESULTS_PER_GROUP),
        });
      } catch {
        if (cancelled) return;
        setFetchError('Search failed. Try again.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [eQuery, open, workspaceId, mode]);

  // Debounced search — 'issues' mode (# prefix)
  useEffect(() => {
    if (!open) return;
    if (mode !== 'issues') return;
    if (!workspaceId) return;

    setIsLoading(true);
    setFetchError(null);
    let cancelled = false;

    const timer = setTimeout(async () => {
      try {
        const res = await issuesApi.list(
          workspaceId,
          eQuery.trim() ? { search: eQuery } : {},
          1,
          MAX_RESULTS_PER_GROUP
        );
        if (cancelled) return;
        setIssueResults(res.items.slice(0, MAX_RESULTS_PER_GROUP));
      } catch {
        if (cancelled) return;
        setFetchError('Issue search failed. Try again.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [eQuery, open, workspaceId, mode]);

  // Debounced search — 'pages' mode (/ prefix)
  useEffect(() => {
    if (!open) return;
    if (mode !== 'pages') return;
    if (!workspaceId) return;

    setIsLoading(true);
    setFetchError(null);
    let cancelled = false;

    const timer = setTimeout(async () => {
      try {
        const res = await notesApi.list(
          workspaceId,
          eQuery.trim() ? { search: eQuery } : {},
          1,
          MAX_RESULTS_PER_GROUP
        );
        if (cancelled) return;
        setPageResults(res.items.slice(0, MAX_RESULTS_PER_GROUP));
      } catch {
        if (cancelled) return;
        setFetchError('Page search failed. Try again.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [eQuery, open, workspaceId, mode]);

  // Clear per-mode results & error when switching modes to prevent stale UI
  useEffect(() => {
    setFetchError(null);
    setIsLoading(false);
    if (mode !== 'issues') setIssueResults([]);
    if (mode !== 'pages') setPageResults([]);
    if (mode !== 'search') setResults({ notes: [], issues: [] });
  }, [mode]);

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

  const handleSelectMember = useCallback(
    (member: WorkspaceMember) => {
      if (!workspaceSlug) {
        handleOpenChange(false);
        return;
      }
      if (member.userId) {
        router.push(`/${workspaceSlug}/members/${member.userId}`);
      } else {
        const name = member.user?.name ?? '';
        router.push(`/${workspaceSlug}/members?q=${encodeURIComponent(name)}`);
      }
      handleOpenChange(false);
    },
    [router, workspaceSlug, handleOpenChange]
  );

  // Prefix legend: prepend prefix, preserving any existing non-prefix input
  const handlePickPrefix = useCallback((prefix: string) => {
    setQuery((prev) => {
      const firstChar = prev.charAt(0);
      const rest = PREFIX_CHARS.includes(firstChar as (typeof PREFIX_CHARS)[number])
        ? prev.slice(1)
        : prev;
      return `${prefix}${rest}`;
    });
  }, []);

  // Commands mode state
  const onCloseCb = useCallback(() => handleOpenChange(false), [handleOpenChange]);
  const commands = useCommands(onCloseCb);
  const filteredCommands = eQuery
    ? commands.filter((c) => c.label.toLowerCase().includes(eQuery.toLowerCase()))
    : commands;

  // Go-to-line mode state
  const parsedLine = parseInt(eQuery, 10);
  const gotoLineNumber = !isNaN(parsedLine) && parsedLine > 0 ? parsedLine : null;

  // People mode: client-side filter against loaded members
  const filteredMembers = useMemo(() => {
    if (!allMembers) return [];
    const q = eQuery.trim().toLowerCase();
    const pool = q
      ? allMembers.filter((m) => {
          const name = (m.user?.name ?? '').toLowerCase();
          const email = (m.user?.email ?? '').toLowerCase();
          return name.includes(q) || email.includes(q);
        })
      : allMembers;
    return pool.slice(0, MAX_RESULTS_PER_GROUP);
  }, [allMembers, eQuery]);

  const hasSearchResults = results.notes.length > 0 || results.issues.length > 0;
  const hasQuery = query.trim().length > 0;
  const showDefaultPlaceholder = !hasQuery && mode === 'search';

  return (
    <CommandDialog
      open={open}
      onOpenChange={handleOpenChange}
      title="Command Palette"
      description="Search issues, people, pages, or run commands"
      className="max-w-xl"
      showCloseButton={false}
      // We handle filtering ourselves (per-mode prefix parsing, debounced API calls).
      // cmdk's built-in filter would hide items whose `value` lacks the raw query (e.g. ">").
      shouldFilter={false}
    >
      <CommandInput
        placeholder={
          mode === 'issues'
            ? 'Search issues...'
            : mode === 'people'
              ? 'Search people...'
              : mode === 'pages'
                ? 'Search pages...'
                : mode === 'commands'
                  ? 'Search commands...'
                  : mode === 'goto-line'
                    ? 'Enter line number...'
                    : 'Search notes and issues...'
        }
        value={query}
        onValueChange={setQuery}
        autoFocus
      />

      {/* ── Modes ── */}

      {/* Issues mode (# prefix) */}
      {mode === 'issues' && (
        <CommandList className="max-h-[400px]">
          {isLoading && <ResultSkeleton />}
          {fetchError && !isLoading && (
            <div role="alert" className="px-3 py-4 text-sm text-destructive text-center">
              {fetchError}
            </div>
          )}
          {!isLoading && !fetchError && issueResults.length === 0 && (
            <CommandEmpty>
              {eQuery ? `No issues for “${eQuery}”` : 'Type to search issues'}
            </CommandEmpty>
          )}
          {!isLoading && !fetchError && issueResults.length > 0 && (
            <CommandGroup heading="Issues">
              {issueResults.map((issue) => (
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
      )}

      {/* People mode (@ prefix) */}
      {mode === 'people' && (
        <CommandList className="max-h-[400px]">
          {(!allMembers || allMembers.length === 0) && (
            <ResultSkeleton />
          )}
          {allMembers && allMembers.length > 0 && filteredMembers.length === 0 && (
            <CommandEmpty>
              {eQuery ? `No people for “${eQuery}”` : 'Type a name or email'}
            </CommandEmpty>
          )}
          {filteredMembers.length > 0 && (
            <CommandGroup heading="People">
              {filteredMembers.map((member) => (
                <CommandItem
                  key={member.userId || member.id}
                  value={`member-${member.userId}-${member.user?.name ?? ''}-${member.user?.email ?? ''}`}
                  onSelect={() => handleSelectMember(member)}
                >
                  <MemberResultItem member={member} />
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      )}

      {/* Pages mode (/ prefix) */}
      {mode === 'pages' && (
        <CommandList className="max-h-[400px]">
          {isLoading && <ResultSkeleton />}
          {fetchError && !isLoading && (
            <div role="alert" className="px-3 py-4 text-sm text-destructive text-center">
              {fetchError}
            </div>
          )}
          {!isLoading && !fetchError && pageResults.length === 0 && (
            <CommandEmpty>
              {eQuery ? `No pages for “${eQuery}”` : 'Type to search pages'}
            </CommandEmpty>
          )}
          {!isLoading && !fetchError && pageResults.length > 0 && (
            <CommandGroup heading="Pages">
              {pageResults.map((note) => (
                <CommandItem
                  key={note.id}
                  value={`page-${note.id}-${note.title}`}
                  onSelect={() => handleSelectNote(note.id)}
                >
                  <NoteResultItem note={note} />
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      )}

      {/* Commands mode (> prefix) */}
      {mode === 'commands' && (
        <CommandList className="max-h-[400px]">
          {filteredCommands.length === 0 ? (
            <CommandEmpty>No commands match &ldquo;{eQuery}&rdquo;</CommandEmpty>
          ) : (
            <CommandGroup heading="Commands">
              {filteredCommands.map((cmd) => (
                <CommandItem key={cmd.id} value={cmd.label} onSelect={cmd.action}>
                  <Terminal className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1">{cmd.label}</span>
                  {cmd.description && (
                    <span className="text-xs text-muted-foreground font-mono shrink-0">
                      {cmd.description}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      )}

      {/* Go-to-line mode (: prefix) */}
      {mode === 'goto-line' && (
        <CommandList className="max-h-[200px]">
          {gotoLineNumber === null ? (
            <CommandEmpty>
              {eQuery === '' ? 'Type a line number to navigate' : 'Enter a valid line number'}
            </CommandEmpty>
          ) : (
            <CommandGroup heading="Go to Line">
              <CommandItem
                value={`goto-line-${gotoLineNumber}`}
                onSelect={() => {
                  window.dispatchEvent(
                    new CustomEvent('code-editor:goto-line', {
                      detail: { lineNumber: gotoLineNumber },
                    })
                  );
                  handleOpenChange(false);
                }}
              >
                <CornerDownLeft className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="text-sm">
                  Go to line <span className="font-mono font-medium">{gotoLineNumber}</span>
                </span>
              </CommandItem>
            </CommandGroup>
          )}
        </CommandList>
      )}

      {/* Default unified search mode (no prefix) */}
      {mode === 'search' && (
        <>
          <CommandList className={cn('max-h-[400px]', !hasQuery && 'hidden')}>
            {isLoading && <ResultSkeleton />}

            {fetchError && !isLoading && (
              <div role="alert" className="px-3 py-4 text-sm text-destructive text-center">
                {fetchError}
              </div>
            )}

            {!isLoading && !fetchError && hasQuery && !hasSearchResults && (
              <CommandEmpty>No results for &ldquo;{query}&rdquo;</CommandEmpty>
            )}

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

          {showDefaultPlaceholder && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Search className="h-4 w-4" />
              <span>Start typing, or use # @ / &gt; to scope your search</span>
            </div>
          )}
        </>
      )}

      {/* Prefix legend footer — always visible, clickable chips */}
      <PrefixLegend currentMode={mode} onPick={handlePickPrefix} />
    </CommandDialog>
  );
});
