'use client';

/**
 * ExtractionPreviewModal - Shows extracted issues for user review before creation.
 *
 * Displays issues extracted by AI from note content with:
 * - Checkboxes for selecting which issues to create (all selected by default)
 * - Title, description preview, priority badge, confidence score, labels
 * - "Create Selected" button to create issues via backend
 * - "Cancel" button to dismiss
 *
 * Feature 009: Intent-to-Issues extraction pipeline.
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { aiApi } from '@/services/api/ai';

/** Extracted issue from SSE stream. */
export interface ExtractedIssue {
  index: number;
  title: string;
  description: string;
  priority: number;
  labels: string[];
  confidenceScore: number;
  confidenceTag: string;
  sourceBlockIds: string[];
  rationale: string;
}

export interface ExtractionPreviewModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback to close the modal */
  onOpenChange: (open: boolean) => void;
  /** Extracted issues to display */
  issues: ExtractedIssue[];
  /** Whether extraction is still in progress */
  isExtracting: boolean;
  /** Extraction error message if any */
  error: string | null;
  /** Workspace ID for issue creation */
  workspaceId: string;
  /** Note ID the issues were extracted from */
  noteId: string;
  /** Callback after issues are created */
  onCreated?: (createdIds: string[]) => void;
}

const PRIORITY_LABELS: Record<number, { label: string; className: string }> = {
  0: { label: 'Urgent', className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' },
  1: {
    label: 'High',
    className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  },
  2: {
    label: 'Medium',
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  },
  3: {
    label: 'Low',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  },
  4: { label: 'None', className: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' },
};

const CONFIDENCE_COLORS: Record<string, string> = {
  explicit: 'text-green-600 dark:text-green-400',
  implicit: 'text-yellow-600 dark:text-yellow-400',
  related: 'text-muted-foreground',
};

/**
 * ExtractionPreviewModal shows AI-extracted issues for user review and creation.
 */
export function ExtractionPreviewModal({
  open,
  onOpenChange,
  issues,
  isExtracting,
  error,
  workspaceId,
  noteId,
  onCreated,
}: ExtractionPreviewModalProps) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Select all issues by default when issues change
  const toggleIssue = useCallback((index: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIndices(new Set(issues.map((i) => i.index)));
  }, [issues]);

  const deselectAll = useCallback(() => {
    setSelectedIndices(new Set());
  }, []);

  // Select all issues when extraction completes (true -> false transition)
  // or on initial mount if issues are already available
  const prevExtractingRef = useRef<boolean | null>(null);
  useEffect(() => {
    const isInitialMount = prevExtractingRef.current === null;
    const extractionJustCompleted = prevExtractingRef.current === true && !isExtracting;
    const mountedWithResults = isInitialMount && !isExtracting && issues.length > 0;

    if ((extractionJustCompleted || mountedWithResults) && issues.length > 0) {
      setSelectedIndices(new Set(issues.map((i) => i.index)));
    }
    prevExtractingRef.current = isExtracting;
  }, [isExtracting, issues]);

  const handleCreate = useCallback(async () => {
    if (selectedIndices.size === 0) return;

    setIsCreating(true);
    setCreateError(null);

    try {
      const selectedIssues = issues
        .filter((i) => selectedIndices.has(i.index))
        .map((i) => ({
          title: i.title,
          description: i.description,
          priority: PRIORITY_LABELS[i.priority]?.label.toLowerCase() ?? 'medium',
          type: 'task' as const,
          source_block_id: i.sourceBlockIds[0] ?? null,
        }));

      const result = await aiApi.createExtractedIssues(workspaceId, noteId, selectedIssues);
      onCreated?.(result.created_issues);
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create issues';
      setCreateError(message);
    } finally {
      setIsCreating(false);
    }
  }, [selectedIndices, issues, workspaceId, noteId, onCreated, onOpenChange]);

  const allSelected = issues.length > 0 && selectedIndices.size === issues.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl max-h-[80vh] flex flex-col"
        aria-describedby="extraction-preview-description"
      >
        <DialogHeader>
          <DialogTitle>Extracted Issues</DialogTitle>
          <DialogDescription id="extraction-preview-description">
            AI found the following issues in your note. Select which ones to create.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-3 py-2 min-h-0">
          {/* Loading state */}
          {isExtracting && issues.length === 0 && (
            <div
              role="status"
              className="flex items-center justify-center py-8 text-muted-foreground"
            >
              <Loader2 className="h-5 w-5 motion-safe:animate-spin mr-2" />
              <span>Analyzing note content...</span>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div
              role="alert"
              className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Create error */}
          {createError && (
            <div
              role="alert"
              className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{createError}</span>
            </div>
          )}

          {/* Select all / deselect all */}
          {issues.length > 1 && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <button
                type="button"
                className="underline hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded-sm"
                onClick={allSelected ? deselectAll : selectAll}
              >
                {allSelected ? 'Deselect all' : 'Select all'}
              </button>
              <span>
                {selectedIndices.size} of {issues.length} selected
              </span>
            </div>
          )}

          {/* Issue list */}
          {issues.map((issue) => {
            const isSelected = selectedIndices.has(issue.index);
            const priorityInfo = PRIORITY_LABELS[issue.priority] ?? {
              label: 'Medium',
              className: 'bg-yellow-100 text-yellow-800',
            };
            const confidenceColor =
              CONFIDENCE_COLORS[issue.confidenceTag] ?? CONFIDENCE_COLORS.related;

            return (
              <label
                key={issue.index}
                className={cn(
                  'flex gap-3 p-3 rounded-lg border cursor-pointer motion-safe:transition-colors',
                  isSelected
                    ? 'border-primary/40 bg-primary/5'
                    : 'border-border hover:border-border/80 bg-background'
                )}
              >
                <Checkbox
                  checked={isSelected}
                  onCheckedChange={() => toggleIssue(issue.index)}
                  aria-label={`Select issue: ${issue.title}`}
                  className="mt-0.5"
                />
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-start gap-2">
                    <span className="font-medium text-sm leading-tight flex-1">{issue.title}</span>
                    <Badge
                      variant="outline"
                      className={cn('text-xs shrink-0', priorityInfo.className)}
                    >
                      {priorityInfo.label}
                    </Badge>
                  </div>

                  {issue.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {issue.description}
                    </p>
                  )}

                  <div className="flex items-center gap-2 flex-wrap">
                    {issue.labels.map((label) => (
                      <Badge key={label} variant="secondary" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                    <span className={cn('text-xs', confidenceColor)}>
                      {Math.round(issue.confidenceScore * 100)}% confidence
                    </span>
                  </div>

                  {issue.rationale && (
                    <p className="text-xs text-muted-foreground italic">{issue.rationale}</p>
                  )}
                </div>
              </label>
            );
          })}

          {/* Extracting indicator when some issues already shown */}
          {isExtracting && issues.length > 0 && (
            <div
              role="status"
              className="flex items-center gap-2 text-xs text-muted-foreground py-2"
            >
              <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
              <span>Finding more issues...</span>
            </div>
          )}

          {/* Empty state after extraction completes */}
          {!isExtracting && !error && issues.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <CheckCircle2 className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No actionable issues found in this note.</p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={selectedIndices.size === 0 || isCreating || isExtracting}
          >
            {isCreating ? (
              <>
                <Loader2 className="h-4 w-4 motion-safe:animate-spin mr-1" />
                Creating...
              </>
            ) : (
              `Create ${selectedIndices.size} issue${selectedIndices.size !== 1 ? 's' : ''}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
