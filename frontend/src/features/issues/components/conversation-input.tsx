/**
 * Conversation Input component.
 *
 * Multi-line textarea with:
 * - Send button
 * - Keyboard shortcuts (Cmd+Enter to send)
 * - Auto-resize
 * - Disabled during AI response
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T213
 */
'use client';

import * as React from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export interface ConversationInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Input field for sending conversation messages.
 *
 * @example
 * ```tsx
 * <ConversationInput
 *   onSend={(msg) => console.log(msg)}
 *   disabled={false}
 * />
 * ```
 */
export function ConversationInput({
  onSend,
  disabled = false,
  placeholder = 'Type a message...',
  className,
}: ConversationInputProps) {
  const [input, setInput] = React.useState('');
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Cmd/Ctrl+Enter
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn('p-4', className)}>
      <div className="flex gap-2 items-end">
        {/* Textarea */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="resize-none min-h-[40px] max-h-[200px] pr-12"
            aria-label="Message input"
          />

          {/* Hint text */}
          <div className="absolute bottom-2 right-2 text-xs text-muted-foreground pointer-events-none">
            {input.trim() && !disabled && (
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">⌘↵</kbd>
            )}
          </div>
        </div>

        {/* Send button */}
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !input.trim()}
          aria-label="Send message"
          className="flex-shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </form>
  );
}
