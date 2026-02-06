/**
 * WordCountBar - Progress bar showing word count with color-coded states.
 *
 * T037: Reusable word count display for skill editor and skill cards.
 * Source: FR-009, FR-010, US6
 */

'use client';

import { cn } from '@/lib/utils';

interface WordCountBarProps {
  wordCount: number;
  maxWords?: number;
  className?: string;
}

/**
 * Get color state based on word count.
 * Green (primary): 0-1799
 * Orange (warning): 1800-1999
 * Red (destructive): 2000+
 */
function getCountState(count: number, max: number): 'normal' | 'warning' | 'over' {
  const warningThreshold = max - 200;
  if (count >= max) return 'over';
  if (count >= warningThreshold) return 'warning';
  return 'normal';
}

const BAR_COLORS = {
  normal: 'bg-primary',
  warning: 'bg-[#D9853F]',
  over: 'bg-destructive',
} as const;

const TEXT_COLORS = {
  normal: 'text-muted-foreground',
  warning: 'text-[#D9853F]',
  over: 'text-destructive',
} as const;

export function WordCountBar({ wordCount, maxWords = 2000, className }: WordCountBarProps) {
  const state = getCountState(wordCount, maxWords);
  const percentage = Math.min((wordCount / maxWords) * 100, 100);

  return (
    <div className={cn('space-y-1', className)}>
      <div
        className="h-1 w-full rounded-full bg-border"
        role="meter"
        aria-valuenow={wordCount}
        aria-valuemin={0}
        aria-valuemax={maxWords}
        aria-label="Word count"
      >
        <div
          className={cn('h-full rounded-full transition-all duration-300', BAR_COLORS[state])}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className={cn('text-xs text-right', TEXT_COLORS[state])}>
        {wordCount} / {maxWords} words
      </p>
    </div>
  );
}
