'use client';

/**
 * PropertyBlockCollapsed - Single-line summary of issue properties.
 *
 * Shows: [StateIcon State] [PriorityIcon Priority] [@Assignee] [Cycle] [DueDate] [labelCount] [expand]
 */
import { ChevronDown, User } from 'lucide-react';
import { Circle, CircleDot, CircleDashed, PlayCircle, CheckCircle2, XCircle } from 'lucide-react';
import { SignalHigh, SignalMedium, SignalLow, AlertTriangle, Minus } from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { stateNameToKey } from '@/lib/issue-helpers';
import type { Issue, IssueState, IssuePriority } from '@/types';

// ---------------------------------------------------------------------------
// State & Priority icon configs (minimal, for collapsed view)
// ---------------------------------------------------------------------------

const STATE_ICON: Record<IssueState, { icon: React.ElementType; className: string }> = {
  backlog: { icon: CircleDashed, className: 'text-gray-500' },
  todo: { icon: Circle, className: 'text-blue-500' },
  in_progress: { icon: PlayCircle, className: 'text-yellow-500' },
  in_review: { icon: CircleDot, className: 'text-purple-500' },
  done: { icon: CheckCircle2, className: 'text-green-500' },
  cancelled: { icon: XCircle, className: 'text-red-500' },
};

const STATE_LABEL: Record<IssueState, string> = {
  backlog: 'Backlog',
  todo: 'Todo',
  in_progress: 'In Progress',
  in_review: 'In Review',
  done: 'Done',
  cancelled: 'Cancelled',
};

const PRIORITY_ICON: Record<IssuePriority, { icon: React.ElementType; className: string }> = {
  urgent: { icon: AlertTriangle, className: 'text-red-500' },
  high: { icon: SignalHigh, className: 'text-orange-500' },
  medium: { icon: SignalMedium, className: 'text-yellow-500' },
  low: { icon: SignalLow, className: 'text-blue-400' },
  none: { icon: Minus, className: 'text-gray-400' },
};

export interface PropertyBlockCollapsedProps {
  issue: Issue;
  onExpand: () => void;
  className?: string;
}

export function PropertyBlockCollapsed({
  issue,
  onExpand,
  className,
}: PropertyBlockCollapsedProps) {
  const issueState = stateNameToKey(issue.state.name);
  const stateConf = STATE_ICON[issueState];
  const StateIcon = stateConf.icon;
  const priorityConf = PRIORITY_ICON[issue.priority ?? 'none'];
  const PriorityIcon = priorityConf.icon;

  const assigneeName = issue.assignee?.displayName ?? issue.assignee?.email;
  const dueDate = issue.targetDate ? format(new Date(issue.targetDate), 'MMM d') : null;
  const labelCount = issue.labels?.length ?? 0;

  return (
    <button
      type="button"
      onClick={onExpand}
      className={cn(
        'flex w-full items-center gap-3 rounded-[12px] border border-[#E5E2DD] bg-[#F8F6F3]',
        'px-4 py-2.5 text-sm transition-colors duration-100',
        'hover:bg-[#F3F0EC] cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className
      )}
      aria-label="Expand issue properties"
    >
      {/* State */}
      <span className={cn('inline-flex items-center gap-1', stateConf.className)}>
        <StateIcon className="size-3.5" />
        <span className="text-foreground">{STATE_LABEL[issueState]}</span>
      </span>

      {/* Priority */}
      <span className={cn('inline-flex items-center gap-1', priorityConf.className)}>
        <PriorityIcon className="size-3.5" />
      </span>

      {/* Assignee */}
      {assigneeName && (
        <span className="inline-flex items-center gap-1 text-muted-foreground">
          <User className="size-3" />
          <span className="max-w-[80px] truncate">{assigneeName.split(' ')[0]}</span>
        </span>
      )}

      {/* Due date */}
      {dueDate && <span className="text-muted-foreground">{dueDate}</span>}

      {/* Label count */}
      {labelCount > 0 && (
        <span className="inline-flex items-center justify-center rounded-full bg-muted px-1.5 text-xs text-muted-foreground">
          {labelCount}
        </span>
      )}

      {/* Spacer + expand icon */}
      <span className="ml-auto">
        <ChevronDown className="size-3.5 text-muted-foreground" />
      </span>
    </button>
  );
}
