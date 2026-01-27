'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Check, X, Clock, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { ToolCall, ToolCallStatus } from './types';

/* -----------------------------------------------------------------------------
 * Tool Call Item
 * -------------------------------------------------------------------------- */

const toolCallVariants = cva('rounded-lg border bg-card text-card-foreground transition-colors', {
  variants: {
    status: {
      pending: 'border-muted bg-muted/50',
      running: 'border-blue-500/50 bg-blue-500/10',
      complete: 'border-emerald-500/50 bg-emerald-500/10',
      error: 'border-destructive/50 bg-destructive/10',
    },
  },
  defaultVariants: {
    status: 'pending',
  },
});

export interface ToolCallItemProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof toolCallVariants> {
  /** Tool call data */
  toolCall: ToolCall;
  /** Whether content is collapsed by default */
  defaultCollapsed?: boolean;
}

const ToolCallItem = React.forwardRef<HTMLDivElement, ToolCallItemProps>(
  ({ className, toolCall, defaultCollapsed = true, ...props }, ref) => {
    const [isOpen, setIsOpen] = React.useState(!defaultCollapsed);
    const hasOutput = toolCall.output || toolCall.error;

    return (
      <div
        ref={ref}
        className={cn(toolCallVariants({ status: toolCall.status }), className)}
        {...props}
      >
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-muted/50 transition-colors">
            <ToolCallStatusIcon status={toolCall.status} />
            <span className="flex-1 text-left font-medium">{toolCall.name}</span>
            {toolCall.duration && (
              <span className="text-xs text-muted-foreground">
                {formatDuration(toolCall.duration)}
              </span>
            )}
            {hasOutput &&
              (isOpen ? (
                <ChevronDown className="size-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="size-4 text-muted-foreground" />
              ))}
          </CollapsibleTrigger>

          {hasOutput && (
            <CollapsibleContent className="border-t px-3 py-2">
              <div className="space-y-2">
                {toolCall.input && Object.keys(toolCall.input).length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-muted-foreground">Input</div>
                    <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">
                      {JSON.stringify(toolCall.input, null, 2)}
                    </pre>
                  </div>
                )}

                {toolCall.output && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-muted-foreground">Output</div>
                    <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">
                      {toolCall.output}
                    </pre>
                  </div>
                )}

                {toolCall.error && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-destructive">Error</div>
                    <pre className="overflow-x-auto rounded bg-destructive/10 p-2 text-xs text-destructive">
                      {toolCall.error}
                    </pre>
                  </div>
                )}
              </div>
            </CollapsibleContent>
          )}
        </Collapsible>
      </div>
    );
  }
);
ToolCallItem.displayName = 'ToolCallItem';

/* -----------------------------------------------------------------------------
 * Tool Call Status Icon
 * -------------------------------------------------------------------------- */

interface ToolCallStatusIconProps {
  status: ToolCallStatus;
  className?: string;
}

function ToolCallStatusIcon({ status, className }: ToolCallStatusIconProps) {
  const baseClass = 'size-4 shrink-0';

  switch (status) {
    case 'pending':
      return <Clock className={cn(baseClass, 'text-muted-foreground', className)} />;
    case 'running':
      return <Loader2 className={cn(baseClass, 'animate-spin text-blue-500', className)} />;
    case 'complete':
      return <Check className={cn(baseClass, 'text-emerald-500', className)} />;
    case 'error':
      return <X className={cn(baseClass, 'text-destructive', className)} />;
    default:
      return null;
  }
}

/* -----------------------------------------------------------------------------
 * Tool Call List
 * -------------------------------------------------------------------------- */

export interface ToolCallListProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Tool calls to display */
  toolCalls: ToolCall[];
  /** Whether items are collapsed by default */
  defaultCollapsed?: boolean;
}

const ToolCallList = React.forwardRef<HTMLDivElement, ToolCallListProps>(
  ({ className, toolCalls, defaultCollapsed = true, ...props }, ref) => {
    if (!toolCalls.length) return null;

    return (
      <div ref={ref} className={cn('space-y-2', className)} {...props}>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            Tools ({toolCalls.length})
          </Badge>
        </div>
        <div className="space-y-1.5">
          {toolCalls.map((toolCall) => (
            <ToolCallItem
              key={toolCall.id}
              toolCall={toolCall}
              defaultCollapsed={defaultCollapsed}
            />
          ))}
        </div>
      </div>
    );
  }
);
ToolCallList.displayName = 'ToolCallList';

/* -----------------------------------------------------------------------------
 * Tool Call Badge
 * -------------------------------------------------------------------------- */

export interface ToolCallBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Tool call status */
  status: ToolCallStatus;
  /** Tool name */
  name: string;
  /** Show duration */
  duration?: number;
}

const ToolCallBadge = React.forwardRef<HTMLDivElement, ToolCallBadgeProps>(
  ({ className, status, name, duration, ...props }, ref) => {
    return (
      <Badge
        ref={ref}
        variant={status === 'error' ? 'destructive' : 'secondary'}
        className={cn('inline-flex items-center gap-1.5', className)}
        {...props}
      >
        <ToolCallStatusIcon status={status} />
        <span className="text-xs">{name}</span>
        {duration && <span className="text-xs opacity-70">{formatDuration(duration)}</span>}
      </Badge>
    );
  }
);
ToolCallBadge.displayName = 'ToolCallBadge';

/* -----------------------------------------------------------------------------
 * Utilities
 * -------------------------------------------------------------------------- */

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/* -----------------------------------------------------------------------------
 * Exports
 * -------------------------------------------------------------------------- */

export { ToolCallItem, ToolCallList, ToolCallBadge, ToolCallStatusIcon, toolCallVariants };
