'use client';

import { useState, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { RefreshCw, GitPullRequest } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useGitStore } from '@/stores/RootStore';
import { useGitStatus } from '../hooks/useGitStatus';
import { BranchSelector } from './BranchSelector';
import { CommitPanel } from './CommitPanel';
import { ChangedFileList } from './ChangedFileList';
import { CreatePRForm } from './CreatePRForm';
import type { ChangedFile } from '../git-types';

interface SourceControlPanelProps {
  workspaceId: string;
  /** GitHub repository owner — from useProjectGitIntegration */
  owner: string | null;
  /** GitHub repository name — from useProjectGitIntegration */
  repo: string | null;
  /**
   * Optional callback invoked when the user clicks a changed file.
   * EditorLayout uses this to open DiffViewer in the center panel.
   */
  onFileSelect?: (file: ChangedFile) => void;
}

/**
 * SourceControlPanel - Main SCM panel for the Monaco IDE sidebar.
 *
 * MobX observer that displays:
 * 1. Header with title and refresh button
 * 2. Branch selector (Popover + Command)
 * 3. Commit panel (message + button)
 * 4. "Create Pull Request" collapsible section
 * 5. Staged changes file list
 * 6. Unstaged changes file list
 *
 * When owner/repo are null (no repository connected), shows a setup prompt.
 *
 * Staging is client-side only (the `staged` boolean on ChangedFile).
 * The CommitPanel reads `gitStore.changedFiles.filter(f => f.staged)`.
 */
export const SourceControlPanel = observer(function SourceControlPanel({
  workspaceId,
  owner,
  repo,
  onFileSelect,
}: SourceControlPanelProps) {
  const gitStore = useGitStore();
  const { refresh, isFetching } = useGitStatus(
    workspaceId,
    owner,
    repo,
    gitStore.currentBranch
  );
  const [showPRForm, setShowPRForm] = useState(false);

  const canCreatePR =
    gitStore.currentBranch !== null &&
    gitStore.defaultBranch !== null &&
    gitStore.currentBranch !== gitStore.defaultBranch;

  // ─── Staging handlers ────────────────────────────────────────────────────

  const toggleStage = useCallback(
    (path: string) => {
      gitStore.setChangedFiles(
        gitStore.changedFiles.map((f: ChangedFile) =>
          f.path === path ? { ...f, staged: !f.staged } : f
        )
      );
    },
    [gitStore]
  );

  const stageAll = useCallback(() => {
    gitStore.setChangedFiles(gitStore.changedFiles.map((f: ChangedFile) => ({ ...f, staged: true })));
  }, [gitStore]);

  const unstageAll = useCallback(() => {
    gitStore.setChangedFiles(gitStore.changedFiles.map((f: ChangedFile) => ({ ...f, staged: false })));
  }, [gitStore]);

  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const handleFileSelect = useCallback(
    (path: string) => {
      setSelectedPath(path);
      if (onFileSelect) {
        const file = gitStore.changedFiles.find((f: ChangedFile) => f.path === path);
        if (file) onFileSelect(file);
      }
    },
    [onFileSelect, gitStore.changedFiles]
  );

  const stagedFiles = gitStore.changedFiles.filter((f: ChangedFile) => f.staged);
  const unstagedFiles = gitStore.changedFiles.filter((f: ChangedFile) => !f.staged);

  // ─── Empty state: no repo connected ──────────────────────────────────────

  if (!owner || !repo) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-4 text-center gap-3">
        <GitPullRequest className="h-8 w-8 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">No repository connected</p>
          <p className="text-xs text-muted-foreground mt-1">
            Connect a GitHub repository in Integration Settings to use Source Control.
          </p>
        </div>
      </div>
    );
  }

  // ─── Main panel ───────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1.5 border-b">
        <span className="text-xs font-semibold uppercase tracking-wide">Source Control</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={refresh}
          disabled={isFetching}
          title="Refresh"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Branch selector */}
      <div className="px-1 py-1 border-b">
        <BranchSelector workspaceId={workspaceId} owner={owner} repo={repo} />
      </div>

      {/* Commit panel */}
      <div className="border-b">
        <CommitPanel workspaceId={workspaceId} owner={owner} repo={repo} />
      </div>

      {/* Create PR button */}
      <div className="px-2 py-1.5 border-b">
        <Button
          variant="outline"
          size="sm"
          className="w-full h-7 text-xs gap-1.5"
          disabled={!canCreatePR}
          onClick={() => setShowPRForm((prev) => !prev)}
          title={canCreatePR ? 'Create pull request' : 'Cannot create PR from default branch'}
        >
          <GitPullRequest className="h-3.5 w-3.5" />
          Create Pull Request
        </Button>
      </div>

      {/* PR creation form */}
      {showPRForm && (
        <div className="border-b">
          <CreatePRForm
            workspaceId={workspaceId}
            owner={owner}
            repo={repo}
            onClose={() => setShowPRForm(false)}
          />
        </div>
      )}

      {/* File lists */}
      <div className="flex-1 overflow-y-auto">
        <ChangedFileList
          title="Staged Changes"
          files={stagedFiles}
          onToggleStage={toggleStage}
          onUnstageAll={unstageAll}
          onSelect={handleFileSelect}
          selectedPath={selectedPath}
        />
        <ChangedFileList
          title="Changes"
          files={unstagedFiles}
          onToggleStage={toggleStage}
          onStageAll={stageAll}
          onSelect={handleFileSelect}
          selectedPath={selectedPath}
        />
      </div>
    </div>
  );
});
