/**
 * MarkdownContent - Renders markdown text from AI responses (G-08).
 *
 * Used by both AssistantMessage (completed) and StreamingContent (in-progress).
 * Supports GFM (tables, strikethrough, task lists) and syntax highlighting.
 *
 * During streaming, renders a single ReactMarkdown instance with a pulsing
 * cursor at the end. The container fades in once on mount via CSS animation.
 * Uses motion-safe prefix for reduced-motion accessibility.
 */

'use client';

import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { cn } from '@/lib/utils';

interface MarkdownContentProps {
  /** Markdown text to render */
  content: string;
  /** Whether content is actively streaming (adds cursor + fade-in) */
  isStreaming?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// Use custom .chat-markdown class defined in globals.css
// (prose- classes require @tailwindcss/typography which is not installed)
const MARKDOWN_CLASSES = 'chat-markdown max-w-none';

const MarkdownPlugins = { remark: [remarkGfm], rehype: [rehypeHighlight] };

// Custom components for ReactMarkdown - wrap tables in scrollable container
const markdownComponents = {
  table: ({ children, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="table-wrapper">
      <table {...props}>{children}</table>
    </div>
  ),
};

export const MarkdownContent = memo<MarkdownContentProps>(({ content, isStreaming, className }) => {
  if (!content) return null;

  return (
    <div className={cn(MARKDOWN_CLASSES, isStreaming && 'motion-safe:animate-fade-up', className)}>
      <ReactMarkdown
        remarkPlugins={MarkdownPlugins.remark}
        rehypePlugins={MarkdownPlugins.rehype}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span
          className="ml-0.5 inline-block h-4 w-[2px] motion-safe:animate-pulse motion-reduce:opacity-70 bg-primary"
          aria-hidden="true"
        />
      )}
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';
