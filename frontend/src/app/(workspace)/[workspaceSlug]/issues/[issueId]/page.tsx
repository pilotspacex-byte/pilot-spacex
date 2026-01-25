'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  MoreHorizontal,
  Trash2,
  Copy,
  ExternalLink,
  Sparkles,
  User,
  Calendar,
  Link as LinkIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { IssueStateSelect, IssuePrioritySelect } from '@/components/issues';
import { AIConfidenceTag } from '@/components/ai/AIConfidenceTag';
import { useStore } from '@/stores';
import type { IssueState, IssuePriority } from '@/types';

/**
 * Get user initials for avatar fallback.
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Format date for display.
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format relative time.
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateStr);
}

/**
 * IssueDetailPage displays a single issue with full details.
 * Shows AI context, activity timeline, and related items.
 */
const IssueDetailPage = observer(function IssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;
  const issueId = params.issueId as string;

  const { issueStore, workspaceStore } = useStore();

  const workspace = workspaceStore.currentWorkspace;
  const issue = issueStore.currentIssue;

  // Load issue on mount
  React.useEffect(() => {
    if (workspace?.id && issueId) {
      issueStore.loadIssue(workspace.id, issueId);
    }
  }, [workspace?.id, issueId, issueStore]);

  // Handlers
  const handleBack = () => {
    router.push(`/${workspaceSlug}/issues`);
  };

  const handleStateChange = async (state: IssueState) => {
    if (workspace?.id && issue?.id) {
      await issueStore.updateIssueState(workspace.id, issue.id, state);
    }
  };

  const handlePriorityChange = async (priority: IssuePriority) => {
    if (workspace?.id && issue?.id) {
      await issueStore.updateIssue(workspace.id, issue.id, { priority });
    }
  };

  const handleDelete = async () => {
    if (workspace?.id && issue?.id) {
      const confirmed = window.confirm('Are you sure you want to delete this issue?');
      if (confirmed) {
        await issueStore.deleteIssue(workspace.id, issue.id);
        router.push(`/${workspaceSlug}/issues`);
      }
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
  };

  if (issueStore.isLoading) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-4 border-b px-6 py-4">
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="flex flex-1 p-6">
          <div className="flex-1 space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="w-80 space-y-4 border-l pl-6">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!issue) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <p className="text-lg font-medium">Issue not found</p>
        <Button variant="link" onClick={handleBack}>
          Back to issues
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon-sm" onClick={handleBack}>
            <ArrowLeft className="size-4" />
          </Button>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">{issue.identifier}</span>
            {issue.aiGenerated && (
              <Badge variant="outline" className="gap-1 text-ai border-ai/30">
                <Sparkles className="size-3" />
                AI Generated
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleCopyLink}>
            <Copy className="mr-2 size-4" />
            Copy link
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleCopyLink}>
                <LinkIcon className="mr-2 size-4" />
                Copy link
              </DropdownMenuItem>
              <DropdownMenuItem>
                <ExternalLink className="mr-2 size-4" />
                Open in new tab
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 size-4" />
                Delete issue
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl space-y-6">
            {/* Title */}
            <h1 className="text-2xl font-semibold">{issue.title}</h1>

            {/* Description */}
            {issue.description ? (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p>{issue.description}</p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">No description provided</p>
            )}

            <Separator />

            {/* AI Context Section */}
            {issueStore.aiContext && (
              <div className="space-y-4">
                <h2 className="flex items-center gap-2 text-lg font-semibold">
                  <Sparkles className="size-5 text-ai" />
                  AI Context
                </h2>

                {/* Related Docs */}
                {issueStore.aiContext.relatedDocs.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Related Documents</h3>
                    <ul className="space-y-1">
                      {issueStore.aiContext.relatedDocs.map((doc, i) => (
                        <li key={i} className="text-sm text-muted-foreground">
                          {doc}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Code References */}
                {issueStore.aiContext.codeReferences.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Code References</h3>
                    <ul className="space-y-2">
                      {issueStore.aiContext.codeReferences.map((ref, i) => (
                        <li key={i} className="rounded-md border bg-muted/50 p-2 text-sm">
                          <div className="flex items-center justify-between">
                            <code className="text-xs">{ref.filePath}</code>
                            <AIConfidenceTag confidence={ref.relevance} className="text-[10px]" />
                          </div>
                          <span className="text-xs text-muted-foreground">
                            Lines {ref.lineStart}-{ref.lineEnd}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggested Tasks */}
                {issueStore.aiContext.suggestedTasks.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Suggested Tasks</h3>
                    <ul className="space-y-2">
                      {issueStore.aiContext.suggestedTasks.map((task, i) => (
                        <li key={i} className="rounded-md border p-2">
                          <p className="text-sm font-medium">{task.title}</p>
                          <p className="text-xs text-muted-foreground">{task.description}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Claude Code Prompts */}
                {issueStore.aiContext.claudeCodePrompts.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Claude Code Prompts</h3>
                    <ul className="space-y-2">
                      {issueStore.aiContext.claudeCodePrompts.map((prompt, i) => (
                        <li key={i} className="rounded-md border bg-muted/50 p-2">
                          <code className="text-xs whitespace-pre-wrap">{prompt}</code>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Activity Timeline placeholder */}
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Activity</h2>
              <p className="text-sm text-muted-foreground">Activity timeline coming soon...</p>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-80 shrink-0 border-l overflow-y-auto">
          <div className="space-y-6 p-6">
            {/* State */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">State</label>
              <IssueStateSelect
                value={issue.state}
                onChange={handleStateChange}
                className="w-full"
              />
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">
                Priority
              </label>
              <IssuePrioritySelect
                value={issue.priority}
                onChange={handlePriorityChange}
                className="w-full"
              />
            </div>

            <Separator />

            {/* Assignee */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">
                Assignee
              </label>
              {issue.assignee ? (
                <div className="flex items-center gap-2">
                  <Avatar className="size-6">
                    <AvatarImage src={issue.assignee.avatarUrl} alt={issue.assignee.name} />
                    <AvatarFallback className="text-[10px]">
                      {getInitials(issue.assignee.name)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm">{issue.assignee.name}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <User className="size-4" />
                  <span className="text-sm">Unassigned</span>
                </div>
              )}
            </div>

            {/* Reporter */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">
                Reporter
              </label>
              {issue.reporter ? (
                <div className="flex items-center gap-2">
                  <Avatar className="size-6">
                    <AvatarImage src={issue.reporter.avatarUrl} alt={issue.reporter.name} />
                    <AvatarFallback className="text-[10px]">
                      {getInitials(issue.reporter.name)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm">{issue.reporter.name}</span>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">Unknown</span>
              )}
            </div>

            <Separator />

            {/* Labels */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">Labels</label>
              {issue.labels.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {issue.labels.map((label) => (
                    <Badge
                      key={label.id}
                      variant="secondary"
                      style={{
                        backgroundColor: `${label.color}20`,
                        color: label.color,
                        borderColor: `${label.color}40`,
                      }}
                    >
                      {label.name}
                    </Badge>
                  ))}
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">No labels</span>
              )}
            </div>

            {/* Due date */}
            {issue.dueDate && (
              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground uppercase">
                  Due Date
                </label>
                <div className="flex items-center gap-2">
                  <Calendar className="size-4 text-muted-foreground" />
                  <span className="text-sm">{formatDate(issue.dueDate)}</span>
                </div>
              </div>
            )}

            <Separator />

            {/* Metadata */}
            <div className="space-y-3 text-xs text-muted-foreground">
              <div className="flex items-center justify-between">
                <span>Created</span>
                <span>{formatRelativeTime(issue.createdAt)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Updated</span>
                <span>{formatRelativeTime(issue.updatedAt)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

export default IssueDetailPage;
