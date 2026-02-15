/**
 * WaitingIndicator — Static banner shown when AI is waiting for user input.
 *
 * Replaces StreamingBanner during question/approval waiting states.
 * Shows context-aware message with pulsing dot indicator.
 *
 * Feature 014: Approval & User Input UX (T09)
 *
 * @module features/ai/ChatView/WaitingIndicator
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';

interface WaitingIndicatorProps {
  /** Type of waiting state determines displayed message */
  waitingType: 'question' | 'approval';
  /** Optional className for positioning */
  className?: string;
}

/**
 * Get message and subtitle based on waiting type.
 */
function getWaitingContent(type: 'question' | 'approval') {
  switch (type) {
    case 'question':
      return {
        message: 'Waiting for your response',
        subtitle: 'Answer the question above to continue',
      };
    case 'approval':
      return {
        message: 'Waiting for your approval',
        subtitle: 'Review the request above to continue',
      };
  }
}

/**
 * WaitingIndicator component.
 *
 * Shows a static indicator when AI is blocked waiting for user action.
 * Unlike StreamingBanner, this is non-animated (only pulsing dot).
 */
export const WaitingIndicator = memo(function WaitingIndicator({
  waitingType,
  className,
}: WaitingIndicatorProps) {
  const { message, subtitle } = getWaitingContent(waitingType);

  return (
    <div
      data-testid="waiting-indicator"
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center gap-2 px-4 py-3',
        'border-t bg-muted/30',
        'text-sm text-muted-foreground',
        'transition-opacity duration-200',
        className
      )}
    >
      {/* Pulsing dot indicator */}
      <div className="h-2 w-2 rounded-full bg-ai animate-pulse" aria-hidden="true" />

      {/* Text content */}
      <div className="flex flex-col gap-0.5">
        <span className="font-medium">{message}</span>
        <span className="text-xs opacity-80">{subtitle}</span>
      </div>
    </div>
  );
});
