/**
 * CommentInput component for adding comments to issues.
 *
 * Plain text textarea with Enter-to-submit, Shift+Enter for newlines,
 * validation, and loading states.
 *
 * @see T036 - Issue Detail Page comment input
 */
'use client';

import * as React from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

const MAX_CHARS = 10_000;

export interface CommentInputProps {
  onSubmit: (content: string) => void;
  isSubmitting?: boolean;
  disabled?: boolean;
  className?: string;
}

export function CommentInput({
  onSubmit,
  isSubmitting = false,
  disabled = false,
  className,
}: CommentInputProps) {
  const [value, setValue] = React.useState('');
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const canSubmit = value.trim().length > 0 && !isSubmitting && !disabled;

  const handleSubmit = React.useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isSubmitting || disabled) return;
    onSubmit(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isSubmitting, disabled, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const next = e.target.value;
    if (next.length > MAX_CHARS) return;
    setValue(next);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmit();
  };

  const isDisabled = isSubmitting || disabled;
  const charsRemaining = MAX_CHARS - value.length;
  const showCharWarning = charsRemaining < 500 && value.length > 0;

  return (
    <form
      onSubmit={handleFormSubmit}
      className={cn('border-t border-border bg-background p-4', className)}
    >
      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Add a comment..."
            disabled={isDisabled}
            rows={1}
            className={cn(
              'resize-none min-h-[40px] max-h-[160px] rounded-lg',
              'bg-background-subtle border-border focus:border-primary'
            )}
            aria-label="Comment input"
          />
          {showCharWarning && (
            <span
              className={cn(
                'absolute bottom-2 right-2 text-[10px]',
                charsRemaining < 100 ? 'text-destructive' : 'text-muted-foreground'
              )}
            >
              {charsRemaining}
            </span>
          )}
        </div>

        <Button
          type="submit"
          size="icon"
          disabled={!canSubmit}
          aria-label="Send comment"
          className="flex-shrink-0 h-9 w-9"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </div>

      <p className="text-[10px] text-muted-foreground mt-1.5">
        <kbd className="px-1 py-0.5 bg-muted rounded text-[10px] font-mono">Enter</kbd> to send,{' '}
        <kbd className="px-1 py-0.5 bg-muted rounded text-[10px] font-mono">Shift+Enter</kbd> for
        newline
      </p>
    </form>
  );
}
