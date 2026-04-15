/**
 * BatchPreviewCard - Container card for previewing, editing, and approving a batch of proposed issues.
 *
 * CRITICAL: Must NOT be wrapped in observer() — plain React.memo + useState only.
 * Same constraint as IssueEditorContent per CLAUDE.md TipTap rule and RESEARCH Pitfall 1.
 *
 * DD-003 approval gate: "Create All" does NOT directly call the batch API.
 * It calls onCreateAll, which triggers the approval flow in the parent wrapper.
 * Only after user confirms in the approval dialog does the batch API call execute.
 *
 * Phase 75: Chat-to-issue pipeline (CIP-03, CIP-04)
 */

'use client';

import { memo, useState, useCallback } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { motion, useReducedMotion, type Easing } from 'motion/react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { ProposedIssue } from '@/stores/ai/types/events';
import { IssuePreviewItem } from './IssuePreviewItem';

type BatchStatus = 'editing' | 'creating' | 'created' | 'error';

export interface BatchPreviewCardProps {
  /** Proposed issues from the AI pipeline */
  issues: ProposedIssue[];
  /** Callback triggered when PM clicks "Create All" — implements DD-003 approval gate */
  onCreateAll: (issues: ProposedIssue[]) => Promise<void>;
  /** Project name for contextual footer label */
  projectName?: string;
}

/**
 * BatchPreviewCard renders a stacked, collapsible list of proposed issues.
 * Uses React.memo + useState for local state. NOT observer().
 */
export const BatchPreviewCard = memo<BatchPreviewCardProps>(function BatchPreviewCard({
  issues: initialIssues,
  onCreateAll,
  projectName,
}) {
  const [editableIssues, setEditableIssues] = useState<ProposedIssue[]>(initialIssues);
  const [status, setStatus] = useState<BatchStatus>('editing');
  const [createdCount, setCreatedCount] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const prefersReducedMotion = useReducedMotion();

  const handleRemove = useCallback((index: number) => {
    setEditableIssues((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpdate = useCallback((index: number, updates: Partial<ProposedIssue>) => {
    setEditableIssues((prev) =>
      prev.map((issue, i) => (i === index ? { ...issue, ...updates } : issue))
    );
  }, []);

  const handleCreateAll = useCallback(async () => {
    if (editableIssues.length === 0 || status !== 'editing') return;
    setStatus('creating');
    try {
      await onCreateAll(editableIssues);
      setCreatedCount(editableIssues.length);
      setStatus('created');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create issues';
      setErrorMessage(msg);
      setStatus('error');
    }
  }, [editableIssues, onCreateAll, status]);

  const issueCount = editableIssues.length;

  // Mount animation: 300ms slide-up + fade (respects prefers-reduced-motion)
  const EASE_OUT: Easing = [0.0, 0.0, 0.2, 1.0];
  const motionProps = prefersReducedMotion
    ? {}
    : {
        initial: { opacity: 0, y: 12 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.3, ease: EASE_OUT },
      };

  // Empty batch state (per locked decision — NOT "Nothing to create yet")
  if (initialIssues.length === 0) {
    return (
      <motion.div
        {...motionProps}
        className="bg-card border border-border rounded-[14px] p-4 shadow-sm"
        data-testid="batch-preview-card"
      >
        <div className="flex items-center gap-2 py-2 text-muted-foreground">
          <AlertCircle size={16} className="text-destructive shrink-0" />
          <div>
            <p className="text-sm font-medium text-foreground">No issues could be extracted</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Try providing more detail about the features, bugs, or tasks you&apos;d like to track.
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  // Created state: replace card stack with success message
  if (status === 'created') {
    const slug = projectName ? ` in ${projectName}` : '';
    return (
      <motion.div
        {...motionProps}
        className="bg-card border border-border rounded-[14px] p-4 shadow-sm"
        data-testid="batch-preview-card"
      >
        <div className="flex items-center gap-2 py-1 text-sm text-foreground">
          <span className="h-2 w-2 rounded-full bg-primary shrink-0" aria-hidden="true" />
          <span>
            <strong>{createdCount} issue{createdCount !== 1 ? 's' : ''}</strong> created{slug}.
          </span>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      {...motionProps}
      className="bg-card border border-border rounded-[14px] p-4 shadow-sm"
      data-testid="batch-preview-card"
    >
      {/* Header */}
      <p className="text-[14px] text-muted-foreground mb-3">
        {issueCount} proposed issue{issueCount !== 1 ? 's' : ''} — review and edit before creating
      </p>

      {/* Issue list */}
      <div role="list" className="rounded-lg border border-border overflow-hidden">
        {editableIssues.map((issue, idx) => (
          <div key={idx}>
            <IssuePreviewItem
              issue={issue}
              index={idx}
              onRemove={handleRemove}
              onUpdate={handleUpdate}
            />
            {idx < editableIssues.length - 1 && (
              <Separator className="bg-border/60" />
            )}
          </div>
        ))}
      </div>

      {/* Error state */}
      {status === 'error' && errorMessage && (
        <p className="mt-2 text-xs text-destructive">
          Some issues couldn&apos;t be created. Try again or create individually.
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 gap-3">
        <p className="text-[12px] text-muted-foreground flex-1 min-w-0">
          {issueCount > 0 ? (
            <>
              <span className="font-mono">{issueCount}</span> issue{issueCount !== 1 ? 's' : ''} ·{' '}
              Labels and assignees can be added after creation
            </>
          ) : (
            'No issues remaining'
          )}
        </p>

        <Button
          variant="default"
          className={cn(
            'h-11 px-4 shrink-0 bg-primary hover:bg-primary/90 text-primary-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
          )}
          disabled={issueCount === 0 || status === 'creating'}
          onClick={handleCreateAll}
          aria-label={
            issueCount === 0
              ? 'No issues remaining'
              : `Create All ${issueCount} Issue${issueCount !== 1 ? 's' : ''}`
          }
        >
          {status === 'creating' ? (
            <>
              <Loader2 size={16} className="animate-spin mr-2" />
              Creating issues...
            </>
          ) : issueCount === 0 ? (
            'No issues remaining'
          ) : (
            `Create All ${issueCount} Issue${issueCount !== 1 ? 's' : ''}`
          )}
        </Button>
      </div>
    </motion.div>
  );
});

BatchPreviewCard.displayName = 'BatchPreviewCard';
