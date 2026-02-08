/**
 * useAIAutoScroll - Auto-scroll to AI-focused blocks.
 *
 * Watches processingBlockIds changes and auto-scrolls to the target block.
 * Uses explicit container scroll (scrollRef.scrollTo) instead of scrollIntoView
 * to handle nested overflow-auto containers correctly.
 *
 * @module hooks/useAIAutoScroll
 */

import { useEffect, useState, useCallback, useRef } from 'react';

interface AIAutoScrollResult {
  /** Whether there's an off-screen AI update the user hasn't seen */
  hasOffScreenUpdate: boolean;
  /** Block ID of the off-screen update */
  offScreenBlockId: string | null;
  /** Direction of the off-screen block relative to the viewport */
  offScreenDirection: 'above' | 'below';
  /** Scroll to the off-screen block */
  scrollToBlock: () => void;
  /** Dismiss the off-screen indicator */
  dismissIndicator: () => void;
}

/**
 * Determine if an element is visible within its scroll container.
 */
function isElementInViewport(el: Element, container: Element): boolean {
  const elRect = el.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  return (
    elRect.top >= containerRect.top - 50 &&
    elRect.bottom <= containerRect.bottom + 50
  );
}

/**
 * Scroll the container so that `target` is vertically centered.
 * Uses explicit scrollTo on the container to avoid nested-scroll issues
 * with scrollIntoView.
 */
function scrollContainerToElement(container: HTMLElement, target: Element): void {
  const containerRect = container.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const offset =
    targetRect.top - containerRect.top - containerRect.height / 2 + targetRect.height / 2;
  container.scrollTo({
    top: container.scrollTop + offset,
    behavior: 'smooth',
  });
}

/**
 * Query DOM for a block element by ID, retrying via rAF if not found
 * (handles TipTap BlockIdExtension appendTransaction timing).
 */
function queryBlockElement(
  blockId: string,
  callback: (el: Element | null) => void
): void {
  const el = document.querySelector(`[data-block-id="${blockId}"]`);
  if (el) {
    callback(el);
    return;
  }
  // Retry after one animation frame — BlockIdExtension may not have run yet
  requestAnimationFrame(() => {
    callback(document.querySelector(`[data-block-id="${blockId}"]`));
  });
}

export function useAIAutoScroll(
  scrollRef: React.RefObject<HTMLDivElement | null>,
  processingBlockIds: string[],
  _userEditingBlockId: string | null
): AIAutoScrollResult {
  const [hasOffScreenUpdate, setHasOffScreenUpdate] = useState(false);
  const [offScreenBlockId, setOffScreenBlockId] = useState<string | null>(null);
  // Direction kept for API compatibility; auto-scroll makes indicator unnecessary
  const offScreenDirection: 'above' | 'below' = 'below';
  const prevBlockIdsRef = useRef<string[]>([]);
  const isMountedRef = useRef(false);

  /**
   * Auto-scroll to a target element within the scroll container.
   * Always scrolls — processingBlockIds only change during AI streaming,
   * so the user expects to see the content being written.
   */
  const scrollToTarget = useCallback(
    (targetEl: Element, container: HTMLElement) => {
      if (isElementInViewport(targetEl, container)) return;
      scrollContainerToElement(container, targetEl);
    },
    []
  );

  // Detect new processing blocks (and handle mount with existing blocks)
  useEffect(() => {
    const prevIds = prevBlockIdsRef.current;
    const container = scrollRef.current;

    // Handle initial mount: if blocks are already processing, scroll
    if (!isMountedRef.current) {
      isMountedRef.current = true;
      if (processingBlockIds.length > 0 && container) {
        const targetId = processingBlockIds[processingBlockIds.length - 1]!;
        queryBlockElement(targetId, (targetEl) => {
          if (targetEl && scrollRef.current) {
            scrollToTarget(targetEl, scrollRef.current);
          }
        });
      }
      prevBlockIdsRef.current = processingBlockIds;
      return;
    }

    const newIds = processingBlockIds.filter((id) => !prevIds.includes(id));
    prevBlockIdsRef.current = processingBlockIds;

    if (newIds.length === 0 || !container) return;

    const targetId = newIds[newIds.length - 1]!;
    queryBlockElement(targetId, (targetEl) => {
      if (targetEl && scrollRef.current) {
        scrollToTarget(targetEl, scrollRef.current);
      }
    });
  }, [processingBlockIds, scrollRef, scrollToTarget]);

  const scrollToBlock = useCallback(() => {
    if (!offScreenBlockId || !scrollRef.current) return;
    const el = document.querySelector(`[data-block-id="${offScreenBlockId}"]`);
    if (el) {
      scrollContainerToElement(scrollRef.current, el);
    }
    setHasOffScreenUpdate(false);
    setOffScreenBlockId(null);
  }, [offScreenBlockId, scrollRef]);

  const dismissIndicator = useCallback(() => {
    setHasOffScreenUpdate(false);
    setOffScreenBlockId(null);
  }, []);

  return { hasOffScreenUpdate, offScreenBlockId, offScreenDirection, scrollToBlock, dismissIndicator };
}
