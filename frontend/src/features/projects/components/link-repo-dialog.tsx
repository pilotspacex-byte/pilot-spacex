'use client';

import { observer } from 'mobx-react-lite';
import { useState } from 'react';
import { FolderOpen } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useProjectStore } from '@/stores/RootStore';
import { isTauri } from '@/lib/tauri';

interface LinkRepoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const LinkRepoDialog = observer(function LinkRepoDialog({
  open,
  onOpenChange,
}: LinkRepoDialogProps) {
  const projectStore = useProjectStore();
  const [selectedPath, setSelectedPath] = useState('');
  const [isLinking, setIsLinking] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleBrowse() {
    if (!isTauri()) return;
    const { openFolderDialog } = await import('@/lib/tauri');
    const path = await openFolderDialog();
    if (path) {
      setSelectedPath(path);
      setLocalError(null);
    }
  }

  async function handleLink() {
    if (!selectedPath.trim()) return;
    setIsLinking(true);
    setLocalError(null);
    // Clear any store-level error
    projectStore.error = null;
    await projectStore.linkExistingRepo(selectedPath.trim());
    setIsLinking(false);
    if (!projectStore.error) {
      // Success — close dialog and reset
      setSelectedPath('');
      onOpenChange(false);
    } else {
      setLocalError(projectStore.error);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (isLinking && !nextOpen) return;
    if (!nextOpen) {
      setSelectedPath('');
      setLocalError(null);
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Link Existing Repository</DialogTitle>
          <DialogDescription>
            Select a local folder that contains an existing git repository to add it to your
            projects list.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="repo-path" className="text-sm font-medium">
              Repository folder
            </label>
            <div className="flex gap-2">
              <Input
                id="repo-path"
                type="text"
                placeholder="Select a folder&hellip;"
                value={selectedPath}
                readOnly
                className="flex-1 cursor-default"
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleBrowse}
                disabled={isLinking || !isTauri()}
                className="shrink-0"
              >
                <FolderOpen className="size-4" />
                Browse&hellip;
              </Button>
            </div>
          </div>

          {/* Error message */}
          {localError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2">
              <p className="text-destructive text-sm">{localError}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isLinking}>
              Cancel
            </Button>
            <Button onClick={handleLink} disabled={!selectedPath.trim() || isLinking}>
              {isLinking ? 'Linking\u2026' : 'Link Repository'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
});
