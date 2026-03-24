'use client';

/**
 * PptxRenderer — Canvas-based PPTX slide renderer using PptxViewJS.
 *
 * Controlled component: the parent (FilePreviewModal) owns `currentSlide` state.
 * This component notifies the parent when the slide count is known and when
 * the user triggers navigation (so the parent can update state and re-render).
 *
 * Phase 5 annotation contract:
 *   - `currentSlide` (prop, 0-indexed): which slide to display
 *   - `onSlideCountKnown(total)`: called after PPTX is parsed with total slide count
 *   - `onNavigate(index)`: called when user navigates (currently unused internally —
 *     parent controls the slide via prop); reserved for Phase 5 annotation overlay
 *
 * Canvas sizing: fills container width while preserving 16:9 aspect ratio by default.
 * ResizeObserver re-renders the current slide when container dimensions change.
 */

import * as React from 'react';
import { PPTXViewer } from 'pptxviewjs';

export interface PptxRendererProps {
  /** Raw PPTX binary data */
  content: ArrayBuffer;
  /** 0-indexed slide to display */
  currentSlide: number;
  /** Called once after PPTX is parsed with the total number of slides */
  onSlideCountKnown: (total: number) => void;
  /** Called when the component wants to navigate to a specific slide (reserved for Phase 5) */
  onNavigate: (index: number) => void;
}

/** Default PPTX aspect ratio (widescreen 16:9). Used before slide dimensions are known. */
const DEFAULT_ASPECT = 16 / 9;

export function PptxRenderer({ content, currentSlide, onSlideCountKnown }: PptxRendererProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const viewerRef = React.useRef<PPTXViewer | null>(null);
  const loadedRef = React.useRef(false);
  const latestSlideRef = React.useRef(currentSlide);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Track canvas dimensions for resize
  const [canvasWidth, setCanvasWidth] = React.useState(0);

  // --- Initialise viewer and load file whenever content changes ---
  React.useEffect(() => {
    if (!canvasRef.current) return;

    let cancelled = false;

    async function init() {
      try {
        setIsLoading(true);
        setError(null);
        loadedRef.current = false;

        // Destroy previous viewer instance before creating a new one
        if (viewerRef.current) {
          viewerRef.current.destroy();
          viewerRef.current = null;
        }

        const viewer = new PPTXViewer({ canvas: canvasRef.current });
        if (cancelled) return;

        viewerRef.current = viewer;

        await viewer.loadFile(content);
        if (cancelled) return;

        loadedRef.current = true;

        const slideCount = viewer.getSlideCount();
        onSlideCountKnown(slideCount);

        // Render the latest slide (may have changed during async load)
        await viewer.renderSlide(latestSlideRef.current, canvasRef.current ?? undefined);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load presentation');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void init();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content]); // Re-run only when content changes; onSlideCountKnown is stable

  // Keep latestSlideRef in sync with prop so load effect reads correct value
  React.useEffect(() => {
    latestSlideRef.current = currentSlide;
  }, [currentSlide]);

  // --- Re-render when currentSlide prop changes (after initial load) ---
  React.useEffect(() => {
    if (!loadedRef.current || !viewerRef.current || !canvasRef.current) return;

    void viewerRef.current.renderSlide(currentSlide, canvasRef.current ?? undefined);
  }, [currentSlide]);

  // --- ResizeObserver: keep canvas width matching container, maintain aspect ratio ---
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const width = Math.floor(entry.contentRect.width);
      if (width > 0) setCanvasWidth(width);
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Re-render slide when canvas dimensions change (after load)
  React.useEffect(() => {
    if (!loadedRef.current || !viewerRef.current || !canvasRef.current || canvasWidth === 0) return;
    void viewerRef.current.renderSlide(currentSlide, canvasRef.current ?? undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasWidth]);

  // --- Cleanup on unmount ---
  React.useEffect(() => {
    return () => {
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, []);

  const canvasHeight = canvasWidth > 0 ? Math.round(canvasWidth / DEFAULT_ASPECT) : 0;

  if (error) {
    return (
      <div className="flex items-center justify-center p-8 text-center">
        <p className="text-sm text-destructive">Failed to load presentation: {error}</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full p-4">
      {isLoading && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-background/80 z-10 rounded-lg"
          role="status"
          aria-label="Loading presentation"
        >
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
        </div>
      )}
      <div className="rounded-lg overflow-hidden shadow-md ring-1 ring-border/40 bg-white dark:bg-neutral-900">
        <canvas
          ref={canvasRef}
          width={canvasWidth || undefined}
          height={canvasHeight || undefined}
          className="block w-full"
          aria-label={`Presentation slide ${currentSlide + 1}`}
        />
      </div>
    </div>
  );
}
