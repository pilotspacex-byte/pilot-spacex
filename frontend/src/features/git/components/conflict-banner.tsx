'use client';

import { observer } from 'mobx-react-lite';
import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { useGitStore } from '@/stores/RootStore';
import { Button } from '@/components/ui/button';

export const ConflictBanner = observer(function ConflictBanner() {
  const gitStore = useGitStore();
  const [expanded, setExpanded] = useState(false);

  if (!gitStore.hasConflicts) {
    return null;
  }

  const conflictedFiles = gitStore.conflictedFiles;
  const count = conflictedFiles.length;

  return (
    <div className="rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 px-3 py-2.5">
      <div className="flex items-start gap-2">
        <AlertTriangle className="size-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
            Merge conflicts detected
          </p>
          <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
            {count} file{count !== 1 ? 's' : ''} have conflicts that need to be resolved manually
          </p>

          {/* Expandable file list */}
          {count > 0 && (
            <button
              onClick={() => setExpanded((prev) => !prev)}
              className="flex items-center gap-1 mt-1.5 text-xs text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronUp className="size-3" />
                  Hide files
                </>
              ) : (
                <>
                  <ChevronDown className="size-3" />
                  Show files
                </>
              )}
            </button>
          )}

          {expanded && (
            <div className="mt-2 flex flex-col gap-0.5">
              {conflictedFiles.map((filePath) => (
                <span
                  key={filePath}
                  className="font-mono text-xs text-amber-800 dark:text-amber-200 truncate"
                >
                  {filePath}
                </span>
              ))}
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="shrink-0 h-7 px-2 text-xs text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 hover:bg-amber-100 dark:hover:bg-amber-900/30"
          onClick={() => gitStore.dismissConflicts()}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
});
