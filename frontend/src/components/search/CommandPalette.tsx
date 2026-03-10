'use client';

/**
 * CommandPalette - Global Cmd+K search modal (T-019)
 *
 * Opens via uiStore.commandPaletteOpen. Searches notes and issues
 * with a 5-result cap per group via server-side search query.
 * Keyboard-navigable with cmdk.
 */

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { FileText, Ticket, Search } from 'lucide-react';

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

interface SearchResults {
  notes: Note[];
  issues: Issue[];
}

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

  // Debounced search
  useEffect(() => {
    if (!open) return;
    if (!workspaceId) return;

    // Clear results when query is empty
    if (!query.trim()) {
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
          notesApi.list(workspaceId, { search: query }, 1, MAX_RESULTS_PER_GROUP),
          issuesApi.list(workspaceId, { search: query }, 1, MAX_RESULTS_PER_GROUP),
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
  }, [query, open, workspaceId]);

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

  return (
    <CommandDialog
      open={open}
      onOpenChange={handleOpenChange}
      title="Search"
      description="Search notes and issues across your workspace"
      className="max-w-xl"
      showCloseButton={false}
    >
      <CommandInput
        placeholder="Search notes and issues..."
        value={query}
        onValueChange={setQuery}
        autoFocus
      />

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
      {!hasQuery && (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
          <Search className="h-4 w-4" />
          <span>Start typing to search notes and issues</span>
        </div>
      )}
    </CommandDialog>
  );
});
