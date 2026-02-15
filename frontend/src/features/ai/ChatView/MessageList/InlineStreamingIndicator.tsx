/**
 * InlineStreamingIndicator - Typing indicator shown inline in message list.
 *
 * Displays the current streaming phase (thinking, connecting, etc.) as a
 * compact inline indicator within the conversation flow, replacing the
 * fixed StreamingBanner for early-phase states before content arrives.
 *
 * @module features/ai/ChatView/MessageList/InlineStreamingIndicator
 */

'use client';

import { memo } from 'react';
import { Brain, Wrench, Pencil, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import { getToolDisplayName } from '../constants';
import type { StreamingPhase } from '@/stores/ai/types/conversation';

interface InlineStreamingIndicatorProps {
  phase?: StreamingPhase;
  activeToolName?: string | null;
  wordCount?: number;
  thinkingStartedAt?: number | null;
}

function getPhaseConfig(phase: StreamingPhase | undefined, activeToolName?: string | null) {
  switch (phase) {
    case 'thinking':
      return { icon: Brain, label: 'Thinking...' };
    case 'tool_use': {
      const toolLabel = activeToolName
        ? `Using ${getToolDisplayName(activeToolName)}...`
        : 'Using tool...';
      return { icon: Wrench, label: toolLabel };
    }
    case 'content':
      return { icon: Pencil, label: 'Writing...' };
    default:
      return { icon: Loader2, label: 'Processing...' };
  }
}

function showsElapsedTime(phase?: StreamingPhase): boolean {
  return phase === 'thinking' || phase === 'tool_use';
}

export const InlineStreamingIndicator = memo<InlineStreamingIndicatorProps>(
  ({ phase, activeToolName, wordCount, thinkingStartedAt }) => {
    const elapsed = useElapsedTime(thinkingStartedAt ?? null, showsElapsedTime(phase));

    const { icon: PhaseIcon, label } = getPhaseConfig(phase, activeToolName);
    const isSpinning = phase === 'connecting' || phase === 'message_start' || !phase;

    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-1.5 text-sm text-muted-foreground"
      >
        <PhaseIcon className={cn('h-3.5 w-3.5', isSpinning && 'animate-spin')} />
        <span>{label}</span>
        {showsElapsedTime(phase) && (
          <span className="font-mono text-xs tabular-nums text-ai ml-1">{elapsed}</span>
        )}
        {phase === 'content' && wordCount != null && (
          <span className="font-mono text-xs tabular-nums text-ai ml-1">{wordCount}w</span>
        )}
      </div>
    );
  }
);

InlineStreamingIndicator.displayName = 'InlineStreamingIndicator';
