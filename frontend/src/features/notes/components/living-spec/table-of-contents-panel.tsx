'use client';

/**
 * TableOfContentsPanel - h1/h2/h3 TOC with click-to-scroll
 * Phase 78: Living Specs sidebar
 *
 * Hidden entirely when note has fewer than 3 headings (UI-SPEC decision).
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import type { TocHeading } from '../../hooks/use-toc-headings';
import { TocItem } from './toc-item';

export interface TableOfContentsPanelProps {
  headings: TocHeading[];
  activeHeadingId: string | null;
}

const MIN_HEADINGS_TO_SHOW = 3;

export const TableOfContentsPanel = React.memo(function TableOfContentsPanel({
  headings,
  activeHeadingId,
}: TableOfContentsPanelProps) {
  // Hidden entirely when < 3 headings
  if (headings.length < MIN_HEADINGS_TO_SHOW) {
    return null;
  }

  function handleHeadingClick(heading: TocHeading) {
    // Find the heading element in the editor by its text content
    const editorEl = document.querySelector('.ProseMirror');
    if (!editorEl) return;

    // Look for heading elements matching the text
    const headingTag = `h${heading.level}`;
    const headingEls = editorEl.querySelectorAll(headingTag);

    for (const el of headingEls) {
      if (el.textContent?.trim() === heading.text.trim()) {
        const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches
          ? 'instant'
          : 'smooth';
        el.scrollIntoView({ behavior: behavior as ScrollBehavior, block: 'start' });
        break;
      }
    }
  }

  return (
    <nav aria-label="Note table of contents">
      {/* Section header */}
      <span className="text-[12px] font-semibold leading-[1.4] uppercase tracking-wide text-muted-foreground block mb-2">
        Table of Contents
      </span>

      {/* TOC items */}
      <div className="space-y-0.5">
        {headings.map((heading) => (
          <TocItem
            key={heading.id}
            text={heading.text}
            level={heading.level}
            isActive={activeHeadingId === heading.id}
            onClick={() => handleHeadingClick(heading)}
          />
        ))}
      </div>
    </nav>
  );
});

TableOfContentsPanel.displayName = 'TableOfContentsPanel';
