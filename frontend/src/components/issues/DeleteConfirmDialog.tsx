'use client';

import { Trash2, AlertTriangle, Loader2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { Issue, PendingApproval } from '@/types';

/** Threshold for requiring approval on bulk delete per DD-003 */
const BULK_DELETE_APPROVAL_THRESHOLD = 5;

export interface DeleteConfirmDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Called when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Issues to be deleted */
  issues: Issue[];
  /** Called when deletion is confirmed (for immediate delete or approval creation) */
  onConfirm: () => Promise<void>;
  /** Called to create an approval request for bulk delete */
  onCreateApproval?: () => Promise<PendingApproval | null>;
  /** Existing pending approval for this action */
  pendingApproval?: PendingApproval | null;
  /** Whether deletion is in progress */
  isDeleting?: boolean;
  /** Whether approval request is in progress */
  isCreatingApproval?: boolean;
}

/**
 * DeleteConfirmDialog confirms issue deletion.
 *
 * Behavior per DD-003:
 * - Single issue or up to 5 issues: Immediate deletion with confirmation
 * - More than 5 issues: Requires approval flow
 * - Shows pending approval status when awaiting approval
 *
 * @example
 * ```tsx
 * <DeleteConfirmDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   issues={selectedIssues}
 *   onConfirm={handleDelete}
 *   onCreateApproval={handleCreateApproval}
 * />
 * ```
 */
export function DeleteConfirmDialog({
  open,
  onOpenChange,
  issues,
  onConfirm,
  onCreateApproval,
  pendingApproval,
  isDeleting = false,
  isCreatingApproval = false,
}: DeleteConfirmDialogProps) {
  const issueCount = issues.length;
  const requiresApproval = issueCount > BULK_DELETE_APPROVAL_THRESHOLD;
  const hasPendingApproval = !!pendingApproval && pendingApproval.status === 'pending';

  const handleConfirm = async () => {
    if (requiresApproval && onCreateApproval && !hasPendingApproval) {
      // Create approval request for bulk delete
      await onCreateApproval();
    } else if (!hasPendingApproval) {
      // Direct delete
      await onConfirm();
    }
  };

  const isLoading = isDeleting || isCreatingApproval;

  // Generate issue list preview (max 5)
  const previewIssues = issues.slice(0, 5);
  const remainingCount = issueCount - 5;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10">
            <Trash2 className="text-destructive" />
          </AlertDialogMedia>
          <AlertDialogTitle>
            Delete {issueCount} Issue{issueCount !== 1 ? 's' : ''}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            {issueCount === 1
              ? `This will permanently delete "${issues[0]?.name ?? 'this issue'}".`
              : `This will permanently delete ${issueCount} issues.`}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-3">
          {/* Issue list preview */}
          {issueCount > 1 && (
            <div className="rounded-md border bg-muted/50 p-3">
              <p className="mb-2 text-sm font-medium">Issues to delete:</p>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {previewIssues.map((issue) => (
                  <li key={issue.id} className="truncate">
                    <span className="font-mono text-xs">{issue.identifier}</span> {issue.name}
                  </li>
                ))}
                {remainingCount > 0 && (
                  <li className="text-muted-foreground">...and {remainingCount} more</li>
                )}
              </ul>
            </div>
          )}

          {/* Approval required warning */}
          {requiresApproval && !hasPendingApproval && (
            <Alert variant="warning">
              <AlertTriangle className="size-4" />
              <AlertDescription>
                Deleting more than {BULK_DELETE_APPROVAL_THRESHOLD} issues requires approval. An
                approval request will be created for review.
              </AlertDescription>
            </Alert>
          )}

          {/* Pending approval status */}
          {hasPendingApproval && (
            <Alert variant="info">
              <Clock className="size-4" />
              <AlertDescription>
                An approval request is pending for this deletion. The issues will be deleted once
                approved.
              </AlertDescription>
            </Alert>
          )}

          {/* Warning about irreversibility */}
          <p className="text-sm text-destructive">
            This action cannot be undone. All issue data including comments, attachments, and
            history will be permanently removed.
          </p>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          {hasPendingApproval ? (
            <Button disabled variant="outline">
              <Clock className="mr-2 size-4" />
              Awaiting Approval
            </Button>
          ) : (
            <AlertDialogAction
              variant="destructive"
              onClick={(e) => {
                e.preventDefault();
                handleConfirm();
              }}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  {isCreatingApproval ? 'Requesting...' : 'Deleting...'}
                </>
              ) : requiresApproval ? (
                'Request Approval'
              ) : (
                <>
                  <Trash2 className="mr-2 size-4" />
                  Delete
                </>
              )}
            </AlertDialogAction>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default DeleteConfirmDialog;
