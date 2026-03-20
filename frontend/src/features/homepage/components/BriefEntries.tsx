'use client';

/**
 * BriefEntries — Extracted sub-components for DailyBrief layout.
 *
 * Includes: SectionDivider, NoteEntry, IssueEntry, ProjectEntry,
 * NoteSkeleton, IssueSkeleton, OnboardingBanner, STATE_COLORS.
 */

import { observer } from 'mobx-react-lite';
import { FileText, Pin, ChevronRight, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { abbreviatedTimeAgo } from '@/lib/format-utils';
import { getIssueStateKey } from '@/lib/issue-helpers';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useOnboardingStore } from '@/stores/RootStore';
import {
  useOnboardingState,
  selectCompletionPercentage,
} from '@/features/onboarding/hooks/useOnboardingState';
import type { ActivityCardNote } from '../types';
import type { Issue, Project } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** State key to display color and human-readable label */
export const STATE_COLORS: Record<string, { dot: string; label: string }> = {
  backlog: { dot: 'bg-[var(--color-state-backlog)]', label: 'Backlog' },
  todo: { dot: 'bg-[var(--color-state-todo)]', label: 'Todo' },
  in_progress: { dot: 'bg-[var(--color-state-in-progress)]', label: 'In Progress' },
  in_review: { dot: 'bg-[var(--color-state-in-review)]', label: 'In Review' },
  done: { dot: 'bg-[var(--color-state-done)]', label: 'Done' },
  cancelled: { dot: 'bg-[var(--color-state-cancelled)]', label: 'Cancelled' },
};

// ---------------------------------------------------------------------------
// SectionDivider
// ---------------------------------------------------------------------------

export function SectionDivider() {
  return <hr className="my-6 border-border" />;
}

// ---------------------------------------------------------------------------
// NoteEntry
// ---------------------------------------------------------------------------

export interface NoteEntryProps {
  note: ActivityCardNote;
  onClick: () => void;
  isLast: boolean;
  /** Optional badge rendered after the title (used by NoteContextBadge) */
  badge?: React.ReactNode;
}

/** Compact note row for tight table-style list */
export function NoteEntry({ note, onClick, isLast, badge }: NoteEntryProps) {
  const timeAgo = abbreviatedTimeAgo(note.updatedAt);
  const isEmpty = !note.wordCount || note.wordCount === 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'group flex w-full items-center gap-2 px-3 py-2 text-left',
        'min-h-[36px] sm:min-h-0 sm:h-9',
        'motion-safe:transition-colors motion-safe:duration-100',
        'hover:bg-gray-50/50 active:bg-gray-100/50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        !isLast && 'border-b border-border-subtle'
      )}
    >
      <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50" aria-hidden="true" />
      <span
        className={cn(
          'min-w-0 flex-1 truncate text-[13px]',
          isEmpty ? 'italic text-muted-foreground' : 'text-foreground'
        )}
      >
        {note.title || 'Untitled'}
      </span>
      {badge}
      {note.isPinned && <Pin className="h-3 w-3 shrink-0 text-primary/60" aria-label="Pinned" />}
      {note.project && (
        <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
          {note.project.identifier}
        </span>
      )}
      <span className="w-7 shrink-0 text-right tabular-nums text-[11px] text-muted-foreground/70">
        {timeAgo}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// IssueEntry
// ---------------------------------------------------------------------------

export interface IssueEntryProps {
  issue: Issue;
  onClick: () => void;
  /** Optional trailing content rendered after the state badge */
  trailing?: React.ReactNode;
}

/** Task-list style issue row with state dot and badge */
export function IssueEntry({ issue, onClick, trailing }: IssueEntryProps) {
  const stateKey = getIssueStateKey(issue.state);
  const fallback = { dot: 'bg-muted-foreground/40', label: 'Backlog' };
  const stateInfo = STATE_COLORS[stateKey] ?? fallback;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left',
        'min-h-[44px]',
        'motion-safe:transition-colors motion-safe:duration-100',
        'hover:bg-gray-50/50 active:bg-gray-100/50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
      )}
    >
      <span className={cn('h-2 w-2 shrink-0 rounded-full', stateInfo.dot)} aria-hidden="true" />
      <span className="shrink-0 font-mono text-xs text-muted-foreground">{issue.identifier}</span>
      <span className="min-w-0 flex-1 truncate text-sm text-foreground">{issue.name}</span>
      {trailing}
      <Badge variant="outline" className="shrink-0 px-1.5 py-0 text-xs">
        {stateInfo.label}
      </Badge>
    </button>
  );
}

// ---------------------------------------------------------------------------
// ProjectEntry
// ---------------------------------------------------------------------------

/** Project row with progress bar */
export function ProjectEntry({ project, onClick }: { project: Project; onClick: () => void }) {
  const total = project.issueCount ?? 0;
  const done = project.completedIssueCount ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left',
        'min-h-[44px]',
        'motion-safe:transition-colors motion-safe:duration-100',
        'hover:bg-gray-50/50 active:bg-gray-100/50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
      )}
    >
      <span className="min-w-[80px] max-w-[140px] shrink-0 truncate text-xs font-medium text-foreground">
        {project.name}
      </span>
      <Progress value={pct} className="h-1.5 flex-1" />
      <span className="w-16 shrink-0 text-right tabular-nums text-xs text-muted-foreground">
        {done}/{total}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Skeletons
// ---------------------------------------------------------------------------

export function NoteSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-border-subtle">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={cn(
            'h-9 motion-safe:animate-pulse bg-muted/30',
            i < 3 && 'border-b border-border-subtle'
          )}
        />
      ))}
    </div>
  );
}

export function IssueSkeleton() {
  return (
    <div className="space-y-1.5">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-10 motion-safe:animate-pulse rounded-md bg-muted/30" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// OnboardingBanner
// ---------------------------------------------------------------------------

/** Inline onboarding progress banner shown below greeting */
export const OnboardingBanner = observer(function OnboardingBanner({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const onboardingStore = useOnboardingStore();
  const { data } = useOnboardingState({ workspaceId });

  if (!data || data.dismissedAt || data.completedAt) return null;

  const percentage = selectCompletionPercentage(data);

  return (
    <button
      type="button"
      onClick={() => onboardingStore.openModal()}
      className={cn(
        'mb-6 flex w-full items-center gap-3 rounded-lg px-4 py-3',
        'border border-primary/20 bg-primary/5',
        'text-left text-sm font-medium text-foreground',
        'motion-safe:transition-all motion-safe:duration-200',
        'hover:border-primary/40 hover:bg-primary/10 hover:shadow-sm',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
      )}
    >
      <Sparkles className="h-4 w-4 shrink-0 text-primary" />
      <span className="flex-1">Continue workspace setup</span>
      <Progress value={percentage} className="h-1.5 w-20" />
      <span className="shrink-0 tabular-nums text-xs text-muted-foreground">{percentage}%</span>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
    </button>
  );
});
