'use client';

/**
 * IssueBody — read-only preview of an issue inside the PeekDrawer.
 *
 * Per `.claude/rules/tiptap.md`: rendering the full `IssueEditorContent` +
 * `IssueNoteContext` stack inside a Sheet portal is possible, but risky —
 * the React 19 + MobX + TipTap `flushSync` collision shows up if any ancestor
 * in the portal tree wraps in `observer()`. The peek drawer intentionally
 * keeps issue previews LIGHT — property chips + description preview — and
 * routes the user to the full /{slug}/issues/{id} page for editing.
 *
 * NOT observer() — plain TanStack-Query consumer.
 */

import { AlertTriangle } from 'lucide-react';
import { useIssueDetail } from '@/features/issues/hooks';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import type { Issue } from '@/types';

interface IssueBodyProps {
  workspaceId: string;
  issueId: string;
  onClose: () => void;
}

const PRIORITY_COLOR: Readonly<Record<string, string>> = {
  urgent: 'var(--priority-urgent)',
  high: 'var(--priority-high)',
  medium: 'var(--priority-medium)',
  low: 'var(--priority-low)',
  none: 'var(--priority-none)',
};

function initials(name: string | undefined): string {
  if (!name) return '?';
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('');
}

function PropertyRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-4 py-1.5">
      <span className="w-24 shrink-0 text-xs font-medium uppercase tracking-[0.06em] text-muted-foreground pt-0.5">
        {label}
      </span>
      <div className="flex-1 min-w-0 text-sm text-foreground">{children}</div>
    </div>
  );
}

function IssueHeader({ issue }: { issue: Issue }) {
  return (
    <div className="border-b border-border/60 px-6 py-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-1">
        {issue.identifier}
      </p>
      <h1 className="text-xl font-semibold leading-tight text-foreground">
        {issue.name ?? issue.title}
      </h1>
    </div>
  );
}

function IssueProperties({ issue }: { issue: Issue }) {
  const priorityColor = PRIORITY_COLOR[issue.priority] ?? 'var(--priority-none)';
  return (
    <div className="px-6 py-4 border-b border-border/60 space-y-0.5">
      <PropertyRow label="State">
        <Badge
          variant="secondary"
          className="text-[11px] font-medium uppercase tracking-[0.04em]"
          style={{
            backgroundColor: issue.state.color
              ? `color-mix(in oklab, ${issue.state.color} 16%, transparent)`
              : undefined,
            color: issue.state.color ?? undefined,
          }}
        >
          {issue.state.name}
        </Badge>
      </PropertyRow>
      <PropertyRow label="Priority">
        <span
          className="inline-flex items-center gap-2 text-sm capitalize"
          style={{ color: priorityColor }}
        >
          <span
            aria-hidden="true"
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: priorityColor }}
          />
          {issue.priority}
        </span>
      </PropertyRow>
      <PropertyRow label="Assignee">
        {issue.assignee ? (
          <span className="inline-flex items-center gap-2">
            <Avatar className="h-5 w-5">
              {issue.assignee.avatarUrl ? (
                <AvatarImage
                  src={issue.assignee.avatarUrl}
                  alt={issue.assignee.displayName ?? issue.assignee.email}
                />
              ) : null}
              <AvatarFallback className="text-[10px]">
                {initials(issue.assignee.displayName ?? issue.assignee.email)}
              </AvatarFallback>
            </Avatar>
            <span>{issue.assignee.displayName ?? issue.assignee.email}</span>
          </span>
        ) : (
          <span className="text-muted-foreground italic">Unassigned</span>
        )}
      </PropertyRow>
      {issue.labels.length > 0 ? (
        <PropertyRow label="Labels">
          <div className="flex flex-wrap gap-1.5">
            {issue.labels.map((label) => (
              <Badge
                key={label.id}
                variant="outline"
                className="text-[11px]"
                style={{
                  borderColor: label.color ? `${label.color}60` : undefined,
                  color: label.color ?? undefined,
                }}
              >
                {label.name}
              </Badge>
            ))}
          </div>
        </PropertyRow>
      ) : null}
      {issue.cycleId ? <PropertyRow label="Cycle">{issue.cycleId}</PropertyRow> : null}
      <PropertyRow label="Updated">
        <span className="font-mono tabular-nums text-xs text-muted-foreground">
          {new Date(issue.updatedAt).toLocaleString()}
        </span>
      </PropertyRow>
    </div>
  );
}

export function IssueBody({ workspaceId, issueId }: IssueBodyProps) {
  const { data: issue, isLoading, isError, error } = useIssueDetail(workspaceId, issueId);

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-7 w-3/4" />
        <div className="pt-4 space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    );
  }

  if (isError || !issue) {
    const status = (error as { status?: number } | null)?.status;
    const message =
      status === 404
        ? 'This issue no longer exists or you do not have access.'
        : 'Failed to load issue preview. Try refreshing or open the full view.';
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
        <AlertTriangle className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <IssueHeader issue={issue} />
      <IssueProperties issue={issue} />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {issue.description ? (
          <div className={cn('prose prose-sm max-w-none text-foreground')}>
            {issue.description.split(/\n\n+/).map((paragraph, idx) => (
              <p key={idx} className="whitespace-pre-wrap leading-relaxed text-[14px]">
                {paragraph}
              </p>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No description yet. Open the full view to add one.
          </p>
        )}
      </div>
    </div>
  );
}
