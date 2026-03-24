'use client';

/**
 * PptxThumbnailStrip — Vertical sidebar with lazy-rendered slide thumbnails.
 *
 * Renders a scrollable vertical list of slide thumbnails. Each thumbnail is
 * lazy-rendered using IntersectionObserver — only visible thumbnails plus a
 * 2-slide buffer ahead/behind are rendered to a small canvas via PptxViewJS.
 *
 * Once a thumbnail is rendered it is cached and not re-rendered on scroll.
 *
 * Clicking a thumbnail calls onNavigate(slideIndex) to navigate the main view.
 * The active slide thumbnail is highlighted with a primary color ring border.
 * When currentSlide changes (via external navigation), the strip auto-scrolls
 * to keep the active thumbnail visible.
 */

import * as React from 'react';
import { PPTXViewer } from 'pptxviewjs';
import { cn } from '@/lib/utils';

export interface PptxThumbnailStripProps {
  /** Raw PPTX binary data */
  content: ArrayBuffer;
  /** Total number of slides (from onSlideCountKnown) */
  slideCount: number;
  /** 0-indexed currently active slide */
  currentSlide: number;
  /** Called when user clicks a thumbnail to navigate */
  onNavigate: (index: number) => void;
}

/** Thumbnail canvas width in pixels */
const THUMB_WIDTH = 120;
/** Default 16:9 aspect ratio for height calculation */
const DEFAULT_ASPECT = 16 / 9;
/** Thumbnail height based on default aspect ratio */
const THUMB_HEIGHT = Math.round(THUMB_WIDTH / DEFAULT_ASPECT);

/**
 * Individual thumbnail slot — observes visibility and renders its canvas
 * once it enters the viewport (+ 200px margin).
 */
function ThumbnailSlot({
  index,
  isActive,
  onClick,
  viewerRef,
  renderedRef,
}: {
  index: number;
  isActive: boolean;
  onClick: () => void;
  viewerRef: React.MutableRefObject<PPTXViewer | null>;
  renderedRef: React.MutableRefObject<Set<number>>;
}) {
  const wrapperRef = React.useRef<HTMLDivElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const [isVisible, setIsVisible] = React.useState(false);
  const [isRendered, setIsRendered] = React.useState(false);

  // IntersectionObserver — triggers render when slot enters viewport
  React.useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          setIsVisible(true);
          // Once visible, no need to keep observing
          observer.disconnect();
        }
      },
      { rootMargin: '200px 0px' }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Render thumbnail canvas once viewer is ready and slot is visible
  React.useEffect(() => {
    if (!isVisible) return;
    if (renderedRef.current.has(index)) {
      setIsRendered(true);
      return;
    }

    const viewer = viewerRef.current;
    const canvas = canvasRef.current;
    if (!viewer || !canvas) return;

    void viewer
      .renderSlide(index, canvas)
      .then(() => {
        renderedRef.current.add(index);
        setIsRendered(true);
      })
      .catch(() => {
        // Mark as rendered to avoid infinite retries; placeholder shows slide number
        renderedRef.current.add(index);
        setIsRendered(true);
      });
  }, [isVisible, index, viewerRef, renderedRef]);

  return (
    <div
      ref={wrapperRef}
      tabIndex={-1}
      aria-hidden="true"
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        'relative cursor-pointer rounded overflow-hidden transition-all duration-150',
        isActive ? 'ring-2 ring-primary shadow-sm' : 'ring-1 ring-border/50 hover:ring-border'
      )}
      style={{ width: THUMB_WIDTH, height: THUMB_HEIGHT }}
    >
      {/* Placeholder — shown before render completes */}
      {!isRendered && (
        <div
          className="absolute inset-0 bg-muted flex items-center justify-center"
          aria-hidden="true"
        >
          <span className="text-xs text-muted-foreground">{index + 1}</span>
        </div>
      )}
      {/* Canvas — rendered by PptxViewJS */}
      <canvas
        ref={canvasRef}
        width={THUMB_WIDTH}
        height={THUMB_HEIGHT}
        className={cn('block', isRendered ? 'opacity-100' : 'opacity-0')}
        aria-hidden="true"
      />
    </div>
  );
}

export function PptxThumbnailStrip({
  content,
  slideCount,
  currentSlide,
  onNavigate,
}: PptxThumbnailStripProps) {
  const viewerRef = React.useRef<PPTXViewer | null>(null);
  /** Tracks which slide indices have already been rendered to avoid re-renders */
  const renderedRef = React.useRef<Set<number>>(new Set());
  const [isReady, setIsReady] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);
  const activeSlotRef = React.useRef<HTMLDivElement>(null);

  // Parse PPTX once on mount using a dedicated viewer instance for thumbnails.
  // This is separate from PptxRenderer's viewer instance — each viewer parses
  // its own copy of the file to avoid cross-instance state issues.
  React.useEffect(() => {
    if (!content || slideCount === 0) return;

    let cancelled = false;

    // Reset cached state when content changes (new deck loaded)
    renderedRef.current = new Set();
    setIsReady(false);
    setError(null);

    async function init() {
      try {
        // Create a hidden off-screen canvas for the thumbnail viewer
        const offscreenCanvas = document.createElement('canvas');
        offscreenCanvas.width = THUMB_WIDTH;
        offscreenCanvas.height = THUMB_HEIGHT;

        const viewer = new PPTXViewer({ canvas: offscreenCanvas });
        if (cancelled) return;

        viewerRef.current = viewer;
        await viewer.loadFile(content);

        if (!cancelled) {
          setIsReady(true);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load thumbnails');
        }
      }
    }

    void init();

    return () => {
      cancelled = true;
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, [content, slideCount]);

  // Auto-scroll and focus active slide when currentSlide changes
  React.useEffect(() => {
    if (!activeSlotRef.current) return;
    activeSlotRef.current.focus({ preventScroll: true });
    activeSlotRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [currentSlide]);

  if (error) {
    return (
      <div className="flex items-center justify-center p-4 w-[140px]">
        <p className="text-xs text-destructive text-center">Failed to load thumbnails</p>
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      className="flex flex-col overflow-y-auto bg-muted/20 py-2"
      style={{ width: 156 }}
      aria-label="Slide thumbnails"
      role="listbox"
      aria-orientation="vertical"
    >
      {Array.from({ length: slideCount }, (_, i) => {
        const active = i === currentSlide;
        return (
          <div
            key={i}
            ref={active ? activeSlotRef : undefined}
            className={cn(
              'flex items-center gap-2 px-2.5 py-1.5 cursor-pointer transition-colors',
              active ? 'bg-primary/8' : 'hover:bg-muted/60'
            )}
            role="option"
            aria-selected={active}
            aria-label={`Slide ${i + 1}`}
            tabIndex={active ? 0 : -1}
            onClick={() => onNavigate(i)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onNavigate(i);
              } else if (e.key === 'ArrowDown' && i < slideCount - 1) {
                e.preventDefault();
                onNavigate(i + 1);
              } else if (e.key === 'ArrowUp' && i > 0) {
                e.preventDefault();
                onNavigate(i - 1);
              }
            }}
          >
            <span
              className={cn(
                'text-[10px] tabular-nums select-none w-4 text-right shrink-0',
                active ? 'text-primary font-semibold' : 'text-muted-foreground'
              )}
            >
              {i + 1}
            </span>
            {isReady ? (
              <ThumbnailSlot
                index={i}
                isActive={active}
                onClick={() => onNavigate(i)}
                viewerRef={viewerRef}
                renderedRef={renderedRef}
              />
            ) : (
              <div
                className="rounded-sm bg-muted animate-pulse"
                style={{ width: THUMB_WIDTH, height: THUMB_HEIGHT }}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
