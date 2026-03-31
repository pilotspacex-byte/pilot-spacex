'use client';

import { useState, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useGitStore } from '@/stores/RootStore';
import { useCommit } from '../hooks/useCommit';

interface CommitPanelProps {
  workspaceId: string;
  owner: string;
  repo: string;
}

/**
 * CommitPanel - Commit message textarea and submit button for the SCM panel.
 *
 * MobX observer that reads staged files from GitStore.
 * Supports Ctrl+Enter / Cmd+Enter keyboard shortcut for committing.
 */
export const CommitPanel = observer(function CommitPanel({
  workspaceId,
  owner,
  repo,
}: CommitPanelProps) {
  const gitStore = useGitStore();
  const { commit, isCommitting } = useCommit(workspaceId, owner, repo);
  const [commitMessage, setCommitMessage] = useState('');

  const stagedFiles = gitStore.changedFiles.filter((f) => f.staged);
  const canCommit = stagedFiles.length > 0 && commitMessage.trim().length > 0 && !isCommitting;

  const handleCommit = useCallback(() => {
    if (!canCommit || !gitStore.currentBranch) return;
    commit(
      { branch: gitStore.currentBranch, message: commitMessage.trim() },
      {
        onSuccess: () => {
          setCommitMessage('');
        },
      }
    );
  }, [canCommit, commit, commitMessage, gitStore.currentBranch]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleCommit();
      }
    },
    [handleCommit]
  );

  return (
    <div className="px-2 py-1.5 space-y-1.5">
      <Textarea
        value={commitMessage}
        onChange={(e) => setCommitMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Message (Ctrl+Enter to commit)"
        className="min-h-[60px] max-h-[120px] resize-y text-sm"
        rows={3}
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {stagedFiles.length} file{stagedFiles.length !== 1 ? 's' : ''} staged
        </span>
        <Button
          size="sm"
          disabled={!canCommit}
          onClick={handleCommit}
          className="h-7 text-xs"
          aria-busy={isCommitting}
        >
          {isCommitting ? (
            <>
              <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              Committing...
            </>
          ) : (
            'Commit'
          )}
        </Button>
      </div>
    </div>
  );
});
