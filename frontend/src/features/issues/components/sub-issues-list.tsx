'use client';

import * as React from 'react';
import Link from 'next/link';
import { Plus, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useCreateSubIssue } from '../hooks/use-create-sub-issue';
import type { Issue } from '@/types';

export interface SubIssuesListProps {
  parentId: string;
  workspaceId: string;
  workspaceSlug: string;
  projectId: string;
  subIssues: Issue[];
  disabled?: boolean;
}

function getInitial(assignee: Issue['assignee']): string {
  if (!assignee) return '?';
  return (assignee.displayName || assignee.email).charAt(0).toUpperCase();
}

function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash) % 360}, 45%, 55%)`;
}

interface SubIssueRowProps {
  issue: Issue;
  workspaceSlug: string;
}

function SubIssueRow({ issue, workspaceSlug }: SubIssueRowProps) {
  const initial = getInitial(issue.assignee);
  const avatarBg = issue.assignee ? hashColor(issue.assignee.id) : 'var(--muted)';

  return (
    <Link
      href={`/${workspaceSlug}/issues/${issue.id}`}
      className={cn(
        'flex items-center gap-3 px-3 py-2.5',
        'border-b border-border-subtle last:border-b-0',
        'hover:bg-[var(--background-subtle)] transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        'rounded-sm'
      )}
    >
      <span className="font-mono text-xs text-muted-foreground shrink-0">{issue.identifier}</span>
      <span className="text-sm truncate flex-1 min-w-0">{issue.name}</span>
      <span
        className="inline-flex items-center gap-1.5 text-xs shrink-0 rounded-full px-2 py-0.5"
        style={{ backgroundColor: `${issue.state.color}18`, color: issue.state.color }}
      >
        <span
          className="size-2 rounded-full"
          style={{ backgroundColor: issue.state?.color }}
          aria-hidden="true"
        />
        {issue.state?.name ?? 'Backlog'}
      </span>
      {issue.assignee && (
        <span
          className="size-6 rounded-full flex items-center justify-center text-[10px] font-medium text-white shrink-0"
          style={{ backgroundColor: avatarBg }}
          title={issue.assignee.displayName || issue.assignee.email}
        >
          {initial}
        </span>
      )}
    </Link>
  );
}

interface InlineCreateFormProps {
  workspaceId: string;
  parentId: string;
  projectId: string;
  onClose: () => void;
}

function InlineCreateForm({ workspaceId, parentId, projectId, onClose }: InlineCreateFormProps) {
  const [title, setTitle] = React.useState('');
  const mutation = useCreateSubIssue(workspaceId, parentId);
  const isValid = title.trim().length >= 1 && title.trim().length <= 255;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid || mutation.isPending) return;
    mutation.mutate(
      { name: title.trim(), projectId },
      {
        onSuccess: () => {
          setTitle('');
          onClose();
        },
      }
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 px-3 py-2">
      <Input
        autoFocus
        placeholder="Sub-issue title..."
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={255}
        className="h-8 text-sm flex-1"
        disabled={mutation.isPending}
        aria-label="Sub-issue title"
      />
      <Button
        type="submit"
        size="sm"
        disabled={!isValid || mutation.isPending}
        className="h-8 px-3"
      >
        {mutation.isPending ? <Loader2 className="size-3.5 animate-spin" /> : 'Add'}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClose}
        className="h-8 px-2"
        aria-label="Cancel"
      >
        <X className="size-3.5" />
      </Button>
    </form>
  );
}

export function SubIssuesList({
  parentId,
  workspaceId,
  workspaceSlug,
  projectId,
  subIssues,
  disabled = false,
}: SubIssuesListProps) {
  const [showForm, setShowForm] = React.useState(false);
  const total = subIssues.length;
  const completed = subIssues.filter((i) => i.state.group === 'completed').length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="space-y-2">
      {total > 0 && (
        <div className="flex items-center gap-3 px-3">
          <Progress value={percent} className="h-1.5 flex-1" />
          <span className="text-xs text-muted-foreground shrink-0">
            {completed} of {total} completed
          </span>
        </div>
      )}

      {total > 0 ? (
        <div className="border border-border-subtle rounded-lg overflow-hidden">
          {subIssues.map((issue) => (
            <SubIssueRow key={issue.id} issue={issue} workspaceSlug={workspaceSlug} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground px-3">No sub-issues</p>
      )}

      {showForm && !disabled && (
        <InlineCreateForm
          workspaceId={workspaceId}
          parentId={parentId}
          projectId={projectId}
          onClose={() => setShowForm(false)}
        />
      )}

      {!showForm && !disabled && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowForm(true)}
          className="text-muted-foreground hover:text-foreground gap-1.5 h-8"
        >
          <Plus className="size-3.5" />
          Add sub-issue
        </Button>
      )}
    </div>
  );
}

export default SubIssuesList;
