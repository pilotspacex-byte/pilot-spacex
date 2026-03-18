'use client';

import ReactMarkdown, { type Components } from 'react-markdown';
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

/** Build heading components with deduplicated IDs matching extractHeadings(). */
function buildMarkdownComponents(slugCounts: Map<string, number>): Components {
  function createHeading(Tag: 'h1' | 'h2' | 'h3' | 'h4') {
    const HeadingComponent: Components['h1'] = ({ node: _node, children, ...props }) => {
      const text = extractText(children);
      const base = slugifyHeading(text);
      const count = slugCounts.get(base) ?? 0;
      slugCounts.set(base, count + 1);
      const id = count === 0 ? base : `${base}-${count}`;
      return (
        <Tag id={id} {...props}>
          {children}
        </Tag>
      );
    };
    HeadingComponent.displayName = `DocsHeading(${Tag})`;
    return HeadingComponent;
  }

  return {
    h1: createHeading('h1'),
    h2: createHeading('h2'),
    h3: createHeading('h3'),
    h4: createHeading('h4'),
    table: ({ node: _node, children, ...props }) => (
      <div className="table-wrapper">
        <table {...props}>{children}</table>
      </div>
    ),
  };
}

export function DocsContent({ content, className }: DocsContentProps) {
  // Fresh slug counter + components each render so deduplicated IDs
  // (e.g. "setup", "setup-1", "setup-2") match extractHeadings() output.
  const components = buildMarkdownComponents(new Map());

  return (
    <article className={cn('chat-markdown docs-markdown max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
