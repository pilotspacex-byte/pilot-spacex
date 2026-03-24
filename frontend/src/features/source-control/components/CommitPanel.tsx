'use client';

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useGitWebStore } from '@/stores/RootStore';
import { useCommit } from '../hooks/useCommit';

/**
 * Commit message input and submit button for the SCM panel.
 *
 * MobX observer -- reads commitMessage, canCommit, isCommitting
 * from the GitWebStore. Supports Ctrl+Enter keyboard shortcut.
 */
export const CommitPanel = observer(function CommitPanel() {
  const gitWebStore = useGitWebStore();
  const { commit, isCommitting } = useCommit(gitWebStore.currentRepo);

  const handleCommit = useCallback(() => {
    if (!gitWebStore.canCommit) return;
    commit({
      branch: gitWebStore.currentBranch,
      message: gitWebStore.commitMessage,
    });
  }, [commit, gitWebStore]);

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
        value={gitWebStore.commitMessage}
        onChange={(e) => gitWebStore.setCommitMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Message (press Ctrl+Enter to commit)"
        className="min-h-[60px] max-h-[120px] resize-y text-sm"
        rows={3}
      />
      <Button
        size="sm"
        className="w-full"
        disabled={!gitWebStore.canCommit || isCommitting}
        onClick={handleCommit}
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
  );
});
