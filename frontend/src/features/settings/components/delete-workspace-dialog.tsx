/**
 * DeleteWorkspaceDialog - Confirmation dialog for workspace deletion.
 *
 * T030: User types workspace name to confirm. Redirects to workspace list on success.
 */

'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useDeleteWorkspace } from '../hooks/use-workspace-settings';

interface DeleteWorkspaceDialogProps {
  workspaceId: string;
  workspaceName: string;
  children?: React.ReactNode;
}

export function DeleteWorkspaceDialog({
  workspaceId,
  workspaceName,
  children,
}: DeleteWorkspaceDialogProps) {
  const router = useRouter();
  const deleteWorkspace = useDeleteWorkspace(workspaceId);

  const [open, setOpen] = React.useState(false);
  const [confirmName, setConfirmName] = React.useState('');

  const isConfirmed = confirmName === workspaceName;

  const handleDelete = async () => {
    if (!isConfirmed) return;

    try {
      await deleteWorkspace.mutateAsync();
      toast.success('Workspace deleted', {
        description: `"${workspaceName}" has been permanently deleted.`,
      });
      setOpen(false);
      router.push('/');
    } catch (err) {
      toast.error('Failed to delete workspace', {
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
      });
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      setConfirmName('');
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {children ?? <Button variant="destructive">Delete Workspace</Button>}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <DialogTitle>Delete Workspace</DialogTitle>
              <DialogDescription>This action is permanent and cannot be undone.</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-sm text-destructive">
              All projects, issues, notes, and data within this workspace will be permanently
              deleted. This cannot be recovered.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-workspace-name">
              Type <span className="font-semibold">{workspaceName}</span> to confirm
            </Label>
            <Input
              id="confirm-workspace-name"
              type="text"
              placeholder={workspaceName}
              value={confirmName}
              onChange={(e) => setConfirmName(e.target.value)}
              disabled={deleteWorkspace.isPending}
              aria-describedby="confirm-hint"
              autoComplete="off"
            />
            <p id="confirm-hint" className="text-xs text-muted-foreground">
              Please type the workspace name exactly as shown above.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={deleteWorkspace.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!isConfirmed || deleteWorkspace.isPending}
            onClick={handleDelete}
            aria-busy={deleteWorkspace.isPending}
          >
            {deleteWorkspace.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            )}
            {deleteWorkspace.isPending ? 'Deleting...' : 'Delete Workspace'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
