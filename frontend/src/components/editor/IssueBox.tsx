'use client';

/**
 * IssueBox - Inline issue reference component for note content
 * Shows issue with rainbow border animation for new issues
 */
import { forwardRef, useState, useEffect } from 'react';
import { Bug, Zap, Pencil, Circle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export type IssueType = 'bug' | 'improvement' | 'performance' | 'task';
export type IssueStatus = 'new' | 'in-progress' | 'completed';

export interface IssueBoxProps {
  /** Issue identifier (e.g., "PS-201") */
  issueId: string;
  /** Issue title */
  title: string;
  /** Issue type for icon selection */
  type?: IssueType;
  /** Issue status */
  status?: IssueStatus;
  /** Whether this is a newly created issue (shows rainbow animation) */
  isNew?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Additional class names */
  className?: string;
}

const issueIcons: Record<IssueType, typeof Bug> = {
  bug: Bug,
  improvement: Pencil,
  performance: Zap,
  task: Circle,
};

const iconColors: Record<IssueType, string> = {
  bug: 'text-destructive',
  improvement: 'text-ai',
  performance: 'text-warning',
  task: 'text-muted-foreground',
};

/**
 * IssueBox component for inline issue references in notes
 */
export const IssueBox = forwardRef<HTMLSpanElement, IssueBoxProps>(function IssueBox(
  { issueId, title, type = 'task', status = 'in-progress', isNew = false, onClick, className },
  ref
) {
  const [showRainbow, setShowRainbow] = useState(isNew);
  const Icon = status === 'completed' ? CheckCircle2 : issueIcons[type];

  // Remove rainbow animation after 2.5 seconds
  useEffect(() => {
    if (isNew) {
      const timer = setTimeout(() => {
        setShowRainbow(false);
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [isNew]);

  return (
    <span
      ref={ref}
      onClick={onClick}
      className={cn(
        'issue-box',
        status === 'completed' && 'issue-box-completed',
        showRainbow && 'issue-box-new',
        onClick && 'cursor-pointer',
        className
      )}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <Icon
        className={cn(
          'issue-box-icon',
          status === 'completed' ? 'text-state-done' : iconColors[type]
        )}
      />
      <span className="issue-box-id">{issueId}</span>
      <span className="issue-box-title">{title}</span>
    </span>
  );
});

export default IssueBox;
