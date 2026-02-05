'use client';

/**
 * Resizable Panel Components
 * Based on react-resizable-panels v4.x with shadcn/ui styling
 *
 * Usage:
 * <ResizablePanelGroup orientation="horizontal">
 *   <ResizablePanel defaultSize="50%">Left content</ResizablePanel>
 *   <ResizableHandle />
 *   <ResizablePanel defaultSize="50%">Right content</ResizablePanel>
 * </ResizablePanelGroup>
 */

import * as React from 'react';
import { EllipsisVertical } from 'lucide-react';
import { Group, Panel, Separator } from 'react-resizable-panels';

import { cn } from '@/lib/utils';

// Re-export Panel directly (it already has proper types)
const ResizablePanel = Panel;

// Wrap Group with styling
const ResizablePanelGroup = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof Group>
>(({ className, ...props }, ref) => (
  <Group
    className={cn('flex h-full w-full', className)}
    {...props}
    elementRef={ref}
  />
));
ResizablePanelGroup.displayName = 'ResizablePanelGroup';

// Wrap Separator with styling and optional handle
interface ResizableHandleProps extends React.ComponentProps<typeof Separator> {
  /** Show a visible handle grip */
  withHandle?: boolean;
  /** Current state: 'min' when right panel at minimum, 'max' when at maximum */
  toggleState?: 'min' | 'max' | 'mid';
  /** Callback when handle is clicked (for toggle min/max) */
  onToggle?: () => void;
}

const ResizableHandle = React.forwardRef<HTMLDivElement, ResizableHandleProps>(
  ({ withHandle, toggleState = 'mid', onToggle, className, ...props }, ref) => (
    <Separator
      className={cn(
        'relative flex w-px items-center justify-center bg-border',
        // Expand hit target for easier dragging
        'after:absolute after:inset-y-0 after:left-1/2 after:w-2 after:-translate-x-1/2',
        // Focus styles
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1',
        // Hover state - highlight and cursor
        'hover:bg-primary/30 transition-colors cursor-col-resize',
        // Active/dragging state (data attribute from library)
        'data-[resize-handle-state=drag]:bg-primary/50',
        'data-[resize-handle-state=hover]:bg-primary/20',
        className
      )}
      {...props}
      elementRef={ref}
    >
      {withHandle && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          className={cn(
            'z-10 flex h-8 w-4 items-center justify-center rounded-sm',
            'border bg-background shadow-sm',
            'hover:bg-muted hover:border-primary/50',
            'active:bg-muted/80',
            'transition-colors cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-primary/50'
          )}
          title={toggleState === 'min' ? 'Expand panel' : 'Collapse panel'}
          aria-label={toggleState === 'min' ? 'Expand panel to maximum' : 'Collapse panel to minimum'}
        >
          <EllipsisVertical className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      )}
    </Separator>
  )
);
ResizableHandle.displayName = 'ResizableHandle';

export { ResizablePanelGroup, ResizablePanel, ResizableHandle };
export type { ResizableHandleProps };
