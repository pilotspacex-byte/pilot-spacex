'use client';

/**
 * PropertyBlockCollapsed - Single-line summary of issue properties.
 *
 * Each property chip opens its dropdown directly (single click) instead of
 * requiring expand → click (two steps). Uses IssueNoteContext for data and
 * update handlers.
 */
import { useCallback, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { ChevronDown, User, CalendarIcon } from 'lucide-react';
import { Circle, CircleDot, CircleDashed, PlayCircle, CheckCircle2, XCircle } from 'lucide-react';
import { SignalHigh, SignalMedium, SignalLow, AlertTriangle, Minus } from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { stateNameToKey } from '@/lib/issue-helpers';
import type { IssueState, IssuePriority, UserBrief } from '@/types';
import { Calendar } from '@/components/ui/calendar';
import { IssueStateSelect, IssuePrioritySelect, AssigneeSelector } from '@/components/issues';
import { useSaveStatus } from '@/features/issues/hooks';
import { useIssueNoteContext } from '@/features/issues/contexts/issue-note-context';
import { PropertyChip } from './property-chip';

// ---------------------------------------------------------------------------
// State & Priority icon configs (minimal, for collapsed view)
// ---------------------------------------------------------------------------

const STATE_ICON: Record<
  IssueState,
  { icon: React.ElementType; className: string; label: string }
> = {
  backlog: { icon: CircleDashed, className: 'text-gray-500', label: 'Backlog' },
  todo: { icon: Circle, className: 'text-blue-500', label: 'Todo' },
  in_progress: { icon: PlayCircle, className: 'text-yellow-500', label: 'In Progress' },
  in_review: { icon: CircleDot, className: 'text-purple-500', label: 'In Review' },
  done: { icon: CheckCircle2, className: 'text-green-500', label: 'Done' },
  cancelled: { icon: XCircle, className: 'text-red-500', label: 'Cancelled' },
};

const PRIORITY_ICON: Record<
  IssuePriority,
  { icon: React.ElementType; className: string; label: string }
> = {
  urgent: { icon: AlertTriangle, className: 'text-red-500', label: 'Urgent' },
  high: { icon: SignalHigh, className: 'text-orange-500', label: 'High' },
  medium: { icon: SignalMedium, className: 'text-yellow-500', label: 'Medium' },
  low: { icon: SignalLow, className: 'text-blue-400', label: 'Low' },
  none: { icon: Minus, className: 'text-gray-400', label: 'None' },
};

const STATE_GROUP_MAP: Record<string, IssueState> = {
  backlog: 'backlog',
  unstarted: 'todo',
  started: 'in_progress',
  completed: 'done',
  cancelled: 'cancelled',
};

export interface PropertyBlockCollapsedProps {
  onExpand: () => void;
  className?: string;
}

export const PropertyBlockCollapsed = observer(function PropertyBlockCollapsed({
  onExpand,
  className,
}: PropertyBlockCollapsedProps) {
  const { issue, members, disabled, onUpdate, onUpdateState } = useIssueNoteContext();

  // Derived state
  const issueState = stateNameToKey(issue.state.name);
  const stateConf = STATE_ICON[issueState];
  const StateIcon = stateConf.icon;
  const priorityConf = PRIORITY_ICON[issue.priority ?? 'none'];
  const PriorityIcon = priorityConf.icon;

  const assigneeUser = useMemo<UserBrief | null>(() => issue.assignee ?? null, [issue.assignee]);
  const dueDate = issue.targetDate ? format(new Date(issue.targetDate), 'MMM d') : null;
  const labelCount = issue.labels?.length ?? 0;

  // -- Handlers --

  const { wrapMutation: wrapState } = useSaveStatus('state');
  const handleStateChange = useCallback(
    (state: IssueState) => {
      const matched = STATE_GROUP_MAP[issue.state.group] === state ? issue.state : null;
      if (matched) return;
      wrapState(() => onUpdateState(state)).catch(() => {});
    },
    [issue.state, wrapState, onUpdateState]
  );

  const { wrapMutation: wrapPriority } = useSaveStatus('priority');
  const handlePriorityChange = useCallback(
    (priority: IssuePriority) => {
      wrapPriority(() => onUpdate({ priority })).catch(() => {});
    },
    [wrapPriority, onUpdate]
  );

  const { wrapMutation: wrapAssignee } = useSaveStatus('assignee');
  const handleAssigneeChange = useCallback(
    (user: UserBrief | null) => {
      if (user) {
        wrapAssignee(() => onUpdate({ assigneeId: user.id })).catch(() => {});
      } else {
        wrapAssignee(() => onUpdate({ clearAssignee: true })).catch(() => {});
      }
    },
    [wrapAssignee, onUpdate]
  );

  const { wrapMutation: wrapDueDate } = useSaveStatus('targetDate');
  const handleDueDateChange = useCallback(
    (d: Date | undefined) => {
      if (d) {
        wrapDueDate(() => onUpdate({ targetDate: d.toISOString().split('T')[0] })).catch(() => {});
      } else {
        wrapDueDate(() => onUpdate({ clearTargetDate: true })).catch(() => {});
      }
    },
    [wrapDueDate, onUpdate]
  );

  return (
    <div
      className={cn(
        'flex w-full items-center gap-1.5 rounded-[10px] border border-[#E5E2DD] bg-[#F8F6F3]',
        'px-2 py-1 text-xs',
        className
      )}
    >
      {/* State */}
      <PropertyChip
        label={`State: ${stateConf.label}`}
        fieldName="state"
        disabled={disabled}
        popoverContent={
          <IssueStateSelect
            value={issueState}
            onChange={handleStateChange}
            disabled={disabled}
            inline
          />
        }
      >
        <StateIcon className={cn('size-3.5', stateConf.className)} />
        <span>{stateConf.label}</span>
      </PropertyChip>

      {/* Priority */}
      <PropertyChip
        label={`Priority: ${priorityConf.label}`}
        fieldName="priority"
        disabled={disabled}
        popoverContent={
          <IssuePrioritySelect
            value={issue.priority ?? 'none'}
            onChange={handlePriorityChange}
            disabled={disabled}
            inline
          />
        }
      >
        <PriorityIcon className={cn('size-3.5', priorityConf.className)} />
      </PropertyChip>

      {/* Assignee */}
      <PropertyChip
        label={`Assignee: ${assigneeUser?.displayName ?? 'Not set'}`}
        fieldName="assignee"
        disabled={disabled}
        popoverContent={
          <AssigneeSelector
            value={assigneeUser}
            members={members}
            onChange={handleAssigneeChange}
            disabled={disabled}
            inline
          />
        }
      >
        <User className="size-3.5 text-muted-foreground" />
        <span>{assigneeUser?.displayName?.split(' ')[0] ?? 'Unassigned'}</span>
      </PropertyChip>

      {/* Due date */}
      {dueDate && (
        <PropertyChip
          label={`Due: ${dueDate}`}
          fieldName="targetDate"
          disabled={disabled}
          popoverContent={
            <Calendar
              mode="single"
              selected={issue.targetDate ? new Date(issue.targetDate) : undefined}
              onSelect={handleDueDateChange}
            />
          }
          popoverWidth="w-auto"
        >
          <CalendarIcon className="size-3 text-muted-foreground" />
          <span>{dueDate}</span>
        </PropertyChip>
      )}

      {/* Label count badge */}
      {labelCount > 0 && (
        <span className="inline-flex items-center justify-center rounded-full bg-muted px-1.5 text-xs text-muted-foreground">
          {labelCount}
        </span>
      )}

      {/* Spacer + expand icon */}
      <button
        type="button"
        onClick={onExpand}
        className={cn(
          'ml-auto inline-flex items-center rounded-[6px] px-1 py-0.5',
          'text-muted-foreground hover:bg-muted/50 transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
        aria-label="Expand issue properties"
      >
        <ChevronDown className="size-3.5" />
      </button>
    </div>
  );
});
