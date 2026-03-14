'use client';

/**
 * DailyBrief -- Read-only document-style homepage rendering all workspace data
 * as a unified "daily brief" with prose typography matching the TipTap editor.
 *
 * Uses React components styled with prose classes for full interactivity
 * (clickable notes, issues, projects) without TipTap overhead.
 *
 * Sections: Greeting, Recent Notes, Working On, AI Insights (SDLC), Projects.
 */

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { format } from 'date-fns';
import {
  FileText,
  ChevronDown,
  ChevronRight,
  Sparkles,
  FolderKanban,
  CircleDot,
  CalendarCheck,
} from 'lucide-react';
import { getIssueStateKey } from '@/lib/issue-helpers';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useAuthStore, useWorkspaceStore } from '@/stores/RootStore';
import { getAIStore } from '@/stores/ai/AIStore';
import { useHomepageActivity } from '../hooks/useHomepageActivity';
import { useWorkspaceDigest } from '../hooks/useWorkspaceDigest';
import { useIssueDevObjects } from '../hooks/useIssueDevObjects';
import { useActiveCycleMetrics } from '../hooks/useActiveCycleMetrics';
import { useStaleIssueDetection } from '../hooks/useStaleIssueDetection';
import { DigestInsights } from './DigestInsights';
import {
  SectionDivider,
  NoteEntry,
  IssueEntry,
  ProjectEntry,
  NoteSkeleton,
  IssueSkeleton,
  OnboardingBanner,
} from './BriefEntries';
import { NoteContextBadge } from './NoteContextBadge';
import { DevObjectIndicators } from './DevObjectIndicators';
import { IssueDetailSheet } from './IssueDetailSheet';
import { SprintSparkline } from './SprintSparkline';
import { StaleLogicAlert } from './StaleLogicAlert';
import { SDLCSuggestionCards } from './SDLCSuggestionCards';
import { useQuery } from '@tanstack/react-query';
import { issuesApi } from '@/services/api/issues';
import { projectsApi } from '@/services/api/projects';
import type { ActivityCardNote, SuggestionCardData } from '../types';
import type { Issue, Project } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_NOTES = 5;
const MAX_ISSUES_COLLAPSED = 5;
const MAX_ISSUES_TOTAL = 20;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

/**
 * Build SDLC suggestion cards from stale issues and cycle metrics.
 * Pure computation — no API calls.
 */
/**
 * Build SDLC suggestion cards from cycle metrics only.
 *
 * C2 fix: stale issues are shown exclusively via StaleLogicAlert (with per-issue
 * detail). Adding a stale_alert here would duplicate that warning in the same
 * section.
 */
function buildSuggestionCards(
  completionPct: number | null,
  cycleName: string | null
): SuggestionCardData[] {
  const cards: SuggestionCardData[] = [];

  if (cycleName && completionPct !== null) {
    cards.push({
      id: 'sprint-completion',
      type: 'sprint_completion',
      title: `${cycleName}: ${completionPct}% complete`,
      description:
        completionPct >= 80
          ? 'Sprint is on track for completion.'
          : completionPct >= 50
            ? 'Sprint is progressing. Review remaining items.'
            : 'Sprint needs attention. Consider scope adjustment.',
      severity: completionPct >= 80 ? 'info' : completionPct >= 50 ? 'warning' : 'critical',
    });
  }

  return cards;
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
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);

  const rawDisplayName = authStore.userDisplayName ?? '';
  const emailPrefix = authStore.user?.email?.split('@')[0] ?? '';
  const firstName =
    rawDisplayName && rawDisplayName !== emailPrefix ? rawDisplayName.split(' ')[0] : '';
  const todayFormatted = format(new Date(), 'EEEE, MMMM d, yyyy');

  // --- Data fetching ---

  const { data: activityData, isLoading: notesLoading } = useHomepageActivity({
    workspaceId,
  });

  // W6: Fetch 50 issues to reduce risk of missing active ones due to in-memory state
  // filtering. Backend `state` filter accepts one value; we filter in_progress+in_review
  // client-side, so we need a large enough page to capture both states.
  const { data: issueData, isLoading: issuesLoading } = useQuery({
    queryKey: ['homepage', 'active-issues', workspaceId],
    queryFn: () => issuesApi.list(workspaceId, {}, 1, 50),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });

  const digest = useWorkspaceDigest({ workspaceId });

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

  // W4: Memoize visibleIssues — slice() creates a new array reference each render,
  // causing downstream memos (visibleIssueIds, devObjects) to recompute unnecessarily.
  const visibleIssues = useMemo(
    () => (issuesExpanded ? activeIssues : activeIssues.slice(0, MAX_ISSUES_COLLAPSED)),
    [activeIssues, issuesExpanded]
  );
  const hiddenCount = Math.max(0, activeIssues.length - MAX_ISSUES_COLLAPSED);
  const projects = useMemo(() => projectData?.items ?? [], [projectData]);
  const projectIds = useMemo(() => projects.map((p: Project) => p.id), [projects]);

  // --- SDLC Context Bridge hooks ---

  // C3: Fetch dev objects for ALL active issues (not just visible ones) so that
  // stale detection covers hidden issues too. useIssueDevObjects caches per-issue
  // at DEV_OBJECT_STALE_TIME (60s), so expanding the list reuses cached results.
  const activeIssueIds = useMemo(() => activeIssues.map((i: Issue) => i.id), [activeIssues]);

  const { devObjects, isLoading: devObjectsLoading } = useIssueDevObjects({
    workspaceId,
    issueIds: activeIssueIds,
    enabled: activeIssueIds.length > 0,
  });

  const {
    activeCycle,
    velocityData,
    averageVelocity,
    isLoading: metricsLoading,
  } = useActiveCycleMetrics({
    workspaceId,
    projectIds,
    enabled: projectIds.length > 0,
  });

  const staleIssues = useStaleIssueDetection({
    activeIssues,
    devObjects,
  });

  const suggestionCards = useMemo(() => {
    const total = activeCycle?.metrics?.totalIssues ?? 0;
    const completed = activeCycle?.metrics?.completedIssues ?? 0;
    const pct = total > 0 ? Math.round((completed / total) * 100) : null;
    return buildSuggestionCards(pct, activeCycle?.name ?? null);
  }, [activeCycle]);

  // --- Navigation ---

  const navigateToNote = useCallback(
    (noteId: string) => {
      router.push(`/${workspaceSlug}/notes/${noteId}`);
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
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {getGreeting()}
              {firstName ? `, ${firstName}` : ''}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">{todayFormatted}</p>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Generate a daily standup summary"
                className="shrink-0 gap-1.5 text-xs text-muted-foreground"
                onClick={() => {
                  const store = getAIStore().pilotSpace;
                  if (store) {
                    store.sendMessage('\\daily-standup');
                  }
                }}
              >
                <CalendarCheck className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Standup</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p>Generate a daily standup summary</p>
            </TooltipContent>
          </Tooltip>
        </div>
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
            className="overflow-hidden rounded-lg border border-gray-100"
            role="list"
            aria-label="Recent notes"
          >
            {notes.map((note, idx) => (
              <NoteEntry
                key={note.id}
                note={note}
                onClick={() => navigateToNote(note.id)}
                isLast={idx === notes.length - 1}
                badge={<NoteContextBadge note={note} projects={projects} />}
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
                  onClick={() => setSelectedIssueId(issue.id)}
                  trailing={
                    <DevObjectIndicators
                      devObjects={devObjects.get(issue.id)}
                      issueId={issue.id}
                      isLoading={devObjectsLoading}
                    />
                  }
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
      {/* AI Insights + SDLC Intelligence */}
      {/* ---------------------------------------------------------------- */}
      <section aria-label="AI insights">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            AI Insights
          </h2>
          {digest.suggestionCount > 0 && (
            <Badge variant="secondary" className="px-1.5 py-0 text-xs">
              {digest.suggestionCount}
            </Badge>
          )}
          {/* Sprint sparkline */}
          <span className="ml-auto">
            <SprintSparkline
              velocityData={velocityData}
              averageVelocity={averageVelocity}
              activeCycle={activeCycle}
              isLoading={metricsLoading}
            />
          </span>
        </div>

        {/* Stale issue alert */}
        <StaleLogicAlert staleIssues={staleIssues} className="mb-3" />

        {/* SDLC suggestion cards */}
        <SDLCSuggestionCards suggestions={suggestionCards} className="mb-3" />

        <DigestInsights
          groups={digest.groups}
          generatedAt={digest.generatedAt}
          isLoading={digest.isLoading}
          isError={digest.isError}
          isRefreshing={digest.isRefreshing}
          onDismiss={digest.dismiss}
          onRefresh={() => digest.refresh()}
          onRetry={() => digest.refetch()}
        />
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

      {/* Issue Detail Sheet */}
      <IssueDetailSheet
        issueId={selectedIssueId}
        workspaceId={workspaceId}
        workspaceSlug={workspaceSlug}
        onClose={() => setSelectedIssueId(null)}
      />
    </article>
  );
});
