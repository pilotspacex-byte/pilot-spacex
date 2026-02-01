'use client';

/**
 * AskPilotInput - Inline AI assistant input at bottom of note canvas
 *
 * Provides persistent AI input field for asking questions about the note content.
 * Per DD-013 Note-First workflow, this enables inline AI collaboration.
 *
 * @see DD-013 Note-First Collaborative Workspace
 * @see UI Spec v3.3 Section 7 - Note Canvas
 */
import { useState, useCallback, useRef, type KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface AskPilotInputProps {
  /** Note ID for context */
  noteId: string;
  /** Workspace ID for context */
  workspaceId?: string;
  /** Callback when user submits a question */
  onSubmit?: (question: string) => Promise<void>;
  /** Callback to open ChatView panel */
  onChatViewOpen?: () => void;
  /** Placeholder text */
  placeholder?: string;
  /** Whether input is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * AskPilotInput provides an inline AI assistant input at the bottom of the note canvas.
 *
 * @example
 * ```tsx
 * <AskPilotInput
 *   noteId="note-123"
 *   workspaceId="workspace-456"
 *   onSubmit={async (question) => {
 *     await askAI(question);
 *   }}
 * />
 * ```
 */
export function AskPilotInput({
  noteId,
  workspaceId,
  onSubmit,
  onChatViewOpen,
  placeholder = 'Ask Pilot...',
  disabled = false,
  className,
}: AskPilotInputProps) {
  const [value, setValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async () => {
    if (!value.trim() || isSubmitting || disabled) return;

    const question = value.trim();
    setValue('');
    setIsSubmitting(true);

    try {
      onChatViewOpen?.();
      await onSubmit?.(question);
    } finally {
      setIsSubmitting(false);
      inputRef.current?.focus();
    }
  }, [value, isSubmitting, disabled, onSubmit, onChatViewOpen]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <div
      className={cn(
        // Container styling - sticky at bottom of canvas
        'sticky bottom-0 left-0 right-0',
        'bg-background/80 backdrop-blur-sm',
        'border-t border-border-subtle',
        // Responsive padding
        'px-3 sm:px-4 py-2 sm:py-3',
        className
      )}
    >
      <div
        className={cn(
          // Input wrapper
          'flex items-center gap-2 sm:gap-3',
          // Responsive max-width - matches editor content width
          'max-w-full sm:max-w-[640px] md:max-w-[680px] lg:max-w-[720px] xl:max-w-[760px] 2xl:max-w-[800px] mx-auto',
          'bg-background',
          'border border-border rounded-full',
          // Responsive padding
          'px-3 sm:px-4 py-1.5 sm:py-2',
          'shadow-sm',
          'transition-all duration-150',
          'focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        {/* AI indicator dot */}
        <div
          className={cn(
            'w-2.5 h-2.5 rounded-full shrink-0',
            'bg-primary',
            isSubmitting && 'animate-pulse'
          )}
          aria-hidden="true"
        />

        {/* Input field */}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isSubmitting}
          className={cn(
            'flex-1 min-w-0',
            'bg-transparent',
            'text-sm text-foreground placeholder:text-muted-foreground',
            'outline-none border-none',
            'disabled:cursor-not-allowed'
          )}
          aria-label="Ask Pilot AI assistant"
          data-note-id={noteId}
          data-workspace-id={workspaceId}
        />

        {/* Submit button */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!value.trim() || isSubmitting || disabled}
          className={cn(
            'shrink-0',
            'p-1.5 rounded-full',
            'text-muted-foreground',
            'transition-all duration-150',
            'hover:text-primary hover:bg-primary/10',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent'
          )}
          aria-label="Send question to Pilot"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

export default AskPilotInput;
