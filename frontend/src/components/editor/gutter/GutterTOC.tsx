'use client';

/**
 * GutterTOC - Vertical dot TOC in the left gutter with magnet snap effect.
 *
 * Renders one dot per heading (H1/H2/H3) positioned at the heading's
 * offsetTop within the scroll container. Active heading is tracked via
 * IntersectionObserver. Neighboring dots are magnetically pulled toward
 * the active dot using framer-motion springs.
 *
 * @see tmp/note-editor-plan.md Section 2b
 * @see tmp/note-editor-ui-design.md Sections 2, 7, 8
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Editor } from '@tiptap/react';
import { motion, useReducedMotion } from 'motion/react';

import { cn } from '@/lib/utils';
import { extractHeadings } from '../AutoTOC';
import type { HeadingItem } from '../AutoTOC';

export interface GutterTOCProps {
  editor: Editor;
}

/** Dot visual sizes by heading level (inactive) */
const DOT_SIZE: Record<number, number> = { 1: 5, 2: 4, 3: 3 };
/** Dot visual sizes by heading level (active) */
const DOT_SIZE_ACTIVE: Record<number, number> = { 1: 10, 2: 8, 3: 6 };

/** Spring config for magnet + activation animations */
const SPRING_CONFIG = { stiffness: 300, damping: 25, mass: 0.8 };

/**
 * Compute magnetic offset for a dot relative to the active heading.
 * Adjacent dots pull 4px, 2-away pull 2px, 3-away pull 1px.
 */
export function getMagnetOffset(dotIndex: number, activeIndex: number): number {
  if (activeIndex < 0) return 0;
  const distance = Math.abs(dotIndex - activeIndex);
  if (distance === 0 || distance > 3) return 0;
  const direction = dotIndex > activeIndex ? -1 : 1;
  const magnitude = [0, 4, 2, 1][distance] ?? 0;
  return direction * magnitude;
}

/** Individual TOC dot with magnet animation and hover label */
function TOCDot({
  heading,
  top,
  isActive,
  activeIndex,
  dotIndex,
  onScrollTo,
  prefersReducedMotion,
}: {
  heading: HeadingItem;
  top: number;
  isActive: boolean;
  activeIndex: number;
  dotIndex: number;
  onScrollTo: (heading: HeadingItem) => void;
  prefersReducedMotion: boolean | null;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const magnetY = getMagnetOffset(dotIndex, activeIndex);

  const inactiveSize = DOT_SIZE[heading.level] ?? 4;
  const activeSize = DOT_SIZE_ACTIVE[heading.level] ?? 8;
  const dotSize = isActive ? activeSize : isHovered ? inactiveSize + 2 : inactiveSize;

  return (
    <div className="absolute left-0 w-7" style={{ top }}>
      <motion.div
        animate={{ y: prefersReducedMotion ? 0 : magnetY }}
        transition={prefersReducedMotion ? { duration: 0 } : { type: 'spring', ...SPRING_CONFIG }}
        className="relative flex items-center justify-center"
      >
        <button
          type="button"
          onClick={() => onScrollTo(heading)}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onFocus={() => setIsHovered(true)}
          onBlur={() => setIsHovered(false)}
          className={cn(
            'flex items-center justify-center',
            'w-6 h-6 cursor-pointer',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 rounded-full'
          )}
          aria-label={`Jump to: ${heading.text || 'Untitled'}`}
          aria-current={isActive ? 'true' : undefined}
        >
          <motion.span
            animate={{ width: dotSize, height: dotSize }}
            transition={
              prefersReducedMotion ? { duration: 0 } : { type: 'spring', ...SPRING_CONFIG }
            }
            className="rounded-full block"
            style={{
              backgroundColor: isActive
                ? 'var(--primary, #29A386)'
                : isHovered
                  ? 'var(--muted-foreground, #737373)'
                  : 'var(--border, #E5E2DD)',
              opacity: isActive || isHovered ? 1 : 0.6,
              boxShadow: isActive ? '0 0 0 3px rgba(41, 163, 134, 0.15)' : 'none',
            }}
          />
        </button>

        {/* Hover label */}
        {isHovered && (
          <motion.div
            initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={prefersReducedMotion ? undefined : { opacity: 0 }}
            transition={
              prefersReducedMotion ? { duration: 0 } : { duration: 0.15, ease: 'easeOut' }
            }
            className={cn(
              'absolute left-8 top-1/2 -translate-y-1/2 z-20',
              'whitespace-nowrap max-w-[180px] truncate',
              'rounded-sm border bg-background px-2 py-1',
              'text-xs font-medium text-foreground shadow-sm',
              'pointer-events-none'
            )}
          >
            {heading.text || 'Untitled'}
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export function GutterTOC({ editor }: GutterTOCProps) {
  const [headings, setHeadings] = useState<HeadingItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  // Use state (not ref) so render can read positions without lint violations
  const [positions, setPositions] = useState<Map<string, number>>(new Map());
  const prefersReducedMotion = useReducedMotion();
  const rafRef = useRef<number>(0);

  // Extract headings and rebuild position cache on editor update (debounced via rAF)
  useEffect(() => {
    if (!editor) return;

    const update = () => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const extracted = extractHeadings(editor);
        setHeadings(extracted);
        const cache = new Map<string, number>();
        for (const h of extracted) {
          const el = editor.view.dom.querySelector(
            `[data-block-id="${CSS.escape(h.id)}"]`
          ) as HTMLElement | null;
          if (el) {
            cache.set(h.id, el.offsetTop);
          }
        }
        setPositions(cache);
      });
    };

    update();
    editor.on('update', update);
    return () => {
      editor.off('update', update);
      cancelAnimationFrame(rafRef.current);
    };
  }, [editor]);

  // IntersectionObserver for active heading tracking
  useEffect(() => {
    if (!editor || headings.length === 0) return;

    const editorDom = editor.view.dom;
    const elements = headings
      .map((h) => editorDom.querySelector(`[data-block-id="${CSS.escape(h.id)}"]`))
      .filter(Boolean) as Element[];

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((e) => e.isIntersecting);
        if (visible) {
          const blockId = (visible.target as HTMLElement).getAttribute('data-block-id');
          if (blockId) setActiveId(blockId);
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [editor, headings]);

  const scrollToHeading = useCallback(
    (heading: HeadingItem) => {
      if (!editor) return;
      setActiveId(heading.id);
      editor.commands.focus();
      editor.commands.setTextSelection(heading.position);
      const el = editor.view.dom.querySelector(`[data-block-id="${CSS.escape(heading.id)}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },
    [editor]
  );

  const activeIndex = useMemo(
    () => headings.findIndex((h) => h.id === activeId),
    [headings, activeId]
  );

  if (headings.length === 0) return null;

  return (
    <nav aria-label="Table of contents" className="relative w-7 flex-shrink-0">
      {/* Connecting lines */}
      {headings.map((heading, i) => {
        if (i === 0) return null;
        const prev = headings[i - 1];
        if (!prev) return null;
        const top = positions.get(prev.id) ?? 0;
        const bottom = positions.get(heading.id) ?? 0;
        if (bottom <= top) return null;

        return (
          <div
            key={`line-${heading.id}`}
            className={cn(
              'absolute left-1/2 -translate-x-1/2',
              heading.level === 3 ? 'border-l border-dashed' : 'border-l border-solid'
            )}
            style={{
              top: top + 12,
              height: Math.max(0, bottom - top - 24),
              borderColor: 'var(--border)',
              opacity: 0.4,
            }}
          />
        );
      })}

      {/* Dots */}
      {headings.map((heading, i) => (
        <TOCDot
          key={heading.id}
          heading={heading}
          top={positions.get(heading.id) ?? 0}
          isActive={heading.id === activeId}
          activeIndex={activeIndex}
          dotIndex={i}
          onScrollTo={scrollToHeading}
          prefersReducedMotion={prefersReducedMotion}
        />
      ))}
    </nav>
  );
}
