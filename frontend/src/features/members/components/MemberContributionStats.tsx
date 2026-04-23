/**
 * MemberContributionStats — 4 stat cards with skeleton loading.
 *
 * Displays: Issues Created, Issues Assigned, Cycle Velocity, Capacity Utilization.
 * PR links shown as a sub-metric on the capacity card.
 */

'use client';

import * as React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';
import type { MemberContributionStats as Stats } from '../types';

interface MemberContributionStatsProps {
  stats?: Stats;
  isLoading?: boolean;
}

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tooltip?: string;
}

function StatCard({ label, value, sub, tooltip }: StatCardProps) {
  return (
    <Card>
      <CardContent className="px-4 pb-3 pt-4">
        <div className="flex items-center gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          {tooltip && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Info
                  className="h-3 w-3 cursor-help text-muted-foreground/50"
                  aria-label={`About ${label}`}
                />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[200px] text-xs">
                {tooltip}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
        {sub && <div className="mt-2">{sub}</div>}
      </CardContent>
    </Card>
  );
}

function StatCardSkeleton({ hasProgress = false }: { hasProgress?: boolean }) {
  return (
    <Card>
      <CardContent className="px-4 pb-3 pt-4">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-2 h-8 w-16" />
        {hasProgress && <Skeleton className="mt-2 h-1.5 w-full" />}
      </CardContent>
    </Card>
  );
}

export function MemberContributionStats({ stats, isLoading }: MemberContributionStatsProps) {
  if (isLoading || !stats) {
    return (
      <TooltipProvider delayDuration={300}>
        <div
          className="grid grid-cols-2 gap-3 sm:grid-cols-4"
          aria-label="Loading contribution stats"
          aria-busy="true"
        >
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton hasProgress />
        </div>
      </TooltipProvider>
    );
  }

  const utilPct = Math.round(stats.capacityUtilizationPct);
  const utilColor =
    utilPct > 90 ? 'text-destructive' : utilPct > 70 ? 'text-amber-600' : 'text-foreground';

  return (
    <TooltipProvider delayDuration={300}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Contribution statistics">
        <StatCard
          label="Tasks Created"
          value={stats.issuesCreated}
          tooltip="Total tasks reported by this member across all projects."
        />
        <StatCard
          label="Tasks Assigned"
          value={stats.issuesAssigned}
          tooltip="Total tasks currently or previously assigned to this member."
        />
        <StatCard
          label="Cycle Velocity"
          value={stats.cycleVelocity.toFixed(1)}
          tooltip="Average issues completed per sprint cycle, based on the last 3 completed cycles."
          sub={<p className="text-xs text-muted-foreground">avg issues/sprint</p>}
        />
        <StatCard
          label="Capacity"
          value={<span className={utilColor}>{utilPct}%</span>}
          tooltip="Estimated hours committed to active issues as a percentage of weekly available hours."
          sub={
            <>
              <Progress
                value={Math.min(utilPct, 100)}
                className="h-1.5"
                aria-label={`Capacity utilization ${utilPct}%`}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                {stats.prCommitLinksCount} PR/commit link
                {stats.prCommitLinksCount !== 1 ? 's' : ''}
              </p>
            </>
          }
        />
      </div>
    </TooltipProvider>
  );
}
