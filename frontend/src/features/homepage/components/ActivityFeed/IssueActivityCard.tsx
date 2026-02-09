'use client';

/**
 * IssueActivityCard (H030) — Activity card for issues.
 * Shows identifier, title, state dot/badge, priority border, assignee avatar, timestamp.
 */

import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import type { ActivityCardIssue, IssuePriority } from '../../types';

interface IssueActivityCardProps {
  card: ActivityCardIssue;
  workspaceSlug: string;
}

/** Maps priority level to Tailwind border-l color class */
const PRIORITY_BORDER: Record<IssuePriority, string> = {
  urgent: 'border-l-priority-urgent',
  high: 'border-l-priority-high',
  medium: 'border-l-priority-medium',
  low: 'border-l-priority-low',
  none: 'border-l-priority-none',
};

/** Maps state group to Tailwind bg color class for the dot */
const STATE_DOT_COLOR: Record<string, string> = {
  backlog: 'bg-state-backlog',
  unstarted: 'bg-state-todo',
  started: 'bg-state-in-progress',
  review: 'bg-state-in-review',
  completed: 'bg-state-done',
  cancelled: 'bg-state-cancelled',
};

function getStateDotColor(group: string): string {
  return STATE_DOT_COLOR[group] ?? 'bg-state-backlog';
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    const first = parts[0]?.[0] ?? '';
    const last = parts[parts.length - 1]?.[0] ?? '';
    return (first + last).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function IssueActivityCard({ card, workspaceSlug }: IssueActivityCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/${workspaceSlug}/issues/${card.id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <article
      role="article"
      aria-label={`Issue: ${card.identifier} ${card.title}${card.state ? `, state: ${card.state.name}` : ''}`}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'group relative flex h-[140px] cursor-pointer flex-col rounded-md',
        'border border-border-subtle border-l-4 bg-card p-4',
        PRIORITY_BORDER[card.priority],
        'motion-safe:transition-all motion-safe:duration-200',
        'hover:-translate-y-0.5 hover:shadow-warm-md',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
      )}
    >
      {/* Header: state dot + identifier + title */}
      <div className="flex items-start gap-2">
        <span
          className={cn(
            'mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full',
            getStateDotColor(card.state?.group ?? 'backlog')
          )}
          aria-hidden="true"
        />
        <div className="flex min-w-0 flex-1 items-baseline gap-1.5">
          <span className="shrink-0 text-xs font-mono text-muted-foreground">
            {card.identifier}
          </span>
          <h3 className="line-clamp-1 text-sm font-medium text-foreground">{card.title}</h3>
        </div>
      </div>

      {/* Meta: project + state badge */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {card.project && (
          <Badge variant="secondary" className="text-xs">
            {card.project.identifier}
          </Badge>
        )}
        {card.state && (
          <Badge
            variant="outline"
            className="text-xs"
            style={{ color: card.state.color, borderColor: `${card.state.color}40` }}
          >
            {card.state.name}
          </Badge>
        )}
      </div>

      {/* Footer: activity summary + assignee + timestamp */}
      <div className="mt-auto flex items-center gap-2">
        <span className="line-clamp-1 flex-1 text-xs text-muted-foreground">
          {card.last_activity}
        </span>

        {card.assignee && (
          <Avatar className="h-6 w-6">
            {card.assignee.avatar_url ? (
              <AvatarImage src={card.assignee.avatar_url} alt={card.assignee.name} />
            ) : null}
            <AvatarFallback className="text-[10px]">
              {getInitials(card.assignee.name)}
            </AvatarFallback>
          </Avatar>
        )}

        <time dateTime={card.updated_at} className="shrink-0 text-xs text-muted-foreground">
          {formatDistanceToNow(new Date(card.updated_at), { addSuffix: true })}
        </time>
      </div>
    </article>
  );
}
