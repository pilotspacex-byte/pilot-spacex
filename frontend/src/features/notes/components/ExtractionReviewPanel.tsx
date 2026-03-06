'use client';

/**
 * ExtractionReviewPanel - Slide-over Sheet for reviewing AI-extracted issues (T-013/T-014).
 *
 * Presents extraction results for human review before creation:
 * - Per-item Approve/Skip toggle
 * - Editable title per item
 * - Collapsible rationale
 * - "Approve All" header button
 * - "Create N Issues" footer (enabled when >=1 approved)
 *
 * Data flow: receives `issues` from SSE streaming (via useIssueExtraction hook).
 * On confirm: calls aiApi.createExtractedIssues → closes panel → fires onCreated callback.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChevronDown, ChevronRight, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { aiApi } from '@/services/api/ai';
import type { ExtractedIssue } from './ExtractionPreviewModal';

// Re-export ExtractedIssue so consumers import from one place
export type { ExtractedIssue };

export interface ExtractionReviewPanelProps {
  /** Whether the panel is open */
  open: boolean;
  /** Callback to change open state */
  onOpenChange: (open: boolean) => void;
  /** Extracted issues from SSE stream */
  issues: ExtractedIssue[];
  /** Whether extraction is still streaming */
  isExtracting: boolean;
  /** Extraction error message */
  error: string | null;
  /** Workspace ID */
  workspaceId: string;
  /** Note ID the issues were extracted from */
  noteId: string;
  /** Optional project ID for issue creation */
  projectId?: string | null;
  /** Fired after issues are created with their IDs */
  onCreated?: (createdIds: string[]) => void;
}

const PRIORITY_LABELS: Record<number, { label: string; className: string }> = {
  0: {
    label: 'Urgent',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-transparent',
  },
  1: {
    label: 'High',
    className:
      'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 border-transparent',
  },
  2: {
    label: 'Medium',
    className:
      'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 border-transparent',
  },
  3: {
    label: 'Low',
    className:
      'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-transparent',
  },
  4: {
    label: 'None',
    className: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border-transparent',
  },
};

const CONFIDENCE_STYLES: Record<string, { label: string; className: string }> = {
  explicit: {
    label: 'HIGH',
    className:
      'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-transparent',
  },
  implicit: {
    label: 'MEDIUM',
    className:
      'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 border-transparent',
  },
  related: {
    label: 'LOW',
    className: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border-transparent',
  },
};

interface ReviewItem {
  issue: ExtractedIssue;
  approved: boolean;
  editedTitle: string;
  rationaleExpanded: boolean;
}

function buildReviewItems(issues: ExtractedIssue[]): ReviewItem[] {
  return issues.map((issue) => ({
    issue,
    approved: true,
    editedTitle: issue.title,
    rationaleExpanded: false,
  }));
}

/** Single issue review card */
function ReviewCard({
  item,
  onToggleApproval,
  onTitleChange,
  onToggleRationale,
}: {
  item: ReviewItem;
  onToggleApproval: (index: number) => void;
  onTitleChange: (index: number, title: string) => void;
  onToggleRationale: (index: number) => void;
}) {
  const { issue, approved, editedTitle, rationaleExpanded } = item;
  const defaultPriority = {
    label: 'Medium',
    className: 'bg-yellow-100 text-yellow-800 border-transparent',
  };
  const defaultConfidence = {
    label: 'LOW',
    className: 'bg-gray-100 text-gray-600 border-transparent',
  };
  const priorityInfo = PRIORITY_LABELS[issue.priority] ?? defaultPriority;
  const confidenceInfo = CONFIDENCE_STYLES[issue.confidenceTag] ?? defaultConfidence;

  return (
    <div
      className={cn(
        'rounded-lg border transition-colors p-3 space-y-2',
        approved ? 'border-primary/30 bg-primary/5' : 'border-border bg-muted/30 opacity-60'
      )}
      data-testid="review-card"
    >
      {/* Header row */}
      <div className="flex items-start gap-2">
        {/* Confidence badge */}
        <Badge
          variant="outline"
          className={cn('text-xs shrink-0 font-semibold', confidenceInfo.className)}
        >
          {confidenceInfo.label}
        </Badge>

        {/* Priority badge */}
        <Badge variant="outline" className={cn('text-xs shrink-0', priorityInfo.className)}>
          {priorityInfo.label}
        </Badge>

        <div className="flex-1" />

        {/* Approve/Skip toggle */}
        <Button
          type="button"
          size="sm"
          variant={approved ? 'default' : 'outline'}
          className="h-7 px-2 text-xs"
          onClick={() => onToggleApproval(issue.index)}
          aria-pressed={approved}
          aria-label={approved ? 'Skip this issue' : 'Approve this issue'}
        >
          {approved ? 'Approved' : 'Skipped'}
        </Button>
      </div>

      {/* Editable title */}
      <Input
        value={editedTitle}
        onChange={(e) => onTitleChange(issue.index, e.target.value)}
        disabled={!approved}
        className="h-8 text-sm font-medium"
        aria-label="Issue title"
        placeholder="Issue title"
      />

      {/* Description */}
      {issue.description && (
        <p className="text-xs text-muted-foreground line-clamp-2">{issue.description}</p>
      )}

      {/* Labels */}
      {issue.labels.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {issue.labels.map((label) => (
            <Badge key={label} variant="secondary" className="text-xs">
              {label}
            </Badge>
          ))}
        </div>
      )}

      {/* Rationale (collapsible) */}
      {issue.rationale && (
        <div>
          <button
            type="button"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded-sm"
            onClick={() => onToggleRationale(issue.index)}
            aria-expanded={rationaleExpanded}
          >
            {rationaleExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            Rationale
          </button>
          {rationaleExpanded && (
            <p className="mt-1 text-xs text-muted-foreground italic pl-4">{issue.rationale}</p>
          )}
        </div>
      )}
    </div>
  );
}

/** Skeleton for loading state */
function ReviewSkeleton() {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-lg border border-border p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-12 rounded" />
            <Skeleton className="h-5 w-16 rounded" />
            <div className="flex-1" />
            <Skeleton className="h-7 w-16 rounded" />
          </div>
          <Skeleton className="h-8 w-full rounded" />
          <Skeleton className="h-4 w-3/4 rounded" />
        </div>
      ))}
    </div>
  );
}

export function ExtractionReviewPanel({
  open,
  onOpenChange,
  issues,
  isExtracting,
  error,
  workspaceId,
  noteId,
  projectId,
  onCreated,
}: ExtractionReviewPanelProps) {
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Sync issues into review items when extraction completes
  const prevExtractingRef = useRef<boolean | null>(null);
  useEffect(() => {
    const wasExtracting = prevExtractingRef.current;
    const extractionCompleted = wasExtracting === true && !isExtracting;
    const mountedWithResults = wasExtracting === null && !isExtracting && issues.length > 0;

    if (extractionCompleted || mountedWithResults) {
      setReviewItems(buildReviewItems(issues));
    } else if (isExtracting && issues.length > 0) {
      // Stream items in as they arrive
      setReviewItems(buildReviewItems(issues));
    }

    prevExtractingRef.current = isExtracting;
  }, [issues, isExtracting]);

  // Reset create error when panel opens
  useEffect(() => {
    if (open) setCreateError(null);
  }, [open]);

  const handleToggleApproval = useCallback((index: number) => {
    setReviewItems((prev) =>
      prev.map((item) =>
        item.issue.index === index ? { ...item, approved: !item.approved } : item
      )
    );
  }, []);

  const handleTitleChange = useCallback((index: number, title: string) => {
    setReviewItems((prev) =>
      prev.map((item) => (item.issue.index === index ? { ...item, editedTitle: title } : item))
    );
  }, []);

  const handleToggleRationale = useCallback((index: number) => {
    setReviewItems((prev) =>
      prev.map((item) =>
        item.issue.index === index ? { ...item, rationaleExpanded: !item.rationaleExpanded } : item
      )
    );
  }, []);

  const handleApproveAll = useCallback(() => {
    setReviewItems((prev) => prev.map((item) => ({ ...item, approved: true })));
  }, []);

  const approvedItems = reviewItems.filter((item) => item.approved);
  const approvedCount = approvedItems.length;

  const handleCreate = useCallback(async () => {
    if (approvedCount === 0) return;

    setIsCreating(true);
    setCreateError(null);

    try {
      const issuesToCreate = approvedItems.map((item) => ({
        title: item.editedTitle.trim() || item.issue.title,
        description: item.issue.description || null,
        priority: item.issue.priority,
        source_block_id: item.issue.sourceBlockIds[0] ?? null,
      }));

      const result = await aiApi.createExtractedIssues(
        workspaceId,
        noteId,
        issuesToCreate,
        projectId
      );

      const count = result.created_issues.length;
      onCreated?.(result.created_issues);
      onOpenChange(false);
      toast.success(`${count} issue${count !== 1 ? 's' : ''} created`, {
        description: 'View them in the Issues board.',
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create issues';
      setCreateError(message);
    } finally {
      setIsCreating(false);
    }
  }, [approvedItems, approvedCount, workspaceId, noteId, projectId, onCreated, onOpenChange]);

  const totalCount = reviewItems.length;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex flex-col w-full sm:max-w-md p-0 gap-0"
        aria-describedby="extraction-panel-description"
      >
        {/* Header */}
        <SheetHeader className="px-4 pt-4 pb-3 border-b border-border gap-0">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-base">
              Extracted Issues
              {totalCount > 0 && (
                <span className="ml-1 text-muted-foreground font-normal">({totalCount} found)</span>
              )}
            </SheetTitle>
            {totalCount > 0 && approvedCount < totalCount && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={handleApproveAll}
                disabled={isExtracting}
              >
                Approve All
              </Button>
            )}
          </div>
          <p id="extraction-panel-description" className="sr-only">
            Review AI-extracted issues and choose which ones to create.
          </p>
        </SheetHeader>

        {/* Body */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {/* Loading state — no issues yet */}
          {isExtracting && reviewItems.length === 0 && <ReviewSkeleton />}

          {/* Streaming indicator when issues already shown */}
          {isExtracting && reviewItems.length > 0 && (
            <div
              role="status"
              className="flex items-center gap-2 text-xs text-muted-foreground px-4 py-2 border-b border-border"
            >
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              <span>Extracting more issues...</span>
            </div>
          )}

          {/* Extraction error */}
          {error && (
            <div
              role="alert"
              className="flex items-center gap-2 m-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Create error */}
          {createError && (
            <div
              role="alert"
              className="flex items-center gap-2 mx-4 mt-3 p-3 rounded-lg bg-destructive/10 text-destructive text-sm"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{createError}</span>
            </div>
          )}

          {/* Empty state after extraction */}
          {!isExtracting && !error && reviewItems.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground px-4">
              <CheckCircle2 className="h-8 w-8 mb-3 opacity-40" />
              <p className="text-sm text-center">No actionable issues found in this note.</p>
            </div>
          )}

          {/* Review items */}
          {reviewItems.length > 0 && (
            <div className="p-4 space-y-3">
              {reviewItems.map((item) => (
                <ReviewCard
                  key={item.issue.index}
                  item={item}
                  onToggleApproval={handleToggleApproval}
                  onTitleChange={handleTitleChange}
                  onToggleRationale={handleToggleRationale}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {reviewItems.length > 0 && (
          <SheetFooter className="px-4 py-3 border-t border-border gap-2">
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() => onOpenChange(false)}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className="flex-1"
              onClick={handleCreate}
              disabled={approvedCount === 0 || isCreating || isExtracting}
            >
              {isCreating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" aria-hidden="true" />
                  Creating...
                </>
              ) : (
                `Create ${approvedCount} Issue${approvedCount !== 1 ? 's' : ''}`
              )}
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  );
}
