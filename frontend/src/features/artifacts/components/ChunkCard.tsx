'use client';

/**
 * ChunkCard + ChunkDivider — Individual chunk display with toggle and drag boundary.
 *
 * ChunkCard: Renders one extraction chunk with heading, char/token counts, and
 *            an include/exclude toggle Switch.
 *
 * ChunkDivider: Draggable horizontal divider between two adjacent chunks.
 *               Calls onDragDelta(pixels) as the user drags up or down.
 *
 * Feature 044: Artifact UI Enhancements (AUI-04, AUI-05)
 */
import * as React from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import type { ExtractionChunk } from '@/types/attachments';

// ─── ChunkDivider ────────────────────────────────────────────────────────────

export interface ChunkDividerProps {
  /** Called with the cumulative pixel delta since drag start */
  onDragDelta: (delta: number) => void;
  className?: string;
}

/**
 * Draggable horizontal divider between adjacent chunks.
 * Uses pointer capture so drag continues outside the element.
 * Hidden on mobile (< md) — touch boundary adjustment is deferred.
 */
export function ChunkDivider({ onDragDelta, className }: ChunkDividerProps) {
  const cleanupRef = React.useRef<(() => void) | null>(null);

  React.useEffect(() => {
    return () => {
      cleanupRef.current?.();
    };
  }, []);

  const handlePointerDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    const startY = e.clientY;

    const cleanup = () => {
      document.removeEventListener('pointermove', handleMove);
      document.removeEventListener('pointerup', handleUp);
      document.removeEventListener('pointercancel', handleUp);
      cleanupRef.current = null;
    };

    const handleMove = (ev: PointerEvent) => {
      onDragDelta(ev.clientY - startY);
    };
    const handleUp = () => {
      cleanup();
    };

    document.addEventListener('pointermove', handleMove);
    document.addEventListener('pointerup', handleUp, { once: true });
    document.addEventListener('pointercancel', handleUp, { once: true });
    cleanupRef.current = cleanup;
  };

  const ARROW_STEP = 4;
  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      onDragDelta(-ARROW_STEP);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      onDragDelta(ARROW_STEP);
    }
  };

  return (
    <button
      type="button"
      role="separator"
      aria-label="Drag to adjust chunk boundary"
      aria-orientation="horizontal"
      aria-valuenow={0}
      className={cn(
        // Hidden on mobile — touch drag is a known limitation
        'hidden md:flex items-center justify-center w-full',
        'h-3 cursor-ns-resize select-none',
        'group',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded-sm',
        className
      )}
      onPointerDown={handlePointerDown}
      onKeyDown={handleKeyDown}
    >
      <div className="h-0.5 w-full rounded-full bg-border transition-colors group-hover:bg-primary/50 group-focus-visible:bg-primary/50" />
    </button>
  );
}

// ─── ChunkCard ────────────────────────────────────────────────────────────────

export interface ChunkCardProps {
  /** Extraction chunk data from the backend */
  chunk: ExtractionChunk;
  /** Whether this chunk is excluded from KG ingestion */
  excluded: boolean;
  /** Called when the include/exclude Switch is toggled */
  onToggle: (chunkIndex: number) => void;
  /** 1-based display index (chunk.chunkIndex is 0-based) */
  displayIndex: number;
  className?: string;
}

/**
 * Renders one chunk section with heading, stats, and toggle.
 * When excluded=true, the card is visually grayed out.
 */
export function ChunkCard({ chunk, excluded, onToggle, displayIndex, className }: ChunkCardProps) {
  const switchId = `chunk-toggle-${chunk.chunkIndex}`;
  const headingLabel = chunk.heading
    ? `Chunk ${displayIndex}: ${chunk.heading}`
    : `Chunk ${displayIndex}`;

  return (
    <div
      className={cn(
        'rounded-md border p-3 transition-opacity',
        excluded ? 'opacity-40' : 'opacity-100',
        className
      )}
      data-testid={`chunk-card-${chunk.chunkIndex}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              'text-sm font-medium truncate',
              excluded && 'line-through text-muted-foreground'
            )}
            data-testid={`chunk-heading-${chunk.chunkIndex}`}
          >
            {headingLabel}
          </p>
          <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
            <span data-testid={`chunk-chars-${chunk.chunkIndex}`}>
              {chunk.charCount.toLocaleString()} chars
            </span>
            <span data-testid={`chunk-tokens-${chunk.chunkIndex}`}>
              ~{chunk.tokenCount.toLocaleString()} tokens
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Label htmlFor={switchId} className="text-xs text-muted-foreground sr-only">
            {excluded ? 'Excluded from ingestion' : 'Included in ingestion'}
          </Label>
          <Switch
            id={switchId}
            checked={!excluded}
            onCheckedChange={() => onToggle(chunk.chunkIndex)}
            aria-label={`${excluded ? 'Include' : 'Exclude'} chunk ${displayIndex}`}
          />
        </div>
      </div>
    </div>
  );
}
