'use client';

/**
 * CommandPaletteModal — Global Cmd+K search command palette.
 *
 * T-019 (FR-024): Provides instant navigation to notes and issues.
 *
 * Features:
 * - Cmd+K (Mac) / Ctrl+K (Win/Linux) keyboard shortcut
 * - Searches notes by title and issues by identifier/title
 * - Client-side search over cached data (fast, no extra requests)
 * - Navigates to selected result
 * - Renders in AppShell so it's always available
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter, useParams } from 'next/navigation';
import { FileText, CircleDot, Search } from 'lucide-react';

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { useUIStore, useNoteStore, useWorkspaceStore } from '@/stores';
import { useStore } from '@/stores';

/**
 * CommandPaletteModal
 *
 * Mounted globally in AppShell. Listens for Cmd+K to open.
 * Searches across notes (title) and issues (identifier + title) from
 * in-memory store caches — no extra API calls needed.
 */
export const CommandPaletteModal = observer(function CommandPaletteModal() {
  const uiStore = useUIStore();
  const noteStore = useNoteStore();
  const workspaceStore = useWorkspaceStore();
  const { issueStore } = useStore();
  const router = useRouter();
  const params = useParams();

  const [query, setQuery] = useState('');

  const workspaceSlug =
    (params?.workspaceSlug as string | undefined) ??
    workspaceStore.currentWorkspace?.slug ??
    '';

  // Register Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;
      if (meta && e.key === 'k') {
        e.preventDefault();
        uiStore.toggleCommandPalette();
      }
      if (e.key === 'Escape' && uiStore.commandPaletteOpen) {
        uiStore.closeCommandPalette();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [uiStore]);

  // Clear query on close
  useEffect(() => {
    if (!uiStore.commandPaletteOpen) {
      setQuery('');
    }
  }, [uiStore.commandPaletteOpen]);

  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (open) {
        uiStore.openCommandPalette();
      } else {
        uiStore.closeCommandPalette();
      }
    },
    [uiStore]
  );

  // Filter notes by title
  const filteredNotes = useMemo(() => {
    const q = query.toLowerCase().trim();
    const notes = noteStore.notesList;
    if (!q) return notes.slice(0, 5);
    return notes
      .filter(
        (n) =>
          n.title.toLowerCase().includes(q)
      )
      .slice(0, 8);
  }, [query, noteStore.notesList]);

  // Filter issues by identifier or title
  const filteredIssues = useMemo(() => {
    const q = query.toLowerCase().trim();
    const issues = issueStore.issuesList;
    if (!q) return issues.slice(0, 5);
    return issues
      .filter(
        (i) =>
          (i.identifier ?? '').toLowerCase().includes(q) ||
          i.name.toLowerCase().includes(q)
      )
      .slice(0, 8);
  }, [query, issueStore.issuesList]);

  const handleSelectNote = useCallback(
    (noteId: string) => {
      uiStore.closeCommandPalette();
      router.push(`/${workspaceSlug}/notes/${noteId}`);
    },
    [router, workspaceSlug, uiStore]
  );

  const handleSelectIssue = useCallback(
    (issueId: string) => {
      uiStore.closeCommandPalette();
      router.push(`/${workspaceSlug}/issues/${issueId}`);
    },
    [router, workspaceSlug, uiStore]
  );

  const hasResults = filteredNotes.length > 0 || filteredIssues.length > 0;

  return (
    <CommandDialog
      open={uiStore.commandPaletteOpen}
      onOpenChange={handleOpenChange}
      title="Search"
      description="Search notes and issues"
    >
      <CommandInput
        placeholder="Search notes, issues…"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        {!hasResults && (
          <CommandEmpty>
            <div className="flex flex-col items-center gap-2 py-6 text-muted-foreground">
              <Search className="h-8 w-8 opacity-40" />
              <p className="text-sm">No results for &ldquo;{query}&rdquo;</p>
            </div>
          </CommandEmpty>
        )}

        {filteredNotes.length > 0 && (
          <CommandGroup heading="Notes">
            {filteredNotes.map((note) => (
              <CommandItem
                key={note.id}
                value={`note-${note.id}-${note.title}`}
                onSelect={() => handleSelectNote(note.id)}
                className="flex items-center gap-2"
              >
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{note.title || 'Untitled'}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {filteredNotes.length > 0 && filteredIssues.length > 0 && <CommandSeparator />}

        {filteredIssues.length > 0 && (
          <CommandGroup heading="Issues">
            {filteredIssues.map((issue) => (
              <CommandItem
                key={issue.id}
                value={`issue-${issue.id}-${issue.identifier ?? ''}-${issue.name}`}
                onSelect={() => handleSelectIssue(issue.id)}
                className="flex items-center gap-2"
              >
                <CircleDot className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="shrink-0 text-xs font-mono text-muted-foreground">
                  {issue.identifier}
                </span>
                <span className="truncate">{issue.name}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
});

export default CommandPaletteModal;
