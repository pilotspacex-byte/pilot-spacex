'use client';

import * as React from 'react';
import {
  Bug,
  Lightbulb,
  Wrench,
  CheckSquare,
  ChevronRight,
  User,
  Calendar,
  AlertCircle,
  ArrowUp,
  Minus,
  ArrowDown,
  Circle,
  CircleDashed,
  PlayCircle,
  CircleDot,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { Issue, IssueState, IssuePriority, IssueType } from '@/types';

const typeIcons: Record<IssueType, { icon: React.ElementType; className: string }> = {
  bug: { icon: Bug, className: 'text-red-500' },
  feature: { icon: Lightbulb, className: 'text-purple-500' },
  improvement: { icon: Wrench, className: 'text-blue-500' },
  task: { icon: CheckSquare, className: 'text-gray-500' },
};

const stateConfig: Record<
  IssueState,
  { icon: React.ElementType; className: string; label: string }
> = {
  backlog: { icon: CircleDashed, className: 'text-[var(--color-state-backlog)]', label: 'Backlog' },
  todo: { icon: Circle, className: 'text-[var(--color-state-todo)]', label: 'Todo' },
  in_progress: {
    icon: PlayCircle,
    className: 'text-[var(--color-state-in-progress)]',
    label: 'In Progress',
  },
  in_review: {
    icon: CircleDot,
    className: 'text-[var(--color-state-in-review)]',
    label: 'In Review',
  },
  done: { icon: CheckCircle2, className: 'text-[var(--color-state-done)]', label: 'Done' },
  cancelled: {
    icon: XCircle,
    className: 'text-[var(--color-state-cancelled)]',
    label: 'Cancelled',
  },
};

const priorityConfig: Record<
  IssuePriority,
  { icon: React.ElementType; className: string; label: string }
> = {
  urgent: { icon: AlertCircle, className: 'text-[var(--color-priority-urgent)]', label: 'Urgent' },
  high: { icon: ArrowUp, className: 'text-[var(--color-priority-high)]', label: 'High' },
  medium: { icon: Minus, className: 'text-[var(--color-priority-medium)]', label: 'Medium' },
  low: { icon: ArrowDown, className: 'text-[var(--color-priority-low)]', label: 'Low' },
  none: { icon: Minus, className: 'text-[var(--color-priority-none)]', label: 'None' },
};

function getIssueStateName(issue: Issue): IssueState {
  return (issue.state?.name?.toLowerCase().replace(/\s+/g, '_') as IssueState) ?? 'backlog';
}

interface ListRowProps {
  issue: Issue;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onStateChange?: (issueId: string, state: IssueState) => void;
  onPriorityChange?: (issueId: string, priority: IssuePriority) => void;
  onNavigate?: (issue: Issue) => void;
  indent?: number;
  showExpandToggle?: boolean;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export function ListRow({
  issue,
  isSelected,
  onToggleSelect,
  onStateChange,
  onPriorityChange,
  onNavigate,
  indent = 0,
  showExpandToggle = false,
  isExpanded = false,
  onToggleExpand,
}: ListRowProps) {
  const issueType = issue.type ?? 'task';
  const TypeIcon = typeIcons[issueType].icon;
  const stateName = getIssueStateName(issue);
  const stateInfo = stateConfig[stateName];
  const StateIcon = stateInfo.icon;
  const priority = issue.priority ?? 'none';
  const priorityInfo = priorityConfig[priority];
  const PriorityIcon = priorityInfo.icon;

  return (
    <div
      className={cn(
        'group flex min-h-[44px] items-center gap-2 border-b px-3 py-1.5',
        'hover:bg-accent/50 transition-colors',
        isSelected && 'bg-accent/30'
      )}
      style={{ paddingLeft: `${12 + indent * 16}px` }}
    >
      {/* Checkbox */}
      <Checkbox
        checked={isSelected}
        onCheckedChange={() => onToggleSelect(issue.id)}
        className="shrink-0"
        aria-label={`Select ${issue.identifier}`}
      />

      {/* Expand toggle for sub-issues */}
      {showExpandToggle ? (
        <button
          onClick={onToggleExpand}
          className="shrink-0 p-0.5"
          aria-expanded={isExpanded}
          aria-label={`${isExpanded ? 'Collapse' : 'Expand'} sub-issues`}
        >
          <ChevronRight
            className={cn('size-3.5 transition-transform', isExpanded && 'rotate-90')}
          />
        </button>
      ) : (
        <div className="w-4 shrink-0" />
      )}

      {/* Type icon */}
      <TypeIcon className={cn('size-4 shrink-0', typeIcons[issueType].className)} />

      {/* Identifier */}
      <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
        {issue.identifier}
      </span>

      {/* Title */}
      <button
        onClick={() => onNavigate?.(issue)}
        className="min-w-0 flex-1 truncate text-left text-sm font-medium hover:text-primary transition-colors"
      >
        {issue.name}
      </button>

      {/* State badge */}
      {onStateChange ? (
        <Popover>
          <PopoverTrigger asChild>
            <button
              className={cn(
                'flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px]',
                'hover:bg-accent transition-colors'
              )}
              aria-label={`Change state from ${stateInfo.label}`}
            >
              <StateIcon className={cn('size-3.5', stateInfo.className)} />
              <span className="hidden lg:inline">{stateInfo.label}</span>
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-40 p-1" align="start">
            {(Object.entries(stateConfig) as [IssueState, typeof stateInfo][]).map(([key, cfg]) => {
              const SIcon = cfg.icon;
              return (
                <button
                  key={key}
                  onClick={() => onStateChange(issue.id, key)}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-xs hover:bg-accent',
                    key === stateName && 'bg-accent'
                  )}
                >
                  <SIcon className={cn('size-3.5', cfg.className)} />
                  {cfg.label}
                </button>
              );
            })}
          </PopoverContent>
        </Popover>
      ) : (
        <span className="flex shrink-0 items-center gap-1 text-[11px]">
          <StateIcon className={cn('size-3.5', stateInfo.className)} />
        </span>
      )}

      {/* Priority badge */}
      {onPriorityChange ? (
        <Popover>
          <PopoverTrigger asChild>
            <button
              className="flex shrink-0 items-center gap-1 rounded-md px-1 py-0.5 hover:bg-accent transition-colors"
              aria-label={`Change priority from ${priorityInfo.label}`}
            >
              <PriorityIcon className={cn('size-3.5', priorityInfo.className)} />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-36 p-1" align="start">
            {(Object.entries(priorityConfig) as [IssuePriority, typeof priorityInfo][]).map(
              ([key, cfg]) => {
                const PIcon = cfg.icon;
                return (
                  <button
                    key={key}
                    onClick={() => onPriorityChange(issue.id, key)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-xs hover:bg-accent',
                      key === priority && 'bg-accent'
                    )}
                  >
                    <PIcon className={cn('size-3.5', cfg.className)} />
                    {cfg.label}
                  </button>
                );
              }
            )}
          </PopoverContent>
        </Popover>
      ) : (
        <span className="flex shrink-0 items-center gap-1 px-1 py-0.5">
          <PriorityIcon className={cn('size-3.5', priorityInfo.className)} />
        </span>
      )}

      {/* Assignee */}
      <div className="shrink-0">
        {issue.assignee ? (
          <Avatar className="size-5">
            <AvatarFallback className="text-[9px]">
              {(issue.assignee.displayName ?? issue.assignee.email).charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
        ) : (
          <User className="size-4 text-muted-foreground/50" />
        )}
      </div>

      {/* Labels */}
      <div className="hidden shrink-0 items-center gap-1 md:flex">
        {issue.labels.slice(0, 2).map((label) => (
          <Badge
            key={label.id}
            variant="secondary"
            className="h-4 px-1 text-[10px]"
            style={{ backgroundColor: `${label.color}20`, color: label.color }}
          >
            {label.name}
          </Badge>
        ))}
        {issue.labels.length > 2 && (
          <span className="text-[10px] text-muted-foreground">+{issue.labels.length - 2}</span>
        )}
      </div>

      {/* Due date */}
      {issue.targetDate && (
        <span className="hidden shrink-0 items-center gap-1 text-[11px] text-muted-foreground lg:flex">
          <Calendar className="size-3" />
          {new Date(issue.targetDate).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
          })}
        </span>
      )}
    </div>
  );
}
