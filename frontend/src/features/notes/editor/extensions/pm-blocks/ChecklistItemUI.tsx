'use client';

/**
 * ChecklistItemUI — Renders a single enhanced task item row.
 *
 * FR-014: Assignee avatar + MemberPicker trigger
 * FR-015: Due date badge + DatePicker trigger (overdue detection)
 * FR-016: Priority badge with color variants
 * FR-017: Optional flag (dashed border + reduced opacity)
 * FR-018: Conditional visibility (grey-out when parent unchecked)
 *
 * @module pm-blocks/ChecklistItemUI
 */
import { useCallback, useMemo } from 'react';
import { Calendar, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlockStyles } from './pm-block-styles';

/* ── Types ────────────────────────────────────────────────────────────── */

type Priority = 'none' | 'low' | 'medium' | 'high' | 'urgent';

export interface ChecklistItemUIProps {
  checked: boolean;
  text: string;
  assignee: string | null;
  dueDate: string | null;
  priority: Priority;
  isOptional: boolean;
  conditionalParentId: string | null;
  isParentChecked: boolean;
  onCheckedChange: (checked: boolean) => void;
  onAssigneeChange: (assignee: string | null) => void;
  onDueDateChange: (date: string | null) => void;
  onPriorityChange: (priority: Priority) => void;
}

/* ── Priority config ──────────────────────────────────────────────────── */

const PRIORITY_LABELS: Record<Priority, string> = {
  urgent: 'Urgent',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  none: '',
};

/* ── Helpers ──────────────────────────────────────────────────────────── */

function formatDueDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isOverdue(dateStr: string): boolean {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dateStr + 'T00:00:00');
  return due < today;
}

/* ── Component ────────────────────────────────────────────────────────── */

export function ChecklistItemUI({
  checked,
  text,
  assignee,
  dueDate,
  priority,
  isOptional,
  conditionalParentId,
  isParentChecked,
  onCheckedChange,
  onAssigneeChange,
  onDueDateChange,
  onPriorityChange,
}: ChecklistItemUIProps) {
  const isConditionallyDisabled = conditionalParentId !== null && !isParentChecked;

  const handleCheckedChange = useCallback(() => {
    onCheckedChange(!checked);
  }, [checked, onCheckedChange]);

  const showOverdue = useMemo(
    () => dueDate !== null && !checked && isOverdue(dueDate),
    [dueDate, checked]
  );

  return (
    <div
      className={cn(
        pmBlockStyles.checklist.item,
        isOptional && pmBlockStyles.checklist.itemOptional,
        isConditionallyDisabled && pmBlockStyles.checklist.itemDisabled
      )}
    >
      {/* Checkbox */}
      <input
        type="checkbox"
        className={pmBlockStyles.checklist.checkbox}
        checked={checked}
        onChange={handleCheckedChange}
        aria-checked={checked}
      />

      {/* Item text */}
      <span
        className={cn(
          pmBlockStyles.checklist.itemText,
          checked && pmBlockStyles.checklist.itemTextChecked
        )}
      >
        {text}
      </span>

      {/* Metadata badges */}
      <div className={pmBlockStyles.checklist.metadata}>
        {/* FR-014: Assignee */}
        {assignee && (
          <span data-testid="checklist-assignee">
            <User className="size-3.5" />
          </span>
        )}

        {!assignee && (
          <button
            type="button"
            aria-label="Assign member"
            className="shrink-0 text-muted-foreground hover:text-foreground"
            onClick={() => onAssigneeChange(null)}
          >
            <User className="size-3.5 opacity-40" />
          </button>
        )}

        {/* FR-015: Due date */}
        {dueDate && (
          <button
            type="button"
            data-testid="checklist-due-date"
            className={cn(
              'inline-flex items-center gap-1 text-xs hover:underline',
              showOverdue && 'text-destructive'
            )}
            onClick={() => onDueDateChange(null)}
            aria-label={`Due date: ${formatDueDate(dueDate)}. Click to change.`}
          >
            <Calendar className="size-3" />
            {formatDueDate(dueDate)}
          </button>
        )}

        {/* FR-016: Priority badge */}
        {priority !== 'none' && (
          <button
            type="button"
            data-testid="checklist-priority"
            className={cn(
              pmBlockStyles.checklist.priorityBadge,
              pmBlockStyles.priorityColors[priority] ?? ''
            )}
            onClick={() => {
              const cycle: Priority[] = ['low', 'medium', 'high', 'urgent', 'none'];
              const idx = cycle.indexOf(priority);
              const next = cycle[(idx + 1) % cycle.length] ?? 'none';
              onPriorityChange(next);
            }}
            aria-label={`Priority: ${PRIORITY_LABELS[priority]}. Click to cycle.`}
          >
            {PRIORITY_LABELS[priority]}
          </button>
        )}
      </div>
    </div>
  );
}
