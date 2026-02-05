/**
 * StreamingBanner — Fixed status banner above chat input (T019).
 *
 * Shows the current streaming phase with icon, label, and
 * contextual right-side info (elapsed time or word count).
 * Uses glass-subtle treatment for frosted glass appearance.
 *
 * @module features/ai/ChatView/StreamingBanner
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Brain, Wrench, Pencil, Loader2, Check, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import { getToolDisplayName } from './constants';
import type { StreamingPhase } from '@/stores/ai/types/conversation';

interface StreamingBannerProps {
  isStreaming: boolean;
  phase?: StreamingPhase;
  activeToolName?: string | null;
  wordCount?: number;
  interrupted?: boolean;
  thinkingStartedAt?: number | null;
  className?: string;
}

/** Auto-hide delay for interrupted state (ms) */
const INTERRUPTED_HIDE_DELAY = 1500;

/** Phase-to-icon/label mapping */
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
      return { icon: Pencil, label: 'Writing response...' };
    case 'connecting':
      return { icon: Loader2, label: 'Connecting...' };
    case 'completing':
      return { icon: Check, label: 'Finishing...' };
    case 'message_start':
      return { icon: Loader2, label: 'Starting...' };
    default:
      return { icon: Loader2, label: 'Processing...' };
  }
}

/** Whether a phase should show elapsed time on the right side */
function showsElapsedTime(phase?: StreamingPhase): boolean {
  return phase === 'thinking' || phase === 'tool_use';
}

/** Whether a phase should animate the icon with spin */
function isSpinningIcon(phase?: StreamingPhase): boolean {
  return phase === 'connecting' || phase === 'message_start';
}

export function StreamingBanner({
  isStreaming,
  phase,
  activeToolName,
  wordCount,
  interrupted,
  thinkingStartedAt,
  className,
}: StreamingBannerProps) {
  const [showInterrupted, setShowInterrupted] = useState(false);
  const lastInterruptedRef = useRef(false);

  const showBanner = useCallback(() => setShowInterrupted(true), []);
  const hideBanner = useCallback(() => setShowInterrupted(false), []);

  const elapsed = useElapsedTime(thinkingStartedAt ?? null, isStreaming && showsElapsedTime(phase));

  // Detect interrupted transitions and manage auto-hide timer
  useEffect(() => {
    const wasInterrupted = lastInterruptedRef.current;
    lastInterruptedRef.current = !!interrupted;

    if (interrupted && !wasInterrupted) {
      // Rising edge: show banner via microtask to satisfy lint rule
      queueMicrotask(showBanner);
    }

    if (!interrupted) return;

    const timer = setTimeout(hideBanner, INTERRUPTED_HIDE_DELAY);
    return () => clearTimeout(timer);
  }, [interrupted, showBanner, hideBanner]);

  // Determine visibility
  const isVisible = isStreaming || showInterrupted;
  if (!isVisible) return null;

  // Interrupted state rendering
  if (showInterrupted && !isStreaming) {
    return (
      <div
        data-testid="streaming-banner"
        role="status"
        aria-live="polite"
        className={cn(
          'h-9 flex items-center justify-between px-3',
          'glass-subtle border-t border-t-border-subtle',
          className
        )}
      >
        <div className="flex items-center gap-1.5">
          <Square className="h-3.5 w-3.5 text-muted-foreground fill-current" />
          <span className="text-sm text-muted-foreground">Stopped</span>
        </div>
      </div>
    );
  }

  // Active streaming rendering
  const { icon: PhaseIcon, label } = getPhaseConfig(phase, activeToolName);
  const spinning = isSpinningIcon(phase);

  return (
    <div
      data-testid="streaming-banner"
      role="status"
      aria-live="polite"
      className={cn(
        'h-9 flex items-center justify-between px-3',
        'glass-subtle',
        className
      )}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={phase ?? 'default'}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="flex items-center gap-1.5"
        >
          <PhaseIcon
            className={cn('h-3.5 w-3.5 text-muted-foreground', spinning && 'animate-spin')}
          />
          <span className="text-sm text-muted-foreground">{label}</span>
        </motion.div>
      </AnimatePresence>

      {/* Right side: elapsed time or word count */}
      {showsElapsedTime(phase) && (
        <span className="font-mono text-xs tabular-nums text-ai">{elapsed}</span>
      )}
      {phase === 'content' && (
        <span className="font-mono text-xs tabular-nums text-ai">{wordCount ?? 0}w</span>
      )}
    </div>
  );
}
