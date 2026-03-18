'use client';

import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { cn } from '@/lib/utils';

interface DocsContentProps {
  content: string;
  className?: string;
}

const remarkPlugins = [remarkGfm];
const rehypePlugins = [rehypeHighlight];

/** Generate a slug from heading text (matches TableOfContents extraction). */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-');
}

/**
 * Custom react-markdown components with heading IDs for TOC linking
 * and table wrapping for horizontal scroll.
 */
const markdownComponents = {
  h1: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
    const text = extractText(children);
    return (
      <h1 id={slugify(text)} {...props}>
        {children}
      </h1>
    );
  },
  h2: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
    const text = extractText(children);
    return (
      <h2 id={slugify(text)} {...props}>
        {children}
      </h2>
    );
  },
  h3: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
    const text = extractText(children);
    return (
      <h3 id={slugify(text)} {...props}>
        {children}
      </h3>
    );
  },
  h4: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
    const text = extractText(children);
    return (
      <h4 id={slugify(text)} {...props}>
        {children}
      </h4>
    );
  },
  table: ({ children, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="table-wrapper">
      <table {...props}>{children}</table>
    </div>
  ),
};

/** Recursively extract plain text from React children. */
function extractText(children: React.ReactNode): string {
  if (typeof children === 'string') return children;
  if (typeof children === 'number') return String(children);
  if (Array.isArray(children)) return children.map(extractText).join('');
  if (children && typeof children === 'object' && 'props' in children) {
    const el = children as React.ReactElement<{ children?: React.ReactNode }>;
    return extractText(el.props.children);
  }
  return '';
}

export function DocsContent({ content, className }: DocsContentProps) {
  const memoizedComponents = useMemo(() => markdownComponents, []);

  return (
    <article className={cn('docs-markdown max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={memoizedComponents}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
