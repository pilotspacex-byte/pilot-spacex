'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Bot, User, Copy, Check, RotateCcw, ThumbsUp, ThumbsDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

/* -----------------------------------------------------------------------------
 * Message Container
 * -------------------------------------------------------------------------- */

const messageVariants = cva('flex gap-3 px-4 py-4', {
  variants: {
    from: {
      user: 'flex-row-reverse',
      assistant: 'flex-row',
      system: 'flex-row justify-center',
    },
  },
  defaultVariants: {
    from: 'assistant',
  },
});

export interface MessageProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof messageVariants> {
  /** Message sender role */
  from?: 'user' | 'assistant' | 'system';
  /** Avatar URL for the sender */
  avatarUrl?: string;
  /** Avatar fallback (initials or icon) */
  avatarFallback?: React.ReactNode;
  /** Hide the avatar */
  hideAvatar?: boolean;
}

const Message = React.forwardRef<HTMLDivElement, MessageProps>(
  (
    {
      className,
      from = 'assistant',
      avatarUrl,
      avatarFallback,
      hideAvatar = false,
      children,
      ...props
    },
    ref
  ) => {
    const defaultAvatar =
      from === 'user' ? <User className="size-4" /> : <Bot className="size-4" />;

    return (
      <div ref={ref} className={cn(messageVariants({ from }), className)} {...props}>
        {!hideAvatar && from !== 'system' && (
          <Avatar className="size-8 shrink-0">
            {avatarUrl && <AvatarImage src={avatarUrl} alt={from} />}
            <AvatarFallback
              className={cn(
                'text-xs',
                from === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              )}
            >
              {avatarFallback ?? defaultAvatar}
            </AvatarFallback>
          </Avatar>
        )}
        <div
          className={cn(
            'flex min-w-0 max-w-[85%] flex-col gap-2',
            from === 'system' && 'max-w-full items-center'
          )}
        >
          {children}
        </div>
      </div>
    );
  }
);
Message.displayName = 'Message';

/* -----------------------------------------------------------------------------
 * Message Content
 * -------------------------------------------------------------------------- */

const messageContentVariants = cva('rounded-2xl px-4 py-3 text-sm', {
  variants: {
    from: {
      user: 'bg-primary text-primary-foreground rounded-br-md',
      assistant: 'bg-muted text-foreground rounded-bl-md',
      system: 'bg-transparent text-muted-foreground text-xs italic',
    },
  },
  defaultVariants: {
    from: 'assistant',
  },
});

export interface MessageContentProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof messageContentVariants> {}

const MessageContent = React.forwardRef<HTMLDivElement, MessageContentProps>(
  ({ className, from = 'assistant', children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn(messageContentVariants({ from }), className)} {...props}>
        {children}
      </div>
    );
  }
);
MessageContent.displayName = 'MessageContent';

/* -----------------------------------------------------------------------------
 * Message Response (Streaming Markdown)
 * -------------------------------------------------------------------------- */

export interface MessageResponseProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Raw markdown content */
  children?: React.ReactNode;
  /** Whether the response is still streaming */
  isStreaming?: boolean;
}

const MessageResponse = React.forwardRef<HTMLDivElement, MessageResponseProps>(
  ({ className, children, isStreaming = false, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'prose prose-sm dark:prose-invert max-w-none',
          'prose-p:my-2 prose-pre:my-2 prose-ul:my-2 prose-ol:my-2',
          'prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5',
          'prose-code:before:content-none prose-code:after:content-none',
          isStreaming && 'animate-pulse',
          className
        )}
        {...props}
      >
        {children}
        {isStreaming && (
          <span className="ml-0.5 inline-block h-4 w-0.5 animate-blink bg-foreground" />
        )}
      </div>
    );
  }
);
MessageResponse.displayName = 'MessageResponse';

/* -----------------------------------------------------------------------------
 * Message Actions
 * -------------------------------------------------------------------------- */

export interface MessageActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Show copy button */
  showCopy?: boolean;
  /** Show regenerate button */
  showRegenerate?: boolean;
  /** Show feedback buttons */
  showFeedback?: boolean;
  /** Content to copy */
  copyContent?: string;
  /** Callback when copy is clicked */
  onCopy?: () => void;
  /** Callback when regenerate is clicked */
  onRegenerate?: () => void;
  /** Callback when thumbs up is clicked */
  onThumbsUp?: () => void;
  /** Callback when thumbs down is clicked */
  onThumbsDown?: () => void;
}

const MessageActions = React.forwardRef<HTMLDivElement, MessageActionsProps>(
  (
    {
      className,
      showCopy = true,
      showRegenerate = false,
      showFeedback = false,
      copyContent,
      onCopy,
      onRegenerate,
      onThumbsUp,
      onThumbsDown,
      ...props
    },
    ref
  ) => {
    const [copied, setCopied] = React.useState(false);

    const handleCopy = async () => {
      if (copyContent) {
        await navigator.clipboard.writeText(copyContent);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        onCopy?.();
      }
    };

    return (
      <TooltipProvider>
        <div
          ref={ref}
          className={cn(
            'flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100',
            className
          )}
          {...props}
        >
          {showCopy && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={handleCopy}
                  aria-label={copied ? 'Copied' : 'Copy message'}
                >
                  {copied ? (
                    <Check className="size-3.5 text-emerald-500" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="text-xs">{copied ? 'Copied!' : 'Copy'}</p>
              </TooltipContent>
            </Tooltip>
          )}

          {showRegenerate && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={onRegenerate}
                  aria-label="Regenerate response"
                >
                  <RotateCcw className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="text-xs">Regenerate</p>
              </TooltipContent>
            </Tooltip>
          )}

          {showFeedback && (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={onThumbsUp}
                    aria-label="Good response"
                  >
                    <ThumbsUp className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p className="text-xs">Good response</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={onThumbsDown}
                    aria-label="Poor response"
                  >
                    <ThumbsDown className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p className="text-xs">Poor response</p>
                </TooltipContent>
              </Tooltip>
            </>
          )}
        </div>
      </TooltipProvider>
    );
  }
);
MessageActions.displayName = 'MessageActions';

/* -----------------------------------------------------------------------------
 * Exports
 * -------------------------------------------------------------------------- */

export {
  Message,
  MessageContent,
  MessageResponse,
  MessageActions,
  messageVariants,
  messageContentVariants,
};
