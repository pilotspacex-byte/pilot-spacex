/**
 * WorkingIndicator - Orange spinner with rotating idioms while AI processes.
 * Claude Code style: rotating random phrases every 3 seconds.
 *
 * @module features/ai/ChatView/ChatInput/WorkingIndicator
 */

'use client';

import { memo, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

const IDIOMS = [
  'Thinking deeply…',
  'Analyzing context…',
  'Crafting a response…',
  'Reading your notes…',
  'Connecting the dots…',
  'Processing request…',
  'Working on it…',
  'Almost there…',
] as const;

const ROTATION_INTERVAL_MS = 3000;

interface WorkingIndicatorProps {
  isVisible: boolean;
}

export const WorkingIndicator = memo<WorkingIndicatorProps>(({ isVisible }) => {
  const [idiomIndex, setIdiomIndex] = useState(0);

  useEffect(() => {
    if (!isVisible) return;

    const timer = setInterval(() => {
      setIdiomIndex((prev) => (prev + 1) % IDIOMS.length);
    }, ROTATION_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 text-xs"
      role="status"
      aria-live="polite"
    >
      <Loader2
        className="h-3 w-3 animate-spin motion-reduce:animate-none"
        style={{ color: '#d9853f' }}
        aria-hidden="true"
      />
      <span className="text-muted-foreground">{IDIOMS[idiomIndex]}</span>
    </div>
  );
});

WorkingIndicator.displayName = 'WorkingIndicator';
