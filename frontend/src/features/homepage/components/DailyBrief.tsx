'use client';

/**
 * DailyBrief -- Read-only document-style homepage rendering all workspace data
 * as a unified "daily brief" with prose typography matching the TipTap editor.
 *
 * Uses React components styled with prose classes for full interactivity
 * (clickable notes, issues, projects) without TipTap overhead.
 *
 * Sections: Greeting, Recent Notes, Working On, AI Insights, Projects.
 */

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { format } from 'date-fns';
import {
  FileText,
  Pin,
  ChevronDown,
  ChevronRight,
  Sparkles,
  FolderKanban,
  CircleDot,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { abbreviatedTimeAgo } from '@/lib/format-utils';
import { getIssueStateKey } from '@/lib/issue-helpers';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useAuthStore, useWorkspaceStore, useOnboardingStore } from '@/stores/RootStore';
import {
  useOnboardingState,
  selectCompletionPercentage,
} from '@/features/onboarding/hooks/useOnboardingState';
import { useHomepageActivity } from '../hooks/useHomepageActivity';
import { useQuery } from '@tanstack/react-query';
import { issuesApi } from '@/services/api/issues';
import { projectsApi } from '@/services/api/projects';
import type { ActivityCardNote } from '../types';
import type { Issue, Project } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_NOTES = 5;
const MAX_ISSUES_COLLAPSED = 5;
const MAX_ISSUES_TOTAL = 20;

/** State key to display color and human-readable label */
const STATE_COLORS: Record<string, { dot: string; label: string }> = {
  backlog: { dot: 'bg-muted-foreground/40', label: 'Backlog' },
  todo: { dot: 'bg-blue-400', label: 'Todo' },
  in_progress: { dot: 'bg-amber-500', label: 'In Progress' },
  in_review: { dot: 'bg-violet-500', label: 'In Review' },
  done: { dot: 'bg-emerald-500', label: 'Done' },
  cancelled: { dot: 'bg-muted-foreground/40', label: 'Cancelled' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionDivider() {
  return <hr className="my-6 border-border" />;
}

/** Compact note row for tight table-style list */
function NoteEntry({
  note,
  onClick,
  isLast,
}: {
  note: ActivityCardNote;
  onClick: () => void;
  isLast: boolean;
}) {
  const timeAgo = abbreviatedTimeAgo(note.updatedAt);
  const isEmpty = !note.wordCount || note.wordCount === 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 px-3 py-2 text-left',
        'min-h-[36px] sm:min-h-0 sm:h-9',
        'motion-safe:transition-colors motion-safe:duration-100',
        'hover:bg-muted/50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        !isLast && 'border-b border-border/50'
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

/** Task-list style issue row with state dot and badge */
function IssueEntry({ issue, onClick }: { issue: Issue; onClick: () => void }) {
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
        'hover:bg-muted/40',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
      )}
    >
      <span className={cn('h-2 w-2 shrink-0 rounded-full', stateInfo.dot)} aria-hidden="true" />
      <span className="shrink-0 font-mono text-xs text-muted-foreground">{issue.identifier}</span>
      <span className="min-w-0 flex-1 truncate text-sm text-foreground">{issue.name}</span>
      <Badge variant="outline" className="shrink-0 px-1.5 py-0 text-xs">
        {stateInfo.label}
      </Badge>
    </button>
  );
}

/** Project row with progress bar */
function ProjectEntry({ project, onClick }: { project: Project; onClick: () => void }) {
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
        'hover:bg-muted/40',
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
// Section Skeletons
// ---------------------------------------------------------------------------

function NoteSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={cn(
            'h-9 motion-safe:animate-pulse bg-muted/30',
            i < 3 && 'border-b border-border/50'
          )}
        />
      ))}
    </div>
  );
}

/** Inline onboarding progress banner shown below greeting */
const OnboardingBanner = observer(function OnboardingBanner({
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

function IssueSkeleton() {
  return (
    <div className="space-y-1.5">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-10 motion-safe:animate-pulse rounded-md bg-muted/30" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

interface DailyBriefProps {
  workspaceSlug: string;
}

export const DailyBrief = observer(function DailyBrief({ workspaceSlug }: DailyBriefProps) {
  const router = useRouter();
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  const [issuesExpanded, setIssuesExpanded] = useState(false);

  const firstName = authStore.userDisplayName?.split(' ')[0] ?? '';
  const todayFormatted = format(new Date(), 'EEEE, MMMM d, yyyy');

  // --- Data fetching ---

  const { data: activityData, isLoading: notesLoading } = useHomepageActivity({
    workspaceId,
  });

  // Client-side state filtering: the backend accepts a `state` query param but
  // does not forward it to the service layer (ListIssuesPayload). Until the
  // backend wires the param through, we fetch 20 items and filter locally.
  const { data: issueData, isLoading: issuesLoading } = useQuery({
    queryKey: ['homepage', 'active-issues', workspaceId],
    queryFn: () => issuesApi.list(workspaceId, {}, 1, 20),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });

  const { data: projectData, isLoading: projectsLoading } = useQuery({
    queryKey: ['homepage', 'projects', workspaceId],
    queryFn: () => projectsApi.list(workspaceId),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });

  // --- Derived data ---

  const notes = useMemo(() => {
    if (!activityData?.pages) return [];
    const collected: ActivityCardNote[] = [];
    for (const page of activityData.pages) {
      for (const cards of Object.values(page.data)) {
        for (const card of cards) {
          if (card.type === 'note') {
            collected.push(card);
            if (collected.length >= MAX_NOTES) return collected;
          }
        }
      }
    }
    return collected;
  }, [activityData]);

  const activeIssues = useMemo(() => {
    return (issueData?.items ?? [])
      .filter((issue: Issue) => {
        const stateKey = getIssueStateKey(issue.state);
        return stateKey === 'in_progress' || stateKey === 'in_review';
      })
      .slice(0, MAX_ISSUES_TOTAL);
  }, [issueData]);

  const visibleIssues = issuesExpanded ? activeIssues : activeIssues.slice(0, MAX_ISSUES_COLLAPSED);

  const hiddenCount = Math.max(0, activeIssues.length - MAX_ISSUES_COLLAPSED);

  const projects = projectData?.items ?? [];

  // --- Navigation ---

  const navigateToNote = useCallback(
    (noteId: string) => {
      router.push(`/${workspaceSlug}/notes/${noteId}`);
    },
    [router, workspaceSlug]
  );

  const navigateToIssue = useCallback(
    (issueId: string) => {
      router.push(`/${workspaceSlug}/issues/${issueId}`);
    },
    [router, workspaceSlug]
  );

  const navigateToProject = useCallback(
    (projectId: string) => {
      router.push(`/${workspaceSlug}/projects/${projectId}`);
    },
    [router, workspaceSlug]
  );

  return (
    <article className="mx-auto max-w-2xl">
      {/* ---------------------------------------------------------------- */}
      {/* Heading */}
      {/* ---------------------------------------------------------------- */}
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {getGreeting()}
          {firstName ? `, ${firstName}` : ''}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{todayFormatted}</p>
      </header>

      {/* Onboarding progress — contextual within the daily brief */}
      <OnboardingBanner workspaceId={workspaceId} />

      {/* ---------------------------------------------------------------- */}
      {/* Recent Notes */}
      {/* ---------------------------------------------------------------- */}
      <section aria-label="Recent notes">
        <div className="mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Recent Notes
          </h2>
        </div>

        {notesLoading ? (
          <NoteSkeleton />
        ) : notes.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No notes yet. Start writing!
          </p>
        ) : (
          <div
            className="overflow-hidden rounded-lg border border-border"
            role="list"
            aria-label="Recent notes"
          >
            {notes.map((note, idx) => (
              <NoteEntry
                key={note.id}
                note={note}
                onClick={() => navigateToNote(note.id)}
                isLast={idx === notes.length - 1}
              />
            ))}
          </div>
        )}
      </section>

      <SectionDivider />

      {/* ---------------------------------------------------------------- */}
      {/* Working On */}
      {/* ---------------------------------------------------------------- */}
      <section aria-label="Working issues">
        <div className="mb-3 flex items-center gap-2">
          <CircleDot className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Working On
          </h2>
          {activeIssues.length > 0 && (
            <Badge variant="secondary" className="px-1.5 py-0 text-xs">
              {activeIssues.length}
            </Badge>
          )}
        </div>

        {issuesLoading ? (
          <IssueSkeleton />
        ) : activeIssues.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No active issues. All clear!
          </p>
        ) : (
          <>
            <div className="space-y-0.5" role="list" aria-label="Working issues">
              {visibleIssues.map((issue: Issue) => (
                <IssueEntry
                  key={issue.id}
                  issue={issue}
                  onClick={() => navigateToIssue(issue.id)}
                />
              ))}
            </div>

            {hiddenCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIssuesExpanded((prev) => !prev)}
                className="mt-1 h-8 w-full gap-1.5 text-xs text-muted-foreground"
              >
                {issuesExpanded ? (
                  <>
                    <ChevronDown className="h-3 w-3" aria-hidden="true" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronRight className="h-3 w-3" aria-hidden="true" />
                    Show {hiddenCount} more
                  </>
                )}
              </Button>
            )}
          </>
        )}
      </section>

      <SectionDivider />

      {/* ---------------------------------------------------------------- */}
      {/* AI Insights */}
      {/* ---------------------------------------------------------------- */}
      <section aria-label="AI insights">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            AI Insights
          </h2>
        </div>

        <p className="py-6 text-center text-sm text-muted-foreground">
          No suggestions yet. Ask AI for insights.
        </p>
      </section>

      <SectionDivider />

      {/* ---------------------------------------------------------------- */}
      {/* Projects */}
      {/* ---------------------------------------------------------------- */}
      {(projectsLoading || projects.length > 0) && (
        <section aria-label="Project progress">
          <div className="mb-3 flex items-center gap-2">
            <FolderKanban className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Projects
            </h2>
          </div>

          {projectsLoading ? (
            <div className="space-y-1.5">
              {[1, 2].map((i) => (
                <div key={i} className="h-10 motion-safe:animate-pulse rounded-md bg-muted/30" />
              ))}
            </div>
          ) : (
            <div className="space-y-0.5" role="list" aria-label="Project progress">
              {projects.map((project: Project) => (
                <ProjectEntry
                  key={project.id}
                  project={project}
                  onClick={() => navigateToProject(project.id)}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </article>
  );
});
