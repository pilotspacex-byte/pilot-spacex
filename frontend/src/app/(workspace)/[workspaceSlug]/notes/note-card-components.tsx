'use client';

/**
 * Note card/list row components extracted from notes page.
 * Includes: NoteGridCard, NoteListRow, GridSkeleton, EmptyState
 */
import { formatDistanceToNow } from 'date-fns';
import { FolderKanban, Pin, Plus } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { Note, Project } from '@/types';

export interface NoteCardProps {
  note: Note;
  workspaceSlug: string;
  projectMap: Map<string, Project>;
  onPrefetch: () => void;
}

/**
 * Note card component for grid view — editorial style
 */
export function NoteGridCard({ note, workspaceSlug, projectMap, onPrefetch }: NoteCardProps) {
  const updatedAt = formatDistanceToNow(new Date(note.updatedAt), { addSuffix: true });
  const topics = note.topics ?? [];
  const linkedIssues = note.linkedIssues ?? [];
  const project = note.projectId ? projectMap.get(note.projectId) : undefined;
  const hasContent = note.summary || topics.length > 0;
  const wordCount = note.wordCount ?? 0;

  return (
    <Link
      href={`/${workspaceSlug}/notes/${note.id}`}
      onMouseEnter={onPrefetch}
      onFocus={onPrefetch}
      className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <article
        className={cn(
          'group relative flex flex-col rounded-xl border border-border bg-card p-5 transition-all duration-200',
          'hover:shadow-warm-md hover:border-primary/20',
          note.isPinned &&
            'ring-1 ring-amber-200/60 dark:ring-amber-700/30 bg-amber-50/20 dark:bg-amber-950/10'
        )}
      >
        {/* Top row: project + pin */}
        <div className="mb-3 flex items-center justify-between gap-2">
          {project ? (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <FolderKanban className="h-3 w-3 shrink-0" />
              <span className="truncate">{project.name}</span>
              <div className="h-1 w-8 rounded-full bg-border overflow-hidden shrink-0">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{
                    width: `${Math.max(0, Math.min(100, ((project.issueCount - project.openIssueCount) / Math.max(project.issueCount, 1)) * 100))}%`,
                  }}
                />
              </div>
            </div>
          ) : (
            <span />
          )}
          {note.isPinned && <Pin className="h-3.5 w-3.5 text-amber-500 shrink-0" />}
        </div>

        {/* Title */}
        <h3 className="mb-1.5 font-display text-base font-semibold text-foreground leading-snug transition-colors group-hover:text-primary line-clamp-2">
          {note.title || 'Untitled'}
        </h3>

        {/* Content preview or linked issues */}
        <div className="flex-1">
          {linkedIssues.length > 0 ? (
            <div className="flex items-center gap-1 mb-2 flex-wrap">
              {linkedIssues.slice(0, 3).map((issue) => (
                <span
                  key={issue.id}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground bg-muted/50"
                  title={`${issue.identifier}: ${issue.state.name}`}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: issue.state.color }}
                    aria-hidden="true"
                  />
                  <span>{issue.identifier}</span>
                  <span className="text-muted-foreground/70">{issue.state.name}</span>
                </span>
              ))}
              {linkedIssues.length > 3 && (
                <span className="text-[10px] text-muted-foreground">
                  +{linkedIssues.length - 3}
                </span>
              )}
            </div>
          ) : hasContent ? (
            <p className="mb-2 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
              {note.summary ? note.summary.slice(0, 120) : topics.join(' · ')}
            </p>
          ) : null}
        </div>

        {/* Footer: word count + timestamp */}
        <div className="mt-auto flex items-center justify-between pt-3 border-t border-border-subtle text-[11px] text-muted-foreground">
          {wordCount > 0 ? (
            <span>{wordCount.toLocaleString()} words</span>
          ) : (
            <span className="text-muted-foreground/50 italic">Empty</span>
          )}
          <span>Updated {updatedAt}</span>
        </div>
      </article>
    </Link>
  );
}

/**
 * Note row component for list view
 */
export function NoteListRow({ note, workspaceSlug, projectMap, onPrefetch }: NoteCardProps) {
  const updatedAt = formatDistanceToNow(new Date(note.updatedAt), { addSuffix: true });
  const topics = note.topics ?? [];
  const linkedIssues = note.linkedIssues ?? [];
  const project = note.projectId ? projectMap.get(note.projectId) : undefined;

  return (
    <Link
      href={`/${workspaceSlug}/notes/${note.id}`}
      onMouseEnter={onPrefetch}
      onFocus={onPrefetch}
      className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <div
        className={cn(
          'group flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3',
          'transition-all hover:border-primary/20 hover:bg-accent/50 hover:shadow-warm-sm',
          note.isPinned &&
            'ring-1 ring-amber-200/60 dark:ring-amber-700/30 bg-amber-50/20 dark:bg-amber-950/10'
        )}
      >
        {/* Pin indicator */}
        {note.isPinned && <Pin className="h-3.5 w-3.5 text-amber-500 shrink-0" />}

        {/* Title & preview */}
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-foreground group-hover:text-primary truncate">
            {note.title || 'Untitled'}
          </h3>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {project && (
              <span className="flex items-center gap-1 truncate">
                <FolderKanban className="h-3 w-3 shrink-0" />
                {project.name}
              </span>
            )}
            {project && topics.length > 0 && <span className="text-border">&middot;</span>}
            <span className="truncate">
              {note.summary
                ? note.summary.slice(0, 80)
                : topics.length > 0
                  ? topics.join(', ')
                  : ''}
            </span>
          </div>
        </div>

        {/* Meta */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground shrink-0">
          {(note.wordCount ?? 0) > 0 && <span>{(note.wordCount ?? 0).toLocaleString()} words</span>}
          {linkedIssues.length > 0 && (
            <div className="flex items-center gap-1">
              {linkedIssues.slice(0, 3).map((issue) => (
                <span
                  key={issue.id}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground bg-muted/50"
                  title={`${issue.identifier}: ${issue.state.name}`}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: issue.state.color }}
                    aria-hidden="true"
                  />
                  <span>{issue.identifier}</span>
                  <span className="text-muted-foreground/70">{issue.state.name}</span>
                </span>
              ))}
              {linkedIssues.length > 3 && (
                <span className="text-[10px] text-muted-foreground">
                  +{linkedIssues.length - 3}
                </span>
              )}
            </div>
          )}
          <span className="w-24 text-right">{updatedAt}</span>
        </div>
      </div>
    </Link>
  );
}

/**
 * Loading skeleton for grid view
 */
export function GridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-3.5 w-3.5 rounded-full" />
          </div>
          <Skeleton className="h-5 w-3/4 mb-2" />
          <Skeleton className="h-4 w-full mb-1" />
          <Skeleton className="h-4 w-2/3 mb-3" />
          <div className="flex justify-between pt-3 border-t border-border-subtle">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state component
 */
export function EmptyState({ onCreate }: { onCreate?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="relative mb-6">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/6">
          <span className="font-display text-4xl font-semibold text-primary/40">N</span>
        </div>
        <div className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-lg bg-background shadow-warm-sm border border-border/50">
          <Plus className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
      <h3 className="font-display text-xl font-semibold text-foreground mb-2">No notes yet</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-sm leading-relaxed">
        Start capturing your thoughts, ideas, and discussions. Notes are the foundation of your
        workflow.
      </p>
      {onCreate && (
        <Button onClick={onCreate} className="shadow-warm-sm">
          <Plus className="mr-2 h-4 w-4" />
          Create your first note
        </Button>
      )}
    </div>
  );
}
