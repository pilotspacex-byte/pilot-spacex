/**
 * MemoryStatsHeader — Aggregated stats cards for workspace memory.
 *
 * Phase 71: Shows total, per-type counts, pinned count, last ingestion.
 */

'use client';

import * as React from 'react';
import { Database, Pin, Clock, Tag } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useMemoryStats } from '../hooks/use-ai-memory';

interface MemoryStatsHeaderProps {
  workspaceId: string;
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function StatCard({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-background-subtle p-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-muted">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <div className="mt-0.5">{children}</div>
      </div>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 rounded-lg border border-border p-3">
          <Skeleton className="h-8 w-8 rounded-md" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-12" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MemoryStatsHeader({ workspaceId }: MemoryStatsHeaderProps) {
  const { data: stats, isLoading } = useMemoryStats(workspaceId);

  if (isLoading || !stats) return <StatsSkeleton />;

  const topTypes = Object.entries(stats.byType)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard icon={Database} label="Total Memories">
        <p className="text-lg font-semibold text-foreground">{stats.total.toLocaleString()}</p>
      </StatCard>

      <StatCard icon={Tag} label="By Type">
        <div className="flex flex-wrap gap-1">
          {topTypes.length === 0 ? (
            <span className="text-sm text-muted-foreground">None</span>
          ) : (
            topTypes.map(([type, count]) => (
              <Badge key={type} variant="secondary" className="text-xs">
                {type.replace(/_/g, ' ')} ({count})
              </Badge>
            ))
          )}
        </div>
      </StatCard>

      <StatCard icon={Pin} label="Pinned">
        <p className="text-lg font-semibold text-foreground">{stats.pinnedCount}</p>
      </StatCard>

      <StatCard icon={Clock} label="Last Ingestion">
        <p className="text-sm font-medium text-foreground">
          {stats.lastIngestion ? formatRelativeTime(stats.lastIngestion) : 'Never'}
        </p>
      </StatCard>
    </div>
  );
}
