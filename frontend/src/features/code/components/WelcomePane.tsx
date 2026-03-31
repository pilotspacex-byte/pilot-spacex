'use client';

import { observer } from 'mobx-react-lite';
import { Code2 } from 'lucide-react';
import { useFileStore } from '@/stores/RootStore';

/**
 * WelcomePane — empty editor state shown when no file is open.
 *
 * Displays Pilot Space Code icon, welcome message, keyboard shortcut hints,
 * and up to 5 recently accessed files from the FileStore history.
 */
export const WelcomePane = observer(function WelcomePane() {
  const fileStore = useFileStore();

  // Recent files: last 5 from tabOrder (most recently accessed last in LRU order → reverse)
  const recentFiles = [...fileStore.tabOrder]
    .reverse()
    .flatMap((id) => {
      const file = fileStore.openFiles.get(id);
      return file ? [file] : [];
    })
    .slice(0, 5);

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8 text-center">
      {/* Logo icon */}
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <Code2 className="h-8 w-8 text-primary" />
      </div>

      {/* Welcome message */}
      <div className="space-y-1.5">
        <h2 className="text-lg font-semibold text-foreground">Open a file to start editing</h2>
        <p className="text-sm text-muted-foreground">
          Select a file from the file tree on the left.
        </p>
      </div>

      {/* Keyboard shortcuts */}
      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            Cmd+K
          </kbd>
          <span>Open command palette</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            Cmd+P
          </kbd>
          <span>Quick open file</span>
        </div>
      </div>

      {/* Recent files */}
      {recentFiles.length > 0 && (
        <div className="w-full max-w-xs space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            Recent
          </p>
          {recentFiles.map((file) => (
            <button
              key={file.id}
              type="button"
              className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-sm text-left hover:bg-muted transition-colors"
              onClick={() => fileStore.setActiveFile(file.id)}
            >
              <span className="truncate text-muted-foreground">{file.path}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
});
