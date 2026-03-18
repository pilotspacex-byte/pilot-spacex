'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import type { TocHeading } from '../lib/markdown-headings';

interface TableOfContentsProps {
  headings: TocHeading[];
  className?: string;
}

export function TableOfContents({ headings, className }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    if (headings.length < 3) return;

    const visibleIds = new Set<string>();

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            visibleIds.add(entry.target.id);
          } else {
            visibleIds.delete(entry.target.id);
          }
        }
        // Pick the first heading in document order that is visible
        const first = headings.find((h) => visibleIds.has(h.id));
        if (first) setActiveId(first.id);
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
