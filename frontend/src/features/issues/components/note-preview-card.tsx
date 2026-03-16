'use client';

import { useRouter } from 'next/navigation';
import { FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NoteLinkType } from '@/types';

interface NotePreviewCardProps {
  noteId: string;
  noteTitle: string;
  linkType: NoteLinkType;
  workspaceSlug: string;
}

const LINK_TYPE_BADGE: Record<NotePreviewCardProps['linkType'], string> = {
  extracted: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  referenced: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
  related: 'bg-slate-100 text-slate-700 dark:bg-slate-800/30 dark:text-slate-400',
  inline: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
};

export function NotePreviewCard({
  noteId,
  noteTitle,
  linkType,
  workspaceSlug,
}: NotePreviewCardProps) {
  const router = useRouter();

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/${workspaceSlug}/notes/${noteId}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          router.push(`/${workspaceSlug}/notes/${noteId}`);
        }
      }}
      className={cn(
        'border border-border rounded-lg p-2.5 flex items-center gap-2',
        'hover:bg-muted/50 cursor-pointer transition-colors'
      )}
    >
      <FileText className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
      <span className="flex-1 text-sm truncate">{noteTitle}</span>
      <span
        className={cn(
          'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
          LINK_TYPE_BADGE[linkType]
        )}
      >
        {linkType.charAt(0).toUpperCase() + linkType.slice(1)}
      </span>
    </div>
  );
}
