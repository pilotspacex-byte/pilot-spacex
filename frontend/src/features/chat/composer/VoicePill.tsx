/**
 * VoicePill — v3 pill wrapper for the existing RecordButton.
 *
 * RecordButton is a MobX-observer that contains its own recording state,
 * permission prompts, and tooltip — we only provide the outer pill frame.
 */

import type { ComponentProps } from 'react';
import { RecordButton } from '@/features/ai/ChatView/ChatInput/RecordButton';
import { cn } from '@/lib/utils';

type RecordButtonProps = ComponentProps<typeof RecordButton>;

export function VoicePill(props: RecordButtonProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center h-8 rounded-full border border-[var(--border-toolbar)] bg-card',
        'transition-colors duration-150 hover:bg-accent',
        '[&_button]:h-8 [&_button]:w-8 [&_button]:rounded-full [&_button]:bg-transparent',
        '[&_button]:text-foreground [&_button]:hover:bg-transparent'
      )}
    >
      <RecordButton {...props} />
    </div>
  );
}
