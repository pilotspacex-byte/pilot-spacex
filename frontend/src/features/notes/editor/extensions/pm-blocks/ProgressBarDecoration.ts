/**
 * ProgressBarDecoration — ProseMirror plugin that renders a progress bar
 * above TaskList nodes in the editor (FR-019).
 *
 * Progress = checkedRequired / totalRequired * 100.
 * Optional items (isOptional: true) are excluded from both numerator and denominator.
 *
 * @module pm-blocks/ProgressBarDecoration
 */
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { EditorState } from '@tiptap/pm/state';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import { pmBlockStyles } from './pm-block-styles';

/** Item shape used by computeProgress. */
export interface ProgressItem {
  checked: boolean;
  isOptional: boolean;
}

/** Progress computation result. */
export interface ProgressResult {
  /** Number of checked required items. */
  checked: number;
  /** Total number of required items. */
  total: number;
  /** Integer percentage (0-100), floored. */
  percentage: number;
}

/**
 * Compute progress from a list of checklist items.
 * Optional items are excluded from both numerator and denominator.
 */
export function computeProgress(items: ProgressItem[]): ProgressResult {
  let checked = 0;
  let total = 0;

  for (const item of items) {
    if (item.isOptional) continue;
    total++;
    if (item.checked) checked++;
  }

  const percentage = total === 0 ? 0 : Math.round((checked / total) * 100);
  return { checked, total, percentage };
}

/** Plugin key for the progress bar decoration. */
export const PROGRESS_BAR_PLUGIN_KEY = new PluginKey('progressBar');

/**
 * Create a progress bar DOM element for the given progress result.
 */
function createProgressBarElement(progress: ProgressResult): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-progress-bar', 'true');
  wrapper.setAttribute('aria-label', `Progress: ${progress.percentage}%`);
  wrapper.setAttribute('role', 'progressbar');
  wrapper.setAttribute('aria-valuenow', String(progress.percentage));
  wrapper.setAttribute('aria-valuemin', '0');
  wrapper.setAttribute('aria-valuemax', '100');

  // Track
  const track = document.createElement('div');
  track.className = pmBlockStyles.checklist.progressTrack;

  // Fill
  const fill = document.createElement('div');
  fill.className = pmBlockStyles.checklist.progressFill;
  fill.style.width = `${progress.percentage}%`;

  track.appendChild(fill);

  // Label: "X/Y (Z%)"
  const label = document.createElement('span');
  label.className = 'text-xs text-muted-foreground ml-1';
  label.textContent = `${progress.checked}/${progress.total} (${progress.percentage}%)`;

  wrapper.appendChild(track);
  wrapper.appendChild(label);

  return wrapper;
}

/**
 * Collect all taskItem children from a taskList node and compute progress.
 */
function collectTaskItems(taskListNode: ProseMirrorNode): ProgressItem[] {
  const items: ProgressItem[] = [];

  taskListNode.forEach((child) => {
    if (child.type.name === 'taskItem') {
      items.push({
        checked: child.attrs.checked === true,
        isOptional: child.attrs.isOptional === true,
      });
    }
  });

  return items;
}

/**
 * Build decoration set by finding all taskList nodes and adding
 * a widget decoration above each one.
 */
function buildDecorations(state: EditorState): DecorationSet {
  const decorations: Decoration[] = [];

  state.doc.descendants((node, pos) => {
    if (node.type.name === 'taskList') {
      const items = collectTaskItems(node);
      const progress = computeProgress(items);

      // Only show progress bar if there are required items
      if (progress.total > 0) {
        const widget = Decoration.widget(pos, () => createProgressBarElement(progress), {
          side: -1, // before the node
          key: `progress-${pos}`,
        });
        decorations.push(widget);
      }
    }
  });

  return DecorationSet.create(state.doc, decorations);
}

/** ProseMirror plugin that renders progress bars above TaskList nodes.
 * Uses stateful plugin to avoid rebuilding decorations on every transaction.
 * Only rebuilds when the document actually changes. */
export const ProgressBarDecoration = new Plugin({
  key: PROGRESS_BAR_PLUGIN_KEY,
  state: {
    init(_, state) {
      return buildDecorations(state);
    },
    apply(tr, decorationSet, _oldState, newState) {
      if (!tr.docChanged) {
        return decorationSet.map(tr.mapping, tr.doc);
      }
      return buildDecorations(newState);
    },
  },
  props: {
    decorations(state) {
      return PROGRESS_BAR_PLUGIN_KEY.getState(state) as DecorationSet | undefined;
    },
  },
});
