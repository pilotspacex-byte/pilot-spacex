'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type SidebarPanelId = 'versions' | 'presence' | 'conversation' | string;

export interface SidebarPanelState {
  isOpen: boolean;
  activePanel: SidebarPanelId | null;
  width: number;
}

const DEFAULT_WIDTH = 320;
const MIN_WIDTH = 240;
const MAX_WIDTH = 480;
const KEYBOARD_RESIZE_STEP = 16;

export interface UseSidebarPanelReturn {
  isOpen: boolean;
  activePanel: SidebarPanelId | null;
  width: number;
  openSidebar: (panel: SidebarPanelId, triggerEl?: HTMLElement | null) => void;
  closeSidebar: () => void;
  setWidth: (width: number) => void;
  /** Attach to the drag handle for keyboard resize (COL-C1). */
  dragHandleKeyDown: (e: React.KeyboardEvent) => void;
}

export function useSidebarPanel(): UseSidebarPanelReturn {
  const [state, setState] = useState<SidebarPanelState>({
    isOpen: false,
    activePanel: null,
    width: DEFAULT_WIDTH,
  });

  // COL-C2: store the element that triggered open so focus can return on close
  const triggerElementRef = useRef<HTMLElement | null>(null);

  const openSidebar = useCallback((panel: SidebarPanelId, triggerEl?: HTMLElement | null) => {
    if (triggerEl !== undefined) {
      triggerElementRef.current = triggerEl;
    }
    setState((prev) => ({ ...prev, isOpen: true, activePanel: panel }));
  }, []);

  const closeSidebar = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false, activePanel: null }));
    // COL-C2: return focus to the element that opened the sidebar
    triggerElementRef.current?.focus();
    triggerElementRef.current = null;
  }, []);

  const setWidth = useCallback((width: number) => {
    const clamped = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
    setState((prev) => ({ ...prev, width: clamped }));
  }, []);

  // COL-C1: keyboard resize — ArrowLeft/Right on drag handle adjust width ±16px
  const dragHandleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setWidth(state.width - KEYBOARD_RESIZE_STEP);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setWidth(state.width + KEYBOARD_RESIZE_STEP);
      }
    },
    [state.width, setWidth]
  );

  // Close on Escape key
  useEffect(() => {
    if (!state.isOpen) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        closeSidebar();
      }
    }

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [state.isOpen, closeSidebar]);

  return {
    isOpen: state.isOpen,
    activePanel: state.activePanel,
    width: state.width,
    openSidebar,
    closeSidebar,
    setWidth,
    dragHandleKeyDown,
  };
}

export const SIDEBAR_DEFAULTS = { DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH };

export type { UseSidebarPanelReturn as SidebarPanelControls };
export { KEYBOARD_RESIZE_STEP };

// Drag-resize hook extracted for testability
export function useSidebarDrag(
  currentWidth: number,
  setWidth: (w: number) => void,
  containerRef: React.RefObject<HTMLElement | null>
) {
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(currentWidth);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      isDragging.current = true;
      startX.current = e.clientX;
      startWidth.current = currentWidth;
      e.preventDefault();

      function onMouseMove(ev: MouseEvent) {
        if (!isDragging.current) return;
        const delta = startX.current - ev.clientX;
        setWidth(startWidth.current + delta);
      }

      function onMouseUp() {
        isDragging.current = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      }

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    },
    [currentWidth, setWidth]
  );

  return { onMouseDown, containerRef };
}
