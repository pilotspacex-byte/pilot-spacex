'use client';

/**
 * TaskItemNodeView — TipTap React NodeView for enhanced TaskItem.
 *
 * Bridges TaskItemEnhanced (TipTap extension with 6 new attrs) to
 * a React rendering with inline metadata badges (assignee, due date,
 * priority, optional flag, conditional visibility).
 *
 * Uses NodeViewContent for the editable text area so TipTap's
 * inline editing, cursor management, and content model are preserved.
 *
 * @module pm-blocks/TaskItemNodeView
 */
import { useCallback, useMemo } from 'react';
import { NodeViewWrapper, NodeViewContent, type NodeViewProps } from '@tiptap/react';
import { Calendar, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlockStyles } from './pm-block-styles';

type Priority = 'none' | 'low' | 'medium' | 'high' | 'urgent';

const PRIORITY_LABELS: Record<Priority, string> = {
  urgent: 'Urgent',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  none: '',
};

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

export function TaskItemNodeView({ node, updateAttributes, editor }: NodeViewProps) {
  const checked = (node.attrs.checked as boolean) ?? false;
  const assignee = (node.attrs.assignee as string | null) ?? null;
  const dueDate = (node.attrs.dueDate as string | null) ?? null;
  const priority = (node.attrs.priority as Priority) ?? 'none';
  const isOptional = (node.attrs.isOptional as boolean) ?? false;
  const conditionalParentId = (node.attrs.conditionalParentId as string | null) ?? null;
  const readOnly = !editor.isEditable;

  const handleCheckedChange = useCallback(() => {
    if (readOnly) return;
    updateAttributes({ checked: !checked });
  }, [checked, readOnly, updateAttributes]);

  const showOverdue = useMemo(
    () => dueDate !== null && !checked && isOverdue(dueDate),
    [dueDate, checked]
  );

  // Look up parent task's checked state for conditional visibility (FR-018).
  const isConditionallyDisabled = useMemo(() => {
    if (!conditionalParentId) return false;

    let parentChecked = false;
    editor.state.doc.descendants((descendant) => {
      if (descendant.type.name === 'taskItem' && descendant.attrs.id === conditionalParentId) {
        parentChecked = descendant.attrs.checked === true;
        return false; // Stop traversal
      }
      return true;
    });

    // Conditional items are DISABLED when parent is NOT checked
    return !parentChecked;
  }, [conditionalParentId, editor.state.doc]);

  return (
    <NodeViewWrapper
      as="li"
      className={cn(
        pmBlockStyles.checklist.item,
        isOptional && pmBlockStyles.checklist.itemOptional,
        isConditionallyDisabled && pmBlockStyles.checklist.itemDisabled
      )}
      data-checked={checked ? 'true' : 'false'}
      data-type="taskItem"
    >
      {/* Checkbox */}
      <label className="flex items-center gap-2 shrink-0" contentEditable={false}>
        <input
          type="checkbox"
          className={pmBlockStyles.checklist.checkbox}
          checked={checked}
          onChange={handleCheckedChange}
          disabled={readOnly || isConditionallyDisabled}
          aria-checked={checked}
        />
      </label>

      {/* Editable content — TipTap manages this */}
      <NodeViewContent
        as="div"
        className={cn(
          'flex-1 min-w-0',
          pmBlockStyles.checklist.itemText,
          checked && pmBlockStyles.checklist.itemTextChecked
        )}
      />

      {/* Metadata badges (non-editable) */}
      <div className={pmBlockStyles.checklist.metadata} contentEditable={false}>
        {/* FR-014: Assignee */}
        {assignee ? (
          <span data-testid="checklist-assignee" className="text-muted-foreground">
            <User className="size-3.5" />
          </span>
        ) : !readOnly ? (
          <button
            type="button"
            aria-label="Assign member"
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <User className="size-3.5 opacity-40" />
          </button>
        ) : null}

        {/* FR-015: Due date */}
        {dueDate && (
          <span
            data-testid="checklist-due-date"
            className={cn(
              'inline-flex items-center gap-1 text-xs',
              showOverdue && 'text-destructive'
            )}
          >
            <Calendar className="size-3" />
            {formatDueDate(dueDate)}
          </span>
        )}

        {/* FR-016: Priority badge */}
        {priority !== 'none' && (
          <span
            data-testid="checklist-priority"
            className={cn(
              pmBlockStyles.checklist.priorityBadge,
              pmBlockStyles.priorityColors[priority] ?? ''
            )}
          >
            {PRIORITY_LABELS[priority]}
          </span>
        )}

        {/* FR-017: Optional label */}
        {isOptional && <span className="text-[10px] text-muted-foreground italic">Optional</span>}
      </div>
    </NodeViewWrapper>
  );
}
