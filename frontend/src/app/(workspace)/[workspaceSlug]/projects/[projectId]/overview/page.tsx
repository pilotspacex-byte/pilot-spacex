'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { RefreshCw, ListTodo, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useProject } from '@/features/projects/hooks';
import { useActiveCycle } from '@/features/cycles/hooks';
import { useWorkspaceStore } from '@/stores/RootStore';
import { ProjectStats } from '@/components/projects/ProjectStats';
import { issuesApi } from '@/services/api';
import { useQuery } from '@tanstack/react-query';
import type { Cycle, Issue } from '@/types';
import { formatDistanceToNow, differenceInDays } from 'date-fns';

function ActiveCycleSummary({ cycle }: { cycle: Cycle }) {
  const daysLeft = cycle.endDate
    ? differenceInDays(new Date(cycle.endDate), new Date())
    : null;
  const pct = cycle.metrics?.completionPercentage ?? 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">{cycle.name}</span>
        {daysLeft !== null && (
          <span className={`text-xs ${daysLeft < 0 ? 'text-destructive' : 'text-muted-foreground'}`}>
            {daysLeft < 0 ? `${Math.abs(daysLeft)} days overdue` : `${daysLeft} days left`}
          </span>
        )}
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{Math.round(pct)}% complete</span>
        {cycle.startDate && cycle.endDate && (
          <span>
            {new Date(cycle.startDate).toLocaleDateString()} —{' '}
            {new Date(cycle.endDate).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );
}

const STATE_COLORS: Record<string, string> = {
  backlog: 'bg-muted text-muted-foreground',
  todo: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  in_progress: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  in_review: 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300',
  done: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
};

export default function ProjectOverviewPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';

  const { data: project } = useProject({ projectId: params.projectId });

  const { data: activeCycle, isLoading: cycleLoading } = useActiveCycle({
    workspaceId,
    projectId: params.projectId,
    enabled: !!workspaceId,
  });

  const { data: recentIssuesData, isLoading: issuesLoading } = useQuery({
    queryKey: ['projects', 'recent-issues', params.projectId],
    queryFn: () => issuesApi.list(workspaceId, { projectId: params.projectId }, 1, 5),
    enabled: !!workspaceId && !!params.projectId,
    staleTime: 1000 * 60 * 2,
  });

  const recentIssues: Issue[] = recentIssuesData?.items ?? [];

  if (!project) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-7 w-32" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[76px] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const completedIssues = project.issueCount - project.openIssueCount;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-semibold">Overview</h2>

      {/* Stats */}
      <ProjectStats
        totalIssues={project.issueCount}
        completedIssues={completedIssues}
        openIssues={project.openIssueCount}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Active Cycle */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Active Cycle
              </CardTitle>
              <Link
                href={`/${params.workspaceSlug}/projects/${params.projectId}/cycles`}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-0.5"
              >
                View all <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {cycleLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-24" />
              </div>
            ) : activeCycle ? (
              <ActiveCycleSummary cycle={activeCycle} />
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground mb-2">No active cycle</p>
                <Link
                  href={`/${params.workspaceSlug}/projects/${params.projectId}/cycles`}
                  className="text-sm text-primary hover:underline"
                >
                  Start a cycle
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Issues */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <ListTodo className="h-4 w-4" />
                Recent Issues
              </CardTitle>
              <Link
                href={`/${params.workspaceSlug}/projects/${params.projectId}/issues`}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-0.5"
              >
                View all <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {issuesLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : recentIssues.length > 0 ? (
              <ul className="space-y-1">
                {recentIssues.map((issue) => (
                  <li key={issue.id}>
                    <Link
                      href={`/${params.workspaceSlug}/issues/${issue.id}`}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent/50 transition-colors"
                    >
                      <Badge
                        variant="secondary"
                        className={`text-[10px] font-mono px-1.5 py-0 ${STATE_COLORS[issue.state?.group ?? ''] ?? ''}`}
                      >
                        {issue.identifier}
                      </Badge>
                      <span className="truncate flex-1">{issue.name}</span>
                      <span className="text-[10px] text-muted-foreground flex-shrink-0">
                        {formatDistanceToNow(new Date(issue.updatedAt), { addSuffix: true })}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-center py-4 text-sm text-muted-foreground">No issues yet</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
