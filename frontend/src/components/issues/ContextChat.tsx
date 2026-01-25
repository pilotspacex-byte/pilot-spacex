'use client';

/**
 * ContextChat - Chat interface for AI context refinement.
 *
 * T215: Provides chat message list with SSE streaming, suggested questions,
 * typing indicator, and conversation management.
 */

import * as React from 'react';
import {
  Send,
  Trash2,
  Sparkles,
  User,
  Bot,
  Loader2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

// ============================================================================
// Types
// ============================================================================

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  /** Unique identifier */
  id: string;
  /** Message role */
  role: MessageRole;
  /** Message content */
  content: string;
  /** Timestamp */
  timestamp: Date;
  /** Whether message is still streaming */
  isStreaming?: boolean;
}

export interface SuggestedQuestion {
  /** Unique identifier */
  id: string;
  /** Question text */
  text: string;
  /** Category for grouping */
  category?: string;
}

export interface ContextChatProps {
  /** Issue ID for API calls */
  issueId: string;
  /** Chat messages */
  messages: ChatMessage[];
  /** Suggested questions */
  suggestedQuestions?: SuggestedQuestion[];
  /** Whether AI is currently responding */
  isTyping?: boolean;
  /** Send message handler */
  onSendMessage: (message: string) => void;
  /** Clear conversation handler */
  onClearConversation?: () => void;
  /** Whether the section is collapsible */
  collapsible?: boolean;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Maximum height for chat area */
  maxHeight?: number;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Message Bubble
// ============================================================================

interface MessageBubbleProps {
  message: ChatMessage;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <Avatar className="size-8 shrink-0">
        <AvatarFallback
          className={cn(isUser ? 'bg-primary text-primary-foreground' : 'bg-ai/10 text-ai')}
        >
          {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
        </AvatarFallback>
      </Avatar>

      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        {message.isStreaming && (
          <span className="inline-block w-1 h-4 ml-1 bg-current animate-pulse" />
        )}
        <p
          className={cn(
            'text-xs mt-1',
            isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// Typing Indicator
// ============================================================================

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <Avatar className="size-8 shrink-0">
        <AvatarFallback className="bg-ai/10 text-ai">
          <Bot className="size-4" />
        </AvatarFallback>
      </Avatar>

      <div className="bg-muted rounded-lg px-4 py-3">
        <div className="flex gap-1">
          <span
            className="size-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: '0ms' }}
          />
          <span
            className="size-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: '150ms' }}
          />
          <span
            className="size-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: '300ms' }}
          />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Suggested Questions
// ============================================================================

interface SuggestedQuestionsProps {
  questions: SuggestedQuestion[];
  onSelect: (question: string) => void;
}

function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  if (questions.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">Suggested questions:</p>
      <div className="flex flex-wrap gap-2">
        {questions.map((q) => (
          <button
            key={q.id}
            onClick={() => onSelect(q.text)}
            className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs hover:bg-muted transition-colors"
          >
            <Sparkles className="size-3 text-ai" />
            {q.text}
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Chat Input
// ============================================================================

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
}

function ChatInput({ value, onChange, onSend, disabled, placeholder }: ChatInputProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend();
      }
    }
  };

  // Auto-resize textarea
  React.useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [value]);

  return (
    <div className="flex gap-2">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Ask about this issue...'}
        disabled={disabled}
        className="min-h-[40px] max-h-[120px] resize-none"
        rows={1}
      />
      <Button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        size="icon"
        className="shrink-0"
      >
        {disabled ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
      </Button>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ContextChat({
  issueId: _issueId,
  messages,
  suggestedQuestions = [],
  isTyping = false,
  onSendMessage,
  onClearConversation,
  collapsible = true,
  defaultCollapsed = false,
  maxHeight = 400,
  className,
}: ContextChatProps) {
  // issueId is available for future use (e.g., analytics, caching)
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const [inputValue, setInputValue] = React.useState('');
  const [showClearDialog, setShowClearDialog] = React.useState(false);
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages arrive
  React.useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      );
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages, isTyping]);

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    onSendMessage(question);
  };

  const handleClear = () => {
    onClearConversation?.();
    setShowClearDialog(false);
  };

  const header = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {collapsible &&
          (isCollapsed ? <ChevronRight className="size-4" /> : <ChevronDown className="size-4" />)}
        <Sparkles className="size-4 text-ai" />
        <span className="text-sm font-medium">AI Assistant</span>
        {messages.length > 0 && (
          <Badge variant="secondary" className="text-xs">
            {messages.length}
          </Badge>
        )}
      </div>

      {!isCollapsed && messages.length > 0 && onClearConversation && (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            setShowClearDialog(true);
          }}
          className="text-muted-foreground"
        >
          <Trash2 className="size-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );

  const content = (
    <div className="space-y-4 mt-3">
      {/* Messages area */}
      {messages.length > 0 ? (
        <ScrollArea ref={scrollAreaRef} className="rounded-lg border" style={{ height: maxHeight }}>
          <div className="p-4 space-y-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && <TypingIndicator />}
          </div>
        </ScrollArea>
      ) : (
        <div className="rounded-lg border p-8 text-center">
          <Bot className="size-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground">
            Ask questions about this issue to refine the context
          </p>
        </div>
      )}

      {/* Suggested questions (only when no messages) */}
      {messages.length === 0 && suggestedQuestions.length > 0 && (
        <SuggestedQuestions questions={suggestedQuestions} onSelect={handleSuggestedQuestion} />
      )}

      {/* Input */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        disabled={isTyping}
        placeholder="Ask about implementation details, related code, or clarify requirements..."
      />
    </div>
  );

  const mainContent = collapsible ? (
    <Collapsible
      open={!isCollapsed}
      onOpenChange={(open) => setIsCollapsed(!open)}
      className={className}
    >
      <CollapsibleTrigger className="w-full text-left">{header}</CollapsibleTrigger>
      <CollapsibleContent>{content}</CollapsibleContent>
    </Collapsible>
  ) : (
    <div className={className}>
      {header}
      {content}
    </div>
  );

  return (
    <>
      {mainContent}

      {/* Clear Conversation Dialog */}
      <AlertDialog open={showClearDialog} onOpenChange={setShowClearDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear Conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove all messages from this chat. The generated context and tasks will not
              be affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleClear}>Clear</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default ContextChat;
