'use client';

/**
 * LargeNoteWarning - Dismissable banner shown when a note exceeds 1000 blocks.
 *
 * - Shown at 1000+ blocks
 * - Dismissable per session (sessionStorage key: 'pilot-large-note-dismissed-{noteId}')
 * - Yellow warning style, non-blocking
 */

import { useCallback, useState } from 'react';
import { TriangleAlert, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const BLOCK_THRESHOLD = 1000;

function getDismissKey(noteId: string): string {
  return `pilot-large-note-dismissed-${noteId}`;
}

export interface LargeNoteWarningProps {
  noteId: string;
  blockCount: number;
  className?: string;
}

export function LargeNoteWarning({ noteId, blockCount, className }: LargeNoteWarningProps) {
  const [dismissed, setDismissed] = useState(() => {
    // Read sessionStorage lazily during initial render (client-only)
    if (typeof sessionStorage === 'undefined') return false;
    return sessionStorage.getItem(getDismissKey(noteId)) === '1';
  });

  const dismiss = useCallback(() => {
    sessionStorage.setItem(getDismissKey(noteId), '1');
    setDismissed(true);
  }, [noteId]);

  if (dismissed || blockCount < BLOCK_THRESHOLD) {
    return null;
  }

  return (
    <div
      role="alert"
      aria-live="polite"
      data-testid="large-note-warning"
      className={cn(
        'flex items-center gap-2 px-3 py-2',
        'bg-amber-50 border-b border-amber-200 text-amber-800',
        'dark:bg-amber-900/20 dark:border-amber-700/50 dark:text-amber-300',
        className
      )}
    >
      <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" aria-hidden="true" />
      <p className="flex-1 text-xs">
        This note is very large. Consider splitting into sub-notes.
      </p>
      <Button
        variant="ghost"
        size="icon"
        className={cn(
          'h-6 w-6 shrink-0 text-amber-600 hover:text-amber-800 hover:bg-amber-100',
          'dark:text-amber-400 dark:hover:bg-amber-800/40'
        )}
        onClick={dismiss}
        aria-label="Dismiss large note warning"
        data-testid="large-note-warning-dismiss"
      >
        <X className="h-3.5 w-3.5" aria-hidden="true" />
      </Button>
    </div>
  );
}
