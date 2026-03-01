'use client';

/**
 * CreateBranchPopover - Popover UI for creating a GitHub branch from an issue.
 *
 * Fetches a branch name suggestion and the list of connected repositories,
 * lets the user edit the branch name and pick a repository, then calls the
 * create branch mutation.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GitBranch, Loader2, Copy, Check } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { integrationsApi } from '@/services/api/integrations';
import { useCreateBranch } from '../hooks/use-create-branch';

export interface CreateBranchPopoverProps {
  workspaceId: string;
  issueId: string;
  integrationId: string;
}

export function CreateBranchPopover({
  workspaceId,
  issueId,
  integrationId,
}: CreateBranchPopoverProps) {
  const [open, setOpen] = useState(false);
  // null means "not yet overridden by user" — falls back to suggestion
  const [overrideBranchName, setOverrideBranchName] = useState<string | null>(null);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: suggestion, isLoading: isSuggestionLoading } = useQuery({
    queryKey: ['branch-name', issueId],
    queryFn: () => integrationsApi.getBranchName(workspaceId, issueId),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  const { data: repositories = [], isLoading: isReposLoading } = useQuery({
    queryKey: ['repositories', workspaceId],
    queryFn: () => integrationsApi.listRepositories(workspaceId),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  // Derive effective values: use override when set, otherwise fall back to suggestion / first repo.
  const branchName = overrideBranchName ?? suggestion?.branchName ?? '';
  const effectiveRepo = selectedRepo ?? repositories[0]?.fullName ?? '';

  const { mutate: createBranch, isPending } = useCreateBranch();

  const handleCreate = () => {
    if (!branchName.trim() || !effectiveRepo) return;

    createBranch(
      {
        workspaceId,
        issueId,
        integrationId,
        repository: effectiveRepo,
        branchName: branchName.trim(),
        baseBranch: 'main',
      },
      {
        onSuccess: () => {
          setOpen(false);
          setOverrideBranchName(null);
          setSelectedRepo(null);
        },
      }
    );
  };

  const handleCopy = async () => {
    if (!branchName.trim()) return;
    await navigator.clipboard.writeText(`git checkout -b ${branchName.trim()}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      setOverrideBranchName(null);
      setSelectedRepo(null);
    }
  };

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" aria-label="Create GitHub branch" aria-expanded={open}>
          <GitBranch className="size-3.5" />
          Create branch
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80 p-4" align="start">
        <h3 className="mb-3 text-sm font-semibold">Create branch</h3>

        <div className="space-y-3">
          <div>
            <label
              htmlFor="cb-repo"
              className="mb-1 block text-xs font-medium text-muted-foreground"
            >
              Repository
            </label>
            {isReposLoading ? (
              <div className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                Loading repositories…
              </div>
            ) : repositories.length === 0 ? (
              <p className="text-xs text-muted-foreground">No repositories connected.</p>
            ) : (
              <Select value={effectiveRepo} onValueChange={setSelectedRepo}>
                <SelectTrigger id="cb-repo" aria-label="Select repository">
                  <SelectValue placeholder="Select a repository" />
                </SelectTrigger>
                <SelectContent>
                  {repositories.map((repo) => (
                    <SelectItem key={repo.id} value={repo.fullName}>
                      {repo.fullName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div>
            <label
              htmlFor="cb-name"
              className="mb-1 block text-xs font-medium text-muted-foreground"
            >
              Branch name
            </label>
            {isSuggestionLoading && !branchName ? (
              <div className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                Generating suggestion…
              </div>
            ) : (
              <Input
                id="cb-name"
                value={branchName}
                onChange={(e) => setOverrideBranchName(e.target.value)}
                placeholder="feature/my-branch"
                aria-label="Branch name"
                className="font-mono text-xs"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCreate();
                  if (e.key === 'Escape') setOpen(false);
                }}
              />
            )}
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={isPending || !branchName.trim() || !effectiveRepo}
            aria-label="Create branch"
            className="flex-1"
          >
            {isPending && <Loader2 className="size-3.5 animate-spin" />}
            {isPending ? 'Creating…' : 'Create branch'}
          </Button>

          <Button
            size="icon-sm"
            variant="outline"
            onClick={() => void handleCopy()}
            disabled={!branchName.trim()}
            aria-label="Copy git checkout command"
            title="Copy git checkout command"
          >
            {copied ? <Check className="size-3.5 text-green-600" /> : <Copy className="size-3.5" />}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
