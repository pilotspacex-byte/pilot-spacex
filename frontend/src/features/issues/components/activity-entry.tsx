/**
 * ActivityEntry component for issue activity timeline.
 *
 * Renders activity items: comments, state changes, assignments,
 * labels, priority changes, creation events, and GitHub integration
 * events (commit linked, PR opened/merged/closed).
 *
 * @see T035 - Issue Detail Page activity timeline
 * @see T183 - LinkCommitService (backend verb: "linked_to_note" + metadata.link_type)
 */
'use client';

import {
  CheckCircle2,
  ExternalLink,
  GitCommitHorizontal,
  GitMerge,
  GitPullRequest,
  Settings,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Activity } from '@/types';

export interface ActivityEntryProps {
  activity: Activity;
  isLast?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getInitial(actor: Activity['actor']): string {
  if (!actor) return '';
  const name = actor.displayName || actor.email;
  return name.charAt(0).toUpperCase();
}

function getActorName(actor: Activity['actor']): string {
  if (!actor) return 'System';
  return actor.displayName || actor.email;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;

  const date = new Date(dateStr);
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  return `${months[date.getMonth()]} ${date.getDate()}`;
}

function isAIGenerated(activity: Activity): boolean {
  if (!activity.metadata) return false;
  return (
    activity.metadata.ai === true ||
    activity.metadata.isAiGenerated === true ||
    activity.metadata.agent != null ||
    activity.metadata.source === 'ai'
  );
}

/** Returns true when the activity is a GitHub commit link event. */
function isCommitLinked(activity: Activity): boolean {
  return activity.activityType === 'linked_to_note' && activity.metadata?.link_type === 'commit';
}

/** Returns true when the activity is a GitHub PR link event. */
function isPRLinked(activity: Activity): boolean {
  return (
    activity.activityType === 'linked_to_note' && activity.metadata?.link_type === 'pull_request'
  );
}

/** Returns true when a state change was triggered by a PR auto-transition. */
function isAutoTransition(activity: Activity): boolean {
  return activity.activityType === 'state_changed' && activity.metadata?.auto_transition === true;
}

function buildDescription(activity: Activity): string {
  const actor = getActorName(activity.actor);
  const { activityType, field, oldValue, newValue } = activity;

  if (activityType === 'created') return `${actor} created this issue`;
  if (activityType === 'comment') return '';

  if (field === 'state') {
    const base = `${actor} changed state from ${oldValue ?? '?'} to ${newValue ?? '?'}`;
    if (isAutoTransition(activity)) {
      const prNum = activity.metadata?.pr_number as number | undefined;
      return prNum ? `${base} (auto · PR #${prNum})` : `${base} (auto-transition)`;
    }
    return base;
  }
  if (field === 'assignee') {
    return newValue ? `${actor} assigned to ${newValue}` : `${actor} removed assignee`;
  }
  if (field === 'labels') {
    return newValue
      ? `${actor} added label ${newValue}`
      : `${actor} removed label ${oldValue ?? 'unknown'}`;
  }
  if (field === 'priority') {
    return `${actor} changed priority from ${oldValue ?? '?'} to ${newValue ?? '?'}`;
  }

  return `${actor} updated ${field ?? 'issue'}`;
}

// ---------------------------------------------------------------------------
// GitHub sub-components
// ---------------------------------------------------------------------------

interface CommitLinkedContentProps {
  activity: Activity;
}

function CommitLinkedContent({ activity }: CommitLinkedContentProps) {
  const meta = activity.metadata ?? {};
  const sha = (meta.sha as string | undefined) ?? activity.newValue ?? '';
  const shortSha = sha.slice(0, 8);
  const message = (meta.commit_message as string | undefined) ?? '';
  const truncatedMessage = message.length > 60 ? `${message.slice(0, 60)}…` : message;
  const externalUrl = meta.external_url as string | undefined;
  const repository = meta.repository as string | undefined;
  const authorName = getActorName(activity.actor);

  return (
    <div className="flex items-start gap-2 min-h-[32px] flex-wrap">
      <div className="flex items-center gap-1.5 flex-wrap">
        {externalUrl ? (
          <a
            href={externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`View commit ${shortSha} on GitHub`}
            className="group inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded"
          >
            {shortSha}
            <ExternalLink
              className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity"
              aria-hidden="true"
            />
          </a>
        ) : (
          <span className="font-mono text-xs text-primary">{shortSha}</span>
        )}
        {truncatedMessage && (
          <span className="text-sm text-muted-foreground">· {truncatedMessage}</span>
        )}
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground ml-auto flex-shrink-0">
        {repository && <span className="hidden sm:inline">{repository} ·</span>}
        <span>{authorName}</span>
        <span>·</span>
        <time dateTime={activity.createdAt}>{formatRelativeTime(activity.createdAt)}</time>
      </div>
    </div>
  );
}

type PRStatus = 'open' | 'merged' | 'closed';

interface PRLinkedContentProps {
  activity: Activity;
}

function PRLinkedContent({ activity }: PRLinkedContentProps) {
  const meta = activity.metadata ?? {};
  const prNumberRaw = meta.pr_number as number | string | undefined;
  // newValue is stored as "#123" by the backend
  const prNumber = prNumberRaw ?? activity.newValue?.replace('#', '') ?? '';
  const prTitle = (meta.pr_title as string | undefined) ?? '';
  const externalUrl = meta.external_url as string | undefined;

  // Derive status from metadata: the backend stores pr_state or state
  const rawState = (meta.pr_state ?? meta.state) as string | undefined;
  const status: PRStatus =
    rawState === 'merged' ? 'merged' : rawState === 'closed' ? 'closed' : 'open';

  const statusConfig: Record<PRStatus, { label: string; badgeClass: string }> = {
    open: {
      label: 'open',
      badgeClass: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    },
    merged: {
      label: 'merged',
      badgeClass: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    },
    closed: {
      label: 'closed',
      badgeClass: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    },
  };

  const { label, badgeClass } = statusConfig[status];
  const displayTitle = prTitle.length > 60 ? `${prTitle.slice(0, 60)}…` : prTitle;

  return (
    <div className="flex items-start gap-2 min-h-[32px] flex-wrap">
      <div className="flex items-center gap-1.5 flex-wrap">
        {externalUrl ? (
          <a
            href={externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`View PR #${prNumber} on GitHub`}
            className="group inline-flex items-center gap-1 text-sm text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded"
          >
            PR #{prNumber}
            <ExternalLink
              className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity"
              aria-hidden="true"
            />
          </a>
        ) : (
          <span className="text-sm text-primary">PR #{prNumber}</span>
        )}
        {displayTitle && <span className="text-sm text-muted-foreground">· {displayTitle}</span>}
        <span
          className={cn(
            'inline-flex items-center rounded-full px-1.5 py-0.5 text-[11px] font-medium leading-none',
            badgeClass
          )}
        >
          {label}
        </span>
      </div>
      <time
        dateTime={activity.createdAt}
        className="text-xs text-muted-foreground flex-shrink-0 ml-auto"
      >
        {formatRelativeTime(activity.createdAt)}
      </time>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI Review sub-component
// ---------------------------------------------------------------------------

/** Returns true when the activity is an AI PR review result. */
function isAIReview(activity: Activity): boolean {
  return activity.activityType === 'ai_review';
}

interface AIReviewContentProps {
  activity: Activity;
}

function AIReviewContent({ activity }: AIReviewContentProps) {
  const meta = activity.metadata ?? {};
  const critical = typeof meta.critical === 'number' ? meta.critical : 0;
  const warning = typeof meta.warning === 'number' ? meta.warning : 0;
  const info = typeof meta.info === 'number' ? meta.info : 0;
  const prUrl = typeof meta.pr_url === 'string' ? meta.pr_url : undefined;
  const approved = meta.approved === true;

  // Badge color: red if any critical, yellow if any warning, green otherwise.
  const badgeClass =
    critical > 0
      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
      : warning > 0
        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
        : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';

  const severityParts: string[] = [];
  if (critical > 0) severityParts.push(`${critical} Critical`);
  if (warning > 0) severityParts.push(`${warning} Warning`);
  if (info > 0) severityParts.push(`${info} Info`);
  const severitySummary = severityParts.length > 0 ? severityParts.join(' · ') : 'No findings';

  return (
    <div className="flex flex-col gap-1.5 min-h-[32px]">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-medium text-foreground">AI Code Review</span>
        <span
          className={cn(
            'inline-flex items-center rounded-full px-1.5 py-0.5 text-[11px] font-medium leading-none',
            badgeClass
          )}
        >
          {approved ? 'Approved' : 'Changes Requested'}
        </span>
        <time
          dateTime={activity.createdAt}
          className="text-xs text-muted-foreground flex-shrink-0 ml-auto"
        >
          {formatRelativeTime(activity.createdAt)}
        </time>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-muted-foreground">{severitySummary}</span>
        {prUrl && (
          <a
            href={prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded ml-auto"
            aria-label="View pull request on GitHub"
          >
            View on GitHub
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Avatar icon resolution
// ---------------------------------------------------------------------------

interface AvatarConfig {
  wrapperClass: string;
  content: React.ReactNode;
}

function resolveAvatarConfig(
  activity: Activity,
  isAI: boolean,
  actor: Activity['actor']
): AvatarConfig {
  if (isCommitLinked(activity)) {
    return {
      wrapperClass: 'bg-muted text-muted-foreground border border-border',
      content: <GitCommitHorizontal className="h-3.5 w-3.5" />,
    };
  }

  if (isAIReview(activity)) {
    const meta = activity.metadata ?? {};
    const approved = meta.approved === true;
    return {
      wrapperClass: approved
        ? 'bg-green-100 text-green-700 border border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800'
        : 'bg-[#6B8FAD]/15 text-[#6B8FAD] border border-[#6B8FAD]/30',
      content: approved ? (
        <CheckCircle2 className="h-3.5 w-3.5" />
      ) : (
        <Sparkles className="h-3.5 w-3.5" />
      ),
    };
  }

  if (isPRLinked(activity)) {
    const meta = activity.metadata ?? {};
    const rawState = (meta.pr_state ?? meta.state) as string | undefined;

    if (rawState === 'merged') {
      return {
        wrapperClass:
          'bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800',
        content: <GitMerge className="h-3.5 w-3.5" />,
      };
    }
    if (rawState === 'closed') {
      return {
        wrapperClass:
          'bg-red-100 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
        content: <XCircle className="h-3.5 w-3.5" />,
      };
    }
    // open (default)
    return {
      wrapperClass:
        'bg-green-100 text-green-700 border border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
      content: <GitPullRequest className="h-3.5 w-3.5" />,
    };
  }

  if (isAI) {
    return {
      wrapperClass: 'bg-[#6B8FAD]/15 text-[#6B8FAD] border border-[#6B8FAD]/30',
      content: <Sparkles className="h-3.5 w-3.5" />,
    };
  }

  if (actor) {
    return {
      wrapperClass: 'bg-primary/10 text-primary border border-primary/20',
      content: getInitial(actor),
    };
  }

  return {
    wrapperClass: 'bg-muted text-muted-foreground border border-border',
    content: <Settings className="h-3.5 w-3.5" />,
  };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ActivityEntry({ activity, isLast = false }: ActivityEntryProps) {
  const isComment = activity.activityType === 'comment_added';
  const actor = activity.actor;
  const isAI = isAIGenerated(activity);
  const isGitHubEvent = isCommitLinked(activity) || isPRLinked(activity);
  const isReview = isAIReview(activity);

  const { wrapperClass, content } = resolveAvatarConfig(activity, isAI, actor);

  return (
    <div className="relative flex gap-3">
      {/* Timeline connector */}
      {!isLast && (
        <div className="absolute left-4 top-9 bottom-0 w-px bg-border" aria-hidden="true" />
      )}

      {/* Avatar */}
      <div
        className={cn(
          'relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium',
          wrapperClass
        )}
        aria-hidden="true"
      >
        {content}
      </div>

      {/* Content */}
      <div className={cn('flex-1 min-w-0 pb-5', isLast && 'pb-0')}>
        {isComment ? (
          <div className="rounded-lg border border-border bg-background-subtle p-3">
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="text-sm font-medium text-foreground truncate">
                {getActorName(actor)}
              </span>
              <time
                dateTime={activity.createdAt}
                className="text-xs text-muted-foreground flex-shrink-0"
              >
                {formatRelativeTime(activity.createdAt)}
              </time>
            </div>
            <p className="text-sm text-foreground whitespace-pre-wrap break-words">
              {activity.comment}
            </p>
          </div>
        ) : isReview ? (
          <div className="flex-1 min-w-0">
            <AIReviewContent activity={activity} />
          </div>
        ) : isGitHubEvent ? (
          <div className="flex-1 min-w-0">
            {isCommitLinked(activity) ? (
              <CommitLinkedContent activity={activity} />
            ) : (
              <PRLinkedContent activity={activity} />
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 min-h-[32px]">
            <p className="text-sm text-muted-foreground">{buildDescription(activity)}</p>
            <time
              dateTime={activity.createdAt}
              className="text-xs text-muted-foreground flex-shrink-0 ml-auto"
            >
              {formatRelativeTime(activity.createdAt)}
            </time>
          </div>
        )}
      </div>
    </div>
  );
}
