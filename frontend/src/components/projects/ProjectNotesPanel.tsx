'use client';

import { useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Pin, Clock, FileText, Plus, ChevronRight, Loader2 } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { useNotes } from '@/features/notes/hooks/useNotes';
import { useCreateNote } from '@/features/notes/hooks/useCreateNote';
import { useWorkspaceStore } from '@/stores/RootStore';
import type { Project } from '@/types';

interface ProjectNotesPanelProps {
  project: Project;
  workspaceSlug: string;
  workspaceId: string;
}

export function ProjectNotesPanel({ project, workspaceSlug, workspaceId }: ProjectNotesPanelProps) {
  const router = useRouter();
  const workspaceStore = useWorkspaceStore();
  const canCreateContent = workspaceStore.currentUserRole !== 'guest';

  const {
    data: pinnedData,
    isLoading: pinnedLoading,
    isError: pinnedError,
  } = useNotes({
    workspaceId,
    projectId: project.id,
    isPinned: true,
    pageSize: 5,
    enabled: !!workspaceId,
  });

  const {
    data: recentData,
    isLoading: recentLoading,
    isError: recentError,
  } = useNotes({
    workspaceId,
    projectId: project.id,
    isPinned: false,
    pageSize: 5,
    enabled: !!workspaceId,
  });

  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  const handleCreateNote = useCallback(() => {
    createNote.mutate({ title: 'Untitled', projectId: project.id });
  }, [createNote, project.id]);

  const isLoading = pinnedLoading || recentLoading;
  const isError = pinnedError || recentError;

  const pinnedNotes = pinnedData?.items ?? [];
  const pinnedTotal = pinnedData?.total ?? 0;
  const recentNotes = recentData?.items ?? [];
  const recentTotal = recentData?.total ?? 0;
  const isEmpty = !isLoading && !isError && pinnedNotes.length === 0 && recentNotes.length === 0;

  return (
    <div className="px-2 py-2">
      {/* Section header */}
      <div className="mb-1.5 flex items-center gap-1.5 px-1.5">
        <FileText className="h-2.5 w-2.5 text-muted-foreground" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Notes
        </span>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="px-1.5 py-1.5 space-y-1">
          <Skeleton className="h-4 w-full rounded" />
          <Skeleton className="h-4 w-full rounded" />
          <Skeleton className="h-4 w-full rounded" />
        </div>
      )}

      {/* Error state */}
      {!isLoading && isError && (
        <p className="px-3 py-2 text-xs text-muted-foreground">Failed to load notes</p>
      )}

      {/* Empty state */}
      {isEmpty && (
        <p className="px-3 py-2 text-xs text-muted-foreground">No notes yet</p>
      )}

      {/* Pinned sub-section */}
      {!isLoading && !isError && pinnedNotes.length > 0 && (
        <div className="mb-2" data-testid="project-pinned-notes">
          <div className="mb-1 flex items-center gap-1.5 px-1.5">
            <Pin className="h-2.5 w-2.5 text-muted-foreground" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Pinned
            </span>
          </div>
          <div className="space-y-px">
            {pinnedNotes.map((note) => (
              <Link
                key={note.id}
                href={`/${workspaceSlug}/notes/${note.id}`}
                data-testid="project-note-item"
                className="group flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-sidebar-foreground transition-colors hover:bg-sidebar-accent/50"
              >
                <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                <span className="truncate">{note.title}</span>
              </Link>
            ))}
          </div>
          {pinnedTotal > 5 && (
            <Link
              href={`/${workspaceSlug}/notes`}
              className="flex items-center gap-1 px-1.5 py-1 text-[10px] text-muted-foreground hover:text-sidebar-foreground transition-colors"
              data-testid="project-notes-view-all-pinned"
            >
              View all <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      )}

      {/* Recent sub-section */}
      {!isLoading && !isError && recentNotes.length > 0 && (
        <div data-testid="project-recent-notes">
          <div className="mb-1 flex items-center gap-1.5 px-1.5">
            <Clock className="h-2.5 w-2.5 text-muted-foreground" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Recent
            </span>
          </div>
          <div className="space-y-px">
            {recentNotes.map((note) => (
              <Link
                key={note.id}
                href={`/${workspaceSlug}/notes/${note.id}`}
                data-testid="project-note-item"
                className="group flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              >
                <FileText className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">{note.title}</span>
              </Link>
            ))}
          </div>
          {recentTotal > 5 && (
            <Link
              href={`/${workspaceSlug}/notes`}
              className="flex items-center gap-1 px-1.5 py-1 text-[10px] text-muted-foreground hover:text-sidebar-foreground transition-colors"
              data-testid="project-notes-view-all-recent"
            >
              View all <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      )}

      {/* New Note button — hidden for guests */}
      {canCreateContent && (
        <Button
          variant="ghost"
          size="sm"
          className="mt-1 w-full justify-start gap-1.5 px-2 text-xs text-muted-foreground hover:text-sidebar-foreground"
          onClick={handleCreateNote}
          disabled={createNote.isPending}
          data-testid="project-new-note-button"
        >
          {createNote.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Plus className="h-3 w-3" />
          )}
          New Note
        </Button>
      )}
    </div>
  );
}
