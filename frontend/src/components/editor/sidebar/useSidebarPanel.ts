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

export interface UseSidebarPanelReturn {
  isOpen: boolean;
  activePanel: SidebarPanelId | null;
  width: number;
  openSidebar: (panel: SidebarPanelId) => void;
  closeSidebar: () => void;
  setWidth: (width: number) => void;
}

export function useSidebarPanel(): UseSidebarPanelReturn {
  const [state, setState] = useState<SidebarPanelState>({
    isOpen: false,
    activePanel: null,
    width: DEFAULT_WIDTH,
  });

  const openSidebar = useCallback((panel: SidebarPanelId) => {
    setState((prev) => ({ ...prev, isOpen: true, activePanel: panel }));
  }, []);

  const closeSidebar = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false, activePanel: null }));
  }, []);

  const setWidth = useCallback((width: number) => {
    const clamped = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
    setState((prev) => ({ ...prev, width: clamped }));
  }, []);

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
  };
}

export const SIDEBAR_DEFAULTS = { DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH };

export type { UseSidebarPanelReturn as SidebarPanelControls };

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
