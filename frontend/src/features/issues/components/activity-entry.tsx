/**
 * ActivityEntry component for issue activity timeline.
 *
 * Renders activity items: comments, state changes, assignments,
 * labels, priority changes, and creation events.
 *
 * @see T035 - Issue Detail Page activity timeline
 */
'use client';

import { Settings, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Activity } from '@/types';

export interface ActivityEntryProps {
  activity: Activity;
  isLast?: boolean;
}

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

function buildDescription(activity: Activity): string {
  const actor = getActorName(activity.actor);
  const { activityType, field, oldValue, newValue } = activity;

  if (activityType === 'created') return `${actor} created this issue`;
  if (activityType === 'comment') return '';

  if (field === 'state') {
    return `${actor} changed state from ${oldValue ?? '?'} to ${newValue ?? '?'}`;
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

export function ActivityEntry({ activity, isLast = false }: ActivityEntryProps) {
  const isComment = activity.activityType === 'comment';
  const actor = activity.actor;
  const isAI = isAIGenerated(activity);

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
          isAI
            ? 'bg-[#6B8FAD]/15 text-[#6B8FAD] border border-[#6B8FAD]/30'
            : actor
              ? 'bg-primary/10 text-primary border border-primary/20'
              : 'bg-muted text-muted-foreground border border-border'
        )}
        aria-hidden="true"
      >
        {isAI ? (
          <Sparkles className="h-3.5 w-3.5" />
        ) : actor ? (
          getInitial(actor)
        ) : (
          <Settings className="h-3.5 w-3.5" />
        )}
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
