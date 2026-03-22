'use client';

import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

export interface TocHeading {
  id: string;
  text: string;
  level: 1 | 2 | 3;
}

interface DocxTocSidebarProps {
  headings: TocHeading[];
  onHeadingClick: (id: string) => void;
  className?: string;
}

/**
 * DocxTocSidebar — collapsible table of contents sidebar for DOCX previews.
 *
 * Renders a vertical list of h1/h2/h3 headings extracted from the rendered
 * document. Each heading is a button that calls `onHeadingClick` with the
 * heading's unique ID, triggering smooth-scroll navigation in the parent.
 *
 * Indentation:
 * - h1: no indent (font-medium)
 * - h2: pl-3 (12px)
 * - h3: pl-6 (24px)
 */
export function DocxTocSidebar({ headings, onHeadingClick, className }: DocxTocSidebarProps) {
  return (
    <aside
      className={cn(
        'w-56 shrink-0 border-r border-border flex flex-col h-full bg-background',
        className
      )}
      aria-label="Table of contents"
    >
      <div className="px-3 py-2 border-b border-border">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Contents
        </p>
      </div>

      <ScrollArea className="flex-1">
        <nav className="px-2 py-2">
          {headings.length === 0 ? (
            <p className="text-xs text-muted-foreground px-2 py-3">No headings found</p>
          ) : (
            <ul className="space-y-0.5">
              {headings.map((heading) => (
                <li key={heading.id}>
                  <button
                    type="button"
                    onClick={() => onHeadingClick(heading.id)}
                    className={cn(
                      'w-full text-left text-sm text-muted-foreground',
                      'hover:text-foreground hover:bg-accent/50',
                      'transition-colors cursor-pointer rounded px-2 py-1 truncate block',
                      heading.level === 1 && 'font-medium',
                      heading.level === 2 && 'pl-3',
                      heading.level === 3 && 'pl-6 text-xs'
                    )}
                    title={heading.text}
                  >
                    {heading.text}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>
      </ScrollArea>
    </aside>
  );
}
