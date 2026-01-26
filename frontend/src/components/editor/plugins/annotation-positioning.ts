/**
 * Annotation Positioning Plugin - Tracks block positions for margin layout
 * T166: Calculates and updates block positions relative to editor viewport
 *
 * Features:
 * - Real-time position tracking with RAF batching
 * - Scroll synchronization
 * - Handles overlapping annotations
 */
import { Plugin, PluginKey } from '@tiptap/pm/state';

export const annotationPositioningKey = new PluginKey('annotationPositioning');

export interface BlockPosition {
  blockId: string;
  top: number;
  height: number;
}

export interface AnnotationPositioningOptions {
  /**
   * Callback invoked when positions are updated.
   * Called with throttled RAF for performance.
   */
  onPositionsUpdate: (positions: BlockPosition[]) => void;
}

/**
 * Create positioning plugin for annotation layout.
 * Tracks block positions and notifies when they change.
 */
export function createAnnotationPositioningPlugin(
  onPositionsUpdate: (positions: BlockPosition[]) => void
): Plugin {
  return new Plugin({
    key: annotationPositioningKey,
    view(editorView) {
      let rafId: number | null = null;
      let isDestroyed = false;

      /**
       * Calculate positions for all blocks with blockId attribute.
       * Returns array of block positions relative to editor top.
       */
      const updatePositions = () => {
        if (isDestroyed) return;

        const positions: BlockPosition[] = [];
        const { doc } = editorView.state;
        const editorRect = editorView.dom.getBoundingClientRect();

        doc.descendants((node, pos) => {
          // Only process blocks with blockId (note content blocks)
          if (node.isBlock && node.attrs.blockId) {
            try {
              // Get DOM node for this position
              const domNode = editorView.nodeDOM(pos);

              if (domNode instanceof HTMLElement) {
                const rect = domNode.getBoundingClientRect();

                // Calculate position relative to editor
                positions.push({
                  blockId: node.attrs.blockId,
                  top: rect.top - editorRect.top + editorView.dom.scrollTop,
                  height: rect.height,
                });
              }
            } catch {
              // nodeDOM may fail for some positions, skip
            }
          }
          return true; // Continue traversal
        });

        onPositionsUpdate(positions);
      };

      /**
       * Schedule position update with RAF batching.
       * Debounces multiple calls within same frame.
       */
      const scheduleUpdate = () => {
        if (rafId !== null) {
          cancelAnimationFrame(rafId);
        }
        rafId = requestAnimationFrame(updatePositions);
      };

      // Initial update after mount
      scheduleUpdate();

      // Update on scroll (editor or window)
      const handleScroll = () => scheduleUpdate();
      editorView.dom.addEventListener('scroll', handleScroll);
      window.addEventListener('scroll', handleScroll);

      // Update on window resize
      const handleResize = () => scheduleUpdate();
      window.addEventListener('resize', handleResize);

      return {
        update(view, prevState) {
          // Update if document structure changed
          if (!view.state.doc.eq(prevState.doc)) {
            scheduleUpdate();
          }
        },
        destroy() {
          isDestroyed = true;
          if (rafId !== null) {
            cancelAnimationFrame(rafId);
          }
          editorView.dom.removeEventListener('scroll', handleScroll);
          window.removeEventListener('scroll', handleScroll);
          window.removeEventListener('resize', handleResize);
        },
      };
    },
  });
}

/**
 * Group overlapping annotations by vertical position.
 * Returns stacks of annotations that should be displayed together.
 *
 * @param positions - Block positions with annotations
 * @param overlapThreshold - Minimum vertical overlap in pixels (default: 20)
 */
export function groupOverlappingAnnotations(
  positions: BlockPosition[],
  overlapThreshold = 20
): BlockPosition[][] {
  if (positions.length === 0) return [];

  // Sort by top position
  const sorted = [...positions].sort((a, b) => a.top - b.top);
  const groups: BlockPosition[][] = [];
  let currentGroup: BlockPosition[] = [sorted[0]!];

  for (let i = 1; i < sorted.length; i++) {
    const current = sorted[i]!;
    const previous = currentGroup[currentGroup.length - 1]!;

    // Check if current overlaps with previous
    const previousBottom = previous.top + previous.height;
    const overlap = previousBottom - current.top;

    if (overlap > overlapThreshold) {
      // Overlapping - add to current group
      currentGroup.push(current);
    } else {
      // Not overlapping - start new group
      groups.push(currentGroup);
      currentGroup = [current];
    }
  }

  // Add final group
  if (currentGroup.length > 0) {
    groups.push(currentGroup);
  }

  return groups;
}

/**
 * Calculate staggered positions for overlapping annotations.
 * Offsets annotations horizontally to prevent visual collision.
 *
 * @param group - Group of overlapping block positions
 * @param offsetStep - Horizontal offset per annotation (default: 8px)
 */
export function calculateStaggeredPositions(
  group: BlockPosition[],
  offsetStep = 8
): Array<BlockPosition & { offset: number }> {
  return group.map((position, index) => ({
    ...position,
    offset: index * offsetStep,
  }));
}
