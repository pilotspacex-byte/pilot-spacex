'use client';

/**
 * OnThisPageTOC - Medium-style "ON THIS PAGE" right sidebar
 *
 * Positioned absolutely to the right of the document canvas.
 * Uses IntersectionObserver for active heading tracking.
 * Visible on 2xl+ screens when chat panel is closed.
 *
 * @see AutoTOC for heading extraction utilities
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Editor } from '@tiptap/react';
import { cn } from '@/lib/utils';
import type { HeadingItem } from './AutoTOC';

export interface OnThisPageTOCProps {
  /** TipTap editor instance (for scroll-to-heading) */
  editor: Editor | null;
  /** Pre-extracted headings from parent */
  headings: HeadingItem[];
  /** Additional CSS classes */
  className?: string;
}

/**
 * Medium-style sticky sidebar TOC showing heading hierarchy.
 * Returns null when fewer than 2 headings (nothing to navigate).
 */
export function OnThisPageTOC({ editor, headings, className }: OnThisPageTOCProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  // Stable key derived from heading IDs — prevents IntersectionObserver teardown/rebuild
  // on every keystroke when the headings array reference changes but content is identical.
  const headingKey = useMemo(() => headings.map((h) => h.id).join(','), [headings]);

  // IntersectionObserver for scroll-based active heading tracking
  useEffect(() => {
    if (!editor || headings.length < 2) return;

    const editorDom = editor.view.dom;
    const headingElements = headings
      .map((h) => editorDom.querySelector(`[data-block-id="${CSS.escape(h.id)}"]`))
      .filter(Boolean) as Element[];

    if (headingElements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries.find((entry) => entry.isIntersecting);
        if (visibleEntry) {
          const blockId = visibleEntry.target.getAttribute('data-block-id');
          if (blockId) setActiveId(blockId);
        }
      },
      {
        // Bias toward top 30% of viewport — marks heading active when near top
        rootMargin: '-10% 0px -70% 0px',
        threshold: 0,
      }
    );

    headingElements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- headingKey is a stable derivative of headings
  }, [editor, headingKey]);

  const scrollToHeading = useCallback(
    (heading: HeadingItem) => {
      if (!editor) return;
      setActiveId(heading.id);
      editor.commands.setTextSelection(heading.position);
      const headingDom = editor.view.dom.querySelector(
        `[data-block-id="${CSS.escape(heading.id)}"]`
      );
      if (headingDom) {
        headingDom.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    },
    [editor]
  );

  if (!editor || headings.length < 2) return null;

  return (
    <nav aria-label="On this page" className={cn('w-[180px] shrink-0', className)}>
      <div className="sticky top-8">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70 mb-3">
          On this page
        </h3>
        <ul className="space-y-0.5 border-l border-border/40">
          {headings.map((heading) => (
            <li key={heading.id}>
              <button
                type="button"
                onClick={() => scrollToHeading(heading)}
                className={cn(
                  'block w-full text-left text-[13px] leading-snug py-1 transition-colors',
                  'hover:text-foreground border-l-2 -ml-px',
                  heading.level === 1 && 'pl-3',
                  heading.level === 2 && 'pl-5',
                  heading.level === 3 && 'pl-7',
                  activeId === heading.id
                    ? 'text-primary border-primary font-medium'
                    : 'text-muted-foreground border-transparent'
                )}
              >
                <span className="line-clamp-2">{heading.text || 'Untitled'}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}

export default OnThisPageTOC;
