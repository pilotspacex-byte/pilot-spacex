'use client';

/**
 * VersionHistorySidebarPanel — T-137 (Feature 016 M8)
 *
 * Lists auto-save timestamps for current note.
 * Shows "Full version history coming in Feature 017" banner.
 * Shows last 10 save times. Read-only.
 * Mounts inside SidebarPanel as content for activePanel="versions".
 */

import { History, Info } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';

export interface SaveTimestamp {
  id: string;
  savedAt: string;
  wordCount?: number;
}

export interface VersionHistorySidebarPanelProps {
  /** Last 10 auto-save timestamps, newest first */
  saveTimestamps?: SaveTimestamp[];
  /** Whether loading */
  isLoading?: boolean;
}

function SaveRow({ entry }: { entry: SaveTimestamp }) {
  const timeAgo = formatDistanceToNow(new Date(entry.savedAt), { addSuffix: true });
  const fullDate = format(new Date(entry.savedAt), 'PPp');

  return (
    <div
      className="flex items-center justify-between px-4 py-2 text-sm hover:bg-muted/50 rounded-md transition-colors"
      title={fullDate}
    >
      <div className="flex items-center gap-2 text-muted-foreground">
        <History className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{timeAgo}</span>
      </div>
      {entry.wordCount != null && (
        <span className="text-xs text-muted-foreground">{entry.wordCount.toLocaleString()} w</span>
      )}
    </div>
  );
}

export function VersionHistorySidebarPanel({
  saveTimestamps = [],
  isLoading = false,
}: VersionHistorySidebarPanelProps) {
  return (
    <div className="flex flex-col gap-3 p-3">
      {/* Feature 017 coming-soon banner */}
      <div
        className={cn(
          'flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2.5'
        )}
        role="note"
        aria-label="Version history coming in Feature 017"
      >
        <Info className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          Full version history with diff view and restore is coming in{' '}
          <span className="font-medium text-foreground">Feature 017</span>. Below are your recent
          auto-saves.
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-6" aria-label="Loading save history">
          <div
            className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent"
            aria-hidden="true"
          />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && saveTimestamps.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <History className="h-8 w-8 text-muted-foreground mb-2" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">No auto-saves yet</p>
          <p className="text-xs text-muted-foreground mt-1">
            Saves appear here as you edit your note.
          </p>
        </div>
      )}

      {/* Save list (last 10) */}
      {!isLoading && saveTimestamps.length > 0 && (
        <div
          className="flex flex-col gap-0.5"
          role="list"
          aria-label={`${saveTimestamps.length} auto-save timestamps`}
        >
          {saveTimestamps.slice(0, 10).map((entry) => (
            <div key={entry.id} role="listitem">
              <SaveRow entry={entry} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
