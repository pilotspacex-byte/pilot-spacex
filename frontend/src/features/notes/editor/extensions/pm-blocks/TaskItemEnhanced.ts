/**
 * TaskItemEnhanced — TipTap extension for Smart Checklist items (FR-013 to FR-018).
 *
 * Extends the default TaskItem with 6 new attributes:
 * assignee, dueDate, priority, isOptional, estimatedEffort, conditionalParentId.
 *
 * These attributes are serialized as `data-*` HTML attributes and
 * round-trip through JSON for TipTap's internal state.
 *
 * @module pm-blocks/TaskItemEnhanced
 */
import TaskItem from '@tiptap/extension-task-item';
import { Fragment, Slice, type Node as ProseMirrorNode } from '@tiptap/pm/model';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { TaskItemNodeView } from './TaskItemNodeView';

export const TaskItemEnhanced = TaskItem.extend({
  addNodeView() {
    return ReactNodeViewRenderer(TaskItemNodeView);
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('taskItemPasteCleanup'),
        props: {
          transformPasted(slice) {
            const cleaned = mapTaskItems(slice.content, (node) => {
              if (node.type.name !== 'taskItem') return node;
              // Clear assignee on paste (FR-054)
              return node.type.create({ ...node.attrs, assignee: null }, node.content, node.marks);
            });
            return new Slice(cleaned, slice.openStart, slice.openEnd);
          },
        },
      }),
    ];
  },

  addAttributes() {
    return {
      /** Inherited from TaskItem — whether the checkbox is ticked. */
      checked: {
        default: false,
        keepOnSplit: false,
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('data-checked') === 'true' ||
          element.getAttribute('data-checked') === '',
        renderHTML: (attributes: Record<string, unknown>) => ({
          'data-checked': attributes.checked ? 'true' : 'false',
        }),
      },

      /** Workspace member ID assigned to this item (FR-014). */
      assignee: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-assignee'),
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.assignee) return {};
          return { 'data-assignee': attributes.assignee as string };
        },
      },

      /** ISO date string for due date (FR-015). */
      dueDate: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-due-date'),
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.dueDate) return {};
          return { 'data-due-date': attributes.dueDate as string };
        },
      },

      /** Priority level: none | low | medium | high | urgent (FR-016). */
      priority: {
        default: 'none',
        parseHTML: (element: HTMLElement) => element.getAttribute('data-priority') || 'none',
        renderHTML: (attributes: Record<string, unknown>) => {
          return { 'data-priority': attributes.priority as string };
        },
      },

      /** Whether this item is optional — excluded from progress bar (FR-017). */
      isOptional: {
        default: false,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-optional') === 'true',
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.isOptional) return {};
          return { 'data-optional': 'true' };
        },
      },

      /** Story points or hours estimate (spec.md). */
      estimatedEffort: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-estimated-effort'),
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.estimatedEffort) return {};
          return { 'data-estimated-effort': attributes.estimatedEffort as string };
        },
      },

      /** Block ID of parent item for conditional visibility (FR-018). */
      conditionalParentId: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-conditional-parent'),
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.conditionalParentId) return {};
          return { 'data-conditional-parent': attributes.conditionalParentId as string };
        },
      },
    };
  },
});

/** Recursively map over a Fragment, transforming nodes. */
function mapTaskItems(
  fragment: Fragment,
  fn: (node: ProseMirrorNode) => ProseMirrorNode
): Fragment {
  const nodes: ProseMirrorNode[] = [];
  fragment.forEach((node) => {
    const mapped = fn(node);
    if (mapped.content.childCount > 0) {
      nodes.push(mapped.copy(mapTaskItems(mapped.content, fn)));
    } else {
      nodes.push(mapped);
    }
  });
  return Fragment.from(nodes);
}
