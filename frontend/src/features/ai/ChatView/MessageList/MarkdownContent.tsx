/**
 * MarkdownContent - Renders markdown text from AI responses (G-08).
 *
 * Used by both AssistantMessage (completed) and StreamingContent (in-progress).
 * Supports GFM (tables, strikethrough, task lists) and syntax highlighting.
 *
 * When streaming, new content fades in using the animate-fade-up animation.
 * Previously rendered content stays at full opacity without animation.
 * Uses motion-safe prefix for reduced-motion accessibility.
 */

'use client';

import { memo, useEffect, useRef, useState } from 'react';
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

const FADE_DELAY_MS = 200;
const MarkdownPlugins = { remark: [remarkGfm], rehype: [rehypeHighlight] };

/**
 * Inner component handling streaming fade-in logic.
 * Separated so MarkdownContent can conditionally render it,
 * keeping static path simple and avoiding lint issues with
 * conditional hooks.
 */
function StreamingMarkdown({ content, className }: { content: string; className?: string }) {
  // splitPoint tracks how much content is "stable" (already faded in)
  const [splitPoint, setSplitPoint] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Schedule split point advance when content grows
  useEffect(() => {
    if (content.length <= splitPoint) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      setSplitPoint(content.length);
      timerRef.current = null;
    }, FADE_DELAY_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [content, splitPoint]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const stableContent = content.substring(0, splitPoint);
  const newContent = content.substring(splitPoint);

  return (
    <div className={cn(PROSE_CLASSES, className)}>
      {stableContent && (
        <ReactMarkdown
          remarkPlugins={MarkdownPlugins.remark}
          rehypePlugins={MarkdownPlugins.rehype}
        >
          {stableContent}
        </ReactMarkdown>
      )}
      {newContent && (
        <span className="motion-safe:animate-fade-up">
          <ReactMarkdown
            remarkPlugins={MarkdownPlugins.remark}
            rehypePlugins={MarkdownPlugins.rehype}
          >
            {newContent}
          </ReactMarkdown>
        </span>
      )}
      <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-primary" />
    </div>
  );
}

export const MarkdownContent = memo<MarkdownContentProps>(({ content, isStreaming, className }) => {
  if (!content) return null;

  if (!isStreaming) {
    return (
      <div className={cn(PROSE_CLASSES, className)}>
        <ReactMarkdown
          remarkPlugins={MarkdownPlugins.remark}
          rehypePlugins={MarkdownPlugins.rehype}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  // key={true} ensures StreamingMarkdown remounts when isStreaming toggles,
  // resetting splitPoint state to 0 naturally without setState-in-effect.
  return <StreamingMarkdown content={content} className={className} />;
});

MarkdownContent.displayName = 'MarkdownContent';
