'use client';

/**
 * Dashboard Page
 *
 * Route: /[workspaceSlug]/dashboard?batchRunId=<id>
 *
 * Composition:
 *   1. Workspace overview (relocated from v2 HomepageHub)
 *      — RecentWorkSection, ActiveRoutines, SprintProgress, DailyBrief, DigestInsights
 *   2. Implementation dashboard (unchanged)
 *      — sprint progress ring, live AI status, attention feed, cost breakdown
 *
 * Uses TanStack Query (useDashboard) + SSE real-time updates (useBatchRunStream).
 * All layout components use React.memo (NOT observer) per CLAUDE.md TipTap constraint.
 *
 * Phase 77 — Implementation Dashboard (DSH-01, DSH-02, DSH-03, DSH-04, UIX-04)
 * Phase 5 (v3 migration) — Relocated v2 homepage sections to give them a stable home
 *   after HomepageHub switched to the chat-first launchpad.
 */
import * as React from 'react';
import { useSearchParams, useParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';
import { useDashboard, dashboardKeys } from '@/features/dashboard/hooks/use-dashboard';
import { useBatchRunStream } from '@/features/issues/hooks/use-batch-run-stream';
import { SprintProgressRing } from '@/features/dashboard/components/sprint-progress-ring';
import { StatusStatCard } from '@/features/dashboard/components/status-stat-card';
import { LiveIssueCard } from '@/features/dashboard/components/live-issue-card';
import { EtaDisplay } from '@/features/dashboard/components/eta-display';
import { AttentionFeedSection } from '@/features/dashboard/components/attention-feed-section';
import { CostBreakdownPanel } from '@/features/dashboard/components/cost-breakdown-panel';
import { ActiveRoutines } from '@/features/homepage/components/ActiveRoutines';
import { SprintProgress } from '@/features/homepage/components/SprintProgress';
import { RecentWorkSection } from '@/features/homepage/components/RecentWorkSection';
import { DailyBrief } from '@/features/homepage/components/DailyBrief';
import { DigestInsights } from '@/features/homepage/components/DigestInsights';
import { useWorkspaceStore } from '@/stores/RootStore';
import { useWorkspaceDigest } from '@/features/homepage/hooks/useWorkspaceDigest';

// -----------------------------------------------------------------------
// Loading skeleton
// -----------------------------------------------------------------------

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Progress ring + stat cards skeleton */}
      <div className="col-span-3 flex flex-col items-center gap-3">
        <Skeleton className="w-[120px] h-[120px] rounded-full" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="col-span-9 grid grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[80px] rounded-lg" />
        ))}
      </div>
      {/* Live status skeleton */}
      <div className="col-span-12 flex flex-col gap-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-[72px] rounded-lg" />
        ))}
      </div>
      {/* Attention + cost skeleton */}
      <div className="col-span-12 lg:col-span-7">
        <Skeleton className="h-[240px] rounded-lg" />
      </div>
      <div className="col-span-12 lg:col-span-5">
        <Skeleton className="h-[240px] rounded-lg" />
      </div>
      <span className="sr-only">Loading sprint status...</span>
    </div>
  );
}

// -----------------------------------------------------------------------
// Empty state
// -----------------------------------------------------------------------

function DashboardEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[320px]">
      <Card className="max-w-md w-full">
        <CardContent className="p-8 text-center">
          <h2 className="text-[20px] font-semibold text-foreground mb-2">No active sprint</h2>
          <p className="text-[14px] font-normal text-muted-foreground">
            Approve a sprint for implementation to see real-time progress here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// -----------------------------------------------------------------------
// Error state
// -----------------------------------------------------------------------

function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <Alert variant="destructive" className="max-w-xl">
      <AlertCircle className="h-4 w-4" />
      <AlertDescription className="flex items-center justify-between gap-4">
        <span>Could not load dashboard. Check your connection and try again.</span>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  );
}

// -----------------------------------------------------------------------
// Main page
// -----------------------------------------------------------------------

export default function DashboardPage() {
  const params = useParams<{ workspaceSlug: string }>();
  const workspaceSlug = params?.workspaceSlug ?? '';
  const searchParams = useSearchParams();
  const batchRunId = searchParams?.get('batchRunId') ?? null;
  const queryClient = useQueryClient();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  // Digest — powers DigestInsights in the workspace overview
  const digest = useWorkspaceDigest({ workspaceId, enabled: !!workspaceId });

  // Dashboard data
  const { data, isLoading, isError, refetch } = useDashboard(workspaceSlug, batchRunId);

  // SSE real-time stream — on events, invalidate dashboard cache so useDashboard refetches
  useBatchRunStream(batchRunId);

  React.useEffect(() => {
    if (!batchRunId) return;
    // Re-trigger dashboard refetch when SSE signals an update.
    // useBatchRunStream already invalidates batchRunKeys; we also need dashboard cache.
    const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
      if (
        event.type === 'updated' &&
        event.query.queryKey[0] === 'batch-run' &&
        event.query.queryKey[1] === batchRunId
      ) {
        queryClient.invalidateQueries({ queryKey: dashboardKeys.detail(batchRunId) });
      }
    });
    return unsubscribe;
  }, [batchRunId, queryClient]);

  // Render
  return (
    <div className="px-8 py-12 min-h-full">
      {/* ── Workspace overview (relocated from v2 HomepageHub) ─────────── */}
      <section aria-label="Workspace overview" className="mx-auto max-w-5xl space-y-8">
        <header>
          <h1 className="text-[24px] font-semibold leading-[1.2] text-foreground">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Everything happening in your workspace at a glance.
          </p>
        </header>

        <RecentWorkSection workspaceSlug={workspaceSlug} workspaceId={workspaceId} />
        <ActiveRoutines workspaceSlug={workspaceSlug} />
        <SprintProgress workspaceSlug={workspaceSlug} workspaceId={workspaceId} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <DailyBrief workspaceSlug={workspaceSlug} />
          <DigestInsights
            groups={digest.groups}
            generatedAt={digest.generatedAt}
            isLoading={digest.isLoading}
            isError={digest.isError}
            isRefreshing={digest.isRefreshing}
            onDismiss={digest.dismiss}
            onRefresh={digest.refresh}
            onRetry={() => void digest.refetch()}
          />
        </div>
      </section>

      {/* ── Implementation dashboard (existing, Phase 77) ──────────────── */}
      <section aria-label="Implementation dashboard" className="mx-auto mt-16 max-w-5xl">
        <h2 className="mb-8 text-[20px] font-semibold leading-[1.2] text-foreground">
          Implementation Dashboard
        </h2>

      {/* No batch run: empty state */}
      {!batchRunId && <DashboardEmptyState />}

      {/* Has batch run: loading → error → active */}
      {batchRunId && isLoading && <DashboardSkeleton />}

      {batchRunId && isError && !isLoading && (
        <DashboardError onRetry={() => void refetch()} />
      )}

      {batchRunId && data && (
        <div className="grid grid-cols-12 gap-6">
          {/* ── Row 1: Progress ring + Stat cards ── */}
          <div className="col-span-12 md:col-span-3 flex flex-col items-center gap-2">
            <SprintProgressRing percent={data.completionPercent} />
            <EtaDisplay issues={data.issues} />
          </div>

          <div className="col-span-12 md:col-span-9">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatusStatCard
                label="Queued"
                count={data.queuedIssues}
                colorToken="--info"
              />
              <StatusStatCard
                label="Running"
                count={data.runningIssues}
                colorToken="--state-in-progress"
              />
              <StatusStatCard
                label="Done"
                count={data.completedIssues}
                colorToken="--primary"
              />
              <StatusStatCard
                label="Failed"
                count={data.failedIssues}
                colorToken="--destructive"
              />
            </div>
          </div>

          {/* ── Row 2: Live AI Status ── */}
          {data.issues.length > 0 && (
            <div className="col-span-12">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-[14px] font-semibold text-muted-foreground uppercase tracking-wide">
                    Live AI Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0 pb-4">
                  <ScrollArea className="max-h-[320px] px-4">
                    {/* aria-live on container, not individual cards — prevents screen reader alert flood */}
                    <div aria-live="polite" className="flex flex-col gap-2">
                      {data.issues.map((issue) => (
                        <LiveIssueCard key={issue.id} issue={issue} />
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          )}

          {/* ── Row 3: Attention feed + Cost breakdown ── */}
          <div className="col-span-12 lg:col-span-7">
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-[14px] font-semibold text-muted-foreground uppercase tracking-wide">
                  Needs Attention
                </CardTitle>
              </CardHeader>
              <CardContent>
                <AttentionFeedSection
                  attentionItems={data.attentionItems}
                  workspaceSlug={workspaceSlug}
                />
              </CardContent>
            </Card>
          </div>

          <div className="col-span-12 lg:col-span-5">
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-[14px] font-semibold text-muted-foreground uppercase tracking-wide">
                  Cost
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CostBreakdownPanel
                  sprintCostCents={data.sprintCostCents}
                  monthlyCostCents={data.monthlyCostCents}
                  issues={data.issues}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      )}
      </section>
    </div>
  );
}
