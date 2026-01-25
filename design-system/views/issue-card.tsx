/**
 * Issue Card Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 *
 * Compact card for displaying issues in board/list views.
 * Features:
 * - Interactive cards with scale+shadow hover
 * - Keyboard accessible (Enter/Space to open)
 * - Proper semantic structure
 * - AI collaborative attribution support
 * - Lucide icons
 */

import * as React from 'react';
import { GripVertical, MessageCircle, Paperclip } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '../components/card';
import { Badge, AIBadge, LabelBadge } from '../components/badge';
import { UserAvatar, AvatarGroup } from '../components/avatar';

// =============================================================================
// TYPES
// =============================================================================

export type IssueState =
  | 'backlog'
  | 'todo'
  | 'in-progress'
  | 'in-review'
  | 'done'
  | 'cancelled';

export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';

export interface IssueLabel {
  id: string;
  name: string;
  color: string;
}

export interface IssueAssignee {
  name: string;
  email?: string;
  avatarUrl?: string | null;
}

export interface Issue {
  id: string;
  identifier: string; // e.g., "PS-123"
  title: string;
  description?: string;
  state: IssueState;
  priority: IssuePriority;
  labels: IssueLabel[];
  assignees: IssueAssignee[];
  commentCount?: number;
  attachmentCount?: number;
  dueDate?: Date;
  isAISuggested?: boolean;
  aiConfidence?: number;
  createdAt: Date;
  updatedAt: Date;
}

// =============================================================================
// STATE ICONS
// =============================================================================

const stateIcons: Record<IssueState, React.ReactNode> = {
  backlog: (
    <div className="h-3.5 w-3.5 rounded-full border-2 border-state-backlog" />
  ),
  todo: (
    <div className="h-3.5 w-3.5 rounded-full border-2 border-state-todo" />
  ),
  'in-progress': (
    <div className="relative h-3.5 w-3.5">
      <div className="absolute inset-0 rounded-full border-2 border-state-in-progress" />
      <div className="absolute inset-[3px] rounded-full bg-state-in-progress" />
    </div>
  ),
  'in-review': (
    <div className="relative h-3.5 w-3.5">
      <div className="absolute inset-0 rounded-full border-2 border-state-in-review" />
      <div className="absolute inset-[3px] rounded-full bg-state-in-review" />
    </div>
  ),
  done: (
    <div className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-state-done text-white">
      <svg className="h-2.5 w-2.5" viewBox="0 0 12 12" fill="none">
        <path
          d="M2.5 6L5 8.5L9.5 4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  ),
  cancelled: (
    <div className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-state-cancelled text-white">
      <svg className="h-2.5 w-2.5" viewBox="0 0 12 12" fill="none">
        <path
          d="M3 9L9 3M3 3L9 9"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    </div>
  ),
};

// =============================================================================
// PRIORITY ICONS
// =============================================================================

function PriorityIcon({ priority }: { priority: IssuePriority }) {
  const bars = {
    urgent: 4,
    high: 3,
    medium: 2,
    low: 1,
    none: 0,
  };

  const colors = {
    urgent: 'bg-priority-urgent',
    high: 'bg-priority-high',
    medium: 'bg-priority-medium',
    low: 'bg-priority-low',
    none: 'bg-priority-none',
  };

  if (priority === 'none') {
    return (
      <div className="flex h-4 w-4 items-center justify-center">
        <div className="h-0.5 w-2 rounded-full bg-muted-foreground/40" />
      </div>
    );
  }

  return (
    <div
      className="flex h-4 w-4 items-end justify-center gap-0.5"
      aria-label={`Priority: ${priority}`}
    >
      {[1, 2, 3, 4].map((level) => (
        <div
          key={level}
          className={cn(
            'w-[3px] rounded-sm',
            level <= bars[priority] ? colors[priority] : 'bg-muted',
            level === 1 && 'h-1',
            level === 2 && 'h-1.5',
            level === 3 && 'h-2',
            level === 4 && 'h-2.5'
          )}
        />
      ))}
    </div>
  );
}

// =============================================================================
// ISSUE CARD COMPONENT
// =============================================================================

export interface IssueCardProps {
  issue: Issue;
  isDragging?: boolean;
  showState?: boolean;
  onClick?: () => void;
  onContextMenu?: (e: React.MouseEvent) => void;
  className?: string;
}

export function IssueCard({
  issue,
  isDragging = false,
  showState = true,
  onClick,
  onContextMenu,
  className,
}: IssueCardProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <Card
      variant="interactive"
      padding="sm"
      className={cn(
        'group relative',
        isDragging && 'rotate-2 scale-105 shadow-lg',
        issue.state === 'cancelled' && 'opacity-60',
        className
      )}
      onClick={onClick}
      onContextMenu={onContextMenu}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Issue ${issue.identifier}: ${issue.title}`}
    >
      {/* Drag handle - visible on hover */}
      <div className="absolute -left-1 top-1/2 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-50">
        <GripVertical className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </div>

      {/* Header: State + Identifier */}
      <div className="mb-2 flex items-center gap-2">
        {showState && (
          <div aria-label={`State: ${issue.state}`}>
            {stateIcons[issue.state]}
          </div>
        )}
        <span className="text-xs font-medium text-muted-foreground">
          {issue.identifier}
        </span>
        {issue.isAISuggested && (
          <AIBadge type="suggestion" confidence={issue.aiConfidence}>
            AI
          </AIBadge>
        )}
      </div>

      {/* Title */}
      <h4
        className={cn(
          'text-sm font-medium leading-snug',
          issue.state === 'cancelled' && 'line-through'
        )}
      >
        {issue.title}
      </h4>

      {/* Labels */}
      {issue.labels.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {issue.labels.slice(0, 3).map((label) => (
            <LabelBadge key={label.id} color={label.color}>
              {label.name}
            </LabelBadge>
          ))}
          {issue.labels.length > 3 && (
            <Badge variant="secondary">+{issue.labels.length - 3}</Badge>
          )}
        </div>
      )}

      {/* Footer: Metadata + Assignees */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PriorityIcon priority={issue.priority} />

          {issue.commentCount !== undefined && issue.commentCount > 0 && (
            <div className="flex items-center gap-0.5 text-xs text-muted-foreground">
              <MessageCircle className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="tabular-nums">{issue.commentCount}</span>
            </div>
          )}

          {issue.attachmentCount !== undefined && issue.attachmentCount > 0 && (
            <div className="flex items-center gap-0.5 text-xs text-muted-foreground">
              <Paperclip className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="tabular-nums">{issue.attachmentCount}</span>
            </div>
          )}

          {issue.dueDate && (
            <span
              className={cn(
                'text-xs',
                new Date(issue.dueDate) < new Date()
                  ? 'text-destructive'
                  : 'text-muted-foreground'
              )}
            >
              {new Intl.DateTimeFormat('en-US', {
                month: 'short',
                day: 'numeric',
              }).format(issue.dueDate)}
            </span>
          )}
        </div>

        {issue.assignees.length > 0 && (
          <AvatarGroup users={issue.assignees} max={2} size="xs" />
        )}
      </div>
    </Card>
  );
}

// =============================================================================
// COMPACT ISSUE ROW (for list views)
// =============================================================================

export interface IssueRowProps {
  issue: Issue;
  isSelected?: boolean;
  onClick?: () => void;
  onDoubleClick?: () => void;
  className?: string;
}

export function IssueRow({
  issue,
  isSelected = false,
  onClick,
  onDoubleClick,
  className,
}: IssueRowProps) {
  return (
    <div
      className={cn(
        'group flex items-center gap-3 rounded-md border bg-card px-3 py-2',
        'cursor-pointer transition-colors hover:bg-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isSelected && 'bg-accent ring-2 ring-primary',
        className
      )}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      tabIndex={0}
      role="button"
      aria-selected={isSelected}
    >
      {/* State icon */}
      <div aria-label={`State: ${issue.state}`}>
        {stateIcons[issue.state]}
      </div>

      {/* Identifier */}
      <span className="w-16 flex-shrink-0 text-xs font-medium text-muted-foreground">
        {issue.identifier}
      </span>

      {/* Title */}
      <span
        className={cn(
          'min-w-0 flex-1 truncate text-sm',
          issue.state === 'cancelled' && 'line-through text-muted-foreground'
        )}
      >
        {issue.title}
      </span>

      {/* AI indicator */}
      {issue.isAISuggested && (
        <AIBadge type="suggestion" className="flex-shrink-0">
          AI
        </AIBadge>
      )}

      {/* Priority */}
      <PriorityIcon priority={issue.priority} />

      {/* Labels (max 2) */}
      <div className="hidden w-32 flex-shrink-0 gap-1 lg:flex">
        {issue.labels.slice(0, 2).map((label) => (
          <LabelBadge key={label.id} color={label.color}>
            {label.name}
          </LabelBadge>
        ))}
      </div>

      {/* Assignee */}
      <div className="w-6 flex-shrink-0">
        {issue.assignees[0] && (
          <UserAvatar user={issue.assignees[0]} size="xs" />
        )}
      </div>
    </div>
  );
}
