'use client';

import { observer } from 'mobx-react-lite';
import { useState } from 'react';
import { GitBranch, Check, Trash2, ChevronDown, Plus } from 'lucide-react';
import { useGitStore } from '@/stores/RootStore';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Input } from '@/components/ui/input';

interface BranchSelectorProps {
  repoPath: string;
}

export const BranchSelector = observer(function BranchSelector({
  repoPath: _repoPath,
}: BranchSelectorProps) {
  const gitStore = useGitStore();
  const [open, setOpen] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');

  const localBranches = gitStore.branches.filter((b) => !b.is_remote);
  const remoteBranches = gitStore.branches.filter((b) => b.is_remote);

  async function handleSwitch(name: string) {
    if (name === gitStore.currentBranch) return;
    await gitStore.switchBranch(name);
    setOpen(false);
  }

  async function handleDelete(e: React.MouseEvent, name: string) {
    e.stopPropagation();
    await gitStore.deleteBranch(name);
  }

  async function handleCreate() {
    const trimmed = newBranchName.trim();
    if (!trimmed) return;
    await gitStore.createBranch(trimmed);
    setNewBranchName('');
    setOpen(false);
  }

  function handleCreateKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      void handleCreate();
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1.5 max-w-48 justify-between">
            <div className="flex items-center gap-1.5 min-w-0">
              <GitBranch className="size-3.5 shrink-0" />
              <span className="truncate">{gitStore.currentBranch || 'Select branch'}</span>
            </div>
            <ChevronDown className="size-3.5 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>

        <PopoverContent className="w-64 p-0" align="start">
          <Command>
            <CommandInput placeholder="Search branches..." />
            <CommandList>
              <CommandEmpty>No branches found.</CommandEmpty>

              {/* Local branches */}
              {localBranches.length > 0 && (
                <CommandGroup heading="Local">
                  {localBranches.map((branch) => (
                    <CommandItem
                      key={branch.name}
                      value={branch.name}
                      onSelect={() => void handleSwitch(branch.name)}
                      className="flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        {branch.is_current ? (
                          <Check className="size-3.5 shrink-0 text-primary" />
                        ) : (
                          <span className="size-3.5 shrink-0" />
                        )}
                        <span className="truncate text-sm">{branch.name}</span>
                      </div>
                      {!branch.is_current && (
                        <button
                          onClick={(e) => void handleDelete(e, branch.name)}
                          className="shrink-0 opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity p-0.5 rounded"
                          aria-label={`Delete branch ${branch.name}`}
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}

              {/* Remote branches */}
              {remoteBranches.length > 0 && (
                <CommandGroup heading="Remote">
                  {remoteBranches.map((branch) => (
                    <CommandItem
                      key={branch.name}
                      value={branch.name}
                      disabled
                      className="opacity-60"
                    >
                      <span className="size-3.5 shrink-0" />
                      <span className="truncate text-sm">{branch.name}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
            </CommandList>

            {/* Create branch footer */}
            <Separator />
            <div className="flex items-center gap-2 p-2">
              <Plus className="size-3.5 shrink-0 text-muted-foreground" />
              <Input
                placeholder="New branch name"
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                onKeyDown={handleCreateKeyDown}
                className="h-7 text-xs"
              />
              <Button
                size="sm"
                className="h-7 px-2 text-xs shrink-0"
                onClick={() => void handleCreate()}
                disabled={!newBranchName.trim()}
              >
                Create
              </Button>
            </div>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Error display */}
      {gitStore.error && <p className="text-destructive text-xs">{gitStore.error}</p>}
    </div>
  );
});
