/**
 * MemberIssueDigest — Issues grouped by state for the Issues tab.
 *
 * Groups: In Progress | In Review | Todo | Backlog | Done | Overdue (past target_date + not done).
 */

'use client';

import Link from 'next/link';
import { ClipboardList } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { MemberIssueDigestItem } from '../types';

interface MemberIssueDigestProps {
  issues: MemberIssueDigestItem[];
  workspaceSlug: string;
}

const STATE_GROUP_LABELS: Record<string, string> = {
  todo: 'Todo',
  in_progress: 'In Progress',
  in_review: 'In Review',
  done: 'Done',
  backlog: 'Backlog',
  overdue: 'Overdue',
};

const STATE_BADGE_COLORS: Record<string, string> = {
  todo: 'bg-muted text-foreground',
  in_progress: 'bg-blue-500/15 text-blue-700 dark:text-blue-400',
  in_review: 'bg-purple-500/15 text-purple-700 dark:text-purple-400',
  done: 'bg-green-500/15 text-green-700 dark:text-green-400',
  backlog: 'bg-muted text-muted-foreground',
  overdue: 'bg-red-500/15 text-red-700 dark:text-red-400',
};

const GROUP_ORDER = ['in_progress', 'in_review', 'todo', 'backlog', 'done', 'overdue'] as const;

function groupByState(issues: MemberIssueDigestItem[]): Record<string, MemberIssueDigestItem[]> {
  return issues.reduce<Record<string, MemberIssueDigestItem[]>>((acc, issue) => {
    const group = issue.state ?? 'in_progress';
    if (!acc[group]) acc[group] = [];
    acc[group]!.push(issue);
    return acc;
  }, {});
}

export function MemberIssueDigest({ issues, workspaceSlug }: MemberIssueDigestProps) {
  if (!issues.length) {
    return (
      <div className="flex flex-col items-center gap-2 py-10 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
          <ClipboardList className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">No assigned tasks</p>
        <p className="max-w-[240px] text-xs text-muted-foreground/70">
          Tasks assigned to this member will appear here, grouped by state.
        </p>
      </div>
    );
  }

  const grouped = groupByState(issues);

  return (
    <section className="space-y-4" aria-label="Tasks by state">
      {GROUP_ORDER.filter((g) => (grouped[g]?.length ?? 0) > 0).map((group) => (
        <div key={group}>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {STATE_GROUP_LABELS[group] ?? group}
            </span>
            <Badge variant="secondary" className="text-xs">
              {grouped[group]!.length}
            </Badge>
          </div>
          <div className="flex flex-wrap gap-2">
            {grouped[group]!.map((issue) => (
              <Link
                key={issue.id}
                href={`/${workspaceSlug}/issues/${issue.identifier}`}
                className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors hover:opacity-80 ${STATE_BADGE_COLORS[group] ?? ''}`}
                aria-label={`${issue.identifier}: ${issue.title}`}
              >
                <span className="font-mono">{issue.identifier}</span>
                <span className="max-w-[180px] truncate sm:max-w-[260px]">{issue.title}</span>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
