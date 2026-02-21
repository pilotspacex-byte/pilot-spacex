'use client';

/**
 * PropertyBlockView - TipTap NodeView for inline issue properties.
 *
 * Renders a compact grid of PropertyChips at document position 0.
 * Reads issue data from IssueNoteContext (not TipTap attributes).
 * Supports expanded (grid) and collapsed (single-line) states.
 */
import { useState, useCallback, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { NodeViewWrapper } from '@tiptap/react';
import { format } from 'date-fns';
import { ChevronUp, CalendarIcon, User, Plus } from 'lucide-react';
import { Circle, CircleDot, CircleDashed, PlayCircle, CheckCircle2, XCircle } from 'lucide-react';
import { SignalHigh, SignalMedium, SignalLow, AlertTriangle, Minus } from 'lucide-react';

import { cn } from '@/lib/utils';
import { stateNameToKey } from '@/lib/issue-helpers';
import type { IssueState, IssuePriority, UserBrief, LabelBrief } from '@/types';
import { Calendar } from '@/components/ui/calendar';
import {
  IssueStateSelect,
  IssuePrioritySelect,
  CycleSelector,
  AssigneeSelector,
  LabelSelector,
} from '@/components/issues';
import { useSaveStatus } from '@/features/issues/hooks';
import { useIssueNoteContext } from '@/features/issues/contexts/issue-note-context';
import { PropertyChip } from './property-chip';
import { PropertyBlockCollapsed } from './property-block-collapsed';
import { EffortField } from './effort-field';

// ---------------------------------------------------------------------------
// State & Priority icon configs
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

// ---------------------------------------------------------------------------
// Storage key for collapsed state
// ---------------------------------------------------------------------------
const COLLAPSED_KEY = 'issue-property-block-collapsed';

function getInitialCollapsed(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(COLLAPSED_KEY) === 'true';
}

// ---------------------------------------------------------------------------
// PropertyBlockView component
// ---------------------------------------------------------------------------

export const PropertyBlockView = observer(function PropertyBlockView() {
  const { issue, members, labels, cycles, onUpdate, onUpdateState, disabled } =
    useIssueNoteContext();

  const [collapsed, setCollapsed] = useState(getInitialCollapsed);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSED_KEY, String(next));
      return next;
    });
  }, []);

  // Derived state
  const issueState = stateNameToKey(issue.state.name);
  const stateConf = STATE_ICON[issueState];
  const StateIcon = stateConf.icon;
  const priorityConf = PRIORITY_ICON[issue.priority ?? 'none'];
  const PriorityIcon = priorityConf.icon;

  const assigneeUser = useMemo<UserBrief | null>(() => issue.assignee ?? null, [issue.assignee]);
  const selectedLabels = useMemo<LabelBrief[]>(() => issue.labels ?? [], [issue.labels]);

  // -- Save-status-wrapped handlers --

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

  const { wrapMutation: wrapLabels } = useSaveStatus('labels');
  const handleLabelsChange = useCallback(
    (next: LabelBrief[]) => {
      wrapLabels(() => onUpdate({ labelIds: next.map((l) => l.id) })).catch(() => {});
    },
    [wrapLabels, onUpdate]
  );

  const { wrapMutation: wrapCycle } = useSaveStatus('cycle');
  const handleCycleChange = useCallback(
    (cycleId: string | null) => {
      if (cycleId) {
        wrapCycle(() => onUpdate({ cycleId })).catch(() => {});
      } else {
        wrapCycle(() => onUpdate({ clearCycle: true })).catch(() => {});
      }
    },
    [wrapCycle, onUpdate]
  );

  const { wrapMutation: wrapStartDate } = useSaveStatus('startDate');
  const handleStartDateChange = useCallback(
    (d: Date | undefined) => {
      if (d) {
        wrapStartDate(() => onUpdate({ startDate: d.toISOString().split('T')[0] })).catch(() => {});
      } else {
        wrapStartDate(() => onUpdate({ clearStartDate: true })).catch(() => {});
      }
    },
    [wrapStartDate, onUpdate]
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

  const { wrapMutation: wrapEstimate } = useSaveStatus('estimate');
  const handlePointsChange = useCallback(
    (points: number | undefined) => {
      if (points !== undefined) {
        wrapEstimate(() => onUpdate({ estimatePoints: points })).catch(() => {});
      } else {
        wrapEstimate(() => onUpdate({ clearEstimate: true })).catch(() => {});
      }
    },
    [wrapEstimate, onUpdate]
  );

  const { wrapMutation: wrapHours } = useSaveStatus('estimateHours');
  const handleHoursChange = useCallback(
    (hours: number | undefined) => {
      wrapHours(() => onUpdate({ estimateHours: hours })).catch(() => {});
    },
    [wrapHours, onUpdate]
  );

  // Current cycle name
  const currentCycleName = useMemo(() => {
    if (!issue.cycleId) return null;
    return cycles.find((c) => c.id === issue.cycleId)?.name ?? null;
  }, [issue.cycleId, cycles]);

  // Formatted dates
  const startDateStr = issue.startDate ? format(new Date(issue.startDate), 'MMM d') : null;
  const dueDateStr = issue.targetDate ? format(new Date(issue.targetDate), 'MMM d') : null;

  if (collapsed) {
    return (
      <NodeViewWrapper className="mb-2" data-testid="property-block">
        <PropertyBlockCollapsed onExpand={toggleCollapsed} />
      </NodeViewWrapper>
    );
  }

  return (
    <NodeViewWrapper className="mb-2" data-testid="property-block">
      <div
        role="toolbar"
        aria-label="Issue properties"
        className={cn(
          'rounded-[10px] border border-[#E5E2DD] bg-[#F8F6F3]',
          'px-3 py-2',
          'motion-safe:transition-all motion-safe:duration-200'
        )}
      >
        {/* Row 1: State, Priority, Assignee, Cycle, Due date */}
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
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
            <span>{priorityConf.label}</span>
          </PropertyChip>

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

          <PropertyChip
            label={`Cycle: ${currentCycleName ?? 'None'}`}
            fieldName="cycle"
            disabled={disabled}
            popoverContent={
              <CycleSelector
                value={issue.cycleId ?? null}
                onChange={handleCycleChange}
                cycles={cycles}
                disabled={disabled}
                inline
              />
            }
          >
            <span className="text-muted-foreground">{currentCycleName ?? 'No cycle'}</span>
          </PropertyChip>

          <PropertyChip
            label={`Due: ${dueDateStr ?? 'Not set'}`}
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
            <CalendarIcon className="size-3.5 text-muted-foreground" />
            <span>{dueDateStr ?? 'No due date'}</span>
          </PropertyChip>
        </div>

        {/* Row 2: Labels, Start date, Effort, Collapse */}
        <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1">
          {selectedLabels.map((label) => (
            <span
              key={label.id}
              className="inline-flex items-center gap-1 rounded-full border px-1.5 py-0 text-xs leading-5"
            >
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: label.color }}
                aria-hidden="true"
              />
              {label.name}
            </span>
          ))}

          <PropertyChip
            label="Add label"
            fieldName="labels"
            disabled={disabled}
            popoverContent={
              <LabelSelector
                selectedLabels={selectedLabels}
                availableLabels={labels}
                onChange={handleLabelsChange}
                disabled={disabled}
                inline
              />
            }
          >
            <Plus className="size-3 text-muted-foreground" />
            <span className="text-muted-foreground text-xs">Label</span>
          </PropertyChip>

          <span className="mx-0.5 h-3 w-px bg-border" aria-hidden="true" />

          <PropertyChip
            label={`Start: ${startDateStr ?? 'Not set'}`}
            fieldName="startDate"
            disabled={disabled}
            popoverContent={
              <Calendar
                mode="single"
                selected={issue.startDate ? new Date(issue.startDate) : undefined}
                onSelect={handleStartDateChange}
              />
            }
            popoverWidth="w-auto"
          >
            <span className="text-xs text-muted-foreground">Start:</span>
            <span>{startDateStr ?? 'Not set'}</span>
          </PropertyChip>

          <PropertyChip
            label="Effort"
            fieldName="estimate"
            disabled={disabled}
            popoverContent={
              <EffortField
                estimatePoints={issue.estimatePoints ?? undefined}
                estimateHours={issue.estimateHours || undefined}
                onPointsChange={handlePointsChange}
                onHoursChange={handleHoursChange}
                disabled={disabled}
              />
            }
          >
            <span className="text-xs text-muted-foreground">Effort:</span>
            <span>
              {issue.estimatePoints != null
                ? `${issue.estimatePoints}pt`
                : issue.estimateHours != null
                  ? `${issue.estimateHours}h`
                  : '—'}
            </span>
          </PropertyChip>

          <button
            type="button"
            onClick={toggleCollapsed}
            className={cn(
              'ml-auto inline-flex items-center rounded-[6px] px-1.5 py-0.5 text-xs',
              'text-muted-foreground hover:bg-muted/50 transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
            aria-label="Collapse properties"
          >
            <ChevronUp className="size-3" />
          </button>
        </div>
      </div>
    </NodeViewWrapper>
  );
});
