/**
 * ConversationBlock — threaded Q&A block for AI clarification questions (FR-066 to FR-068).
 *
 * Displays AI question + reply input. Thread shows exchange history.
 * 5s SLA indicator per FR-068.
 *
 * Spec: specs/015-ai-workforce-platform/ui-design.md §4
 * T-055
 */
'use client';

import { memo, useCallback, useEffect, useRef, useState, KeyboardEvent } from 'react';
import { MessageCircle, Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

export interface ConversationThread {
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

interface ConversationBlockProps {
  questionId: string;
  question: string;
  thread?: ConversationThread[];
  onReply: (questionId: string, answer: string) => Promise<void>;
  /** Whether AI is currently processing the latest reply (< 5s per FR-068) */
  isProcessing?: boolean;
  /** Whether this question has been answered */
  isAnswered?: boolean;
  className?: string;
}

export const ConversationBlock = memo<ConversationBlockProps>(function ConversationBlock({
  questionId,
  question,
  thread = [],
  onReply,
  isProcessing = false,
  isAnswered = false,
  className,
}) {
  const [answer, setAnswer] = useState('');
  const [isSending, setIsSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [processingSeconds, setProcessingSeconds] = useState(0);

  // 5s SLA counter when processing
  useEffect(() => {
    if (!isProcessing) {
      setProcessingSeconds(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => {
      setProcessingSeconds(Math.floor((Date.now() - start) / 1_000));
    }, 500);
    return () => clearInterval(id);
  }, [isProcessing]);

  const handleSend = useCallback(async () => {
    const trimmed = answer.trim();
    if (!trimmed || isSending || isAnswered) return;

    setIsSending(true);
    try {
      await onReply(questionId, trimmed);
      setAnswer('');
    } finally {
      setIsSending(false);
    }
  }, [answer, isSending, isAnswered, questionId, onReply]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div
      role="article"
      aria-label="AI clarification question"
      className={cn(
        'mx-4 my-3 rounded-[14px] border bg-background p-4 animate-fade-up',
        !isAnswered && 'border-l-[3px] border-l-[#6B8FAD]',
        isAnswered && 'border-border',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <MessageCircle className="h-4 w-4 text-[#6B8FAD] shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-[#6B8FAD]">AI Question</span>
      </div>

      {/* Question text */}
      <p className="text-sm text-foreground mt-2 mb-3">{question}</p>

      {/* Reply input (hidden when answered) */}
      {!isAnswered && (
        <div className="flex items-center gap-2 mb-3">
          <Input
            ref={inputRef}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Your answer…"
            disabled={isSending}
            aria-label="Reply to AI question"
            className="flex-1 text-sm h-9"
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!answer.trim() || isSending}
            aria-label="Send reply"
            className="h-9 w-9 shrink-0"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      )}

      {/* Processing indicator (5s SLA) */}
      {isProcessing && (
        <div
          className="flex items-center gap-2 mb-3 text-xs text-muted-foreground"
          aria-live="polite"
        >
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          <span>
            AI is thinking…
            {processingSeconds >= 3 && ` (${processingSeconds}s)`}
          </span>
        </div>
      )}

      {/* Thread */}
      {thread.length > 0 && (
        <div
          role="list"
          aria-label={`Thread (${thread.length} ${thread.length === 1 ? 'reply' : 'replies'})`}
          className="border-l-2 border-border pl-3 space-y-2 mt-1"
        >
          {thread.map((entry) => (
            <div key={entry.timestamp.toISOString()} role="listitem" className="text-sm">
              <span className="text-xs font-bold text-foreground">
                {entry.role === 'user' ? 'You' : 'AI'}:
              </span>{' '}
              <span className="text-foreground">{entry.content}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
