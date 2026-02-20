'use client';

/**
 * BacklinksPanel — Sidebar panel showing notes that link to the current note (FR-003).
 *
 * Displays incoming note references with title.
 * Uses TanStack Query for data fetching. Mounted in NoteCanvasLayout
 * as the content for activePanel="backlinks".
 *
 * @see specs/018-note-editor-enhancements/spec.md FR-003
 * @see tmp/note-editor-plan.md Section 1f
 */
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { FileText, Link2, Loader2 } from 'lucide-react';
import { notesApi } from '@/services/api/notes';
import type { NoteBacklink } from '@/types';
import { cn } from '@/lib/utils';

export interface BacklinksPanelProps {
  workspaceId: string;
  noteId: string;
}

export function BacklinksPanel({ workspaceId, noteId }: BacklinksPanelProps) {
  const router = useRouter();
  const params = useParams<{ workspaceSlug: string }>();
  const workspaceSlug = params.workspaceSlug ?? '';

  const {
    data: backlinks,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['note-backlinks', workspaceId, noteId],
    queryFn: () => notesApi.getNoteBacklinks(workspaceId, noteId),
    staleTime: 30 * 1000,
    enabled: !!workspaceId && !!noteId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        <span className="text-sm">Loading backlinks...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-8 text-center text-sm text-destructive">
        Failed to load backlinks.
      </div>
    );
  }

  if (!backlinks || backlinks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
        <Link2 className="h-8 w-8 opacity-40" />
        <p className="text-sm">No notes link to this note yet.</p>
        <p className="text-xs opacity-60">
          Use <code className="px-1 py-0.5 rounded bg-muted">[[</code> in other notes to create
          links.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col" role="list" aria-label="Backlinks">
      <p className="px-4 py-2 text-xs text-muted-foreground font-medium">
        {backlinks.length} incoming {backlinks.length === 1 ? 'link' : 'links'}
      </p>
      {(backlinks as NoteBacklink[]).map((link) => (
        <div key={link.id} role="listitem">
          <button
            className={cn(
              'flex items-center gap-3 px-4 py-2.5 w-full text-left',
              'hover:bg-accent/50 transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-inset'
            )}
            onClick={() => {
              if (workspaceSlug && link.sourceNoteId) {
                router.push(`/${workspaceSlug}/notes/${link.sourceNoteId}`);
              }
            }}
          >
            <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">
                {link.sourceNoteTitle || 'Untitled'}
              </div>
              <div className="text-xs text-muted-foreground">
                {link.linkType === 'embed' ? 'Embedded' : 'Inline link'}
              </div>
            </div>
          </button>
        </div>
      ))}
    </div>
  );
}

export default BacklinksPanel;
