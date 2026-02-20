'use client';

/**
 * AutoTOC - Automatic Table of Contents from editor headings
 * Supports two variants:
 * - "horizontal": Sticky pills at top of document (UI Spec v3.3 / Prototype v4)
 * - "tree": Nested tree structure in sidebar (legacy)
 *
 * @see DD-013 Note-First Collaborative Workspace
 * @see UI Spec v3.3 Section 7 - Note Canvas
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Editor } from '@tiptap/react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import { Hash, ChevronRight, FileText } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface AutoTOCProps {
  /** TipTap editor instance */
  editor: Editor | null;
  /** Display variant: "horizontal" pills or "tree" nested */
  variant?: 'horizontal' | 'tree';
  /** CSS class for container */
  className?: string;
}

export interface HeadingItem {
  id: string;
  level: 1 | 2 | 3;
  text: string;
  position: number;
}

/**
 * Extract headings from editor content
 */
export function extractHeadings(editor: Editor): HeadingItem[] {
  const headings: HeadingItem[] = [];

  editor.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      const level = node.attrs.level as 1 | 2 | 3;
      if (level >= 1 && level <= 3) {
        const text = node.textContent;
        const id = node.attrs.blockId ?? `heading-${pos}`;
        headings.push({
          id,
          level,
          text,
          position: pos,
        });
      }
    }
    return true;
  });

  return headings;
}

/**
 * Build nested heading structure (for tree variant)
 */
interface NestedHeading extends HeadingItem {
  children: NestedHeading[];
}

function buildNestedHeadings(headings: HeadingItem[]): NestedHeading[] {
  const result: NestedHeading[] = [];
  const stack: NestedHeading[] = [];

  headings.forEach((heading) => {
    const nested: NestedHeading = { ...heading, children: [] };

    while (stack.length > 0) {
      const last = stack[stack.length - 1];
      if (last && last.level >= heading.level) {
        stack.pop();
      } else {
        break;
      }
    }

    if (stack.length === 0) {
      result.push(nested);
    } else {
      const parent = stack[stack.length - 1];
      if (parent) {
        parent.children.push(nested);
      }
    }

    stack.push(nested);
  });

  return result;
}

/**
 * Single TOC item for tree variant
 */
function TOCTreeItem({
  heading,
  isActive,
  onClick,
  depth = 0,
}: {
  heading: NestedHeading;
  isActive: boolean;
  onClick: () => void;
  depth?: number;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = heading.children.length > 0;

  return (
    <div>
      <button
        onClick={onClick}
        className={cn(
          'group flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-sm',
          'transition-colors hover:bg-accent',
          isActive && 'bg-accent text-accent-foreground font-medium',
          !isActive && 'text-muted-foreground'
        )}
        style={{ paddingLeft: `${(depth + 1) * 8}px` }}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="flex h-4 w-4 items-center justify-center shrink-0 hover:text-foreground"
          >
            <ChevronRight
              className={cn('h-3 w-3 transition-transform', isExpanded && 'rotate-90')}
            />
          </button>
        )}
        {!hasChildren && <span className="w-4" />}
        <Hash
          className={cn(
            'h-3 w-3 shrink-0 transition-colors',
            heading.level === 1 && 'text-primary',
            heading.level === 2 && 'text-muted-foreground',
            heading.level === 3 && 'text-muted-foreground/60'
          )}
        />
        <span className="truncate">{heading.text || 'Untitled'}</span>
      </button>

      <AnimatePresence initial={false}>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {heading.children.map((child) => (
              <TOCTreeItem
                key={child.id}
                heading={child}
                isActive={false}
                onClick={() => {}}
                depth={depth + 1}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Empty state when no headings
 */
function EmptyState({ variant }: { variant: 'horizontal' | 'tree' }) {
  if (variant === 'horizontal') {
    // Don't show empty state for horizontal - just hide TOC
    return null;
  }

  return (
    <div className="flex flex-col items-center justify-center p-4 text-center">
      <FileText className="h-8 w-8 text-muted-foreground/30 mb-2" />
      <p className="text-xs text-muted-foreground">Add headings to see outline</p>
    </div>
  );
}

/**
 * Horizontal TOC Pills - UI Spec v3.3 / Prototype v4 aligned
 */
function HorizontalTOC({
  headings,
  activeId,
  onHeadingClick,
  className,
}: {
  headings: HeadingItem[];
  activeId: string | null;
  onHeadingClick: (heading: HeadingItem) => void;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Only show top-level headings (H1, H2) for cleaner horizontal display
  const displayHeadings = headings.filter((h) => h.level <= 2);

  if (displayHeadings.length === 0) {
    return null;
  }

  return (
    <div ref={containerRef} className={cn('toc-container', className)}>
      <div className="toc-label">Contents</div>
      <div className="toc-items">
        {displayHeadings.map((heading) => (
          <button
            key={heading.id}
            onClick={() => onHeadingClick(heading)}
            className={cn('toc-item', activeId === heading.id && 'active')}
          >
            {heading.text || 'Untitled'}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Tree TOC - Legacy sidebar variant
 */
function TreeTOC({
  nestedHeadings,
  activeId,
  onHeadingClick,
  className,
}: {
  nestedHeadings: NestedHeading[];
  activeId: string | null;
  onHeadingClick: (heading: HeadingItem) => void;
  className?: string;
}) {
  return (
    <div className={cn('py-2', className)}>
      {nestedHeadings.map((heading) => (
        <TOCTreeItem
          key={heading.id}
          heading={heading}
          isActive={activeId === heading.id}
          onClick={() => onHeadingClick(heading)}
        />
      ))}
    </div>
  );
}

/**
 * AutoTOC component - supports horizontal pills and tree variants
 */
export const AutoTOC = observer(function AutoTOC({
  editor,
  variant = 'horizontal',
  className,
}: AutoTOCProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [headings, setHeadings] = useState<HeadingItem[]>([]);

  // Extract headings on content change
  useEffect(() => {
    if (!editor) return;

    const updateHeadings = () => {
      const extracted = extractHeadings(editor);
      setHeadings(extracted);
    };

    updateHeadings();
    editor.on('update', updateHeadings);

    return () => {
      editor.off('update', updateHeadings);
    };
  }, [editor]);

  // Build nested structure for tree variant
  const nestedHeadings = useMemo(() => buildNestedHeadings(headings), [headings]);

  // Scroll to heading
  const scrollToHeading = useCallback(
    (heading: HeadingItem) => {
      if (!editor) return;

      setActiveId(heading.id);

      // Focus the editor at the heading position
      editor.commands.focus();
      editor.commands.setTextSelection(heading.position);

      // Scroll the heading into view
      const editorDom = editor.view.dom;
      const headingDom = editorDom.querySelector(`[data-block-id="${heading.id}"]`);
      if (headingDom) {
        headingDom.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    },
    [editor]
  );

  // Set up IntersectionObserver for scroll-based active state (horizontal variant)
  useEffect(() => {
    if (!editor || variant !== 'horizontal' || headings.length === 0) return;

    const editorDom = editor.view.dom;
    const headingElements = headings
      .map((h) => editorDom.querySelector(`[data-block-id="${h.id}"]`))
      .filter(Boolean) as Element[];

    if (headingElements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the first visible heading
        const visibleEntry = entries.find((entry) => entry.isIntersecting);
        if (visibleEntry) {
          const blockId = visibleEntry.target.getAttribute('data-block-id');
          if (blockId) {
            setActiveId(blockId);
          }
        }
      },
      {
        rootMargin: '-20% 0px -60% 0px', // Bias toward top of viewport
        threshold: 0,
      }
    );

    headingElements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [editor, variant, headings]);

  if (!editor) {
    return null;
  }

  if (headings.length === 0) {
    return <EmptyState variant={variant} />;
  }

  if (variant === 'horizontal') {
    return (
      <HorizontalTOC
        headings={headings}
        activeId={activeId}
        onHeadingClick={scrollToHeading}
        className={className}
      />
    );
  }

  return (
    <TreeTOC
      nestedHeadings={nestedHeadings}
      activeId={activeId}
      onHeadingClick={scrollToHeading}
      className={className}
    />
  );
});

export default AutoTOC;
