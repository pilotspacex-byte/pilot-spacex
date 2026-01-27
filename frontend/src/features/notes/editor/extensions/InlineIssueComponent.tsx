'use client';

/**
 * InlineIssueComponent - React component for inline issue TipTap node
 *
 * Per UI Spec v3.3 / Prototype v4:
 * - Rainbow gradient border for active issues
 * - Green border for completed issues
 * - Type icon (bug, improvement, feature)
 * - Issue key and truncated title
 * - Hover shows issue details card
 *
 * @see DD-013 Note-First Collaborative Workspace
 * @see UI Spec v3.3 Section 7 - Issue Box Specifications
 */
import { useCallback, useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { Bug, Wrench, Zap, CheckSquare, Check, ExternalLink } from 'lucide-react';
import Link from 'next/link';

import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type {
  InlineIssueAttributes,
  IssueType,
  IssueState,
  IssuePriority,
} from './InlineIssueExtension';

/**
 * Issue type icons
 */
const ISSUE_TYPE_ICONS: Record<IssueType, typeof Bug> = {
  bug: Bug,
  improvement: Wrench,
  feature: Zap,
  task: CheckSquare,
};

/**
 * Issue type colors
 */
const ISSUE_TYPE_COLORS: Record<IssueType, string> = {
  bug: 'text-destructive',
  improvement: 'text-primary',
  feature: 'text-ai',
  task: 'text-foreground',
};

/**
 * State badge styles
 */
const STATE_STYLES: Record<IssueState, { bg: string; text: string; label: string }> = {
  backlog: {
    bg: 'bg-gray-100 dark:bg-gray-800',
    text: 'text-gray-600 dark:text-gray-400',
    label: 'Backlog',
  },
  todo: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-400',
    label: 'Todo',
  },
  in_progress: {
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-600 dark:text-amber-400',
    label: 'In Progress',
  },
  in_review: {
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    text: 'text-purple-600 dark:text-purple-400',
    label: 'In Review',
  },
  done: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-600 dark:text-green-400',
    label: 'Done',
  },
  cancelled: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-600 dark:text-red-400',
    label: 'Cancelled',
  },
};

/**
 * Priority display
 */
const PRIORITY_DISPLAY: Record<IssuePriority, { bars: number; color: string }> = {
  urgent: { bars: 4, color: 'bg-destructive' },
  high: { bars: 3, color: 'bg-orange-500' },
  medium: { bars: 2, color: 'bg-yellow-500' },
  low: { bars: 1, color: 'bg-blue-400' },
  none: { bars: 0, color: 'bg-gray-300' },
};

/**
 * Priority bars indicator
 */
function PriorityBars({ priority }: { priority: IssuePriority }) {
  const { bars, color } = PRIORITY_DISPLAY[priority];

  if (bars === 0) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className={cn('w-1 h-2.5 rounded-sm', i < bars ? color : 'bg-gray-200 dark:bg-gray-700')}
        />
      ))}
    </div>
  );
}

/**
 * InlineIssueComponent renders an inline issue reference with rainbow border
 */
export function InlineIssueComponent({ node }: NodeViewProps) {
  const params = useParams<{ workspaceSlug: string }>();
  const workspaceSlug = params.workspaceSlug ?? '';

  const attrs = node.attrs as InlineIssueAttributes;
  const {
    issueId,
    issueKey,
    title,
    type = 'task',
    state = 'todo',
    priority = 'none',
    isNew = false,
  } = attrs;

  const [showRainbow, setShowRainbow] = useState(isNew);
  const isDone = state === 'done';
  const isCancelled = state === 'cancelled';
  const Icon = ISSUE_TYPE_ICONS[type] || CheckSquare;
  const typeColor = ISSUE_TYPE_COLORS[type];
  const stateStyle = STATE_STYLES[state];

  // Remove rainbow animation after initial display
  useEffect(() => {
    if (isNew) {
      const timer = setTimeout(() => {
        setShowRainbow(false);
      }, 3000); // Animation duration
      return () => clearTimeout(timer);
    }
  }, [isNew]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Navigate or open issue panel
    // This would be passed from the extension options
  }, []);

  return (
    <NodeViewWrapper as="span" className="inline align-middle">
      <HoverCard openDelay={300} closeDelay={100}>
        <HoverCardTrigger asChild>
          <span
            role="button"
            tabIndex={0}
            onClick={handleClick}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                handleClick(e as unknown as React.MouseEvent);
              }
            }}
            className={cn(
              'inline-issue-node',
              // Base styling handled by CSS - just add modifier classes
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
              // State-based styling
              isDone && 'state-done',
              isCancelled && 'opacity-60',
              // Type-based class for gradient
              `type-${type}`,
              // Rainbow animation for new issues (always visible)
              showRainbow && 'issue-rainbow-border',
              // Done state uses green border
              isDone && 'issue-done-border'
            )}
            data-issue-id={issueId}
          >
            {/* Type icon */}
            <Icon className={cn('h-3.5 w-3.5 flex-shrink-0', typeColor)} />

            {/* Issue key */}
            <span className="issue-key font-mono text-xs font-medium text-muted-foreground">
              {issueKey}
            </span>

            {/* Title */}
            <span
              className={cn(
                'issue-title text-sm font-medium truncate max-w-[180px]',
                isDone && 'line-through text-muted-foreground',
                !isDone && 'text-foreground'
              )}
            >
              {title}
            </span>

            {/* Done checkmark */}
            {isDone && <Check className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />}
          </span>
        </HoverCardTrigger>

        {/* Hover Card Content */}
        <HoverCardContent
          side="bottom"
          align="start"
          className="w-80 p-0 overflow-hidden"
          sideOffset={8}
        >
          <div className="p-4 space-y-3">
            {/* Header */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <Icon className={cn('h-4 w-4 flex-shrink-0', typeColor)} />
                <span className="font-mono text-sm font-semibold text-foreground">{issueKey}</span>
              </div>
              <Button variant="ghost" size="sm" className="h-7 px-2 -mr-2" asChild>
                <Link href={`/${workspaceSlug}/issues/${issueId}`}>
                  Open <ExternalLink className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            </div>

            {/* Title */}
            <h4 className="font-medium text-foreground leading-snug">{title}</h4>

            {/* Meta row */}
            <div className="flex items-center gap-3 text-xs">
              <Badge
                variant="secondary"
                className={cn('font-normal', stateStyle.bg, stateStyle.text)}
              >
                {stateStyle.label}
              </Badge>
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <span>Priority:</span>
                <PriorityBars priority={priority} />
              </div>
            </div>

            {/* Footer */}
            <div className="pt-2 border-t border-border text-xs text-muted-foreground">
              <span>Linked from this note</span>
            </div>
          </div>
        </HoverCardContent>
      </HoverCard>
    </NodeViewWrapper>
  );
}

export default InlineIssueComponent;
