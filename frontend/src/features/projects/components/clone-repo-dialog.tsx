'use client';

import { observer } from 'mobx-react-lite';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useProjectStore } from '@/stores/RootStore';

interface CloneRepoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const CloneRepoDialog = observer(function CloneRepoDialog({
  open,
  onOpenChange,
}: CloneRepoDialogProps) {
  const projectStore = useProjectStore();
  const [url, setUrl] = useState('');

  async function handleClone() {
    if (!url.trim()) return;
    await projectStore.cloneRepo(url.trim());
    if (!projectStore.cloneError) {
      // Clone succeeded — close dialog and reset URL
      setUrl('');
      onOpenChange(false);
    }
  }

  function handleCancel() {
    projectStore.cancelClone();
  }

  function handleOpenChange(nextOpen: boolean) {
    // Prevent closing while clone is in progress
    if (projectStore.isCloning && !nextOpen) return;
    if (!nextOpen) {
      setUrl('');
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Clone Repository</DialogTitle>
          <DialogDescription>
            Enter the URL of the repository you want to clone. The repository will be cloned into
            your configured projects directory.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="clone-url" className="text-sm font-medium">
              Repository URL
            </label>
            <Input
              id="clone-url"
              type="url"
              placeholder="https://github.com/user/repo.git"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={projectStore.isCloning}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !projectStore.isCloning) {
                  handleClone();
                }
              }}
            />
          </div>

          {/* Progress section — shown while cloning */}
          {projectStore.isCloning && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Cloning&hellip;</span>
                <span className="text-muted-foreground text-xs">
                  {projectStore.cloneProgress?.pct ?? 0}%
                </span>
              </div>
              <Progress value={projectStore.cloneProgress?.pct ?? 0} />
              {projectStore.cloneProgress?.message && (
                <p className="text-muted-foreground text-xs">
                  {projectStore.cloneProgress.message}
                </p>
              )}
            </div>
          )}

          {/* Error message */}
          {projectStore.cloneError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2">
              <p className="text-destructive text-sm">{projectStore.cloneError}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-2">
            {projectStore.isCloning ? (
              <Button variant="outline" onClick={handleCancel}>
                Cancel Clone
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => handleOpenChange(false)}>
                  Cancel
                </Button>
                <Button onClick={handleClone} disabled={!url.trim()}>
                  Clone
                </Button>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
});
