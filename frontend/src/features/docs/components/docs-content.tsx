'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { cn } from '@/lib/utils';
import { slugifyHeading } from '../lib/markdown-headings';

interface DocsContentProps {
  content: string;
  className?: string;
}

const remarkPlugins = [remarkGfm];
const rehypePlugins = [rehypeHighlight];

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

/** Factory for heading components that inject IDs for TOC anchor linking. */
function createHeading(Tag: 'h1' | 'h2' | 'h3' | 'h4') {
  const HeadingComponent = ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
    const text = extractText(children);
    return (
      <Tag id={slugifyHeading(text)} {...props}>
        {children}
      </Tag>
    );
  };
  HeadingComponent.displayName = `DocsHeading(${Tag})`;
  return HeadingComponent;
}

const markdownComponents = {
  h1: createHeading('h1'),
  h2: createHeading('h2'),
  h3: createHeading('h3'),
  h4: createHeading('h4'),
  table: ({ children, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="table-wrapper">
      <table {...props}>{children}</table>
    </div>
  ),
};

export function DocsContent({ content, className }: DocsContentProps) {
  return (
    <article className={cn('chat-markdown docs-markdown max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
