/**
 * AttachmentPill — v3 icon-only pill that forwards clicks to AttachmentButton.
 *
 * AttachmentButton owns its own hidden <input type="file"> and drive menu
 * behaviour, so we render it inside the pill rather than replacing it — the
 * Pill wrapper provides the v3 visual frame.
 */

import type { ComponentProps } from 'react';
import { AttachmentButton } from '@/features/ai/ChatView/ChatInput/AttachmentButton';
import { cn } from '@/lib/utils';

type AttachmentButtonProps = ComponentProps<typeof AttachmentButton>;

export function AttachmentPill(props: AttachmentButtonProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center h-8 rounded-full border border-[var(--border-toolbar)] bg-card',
        'transition-colors duration-150 hover:bg-accent',
        '[&_button]:h-8 [&_button]:w-8 [&_button]:rounded-full [&_button]:bg-transparent',
        '[&_button]:text-foreground [&_button]:hover:bg-transparent'
      )}
    >
      <AttachmentButton {...props} />
    </div>
  );
}
