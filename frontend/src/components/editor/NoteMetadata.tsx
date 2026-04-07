'use client';

/**
 * NoteMetadata - Compact metadata bar showing linked issues for a note.
 * Renders between InlineNoteHeader and the scrollable editor area.
 *
 * Project context (name, progress) is now rendered by ProjectContextHeader
 * when the note belongs to a project. This component handles linked issues only.
 *
 * - Linked issues: clickable badges with state color dots (max 5 visible)
 */
import type React from 'react';
import Link from 'next/link';
import { Link2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { LinkedIssueBrief } from '@/types';

/** Maximum number of linked issue badges shown before "+N more" */
const MAX_VISIBLE_ISSUES = 5;

export interface NoteMetadataProps {
  /** Issues linked to this note */
  linkedIssues: LinkedIssueBrief[];
  /** Workspace slug for building internal links */
  workspaceSlug: string;
  /** Additional CSS classes */
  className?: string;
}

export function NoteMetadata({ linkedIssues, workspaceSlug, className }: NoteMetadataProps) {
  if (linkedIssues.length === 0) return null;

  return (
    <div
      data-testid="note-metadata"
      className={cn(
        'flex flex-wrap items-center gap-2 px-4 py-1.5 text-xs text-muted-foreground',
        'border-b border-border/30 bg-background-subtle/50',
        className
      )}
    >
      {/* Linked issues */}
      <div className="flex items-center gap-1.5" data-testid="note-metadata-issues">
        <Link2 className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
        <div className="flex flex-wrap items-center gap-1">
          {linkedIssues.slice(0, MAX_VISIBLE_ISSUES).map((issue) => (
            <Tooltip key={issue.id}>
              <TooltipTrigger asChild>
                <Link
                  href={`/${workspaceSlug}/issues/${issue.id}`}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium hover:bg-accent/50 transition-colors"
                  data-testid={`note-metadata-issue-${issue.identifier}`}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full flex-shrink-0 bg-[var(--state-color)]"
                    style={{ '--state-color': issue.state.color } as React.CSSProperties}
                    aria-hidden="true"
                  />
                  {issue.identifier}
                </Link>
              </TooltipTrigger>
              <TooltipContent>
                <div className="max-w-[200px]">
                  <div className="font-medium">
                    {issue.identifier}: {issue.name}
                  </div>
                  <div className="text-muted-foreground">{issue.state.name}</div>
                </div>
              </TooltipContent>
            </Tooltip>
          ))}
          {linkedIssues.length > MAX_VISIBLE_ISSUES && (
            <span className="text-xs text-muted-foreground" data-testid="note-metadata-more">
              +{linkedIssues.length - MAX_VISIBLE_ISSUES} more
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
