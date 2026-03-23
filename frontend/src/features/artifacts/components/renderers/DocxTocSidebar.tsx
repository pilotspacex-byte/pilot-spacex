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
        'w-56 shrink-0 border-r border-border/60 flex flex-col h-full bg-muted/10',
        className
      )}
      aria-label="Table of contents"
    >
      <div className="px-3 py-2 border-b border-border/60 bg-muted/20">
        <p className="text-[10px] font-semibold text-muted-foreground/70 uppercase tracking-wider">
          Contents
        </p>
      </div>

      <ScrollArea className="flex-1">
        <nav className="px-1.5 py-2">
          {headings.length === 0 ? (
            <p className="text-xs text-muted-foreground/60 px-2 py-4 text-center">
              No headings found
            </p>
          ) : (
            <ul className="space-y-px">
              {headings.map((heading) => (
                <li key={heading.id}>
                  <button
                    type="button"
                    onClick={() => onHeadingClick(heading.id)}
                    className={cn(
                      'w-full text-left text-[13px] text-muted-foreground leading-snug',
                      'hover:text-foreground hover:bg-accent/60 active:bg-accent/80',
                      'transition-colors cursor-pointer rounded-md px-2 py-1.5 truncate block',
                      heading.level === 1 && 'font-medium text-foreground/80',
                      heading.level === 2 && 'pl-4',
                      heading.level === 3 && 'pl-7 text-xs text-muted-foreground/70'
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
