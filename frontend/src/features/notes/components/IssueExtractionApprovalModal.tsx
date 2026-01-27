/**
 * Issue Extraction Approval Modal Component.
 *
 * Displays approval confirmation for creating selected issues.
 * Follows DD-003 critical approval pattern for issue creation.
 *
 * @module features/notes/components/IssueExtractionApprovalModal
 * @see specs/004-mvp-agents-build/tasks/P20-T154-T164.md#T157
 */

import { observer } from 'mobx-react-lite';
import { useStore } from '@/stores';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import type { ExtractedIssue } from '@/stores/ai';

interface IssueExtractionApprovalModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedIndices: number[];
  issues: ExtractedIssue[];
  onApproved?: () => void;
}

export const IssueExtractionApprovalModal = observer(function IssueExtractionApprovalModal({
  open,
  onOpenChange,
  selectedIndices,
  issues,
  onApproved,
}: IssueExtractionApprovalModalProps) {
  const store = useStore();
  const { issueExtraction } = store.aiStore;

  const handleApprove = async () => {
    try {
      await issueExtraction.createApprovedIssues(selectedIndices);
      onApproved?.();
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to create issues:', error);
    }
  };

  const selectedIssues = selectedIndices
    .map((i) => issues[i])
    .filter((issue): issue is ExtractedIssue => issue !== undefined);
  const recommendedCount = selectedIssues.filter((issue) => issue.confidence_score > 0.8).length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            Create Issues
          </DialogTitle>
          <DialogDescription>
            You are about to create {selectedIndices.length} issue
            {selectedIndices.length > 1 ? 's' : ''} from the extracted suggestions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              This action requires approval and will create actual issues in your project.
              {recommendedCount > 0 && (
                <span className="block mt-1 text-green-600 dark:text-green-400 font-medium">
                  {recommendedCount} recommended issue{recommendedCount > 1 ? 's' : ''} selected
                </span>
              )}
            </AlertDescription>
          </Alert>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {selectedIssues.map((issue, index) => (
              <div
                key={index}
                className="p-3 bg-muted rounded-lg border border-border hover:border-primary/50 transition-colors"
              >
                <p className="font-medium text-sm mb-1">{issue.title}</p>
                <p className="text-xs text-muted-foreground line-clamp-2">{issue.description}</p>
                {issue.labels && issue.labels.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {issue.labels.map((label, i) => (
                      <span key={i} className="text-xs bg-background px-1.5 py-0.5 rounded">
                        {label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {issueExtraction.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{issueExtraction.error.message}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={issueExtraction.isCreating}
          >
            Cancel
          </Button>
          <Button onClick={handleApprove} disabled={issueExtraction.isCreating}>
            {issueExtraction.isCreating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Create {selectedIndices.length} Issue{selectedIndices.length > 1 ? 's' : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});
