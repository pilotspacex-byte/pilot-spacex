'use client';

import Link from 'next/link';
import { FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NoteIssueLink } from '@/types';

export interface SourceNotesListProps {
  links: NoteIssueLink[];
  workspaceSlug: string;
  className?: string;
}

const linkTypeConfig: Record<NoteIssueLink['linkType'], { label: string; className: string }> = {
  EXTRACTED: {
    label: 'Extracted',
    className: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  },
  CREATED: {
    label: 'Created',
    className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
  },
  REFERENCED: {
    label: 'Referenced',
    className: 'bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-300',
  },
};

/**
 * SourceNotesList displays notes linked to an issue with navigation.
 * Shows note title, link type badge, and navigates to the note editor.
 *
 * @example
 * ```tsx
 * <SourceNotesList links={noteLinks} workspaceSlug="my-team" />
 * ```
 */
export function SourceNotesList({ links, workspaceSlug, className }: SourceNotesListProps) {
  if (links.length === 0) {
    return (
      <div className={cn('flex flex-col items-center gap-2 py-6 text-center', className)}>
        <FileText className="size-8 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No linked notes</p>
      </div>
    );
  }

  return (
    <ul className={cn('space-y-1', className)} role="list" aria-label="Linked notes">
      {links.map((link) => {
        const config = linkTypeConfig[link.linkType];

        return (
          <li key={link.id}>
            <Link
              href={`/${workspaceSlug}/notes/${link.noteId}`}
              className={cn(
                'group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                'hover:bg-accent',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
            >
              <FileText className="size-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{link.noteTitle}</span>
              <span
                className={cn(
                  'ml-auto shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                  config.className
                )}
              >
                {config.label}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export default SourceNotesList;
