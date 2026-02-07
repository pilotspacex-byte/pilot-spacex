'use client';

/**
 * CompactChatInput (H035) — 48px collapsed chat bar.
 * Shows AI avatar with pulsing dot, placeholder input, and keyboard hint [/].
 */

import { forwardRef } from 'react';
import { Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useWorkspaceStore } from '@/stores/RootStore';

interface CompactChatInputProps {
  onFocus: () => void;
  disabled?: boolean;
}

export const CompactChatInput = forwardRef<HTMLInputElement, CompactChatInputProps>(
  function CompactChatInput({ onFocus, disabled = false }, ref) {
    const workspaceStore = useWorkspaceStore();
    const slug = workspaceStore.currentWorkspace?.slug ?? '';

    return (
      <div
        className={cn(
          'flex h-12 items-center gap-3 rounded-lg border border-border-subtle',
          'bg-background-subtle px-4',
          'motion-safe:transition-all motion-safe:duration-200',
          disabled && 'opacity-60'
        )}
      >
        {/* AI avatar with pulsing dot (H-1: use AI-colored scale pulse) */}
        <div className="relative shrink-0">
          <Bot className="h-6 w-6 text-ai" aria-hidden="true" />
          <span
            className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-ai motion-safe:animate-[pulse_2s_ease-in-out_infinite]"
            aria-hidden="true"
          />
        </div>

        {/* Input area */}
        {disabled ? (
          <span className="flex-1 text-sm text-muted-foreground">
            Configure AI provider in{' '}
            <a
              href={`/${slug}/settings/ai-providers`}
              className="text-primary underline underline-offset-2"
            >
              Settings
            </a>
          </span>
        ) : (
          <input
            ref={ref}
            type="text"
            readOnly
            onFocus={onFocus}
            placeholder="What's on your mind?"
            aria-label="Chat with PilotSpace AI"
            className={cn(
              'flex-1 cursor-pointer bg-transparent text-sm text-foreground',
              'placeholder:text-muted-foreground',
              'focus:outline-none'
            )}
          />
        )}

        {/* Keyboard hint (L-3: show bracketed format) */}
        {!disabled && (
          <kbd className="shrink-0 rounded-sm border border-border-subtle bg-background-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
            [/]
          </kbd>
        )}
      </div>
    );
  }
);
