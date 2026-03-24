'use client';

/**
 * MarkdownPreview - Full-featured markdown preview component.
 *
 * Renders extended markdown with:
 * - GFM (tables, strikethrough, autolinks, task lists)
 * - KaTeX math (inline $...$ and block $$...$$)
 * - Mermaid diagrams (```mermaid code blocks)
 * - Syntax-highlighted code blocks (via highlight.js)
 * - Custom admonition containers (:::note, :::warning, :::tip, :::danger, :::info)
 * - DOMPurify sanitization for XSS prevention
 *
 * Used in the Edit/Preview toggle mode for notes and markdown files.
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkDirective from 'remark-directive';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeHighlight from 'rehype-highlight';
import DOMPurify from 'dompurify';
import 'katex/dist/katex.min.css';

import { cn } from '@/lib/utils';
import { MermaidPreview } from '@/features/notes/editor/extensions/pm-blocks/MermaidPreview';
import { remarkAdmonition } from './plugins/remarkAdmonition';
import { rehypeMermaid } from './plugins/rehypeMermaid';

import type { Components } from 'react-markdown';

interface MarkdownPreviewProps {
  /** Markdown content to render */
  content: string;
  /** Additional CSS classes for the wrapper */
  className?: string;
}

/** Remark plugin chain: GFM + math + directive containers + admonitions */
const remarkPlugins = [remarkGfm, remarkMath, remarkDirective, remarkAdmonition];

/** Rehype plugin chain: raw HTML passthrough + KaTeX + syntax highlighting + mermaid */
const rehypePlugins = [rehypeRaw, rehypeKatex, rehypeHighlight, rehypeMermaid];

/**
 * Custom component overrides for ReactMarkdown.
 * Maps mermaid code blocks and data-mermaid divs to MermaidPreview.
 */
const components: Components = {
  code({ className, children, ...props }) {
    // Mermaid code blocks: render via MermaidPreview
    if (className?.includes('language-mermaid')) {
      return <MermaidPreview code={String(children).trim()} />;
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  div({ node, children, ...props }) {
    // data-mermaid divs (from rehypeMermaid plugin): render via MermaidPreview
    const mermaidContent = props['data-mermaid' as keyof typeof props];
    if (typeof mermaidContent === 'string') {
      return <MermaidPreview code={mermaidContent} />;
    }
    return <div {...props}>{children}</div>;
  },
};

export function MarkdownPreview({ content, className }: MarkdownPreviewProps) {
  const sanitized = DOMPurify.sanitize(content);

  return (
    <div className={cn('prose prose-sm dark:prose-invert max-w-[720px] mx-auto px-8', className)}>
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {sanitized}
      </ReactMarkdown>
    </div>
  );
}
