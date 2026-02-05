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

const PROSE_CLASSES = cn(
  'prose prose-sm max-w-none text-foreground dark:prose-invert',
  'prose-headings:text-foreground prose-headings:font-semibold',
  'prose-p:leading-relaxed prose-p:text-foreground',
  'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
  'prose-code:rounded prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5',
  'prose-code:text-[13px] prose-code:font-mono prose-code:before:content-none prose-code:after:content-none',
  'prose-pre:rounded-[10px] prose-pre:bg-muted prose-pre:font-mono',
  'prose-blockquote:border-l-ai/30'
);

const MarkdownPlugins = { remark: [remarkGfm], rehype: [rehypeHighlight] };

export const MarkdownContent = memo<MarkdownContentProps>(({ content, isStreaming, className }) => {
  if (!content) return null;

  return (
    <div className={cn(PROSE_CLASSES, isStreaming && 'motion-safe:animate-fade-up', className)}>
      <ReactMarkdown remarkPlugins={MarkdownPlugins.remark} rehypePlugins={MarkdownPlugins.rehype}>
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
