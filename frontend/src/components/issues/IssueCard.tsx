'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  AlertCircle,
  ArrowUp,
  ArrowDown,
  Minus,
  Bug,
  Lightbulb,
  Wrench,
  CheckSquare,
  User,
  Calendar,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { Issue, IssuePriority, IssueType } from '@/types';

export interface IssueCardProps {
  issue: Issue;
  onClick?: (issue: Issue) => void;
  /** Navigate to issue detail page */
  onOpenIssue?: (issue: Issue) => void;
  onDragStart?: (e: React.DragEvent, issue: Issue) => void;
  isDragging?: boolean;
  compact?: boolean;
  className?: string;
}

/**
 * Priority icon mapping with colors.
 */
const priorityConfig: Record<
  IssuePriority,
  { icon: React.ElementType; className: string; label: string }
> = {
  urgent: { icon: AlertCircle, className: 'text-red-500', label: 'Urgent' },
  high: { icon: ArrowUp, className: 'text-orange-500', label: 'High' },
  medium: { icon: Minus, className: 'text-yellow-500', label: 'Medium' },
  low: { icon: ArrowDown, className: 'text-blue-500', label: 'Low' },
  none: { icon: Minus, className: 'text-gray-400', label: 'No priority' },
};

/**
 * Issue type icon mapping.
 */
const typeConfig: Record<IssueType, { icon: React.ElementType; className: string; label: string }> =
  {
    bug: { icon: Bug, className: 'text-red-500', label: 'Bug' },
    feature: { icon: Lightbulb, className: 'text-purple-500', label: 'Feature' },
    improvement: { icon: Wrench, className: 'text-blue-500', label: 'Improvement' },
    task: { icon: CheckSquare, className: 'text-gray-500', label: 'Task' },
  };

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
  className,
}: IssueCardProps) {
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

  return (
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
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={cn('flex items-center', typeConfig[issueType].className)}>
                  <TypeIcon className="size-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent>{typeConfig[issueType].label}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <span className="text-[10px] font-medium text-muted-foreground">{issue.identifier}</span>
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
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center text-ai">
                    <Sparkles className="size-3.5" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>AI-generated issue</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          <TooltipProvider>
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
          </TooltipProvider>
        </div>
      </div>

      {/* Title */}
      <h4 className="mb-1.5 line-clamp-2 text-xs font-medium leading-snug">{issue.name}</h4>

      {/* Description (if not compact) */}
      {!compact && issue.description && (
        <p className="mb-2 line-clamp-2 text-[10px] text-muted-foreground">{issue.description}</p>
      )}

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
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Avatar className="size-5">
                    <AvatarImage src="" alt={issue.assignee.displayName ?? issue.assignee.email} />
                    <AvatarFallback className="text-[10px]">
                      {getInitials(issue.assignee.displayName ?? issue.assignee.email)}
                    </AvatarFallback>
                  </Avatar>
                </TooltipTrigger>
                <TooltipContent>
                  Assigned to {issue.assignee.displayName ?? issue.assignee.email}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center text-muted-foreground/50">
                    <User className="size-4" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>Unassigned</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          {issue.targetDate && (
            <TooltipProvider>
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
            </TooltipProvider>
          )}
        </div>

        <span className="text-muted-foreground/60">{formatRelativeDate(issue.updatedAt)}</span>
      </div>
    </div>
  );
});

export default IssueCard;
