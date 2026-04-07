'use client';

/**
 * ProjectContextHeader - Slim subordinate project context bar above note canvas and issue detail.
 *
 * Displays: project icon/name link, inline progress bar, nav tabs (Overview/Issues/Cycles).
 * Visual weight: h-8, bg-background-subtle/50 — intentionally lighter than the page header below.
 *
 * @module components/editor/ProjectContextHeader
 */
import Link from 'next/link';
import { Folder } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { useProject } from '@/features/projects/hooks';
import { useActiveCycle } from '@/features/cycles/hooks/useCycle';

export interface ProjectContextHeaderProps {
  /** Project ID — drives internal data fetch. Renders null if empty. */
  projectId: string;
  /** Workspace slug for building tab hrefs. */
  workspaceSlug: string;
  /** Workspace ID for fetching active cycle. */
  workspaceId?: string;
  /** Highlights the matching tab with a primary underline. */
  activeTab?: 'overview' | 'issues' | 'cycles';
}

const TABS = [
  { id: 'overview' as const, label: 'Overview' },
  { id: 'issues' as const, label: 'Issues' },
  { id: 'cycles' as const, label: 'Cycles' },
];

export function ProjectContextHeader({
  projectId,
  workspaceSlug,
  workspaceId,
  activeTab,
}: ProjectContextHeaderProps) {
  const { data: project, isLoading } = useProject({ projectId });
  const { data: activeCycle } = useActiveCycle({
    workspaceId: workspaceId ?? '',
    projectId,
    enabled: !!workspaceId && !!projectId,
  });

  if (!projectId) return null;

  const baseUrl = `/${workspaceSlug}/projects/${projectId}`;

  if (isLoading) {
    return (
      <div className="flex h-8 shrink-0 items-center gap-3 bg-background-subtle/50 px-4">
        <Skeleton className="h-3 w-20" />
        <div className="flex gap-3">
          <Skeleton className="h-3 w-14" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-10" />
        </div>
      </div>
    );
  }

  if (!project) return null;

  const completedCount = project.issueCount - project.openIssueCount;
  const progress = project.issueCount > 0 ? (completedCount / project.issueCount) * 100 : 0;

  return (
    <div className="flex h-8 shrink-0 items-center bg-background-subtle/50 px-4">
      {/* Project identity link */}
      <Link
        href={baseUrl}
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground motion-safe:transition-colors motion-safe:duration-100"
      >
        {project.icon ? (
          <span className="text-sm leading-none shrink-0" aria-hidden="true">
            {project.icon}
          </span>
        ) : (
          <Folder className="size-3 shrink-0" aria-hidden="true" />
        )}
        {project.name}
      </Link>

      {/* Compact inline progress bar */}
      {project.issueCount > 0 && (
        <div className="ml-2 flex items-center gap-1">
          <div
            className="h-1 w-10 rounded-full bg-border/60 overflow-hidden"
            role="progressbar"
            aria-valuenow={completedCount}
            aria-valuemin={0}
            aria-valuemax={project.issueCount}
            aria-label={`${completedCount} of ${project.issueCount} issues completed`}
          >
            <div
              className="h-full rounded-full bg-primary/70 motion-safe:transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground/70 tabular-nums">
            {completedCount}/{project.issueCount}
          </span>
        </div>
      )}

      {/* Active cycle burn-down — shown when a cycle has metrics */}
      {activeCycle?.metrics && (
        <div className="ml-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="text-border/60">·</span>
          <span className="truncate max-w-[80px]">{activeCycle.name}</span>
          <div
            className="h-1 w-16 rounded-full bg-muted overflow-hidden"
            role="progressbar"
            aria-valuenow={activeCycle.metrics.completedIssues}
            aria-valuemin={0}
            aria-valuemax={activeCycle.metrics.totalIssues}
            aria-label={`Cycle: ${activeCycle.metrics.completedIssues} of ${activeCycle.metrics.totalIssues} completed`}
          >
            <div
              className="h-full bg-success/70 rounded-full"
              style={{
                width: `${activeCycle.metrics.totalIssues > 0 ? (activeCycle.metrics.completedIssues / activeCycle.metrics.totalIssues) * 100 : 0}%`,
              }}
            />
          </div>
          <span className="tabular-nums">
            {activeCycle.metrics.completedIssues}/{activeCycle.metrics.totalIssues}
          </span>
        </div>
      )}

      {/* Divider */}
      <div className="mx-2.5 h-3.5 w-px bg-border/40" aria-hidden="true" />

      {/* Nav tabs — hidden on mobile to avoid overflow */}
      <nav className="hidden md:flex items-center" aria-label="Project navigation">
        {TABS.map((tab) => (
          <Link
            key={tab.id}
            href={`${baseUrl}/${tab.id}`}
            aria-current={activeTab === tab.id ? 'page' : undefined}
            className={cn(
              'flex h-8 items-center gap-1 px-2.5 text-xs border-b-2 motion-safe:transition-colors',
              activeTab === tab.id
                ? 'border-primary text-foreground font-medium'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
            {tab.id === 'issues' && project.openIssueCount > 0 && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {project.openIssueCount}
              </span>
            )}
          </Link>
        ))}
      </nav>
    </div>
  );
}
