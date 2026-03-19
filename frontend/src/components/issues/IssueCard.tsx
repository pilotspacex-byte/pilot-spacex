'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  AlertCircle,
  ArrowUp,
  ArrowDown,
  Minus,
  User,
  Calendar,
  Sparkles,
  ExternalLink,
  Circle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { Issue, IssuePriority } from '@/types';
import { ISSUE_TYPE_CONFIG } from './issue-type-config';

/** Strip HTML tags and collapse whitespace for plain-text preview. */
function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export type IssueCardDensity = 'comfortable' | 'compact' | 'minimal';

export interface IssueCardProps {
  issue: Issue;
  onClick?: (issue: Issue) => void;
  /** Navigate to issue detail page */
  onOpenIssue?: (issue: Issue) => void;
  onDragStart?: (e: React.DragEvent, issue: Issue) => void;
  isDragging?: boolean;
  /** @deprecated Use `density` instead. Maps to density='compact' when true. */
  compact?: boolean;
  density?: IssueCardDensity;
  className?: string;
}

/**
 * Priority icon mapping with colors.
 */
const priorityConfig: Record<
  IssuePriority,
  { icon: React.ElementType; className: string; label: string; dotColor: string }
> = {
  urgent: {
    icon: AlertCircle,
    className: 'text-[var(--color-priority-urgent)]',
    label: 'Urgent',
    dotColor: 'text-[var(--color-priority-urgent)]',
  },
  high: {
    icon: ArrowUp,
    className: 'text-[var(--color-priority-high)]',
    label: 'High',
    dotColor: 'text-[var(--color-priority-high)]',
  },
  medium: {
    icon: Minus,
    className: 'text-[var(--color-priority-medium)]',
    label: 'Medium',
    dotColor: 'text-[var(--color-priority-medium)]',
  },
  low: {
    icon: ArrowDown,
    className: 'text-[var(--color-priority-low)]',
    label: 'Low',
    dotColor: 'text-[var(--color-priority-low)]',
  },
  none: {
    icon: Minus,
    className: 'text-[var(--color-priority-none)]',
    label: 'No priority',
    dotColor: 'text-[var(--color-priority-none)]',
  },
};

/**
 * Issue type icon mapping.
 */
const typeConfig = ISSUE_TYPE_CONFIG;

/**
 * Get user initials for avatar fallback.
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n.charAt(0))
    .filter(Boolean)
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Format relative date.
 */
function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

/**
 * IssueCard displays a single issue in a card format.
 * Supports drag-and-drop for Kanban board functionality.
 *
 * @example
 * ```tsx
 * <IssueCard
 *   issue={issue}
 *   onClick={(issue) => openIssueModal(issue)}
 *   onDragStart={(e, issue) => handleDragStart(e, issue)}
 *   density="compact"
 * />
 * ```
 */
export const IssueCard = observer(function IssueCard({
  issue,
  onClick,
  onOpenIssue,
  onDragStart,
  isDragging = false,
  compact = false,
  density: densityProp,
  className,
}: IssueCardProps) {
  const density: IssueCardDensity = densityProp ?? (compact ? 'compact' : 'comfortable');
  const effectivePriority = issue.priority ?? 'none';
  const PriorityIcon = priorityConfig[effectivePriority].icon;
  const issueType = issue.type ?? 'task';
  const TypeIcon = typeConfig[issueType].icon;

  const handleClick = () => {
    onClick?.(issue);
  };

  const handleDragStart = (e: React.DragEvent) => {
    onDragStart?.(e, issue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.(issue);
    }
  };

  if (density === 'minimal') {
    return (
      <div
        className={cn(
          'group flex items-center gap-2 rounded-md border bg-card px-2 py-1 transition-all',
          'hover:border-primary/50 hover:bg-accent/50',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          isDragging && 'opacity-50 ring-2 ring-primary',
          onClick && 'cursor-pointer',
          className
        )}
        onClick={handleClick}
        onDragStart={handleDragStart}
        onKeyDown={handleKeyDown}
        draggable={!!onDragStart}
        tabIndex={onClick ? 0 : undefined}
        role={onClick ? 'button' : undefined}
        aria-label={`Issue ${issue.identifier}: ${issue.name}`}
      >
        <Circle className={cn('size-2.5 shrink-0', priorityConfig[effectivePriority].dotColor)} />
        <span className="shrink-0 text-[10px] font-medium text-muted-foreground">
          {issue.identifier}
        </span>
        <span className="truncate text-xs font-medium">{issue.name}</span>
      </div>
    );
  }

  if (density === 'compact') {
    return (
      <TooltipProvider>
        <div
          className={cn(
            'group relative rounded-lg border bg-card p-1.5 shadow-sm transition-all',
            'hover:border-primary/50 hover:shadow-md',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            isDragging && 'opacity-50 ring-2 ring-primary',
            onClick && 'cursor-pointer',
            className
          )}
          onClick={handleClick}
          onDragStart={handleDragStart}
          onKeyDown={handleKeyDown}
          draggable={!!onDragStart}
          tabIndex={onClick ? 0 : undefined}
          role={onClick ? 'button' : undefined}
          aria-label={`Issue ${issue.identifier}: ${issue.name}`}
        >
          {/* Header row: type + identifier + title | priority + AI */}
          <div className="mb-1 flex items-center gap-1.5">
            <span className={cn('flex shrink-0 items-center', typeConfig[issueType].className)}>
              <TypeIcon className="size-3.5" />
            </span>
            <span className="shrink-0 text-[10px] font-medium text-muted-foreground">
              {issue.identifier}
            </span>
            <span className="line-clamp-1 min-w-0 flex-1 text-xs font-medium">{issue.name}</span>
            <div className="flex shrink-0 items-center gap-1">
              <span
                className={cn('flex items-center', priorityConfig[effectivePriority].className)}
              >
                <PriorityIcon className="size-3.5" />
              </span>
              {issue.aiGenerated && (
                <span className="flex items-center text-ai">
                  <Sparkles className="size-3" />
                </span>
              )}
            </div>
          </div>

          {/* Meta row: assignee + due date + updated */}
          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
            <div className="flex items-center gap-2">
              {issue.assignee ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Avatar className="size-4">
                      <AvatarImage
                        src={issue.assignee.avatarUrl ?? ''}
                        alt={issue.assignee.displayName ?? issue.assignee.email}
                      />
                      <AvatarFallback className="text-[8px]">
                        {getInitials(issue.assignee.displayName ?? issue.assignee.email)}
                      </AvatarFallback>
                    </Avatar>
                  </TooltipTrigger>
                  <TooltipContent>
                    Assigned to {issue.assignee.displayName ?? issue.assignee.email}
                  </TooltipContent>
                </Tooltip>
              ) : (
                <span className="flex items-center text-muted-foreground/50">
                  <User className="size-3.5" />
                </span>
              )}

              {issue.targetDate && (
                <span className="flex items-center gap-0.5">
                  <Calendar className="size-2.5" />
                  {new Date(issue.targetDate).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              )}
            </div>

            <span className="text-muted-foreground/60">{formatRelativeDate(issue.updatedAt)}</span>
          </div>
        </div>
      </TooltipProvider>
    );
  }

  // density === 'comfortable' (default — original layout)
  return (
    <TooltipProvider>
      <div
        className={cn(
          'group relative rounded-lg border bg-card p-2 shadow-sm transition-all',
          'hover:border-primary/50 hover:shadow-md',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          isDragging && 'opacity-50 ring-2 ring-primary',
          onClick && 'cursor-pointer',
          className
        )}
        onClick={handleClick}
        onDragStart={handleDragStart}
        onKeyDown={handleKeyDown}
        draggable={!!onDragStart}
        tabIndex={onClick ? 0 : undefined}
        role={onClick ? 'button' : undefined}
        aria-label={`Issue ${issue.identifier}: ${issue.name}`}
      >
        {/* Header: Identifier + Priority + AI indicator */}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={cn('flex items-center', typeConfig[issueType].className)}>
                  <TypeIcon className="size-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent>{typeConfig[issueType].label}</TooltipContent>
            </Tooltip>
            <span className="text-[10px] font-medium text-muted-foreground">
              {issue.identifier}
            </span>
          </div>

          <div className="flex items-center gap-1">
            {onOpenIssue && (
              <Button
                variant="ghost"
                size="icon-sm"
                className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenIssue(issue);
                }}
                aria-label={`Open issue ${issue.identifier}`}
              >
                <ExternalLink className="size-3.5" />
              </Button>
            )}
            {issue.aiGenerated && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center text-ai">
                    <Sparkles className="size-3.5" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>AI-generated issue</TooltipContent>
              </Tooltip>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className={cn('flex items-center', priorityConfig[effectivePriority].className)}
                >
                  <PriorityIcon className="size-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent>{priorityConfig[effectivePriority].label}</TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Title */}
        <h4 className="mb-1.5 line-clamp-2 text-xs font-medium leading-snug">{issue.name}</h4>

        {/* Description */}
        {issue.description &&
          (() => {
            const text = stripHtml(issue.description);
            return text ? (
              <p className="mb-2 line-clamp-2 text-[10px] text-muted-foreground">{text}</p>
            ) : null;
          })()}

        {/* Labels */}
        {issue.labels.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {issue.labels.slice(0, 3).map((label) => (
              <Badge
                key={label.id}
                variant="secondary"
                className="text-[10px]"
                style={{
                  backgroundColor: `${label.color}20`,
                  color: label.color,
                  borderColor: `${label.color}40`,
                }}
              >
                {label.name}
              </Badge>
            ))}
            {issue.labels.length > 3 && (
              <Badge variant="outline" className="text-[10px]">
                +{issue.labels.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Footer: Assignee + Due date + Updated */}
        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <div className="flex items-center gap-2">
            {issue.assignee ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Avatar className="size-5">
                    <AvatarImage
                      src={issue.assignee.avatarUrl ?? ''}
                      alt={issue.assignee.displayName ?? issue.assignee.email}
                    />
                    <AvatarFallback className="text-[10px]">
                      {getInitials(issue.assignee.displayName ?? issue.assignee.email)}
                    </AvatarFallback>
                  </Avatar>
                </TooltipTrigger>
                <TooltipContent>
                  Assigned to {issue.assignee.displayName ?? issue.assignee.email}
                </TooltipContent>
              </Tooltip>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center text-muted-foreground/50">
                    <User className="size-4" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>Unassigned</TooltipContent>
              </Tooltip>
            )}

            {issue.targetDate && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center gap-1">
                    <Calendar className="size-3" />
                    {new Date(issue.targetDate).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  Due {new Date(issue.targetDate).toLocaleDateString()}
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          <span className="text-muted-foreground/60">{formatRelativeDate(issue.updatedAt)}</span>
        </div>
      </div>
    </TooltipProvider>
  );
});

export default IssueCard;
