'use client';

import { useEffect, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

interface TocHeading {
  id: string;
  text: string;
  level: number;
}

interface TableOfContentsProps {
  content: string;
  className?: string;
}

/** Extract headings from markdown text via regex. */
function extractHeadings(markdown: string): TocHeading[] {
  const headings: TocHeading[] = [];
  const lines = markdown.split('\n');

  for (const line of lines) {
    // Skip code blocks
    if (line.trim().startsWith('```')) continue;

    const match = line.match(/^(#{1,4})\s+(.+)$/);
    if (match?.[1] && match[2]) {
      const level = match[1].length;
      const text = match[2].replace(/[`*_~]/g, '').trim();
      const id = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-');
      headings.push({ id, text, level });
    }
  }

  return headings;
}

export function TableOfContents({ content, className }: TableOfContentsProps) {
  const headings = useMemo(() => extractHeadings(content), [content]);
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: '-80px 0px -70% 0px', threshold: 0 }
    );

    for (const heading of headings) {
      const el = document.getElementById(heading.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [headings]);

  if (headings.length < 3) return null;

  const minLevel = Math.min(...headings.map((h) => h.level));

  return (
    <nav className={cn('w-52 shrink-0', className)} aria-label="Table of contents">
      <div className="sticky top-6">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          On this page
        </h4>
        <ul className="space-y-1 text-sm">
          {headings.map((heading) => (
            <li key={heading.id}>
              <a
                href={`#${heading.id}`}
                className={cn(
                  'block rounded py-1 pr-2 text-foreground/60 transition-colors hover:text-foreground',
                  heading.id === activeId && 'font-medium text-primary'
                )}
                style={{ paddingLeft: `${(heading.level - minLevel) * 12 + 8}px` }}
              >
                {heading.text}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
