'use client';

import Link from 'next/link';
import { Clock, FileText, ChevronRight } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { useNotes } from '@/features/notes/hooks/useNotes';
import type { Project } from '@/types';

interface ProjectNotesPanelProps {
  project: Project;
  workspaceSlug: string;
  workspaceId: string;
}

export function ProjectNotesPanel({ project, workspaceSlug, workspaceId }: ProjectNotesPanelProps) {
  const {
    data: recentData,
    isLoading,
    isError,
  } = useNotes({
    workspaceId,
    projectIds: [project.id],
    isPinned: false,
    pageSize: 5,
    enabled: !!workspaceId,
  });

  const recentNotes = recentData?.items ?? [];
  const recentTotal = recentData?.total ?? 0;
  const isEmpty = !isLoading && !isError && recentNotes.length === 0;

  return (
    <div className="px-2 py-2">
      {/* Section header with inline "View all" when notes overflow */}
      <div className="mb-1 flex items-center justify-between px-1.5">
        <div className="flex items-center gap-1.5">
          <Clock className="h-2.5 w-2.5 text-muted-foreground" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Recent
          </span>
        </div>
        {recentTotal > 5 && (
          <Link
            href={`/${workspaceSlug}/notes?projectId=${project.id}`}
            className="flex items-center gap-0.5 text-[10px] text-muted-foreground hover:text-sidebar-foreground transition-colors"
            data-testid="project-notes-view-all-recent"
          >
            View all <ChevronRight className="h-3 w-3" />
          </Link>
        )}
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
      {isEmpty && <p className="px-3 py-2 text-xs text-muted-foreground">No notes yet</p>}

      {/* Recent sub-section */}
      {!isLoading && !isError && recentNotes.length > 0 && (
        <div data-testid="project-recent-notes">
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
        </div>
      )}
    </div>
  );
}
