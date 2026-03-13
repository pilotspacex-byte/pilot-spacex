'use client';

/**
 * PersonalPagesList - Flat list of personal pages for sidebar Notes section.
 *
 * Renders notes without a projectId (personal/user-owned pages) as clickable
 * links with active page highlighting.
 */

import { observer } from 'mobx-react-lite';
import { FileText } from 'lucide-react';
import Link from 'next/link';

import { cn } from '@/lib/utils';
import { usePersonalPages } from '@/features/notes/hooks/usePersonalPages';

interface PersonalPagesListProps {
  workspaceId: string;
  workspaceSlug: string;
  currentNoteId?: string;
}

export const PersonalPagesList = observer(function PersonalPagesList({
  workspaceId,
  workspaceSlug,
  currentNoteId,
}: PersonalPagesListProps) {
  const { data: pages = [] } = usePersonalPages(workspaceId);

  if (pages.length === 0) {
    return <div className="px-3 py-1 text-xs text-muted-foreground/60">No personal pages</div>;
  }

  return (
    <div className="space-y-px">
      {pages.map((note) => {
        const isActive = note.id === currentNoteId;
        return (
          <Link
            key={note.id}
            href={`/${workspaceSlug}/notes/${note.id}`}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs transition-colors',
              isActive
                ? 'bg-sidebar-accent text-sidebar-foreground font-medium'
                : 'text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
            )}
          >
            <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
            <span className="truncate">{note.title || 'Untitled'}</span>
          </Link>
        );
      })}
    </div>
  );
});
