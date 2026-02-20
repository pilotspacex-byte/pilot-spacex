'use client';

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useWorkspaceStore } from '@/stores/RootStore';
import { issuesApi } from '@/services/api';
import type { Issue, StateGroup } from '@/types';

const STATE_TABS: { label: string; value: StateGroup | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Backlog', value: 'backlog' },
  { label: 'Todo', value: 'unstarted' },
  { label: 'In Progress', value: 'started' },
  { label: 'Done', value: 'completed' },
];

const PRIORITY_ICONS: Record<string, string> = {
  urgent: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🟢',
  none: '⚪',
};

export default function ProjectIssuesPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';
  const [stateFilter, setStateFilter] = useState<StateGroup | 'all'>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['projects', 'issues', params.projectId],
    queryFn: () => issuesApi.list(workspaceId, { projectId: params.projectId }),
    enabled: !!workspaceId,
    staleTime: 1000 * 60 * 2,
  });

  const issues: Issue[] = useMemo(() => {
    const all = data?.items ?? [];
    if (stateFilter === 'all') return all;
    return all.filter((i) => i.state?.group === stateFilter);
  }, [data, stateFilter]);

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-semibold">Issues</h2>

      {/* State filter tabs */}
      <div className="flex gap-1 overflow-x-auto">
        {STATE_TABS.map((tab) => (
          <Button
            key={tab.label}
            variant={stateFilter === tab.value ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setStateFilter(tab.value)}
            className="text-xs"
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Issue list */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : issues.length === 0 ? (
        <div className="text-center py-12 text-sm text-muted-foreground">
          {stateFilter === 'all' ? 'No issues in this project' : `No ${stateFilter} issues`}
        </div>
      ) : (
        <div className="border border-border rounded-lg divide-y divide-border">
          {issues.map((issue) => (
            <Link
              key={issue.id}
              href={`/${params.workspaceSlug}/issues/${issue.id}`}
              className="flex items-center gap-3 px-4 py-3 hover:bg-accent/30 transition-colors"
            >
              <Badge variant="outline" className="font-mono text-[10px] flex-shrink-0">
                {issue.identifier}
              </Badge>
              <span className="text-sm truncate flex-1">{issue.name}</span>
              <Badge
                variant="secondary"
                className="text-[10px] flex-shrink-0"
                style={
                  issue.state?.color
                    ? { backgroundColor: issue.state.color + '20', color: issue.state.color }
                    : undefined
                }
              >
                {issue.state?.name}
              </Badge>
              <span className="text-xs flex-shrink-0">{PRIORITY_ICONS[issue.priority] ?? ''}</span>
              {issue.assignee && (
                <Avatar className="h-6 w-6 flex-shrink-0">
                  <AvatarFallback className="text-[10px]">
                    {issue.assignee.displayName?.charAt(0).toUpperCase() ?? '?'}
                  </AvatarFallback>
                </Avatar>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
