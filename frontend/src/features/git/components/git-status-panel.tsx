'use client';

import { observer } from 'mobx-react-lite';
import { useEffect } from 'react';
import { ArrowDown, ArrowUp, RefreshCw, GitBranch } from 'lucide-react';
import { useGitStore } from '@/stores/RootStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface GitStatusPanelProps {
  repoPath: string;
}

export const GitStatusPanel = observer(function GitStatusPanel({ repoPath }: GitStatusPanelProps) {
  const gitStore = useGitStore();

  useEffect(() => {
    if (repoPath) {
      gitStore.setRepoPath(repoPath);
    }
  }, [repoPath, gitStore]);

  const stagedFiles = gitStore.stagedFiles;
  const modifiedFiles = gitStore.modifiedFiles.filter((f) => !f.staged);
  const untrackedFiles = gitStore.untrackedFiles;
  const totalChanges = stagedFiles.length + modifiedFiles.length + untrackedFiles.length;

  return (
    <div className="flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-center gap-2">
        <GitBranch className="text-muted-foreground size-4 shrink-0" />
        <span className="text-sm font-medium truncate">{gitStore.currentBranch || '—'}</span>
        {(gitStore.status?.ahead ?? 0) > 0 && (
          <Badge variant="secondary" className="text-xs shrink-0">
            {gitStore.status!.ahead} ahead
          </Badge>
        )}
        {(gitStore.status?.behind ?? 0) > 0 && (
          <Badge variant="outline" className="text-xs shrink-0">
            {gitStore.status!.behind} behind
          </Badge>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto size-7 p-0"
          onClick={() => void gitStore.refreshAll()}
          disabled={gitStore.isLoadingStatus || gitStore.isLoadingBranches}
          aria-label="Refresh status"
        >
          <RefreshCw
            className={`size-3.5 ${gitStore.isLoadingStatus || gitStore.isLoadingBranches ? 'animate-spin' : ''}`}
          />
        </Button>
      </div>

      {/* Pull / Push buttons */}
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => void gitStore.pull()}
            disabled={gitStore.isPulling || gitStore.isPushing}
          >
            <ArrowDown className="size-3.5" />
            Pull
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => void gitStore.push()}
            disabled={gitStore.isPushing || gitStore.isPulling}
          >
            <ArrowUp className="size-3.5" />
            Push
          </Button>
        </div>

        {/* Pull progress */}
        {gitStore.isPulling && (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground text-xs">Pulling&hellip;</span>
              <span className="text-muted-foreground text-xs">
                {gitStore.pullProgress?.pct ?? 0}%
              </span>
            </div>
            <Progress value={gitStore.pullProgress?.pct ?? 0} className="h-1.5" />
            {gitStore.pullProgress?.message && (
              <p className="text-muted-foreground text-xs">{gitStore.pullProgress.message}</p>
            )}
          </div>
        )}
        {gitStore.pullError && <p className="text-destructive text-xs">{gitStore.pullError}</p>}

        {/* Push progress */}
        {gitStore.isPushing && (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground text-xs">Pushing&hellip;</span>
              <span className="text-muted-foreground text-xs">
                {gitStore.pushProgress?.pct ?? 0}%
              </span>
            </div>
            <Progress value={gitStore.pushProgress?.pct ?? 0} className="h-1.5" />
            {gitStore.pushProgress?.message && (
              <p className="text-muted-foreground text-xs">{gitStore.pushProgress.message}</p>
            )}
          </div>
        )}
        {gitStore.pushError && <p className="text-destructive text-xs">{gitStore.pushError}</p>}
      </div>

      <Separator />

      {/* File list section */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Changes</span>
          {totalChanges > 0 && (
            <Badge variant="secondary" className="text-xs">
              {totalChanges}
            </Badge>
          )}
        </div>

        {gitStore.error && <p className="text-destructive text-xs">{gitStore.error}</p>}

        {totalChanges === 0 && !gitStore.isLoadingStatus ? (
          <p className="text-muted-foreground text-xs italic">Working tree clean</p>
        ) : (
          <ScrollArea className={totalChanges > 10 ? 'max-h-48' : undefined}>
            <div className="flex flex-col gap-1">
              {/* Staged files */}
              {stagedFiles.length > 0 && (
                <FileGroup
                  label="Staged"
                  dotClass="bg-green-500"
                  files={stagedFiles.map((f) => f.path)}
                />
              )}

              {/* Modified files */}
              {modifiedFiles.length > 0 && (
                <FileGroup
                  label="Modified"
                  dotClass="bg-yellow-500"
                  files={modifiedFiles.map((f) => f.path)}
                />
              )}

              {/* Untracked files */}
              {untrackedFiles.length > 0 && (
                <FileGroup
                  label="Untracked"
                  dotClass="bg-muted-foreground"
                  files={untrackedFiles.map((f) => f.path)}
                />
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
});

interface FileGroupProps {
  label: string;
  dotClass: string;
  files: string[];
}

function FileGroup({ label, dotClass, files }: FileGroupProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5 py-0.5">
        <span className={`rounded-full size-2 shrink-0 ${dotClass}`} />
        <span className="text-muted-foreground text-xs font-medium">{label}</span>
        <span className="text-muted-foreground text-xs">({files.length})</span>
      </div>
      {files.map((path) => (
        <div key={path} className="flex items-center gap-1.5 pl-3.5 py-0.5">
          <span className="font-mono text-xs truncate">{path}</span>
        </div>
      ))}
    </div>
  );
}
