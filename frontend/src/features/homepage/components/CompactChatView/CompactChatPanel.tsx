'use client';

/**
 * CompactChatPanel (H038) — Expanded chat panel (max 400px).
 * Contains message list + auto-expanding textarea + send/stop buttons.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, ChevronDown, Send, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { CHAT_MAX_HEIGHT } from '../../constants';
import { CompactMessageList } from './CompactMessageList';

interface CompactChatPanelProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
  error: string | null;
  onSendMessage: (text: string) => void;
  onAbort: () => void;
  onMinimize: () => void;
  /** H-5: Auto-focus textarea when panel mounts */
  autoFocus?: boolean;
}

export function CompactChatPanel({
  messages,
  isStreaming,
  streamContent,
  error,
  onSendMessage,
  onAbort,
  onMinimize,
  autoFocus = false,
}: CompactChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // H-5: Focus textarea on mount when autoFocus is true
  useEffect(() => {
    if (autoFocus) {
      textareaRef.current?.focus();
    }
  }, [autoFocus]);

  const handleSubmit = useCallback(() => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;
    onSendMessage(text);
    setInputValue('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [inputValue, isStreaming, onSendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'Escape') {
      onMinimize();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    // Auto-expand textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  };

  return (
    <div
      className={cn(
        'flex flex-col overflow-hidden rounded-lg border border-border-subtle',
        'bg-card shadow-warm-md'
      )}
      style={{ maxHeight: `${CHAT_MAX_HEIGHT}px` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-2">
        <span className="text-sm font-medium text-foreground">PilotSpace AI</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 min-h-[44px] min-w-[44px]"
          onClick={onMinimize}
          aria-label="Minimize chat"
        >
          <ChevronDown className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <CompactMessageList
        messages={messages}
        isStreaming={isStreaming}
        streamContent={streamContent}
      />

      {/* Error display */}
      {error && (
        <div
          className="flex items-center gap-2 border-t border-destructive/20 bg-destructive/5 px-3 py-2"
          role="alert"
        >
          <AlertCircle className="h-3.5 w-3.5 shrink-0 text-destructive" aria-hidden="true" />
          <p className="text-xs text-destructive">{error}</p>
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2 border-t border-border-subtle p-3">
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          rows={1}
          aria-label="Chat message input"
          className={cn(
            'flex-1 resize-none rounded-md border border-border-subtle bg-background px-3 py-2',
            'text-sm text-foreground placeholder:text-muted-foreground',
            'focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary'
          )}
          style={{ maxHeight: '120px' }}
        />

        {isStreaming ? (
          <Button
            variant="ghost"
            size="icon"
            onClick={onAbort}
            aria-label="Stop generating"
            className="h-9 w-9 min-h-[44px] min-w-[44px] shrink-0 text-destructive"
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            variant="default"
            size="icon"
            onClick={handleSubmit}
            disabled={!inputValue.trim()}
            aria-label="Send message"
            className="h-9 w-9 min-h-[44px] min-w-[44px] shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
