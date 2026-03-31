'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { GitBranch, Star, Lock, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';
import { useGitStore } from '@/stores/RootStore';
import { useBranches } from '../hooks/useBranches';
import { createBranch, deleteBranch } from '@/services/api/git-proxy';
import { toast } from 'sonner';
import type { BranchInfo } from '../git-types';

interface BranchSelectorProps {
  workspaceId: string;
  owner: string;
  repo: string;
}

/**
 * BranchSelector - Popover + Command (cmdk) dropdown for branch management.
 *
 * MobX observer that reads the current branch from GitStore.
 * Supports:
 * - Searchable branch list (300ms debounce)
 * - Default branch marked with star icon
 * - Protected branches marked with lock icon
 * - Click to switch branch
 * - Create new branch with inline input
 * - Delete non-default, non-protected branches with confirmation
 */
export const BranchSelector = observer(function BranchSelector({
  workspaceId,
  owner,
  repo,
}: BranchSelectorProps) {
  const gitStore = useGitStore();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');
  const [deletingBranch, setDeletingBranch] = useState<BranchInfo | null>(null);
  const [isCreatingBranch, setIsCreatingBranch] = useState(false);
  const [isDeletingBranch, setIsDeletingBranch] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const { branches, isLoading } = useBranches(
    workspaceId,
    owner,
    repo,
    debouncedSearch || undefined
  );

  // Debounce search input
  useEffect(() => {
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [search]);

  const handleSelect = useCallback(
    (branchName: string) => {
      gitStore.setBranch(branchName);
      setOpen(false);
    },
    [gitStore]
  );

  const handleCreate = useCallback(async () => {
    if (!newBranchName.trim() || !gitStore.currentBranch || isCreatingBranch) return;
    setIsCreatingBranch(true);
    try {
      await createBranch(workspaceId, owner, repo, newBranchName.trim(), gitStore.currentBranch);
      gitStore.setBranch(newBranchName.trim());
      toast.success(`Branch "${newBranchName.trim()}" created`);
      setNewBranchName('');
      setIsCreating(false);
      setOpen(false);
    } catch (err) {
      toast.error(
        `Failed to create branch: ${err instanceof Error ? err.message : 'Unknown error'}`
      );
    } finally {
      setIsCreatingBranch(false);
    }
  }, [gitStore, newBranchName, workspaceId, owner, repo, isCreatingBranch]);

  const handleDelete = useCallback(async () => {
    if (!deletingBranch || isDeletingBranch) return;
    setIsDeletingBranch(true);
    try {
      await deleteBranch(workspaceId, owner, repo, deletingBranch.name);
      toast.success(`Branch "${deletingBranch.name}" deleted`);
      setDeletingBranch(null);
    } catch (err) {
      toast.error(
        `Failed to delete branch: ${err instanceof Error ? err.message : 'Unknown error'}`
      );
    } finally {
      setIsDeletingBranch(false);
    }
  }, [deletingBranch, workspaceId, owner, repo, isDeletingBranch]);

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-1.5 px-2 h-7 text-xs font-normal"
          >
            <GitBranch className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate">{gitStore.currentBranch || 'No branch'}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search branches..."
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandEmpty>{isLoading ? 'Loading...' : 'No branches found'}</CommandEmpty>
              <CommandGroup>
                {branches.map((branch) => (
                  <CommandItem
                    key={branch.name}
                    value={branch.name}
                    onSelect={() => handleSelect(branch.name)}
                    className="flex items-center gap-1.5 text-sm group"
                  >
                    <span
                      className={cn(
                        'truncate flex-1',
                        branch.name === gitStore.currentBranch && 'font-semibold'
                      )}
                    >
                      {branch.name}
                    </span>
                    {branch.isDefault && (
                      <span aria-label="Default branch">
                        <Star className="h-3 w-3 shrink-0 text-yellow-500" />
                      </span>
                    )}
                    {branch.isProtected && (
                      <span aria-label="Protected branch">
                        <Lock className="h-3 w-3 shrink-0 text-muted-foreground" />
                      </span>
                    )}
                    {!branch.isDefault && !branch.isProtected && (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete branch ${branch.name}`}
                        className="h-5 w-5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingBranch(branch);
                        }}
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup>
                {isCreating ? (
                  <div className="flex items-center gap-1 px-2 py-1">
                    <Input
                      value={newBranchName}
                      onChange={(e) => setNewBranchName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') void handleCreate();
                        if (e.key === 'Escape') setIsCreating(false);
                      }}
                      placeholder="branch-name"
                      className="h-6 text-xs"
                      autoFocus
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-6 w-6 shrink-0"
                      onClick={() => void handleCreate()}
                      disabled={!newBranchName.trim() || isCreatingBranch}
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <CommandItem onSelect={() => setIsCreating(true)} className="text-sm">
                    <Plus className="h-3.5 w-3.5 mr-1.5" />
                    Create Branch
                  </CommandItem>
                )}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Delete confirmation dialog */}
      <AlertDialog
        open={!!deletingBranch}
        onOpenChange={(open) => !open && setDeletingBranch(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete branch?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the branch &ldquo;{deletingBranch?.name}&rdquo;. This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void handleDelete()}
              disabled={isDeletingBranch}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
});
