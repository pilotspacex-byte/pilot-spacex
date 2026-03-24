'use client';

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { RefreshCw, GitPullRequest } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useGitWebStore } from '@/stores/RootStore';
import { useGitStatus } from '../hooks/useGitStatus';
import { BranchSelector } from './BranchSelector';
import { CommitPanel } from './CommitPanel';
import { ChangedFileList } from './ChangedFileList';
import { CreatePRForm } from './CreatePRForm';

/**
 * SourceControlPanel - Main SCM panel for the left sidebar.
 *
 * MobX observer that displays:
 * 1. Header with title and refresh button
 * 2. Branch selector (Popover+Command)
 * 3. Commit panel (message + button)
 * 4. Staged changes file list
 * 5. Unstaged changes file list
 *
 * When no repository is configured, shows a setup prompt.
 */
export const SourceControlPanel = observer(function SourceControlPanel() {
  const gitWebStore = useGitWebStore();
  const { refresh, isFetching } = useGitStatus(gitWebStore.currentRepo, gitWebStore.currentBranch);
  const [showPRForm, setShowPRForm] = useState(false);
  const canCreatePR = gitWebStore.currentBranch !== gitWebStore.defaultBranch;

  // No repo configured: show setup prompt
  if (!gitWebStore.currentRepo) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-4 text-center gap-3">
        <GitPullRequest className="h-8 w-8 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">No repository connected</p>
          <p className="text-xs text-muted-foreground mt-1">
            Connect a repository in Integration Settings to use Source Control.
          </p>
        </div>
      </div>
    );
  }

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
        <BranchSelector />
      </div>

      {/* Commit panel */}
      <div className="border-b">
        <CommitPanel />
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
          <CreatePRForm onClose={() => setShowPRForm(false)} />
        </div>
      )}

      {/* File lists */}
      <div className="flex-1 overflow-y-auto">
        <ChangedFileList
          title="Staged Changes"
          files={gitWebStore.stagedFiles}
          onToggleStage={(path) => gitWebStore.unstageFile(path)}
          onUnstageAll={() => gitWebStore.unstageAll()}
          onSelect={(path) => gitWebStore.selectFile(path)}
          selectedPath={gitWebStore.selectedFilePath}
        />
        <ChangedFileList
          title="Changes"
          files={gitWebStore.unstagedFiles}
          onToggleStage={(path) => gitWebStore.stageFile(path)}
          onStageAll={() => gitWebStore.stageAll()}
          onSelect={(path) => gitWebStore.selectFile(path)}
          selectedPath={gitWebStore.selectedFilePath}
        />
      </div>
    </div>
  );
});
