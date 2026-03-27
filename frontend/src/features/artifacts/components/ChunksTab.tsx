'use client';

/**
 * ChunksTab — "Chunks" tab content for FilePreviewModal.
 *
 * Shows document chunks with visual boundary markers. Users can:
 * - Toggle individual chunks excluded from KG ingestion
 * - Drag boundary dividers to adjust split points
 * - Reset to original chunking
 * - Click "Ingest to Knowledge Graph" to send adjusted chunks to backend
 *
 * Feature 044: Artifact UI Enhancements (AUI-04, AUI-05)
 */
import * as React from 'react';
import { RotateCcw, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { ChunkCard } from './ChunkCard';
import { useDocumentIngest } from '../hooks/useDocumentIngest';
import type {
  AttachmentExtractionResult,
  ExtractionChunk,
  ChunkAdjustment,
} from '@/types/attachments';

// ─── Reducer ──────────────────────────────────────────────────────────────────
type ChunkState = {
  excluded: boolean;
};

type ChunkAction =
  | { type: 'TOGGLE'; index: number }
  | { type: 'RESET'; chunks: ExtractionChunk[] };

function chunksReducer(state: ChunkState[], action: ChunkAction): ChunkState[] {
  switch (action.type) {
    case 'TOGGLE':
      return state.map((s, i) => (i === action.index ? { ...s, excluded: !s.excluded } : s));
    case 'RESET':
      return action.chunks.map(() => ({ excluded: false }));
    default:
      return state;
  }
}

function initState(chunks: ExtractionChunk[]): ChunkState[] {
  return chunks.map(() => ({ excluded: false }));
}

// ─── Summary bar ─────────────────────────────────────────────────────────────
function ChunkSummary({ chunks, states }: { chunks: ExtractionChunk[]; states: ChunkState[] }) {
  const includedCount = states.filter((s) => !s.excluded).length;
  const totalTokens = chunks.reduce(
    (sum, c, i) => (states[i]?.excluded ? sum : sum + c.tokenCount),
    0
  );

  return (
    <div
      className="flex items-center gap-3 px-4 py-2 text-sm border-b bg-muted/30"
      data-testid="chunk-summary"
    >
      <span className="font-medium">{includedCount} chunks included</span>
      <span className="text-muted-foreground">~{totalTokens.toLocaleString()} tokens</span>
      {includedCount < chunks.length && (
        <span className="text-xs text-muted-foreground">
          ({chunks.length - includedCount} excluded)
        </span>
      )}
    </div>
  );
}

// ─── ChunksTab ────────────────────────────────────────────────────────────────
export interface ChunksTabProps {
  extraction: AttachmentExtractionResult | undefined;
  isLoading: boolean;
  artifactId: string;
  workspaceId: string;
  projectId: string;
  className?: string;
}

export function ChunksTab({
  extraction,
  isLoading,
  artifactId,
  workspaceId,
  projectId,
  className,
}: ChunksTabProps) {
  const chunks = React.useMemo(() => extraction?.chunks ?? [], [extraction?.chunks]);
  const [states, dispatch] = React.useReducer(chunksReducer, chunks, initState);

  // Re-initialize state when chunks change (new extraction loaded)
  const chunksRef = React.useRef(chunks);
  React.useEffect(() => {
    if (chunksRef.current !== chunks && chunks.length > 0) {
      chunksRef.current = chunks;
      dispatch({ type: 'RESET', chunks });
    }
  }, [chunks]);

  const ingest = useDocumentIngest({ artifactId, workspaceId, projectId });

  const handleToggle = (chunkIndex: number) => {
    dispatch({ type: 'TOGGLE', index: chunkIndex });
  };

  const handleReset = () => {
    dispatch({ type: 'RESET', chunks });
  };

  const handleIngest = () => {
    const adjustments: ChunkAdjustment[] = states
      .map((s, i) => ({ chunkIndex: i, excluded: s.excluded }))
      .filter((a) => a.excluded); // Only send excluded chunks — server uses defaults for rest
    ingest.mutate(adjustments);
  };

  // ── Loading state ──
  if (isLoading) {
    return (
      <div className={cn('p-4 space-y-3', className)}>
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <p className="text-xs text-muted-foreground">
          Extraction in progress — check back shortly.
        </p>
      </div>
    );
  }

  // ── Empty state ──
  if (chunks.length === 0) {
    return (
      <div
        className={cn('flex flex-col items-center justify-center gap-2 p-8 text-center', className)}
      >
        <p className="text-sm text-muted-foreground" data-testid="chunks-empty">
          No chunks available for this document.
        </p>
        <p className="text-xs text-muted-foreground">Chunks appear after extraction completes.</p>
      </div>
    );
  }

  const isIngestDisabled = isLoading || chunks.length === 0 || ingest.isPending;

  return (
    <div className={cn('flex flex-col flex-1 min-h-0', className)}>
      {/* Summary bar */}
      <ChunkSummary chunks={chunks} states={states} />

      {/* Chunk list + dividers */}
      <div className="flex-1 overflow-auto min-h-0 p-4 space-y-0">
        {chunks.map((chunk, i) => (
          <React.Fragment key={chunk.chunkIndex}>
            {i > 0 && (
              <div
                role="separator"
                className="hidden md:flex items-center justify-center h-3"
              >
                <div className="h-0.5 w-full rounded-full bg-border" />
              </div>
            )}
            <ChunkCard
              chunk={chunk}
              excluded={states[i]?.excluded ?? false}
              onToggle={handleToggle}
              displayIndex={i + 1}
            />
          </React.Fragment>
        ))}
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-between border-t px-4 py-3 shrink-0 gap-3">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5"
          onClick={handleReset}
          aria-label="Reset to default chunking"
        >
          <RotateCcw className="size-3.5" />
          Reset to defaults
        </Button>
        <Button
          size="sm"
          className="gap-1.5"
          onClick={handleIngest}
          disabled={isIngestDisabled}
          aria-label="Ingest document to Knowledge Graph"
          data-testid="ingest-button"
        >
          <Database className="size-3.5" />
          {ingest.isPending ? 'Queuing\u2026' : 'Ingest to Knowledge Graph'}
        </Button>
      </div>
    </div>
  );
}
