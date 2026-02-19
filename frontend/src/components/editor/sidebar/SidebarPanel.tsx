'use client';

/**
 * SidebarPanel - Right-side sliding panel container for Features 016 and 017.
 *
 * - Configurable tabs (Versions, Presence, Conversation)
 * - Resizable via drag handle (min 240px, default 320px, max 480px)
 * - Responsive: full overlay on mobile (<768px)
 * - Animation: slide-in from right, 200ms ease-out
 * - Accessible: focus trap, aria roles, Escape to close
 */

import { useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SidebarPanelHeader } from './SidebarPanelHeader';
import { SidebarPanelContent } from './SidebarPanelContent';
import { useSidebarDrag } from './useSidebarPanel';
import type { SidebarTab } from './SidebarPanelHeader';
import type { SidebarPanelId } from './useSidebarPanel';

export interface SidebarPanelProps {
  /** Whether the sidebar is visible */
  isOpen: boolean;
  /** Currently active tab/panel */
  activePanel: SidebarPanelId | null;
  /** Configurable tabs shown in the header */
  tabs?: SidebarTab[];
  /** Panel title shown in header */
  title?: string;
  /** Panel width in pixels (clamped between min/max) */
  width?: number;
  /** Content to render inside the panel */
  children: React.ReactNode;
  /** Called when user switches tabs */
  onTabChange: (panel: SidebarPanelId) => void;
  /** Called when user closes the panel */
  onClose: () => void;
  /** Called when user resizes the panel */
  onWidthChange?: (width: number) => void;
  /** Additional class for the panel root */
  className?: string;
}

const ANIMATION_DURATION = 0.2;

export function SidebarPanel({
  isOpen,
  activePanel,
  tabs,
  title = 'Panel',
  width = 320,
  children,
  onTabChange,
  onClose,
  onWidthChange,
  className,
}: SidebarPanelProps) {
  const panelRef = useRef<HTMLElement | null>(null);

  // Focus trap: when opened, move focus to first focusable element in panel
  useEffect(() => {
    if (!isOpen) return;
    const panel = panelRef.current;
    if (!panel) return;
    const firstFocusable = panel.querySelector<HTMLElement>(
      'button:not([disabled]), a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    firstFocusable?.focus();
  }, [isOpen]);

  // Focus trap: intercept Tab to stay within panel
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key !== 'Tab') return;

      const panel = panelRef.current;
      if (!panel) return;

      const focusable = panel.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    },
    [isOpen, onClose]
  );

  const { onMouseDown } = useSidebarDrag(width, onWidthChange ?? (() => {}), panelRef);

  const panelStyle = { width: `${width}px`, minWidth: '240px', maxWidth: '480px' };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Mobile backdrop (<768px) */}
          <motion.div
            key="sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: ANIMATION_DURATION }}
            className="fixed inset-0 bg-background/60 backdrop-blur-sm z-30 md:hidden"
            onClick={onClose}
            aria-hidden="true"
            data-testid="sidebar-backdrop"
          />

          {/* Drag handle (desktop only, positioned absolutely left of panel) */}
          <motion.div
            key="sidebar-drag-handle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: ANIMATION_DURATION }}
            className="hidden md:flex fixed right-0 top-0 bottom-0 z-40 items-center"
            style={{ right: `${width}px` }}
          >
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize sidebar panel"
              onMouseDown={onMouseDown}
              className={cn(
                'flex h-12 w-3 cursor-col-resize items-center justify-center',
                'rounded-l-md bg-border/60 hover:bg-border transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
              data-testid="sidebar-drag-handle"
            >
              <GripVertical className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
            </div>
          </motion.div>

          {/* Panel */}
          <motion.aside
            key="sidebar-panel"
            ref={panelRef as React.RefObject<HTMLElement>}
            role="complementary"
            aria-label={`${title} panel`}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: ANIMATION_DURATION, ease: 'easeOut' }}
            onKeyDown={handleKeyDown}
            className={cn(
              'fixed inset-y-0 right-0 z-40',
              'flex flex-col',
              'bg-background border-l border-border shadow-xl',
              // Mobile: full width overlay
              'w-full md:w-auto',
              className
            )}
            style={panelStyle}
            data-testid="sidebar-panel"
          >
            <SidebarPanelHeader
              title={title}
              tabs={tabs}
              activePanel={activePanel}
              onTabChange={onTabChange}
              onClose={onClose}
              // Expose close button ref for focus management
            />
            <SidebarPanelContent activePanel={activePanel}>{children}</SidebarPanelContent>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
