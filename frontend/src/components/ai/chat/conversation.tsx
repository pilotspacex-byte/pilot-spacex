'use client';

import * as React from 'react';
import { ArrowDown } from 'lucide-react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

/* -----------------------------------------------------------------------------
 * Conversation Container
 * -------------------------------------------------------------------------- */

const conversationVariants = cva('relative flex flex-col', {
  variants: {
    size: {
      sm: 'h-[400px]',
      md: 'h-[600px]',
      lg: 'h-[800px]',
      full: 'h-full',
    },
  },
  defaultVariants: {
    size: 'full',
  },
});

export interface ConversationProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof conversationVariants> {
  /** Auto-scroll to bottom on new messages */
  autoScroll?: boolean;
  /** Show scroll-to-bottom button when scrolled up */
  showScrollButton?: boolean;
}

const Conversation = React.forwardRef<HTMLDivElement, ConversationProps>(
  (
    { className, size = 'full', autoScroll = true, showScrollButton = true, children, ...props },
    ref
  ) => {
    const scrollRef = React.useRef<HTMLDivElement>(null);
    const [showButton, setShowButton] = React.useState(false);
    const [isUserScrolling, setIsUserScrolling] = React.useState(false);

    /**
     * Check if user has scrolled away from bottom
     */
    const checkScrollPosition = React.useCallback(() => {
      if (!scrollRef.current) return;

      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      const isAtBottom = distanceFromBottom < 100;

      setShowButton(!isAtBottom && showScrollButton);
      setIsUserScrolling(!isAtBottom);
    }, [showScrollButton]);

    /**
     * Scroll to bottom of conversation
     */
    const scrollToBottom = React.useCallback((smooth = true) => {
      if (!scrollRef.current) return;

      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      });
    }, []);

    /**
     * Auto-scroll on new content if at bottom
     */
    React.useEffect(() => {
      if (autoScroll && !isUserScrolling) {
        scrollToBottom(false);
      }
    }, [children, autoScroll, isUserScrolling, scrollToBottom]);

    /**
     * Attach scroll listener
     */
    React.useEffect(() => {
      const scrollElement = scrollRef.current;
      if (!scrollElement) return;

      scrollElement.addEventListener('scroll', checkScrollPosition);
      return () => scrollElement.removeEventListener('scroll', checkScrollPosition);
    }, [checkScrollPosition]);

    return (
      <div ref={ref} className={cn(conversationVariants({ size }), className)} {...props}>
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto scroll-smooth"
          role="log"
          aria-live="polite"
          aria-atomic="false"
        >
          {children}
        </div>

        {showButton && (
          <Button
            variant="outline"
            size="icon"
            className="absolute bottom-4 right-4 size-10 rounded-full shadow-lg"
            onClick={() => {
              scrollToBottom(true);
              setIsUserScrolling(false);
            }}
            aria-label="Scroll to bottom"
          >
            <ArrowDown className="size-4" />
          </Button>
        )}
      </div>
    );
  }
);
Conversation.displayName = 'Conversation';

/* -----------------------------------------------------------------------------
 * Scroll Anchor
 * -------------------------------------------------------------------------- */

export interface ScrollAnchorProps {
  /** Whether to track visibility */
  trackVisibility?: boolean;
}

/**
 * Invisible anchor element for auto-scrolling
 */
const ScrollAnchor = React.forwardRef<HTMLDivElement, ScrollAnchorProps>(
  ({ trackVisibility = true }, ref) => {
    const anchorRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
      if (!trackVisibility || !anchorRef.current) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
          });
        },
        { threshold: 0.5 }
      );

      observer.observe(anchorRef.current);
      return () => observer.disconnect();
    }, [trackVisibility]);

    return <div ref={ref || anchorRef} className="h-px w-full" aria-hidden="true" />;
  }
);
ScrollAnchor.displayName = 'ScrollAnchor';

/* -----------------------------------------------------------------------------
 * Exports
 * -------------------------------------------------------------------------- */

export { Conversation, ScrollAnchor, conversationVariants };
