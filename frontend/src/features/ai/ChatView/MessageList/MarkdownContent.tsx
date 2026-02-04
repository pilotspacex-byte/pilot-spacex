/**
 * MarkdownContent - Renders markdown text from AI responses (G-08).
 *
 * Used by both AssistantMessage (completed) and StreamingContent (in-progress).
 * Supports GFM (tables, strikethrough, task lists) and syntax highlighting.
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
  /** Whether content is actively streaming (adds cursor) */
  isStreaming?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export const MarkdownContent = memo<MarkdownContentProps>(({ content, isStreaming, className }) => {
  if (!content) return null;

  return (
    <div
      className={cn(
        'prose prose-sm max-w-none text-foreground dark:prose-invert',
        // Override prose defaults to match design system
        'prose-headings:text-foreground prose-headings:font-semibold',
        'prose-p:leading-relaxed prose-p:text-foreground',
        'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
        'prose-code:rounded prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5',
        'prose-code:text-[13px] prose-code:font-mono prose-code:before:content-none prose-code:after:content-none',
        'prose-pre:rounded-[10px] prose-pre:bg-muted prose-pre:font-mono',
        'prose-blockquote:border-l-ai/30',
        className
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {content}
      </ReactMarkdown>
      {isStreaming && <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-primary" />}
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';
