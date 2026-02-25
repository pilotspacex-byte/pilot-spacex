'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { NotePreviewCard } from '@/features/issues/components/note-preview-card';
import { IssueReferenceCard } from '@/features/issues/components/issue-reference-card';

// ─── ContextNotesResultCard ───────────────────────────────────────────────

interface NoteItem {
  noteId: string;
  noteTitle: string;
  linkType: string;
  /** Per-item workspace slug; falls back to data.workspaceSlug if absent. */
  workspaceSlug?: string;
}

interface ContextNotesResultCardProps {
  data: Record<string, unknown>;
  className?: string;
}

export const ContextNotesResultCard = memo<ContextNotesResultCardProps>(
  function ContextNotesResultCard({ data, className }) {
    const notes = (data.notes ?? []) as NoteItem[];
    // AI backend sets workspaceSlug once at the top level; per-item slug is optional fallback.
    const topSlug = typeof data.workspaceSlug === 'string' ? data.workspaceSlug : '';

    return (
      <div className={cn('flex flex-col gap-2', className)}>
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Related Notes
        </span>
        {notes.length === 0 ? (
          <p className="text-xs text-muted-foreground">No related notes found</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {notes.map((note, idx) => (
              <NotePreviewCard
                key={note.noteId ?? idx}
                noteId={note.noteId}
                noteTitle={note.noteTitle}
                linkType={note.linkType as 'CREATED' | 'EXTRACTED' | 'REFERENCED'}
                workspaceSlug={note.workspaceSlug ?? topSlug}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
);

// ─── ContextIssuesResultCard ──────────────────────────────────────────────

interface IssueItem {
  issueId: string;
  identifier: string;
  title: string;
  stateGroup: string;
  relationType: string;
  /** Per-item workspace slug; falls back to data.workspaceSlug if absent. */
  workspaceSlug?: string;
}

interface ContextIssuesResultCardProps {
  data: Record<string, unknown>;
  className?: string;
}

export const ContextIssuesResultCard = memo<ContextIssuesResultCardProps>(
  function ContextIssuesResultCard({ data, className }) {
    const issues = (data.issues ?? []) as IssueItem[];
    // AI backend sets workspaceSlug once at the top level; per-item slug is optional fallback.
    const topSlug = typeof data.workspaceSlug === 'string' ? data.workspaceSlug : '';

    return (
      <div className={cn('flex flex-col gap-2', className)}>
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Related Issues
        </span>
        {issues.length === 0 ? (
          <p className="text-xs text-muted-foreground">No related issues found</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {issues.map((issue, idx) => (
              <IssueReferenceCard
                key={issue.issueId ?? idx}
                issueId={issue.issueId}
                identifier={issue.identifier}
                title={issue.title}
                stateGroup={issue.stateGroup}
                relationType={issue.relationType as 'blocks' | 'blocked_by' | 'relates'}
                workspaceSlug={issue.workspaceSlug ?? topSlug}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
);
