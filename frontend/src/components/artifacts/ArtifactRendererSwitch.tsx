/**
 * ArtifactRendererSwitch — dispatch component for every artifact type.
 *
 * Phase 86: read-only previews for peek drawer + focus pane. Heavy renderers
 * are lazy-loaded via `next/dynamic` so peek open cost stays low.
 *
 * Types without a working renderer show a graceful "Preview unavailable"
 * placeholder with a link to the detail page (Phase 87+ will fill in).
 *
 * See `.planning/phases/86-peek-drawer-split-pane-lineage/86-UI-SPEC.md` §6.
 */
'use client';

import dynamic from 'next/dynamic';
import { AlertTriangle, FileQuestion, Loader2 } from 'lucide-react';
import type { ArtifactTokenKey } from '@/lib/artifact-tokens';
import { artifactLabel } from '@/lib/artifact-labels';
import { useArtifactQuery, type ArtifactData } from '@/hooks/use-artifact-query';
import { cn } from '@/lib/utils';

const NoteReadOnly = dynamic(
  () => import('./renderers/NoteReadOnly').then((m) => m.NoteReadOnly),
  { ssr: false, loading: () => <RendererSkeleton /> },
);

const IssueReadOnly = dynamic(
  () => import('./renderers/IssueReadOnly').then((m) => m.IssueReadOnly),
  { ssr: false, loading: () => <RendererSkeleton /> },
);

// Phase 87.1 Plan 04 — MD + HTML preview renderers (existing). Reused
// verbatim. HtmlRenderer carries empty-sandbox iframe + DOMPurify; preserve
// that posture (T-87.1-04-01 invariant).
const MarkdownRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/MarkdownRenderer').then(
      (m) => m.MarkdownRenderer,
    ),
  { ssr: false, loading: () => <RendererSkeleton /> },
);

const HtmlRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/HtmlRenderer').then(
      (m) => m.HtmlRenderer,
    ),
  { ssr: false, loading: () => <RendererSkeleton /> },
);

export interface ArtifactRendererSwitchProps {
  type: ArtifactTokenKey;
  id: string;
  className?: string;
}

export function ArtifactRendererSwitch({ type, id, className }: ArtifactRendererSwitchProps) {
  const { data, isLoading, error, refetch } = useArtifactQuery(type, id);

  if (isLoading) {
    return (
      <div
        className={cn('flex h-full items-center justify-center py-16 text-muted-foreground', className)}
        role="status"
        aria-busy="true"
        aria-label="Loading artifact"
      >
        <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
        <span className="text-sm">Loading…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('flex flex-col items-center gap-3 py-16 text-center', className)} role="alert">
        <AlertTriangle className="h-6 w-6 text-destructive" aria-hidden="true" />
        <p className="text-sm text-foreground">Couldn’t load artifact</p>
        <p className="max-w-sm text-xs text-muted-foreground">{error.message}</p>
        <button
          type="button"
          className="rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => refetch()}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return <EmptyState className={className} />;
  }

  if (data.placeholder) {
    return <UnsupportedState type={type} id={id} className={className} />;
  }

  return (
    <div className={cn('h-full overflow-auto', className)} data-testid="artifact-renderer">
      <Dispatch data={data} />
    </div>
  );
}

function Dispatch({ data }: { data: ArtifactData }) {
  const { type } = data;
  switch (type) {
    case 'NOTE':
      return data.note ? <NoteReadOnly note={data.note} /> : <EmptyState />;
    case 'ISSUE':
      return data.issue ? <IssueReadOnly issue={data.issue} /> : <EmptyState />;
    case 'MD':
      // Phase 87.1 Plan 04 — content fetched via useArtifactQuery → workspace
      // signed URL → fetch → text. Until content arrives we show EmptyState.
      return data.content !== undefined ? (
        <MarkdownRenderer content={data.content} />
      ) : (
        <EmptyState />
      );
    case 'HTML':
      // Phase 87.1 Plan 04 — same flow as MD; HtmlRenderer carries the empty
      // sandbox + DOMPurify posture (T-87.1-04-01 invariant).
      return data.content !== undefined ? (
        <HtmlRenderer
          content={data.content}
          filename={data.title ?? 'preview.html'}
        />
      ) : (
        <EmptyState />
      );
    case 'SPEC':
    case 'DECISION':
    case 'SKILL':
    case 'CODE':
    case 'PDF':
    case 'CSV':
    case 'IMG':
    case 'PPTX':
    case 'LINK':
      return <UnsupportedState type={type} id={data.id} />;
    default: {
      const _exhaustive: never = type;
      return <UnsupportedState type={_exhaustive} id={data.id} />;
    }
  }
}

function RendererSkeleton() {
  return (
    <div className="flex h-full items-center justify-center py-16 text-muted-foreground" role="status" aria-busy="true">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
      <span className="text-sm">Loading…</span>
    </div>
  );
}

function EmptyState({ className }: { className?: string }) {
  return (
    <div className={cn('flex flex-col items-center gap-2 py-16 text-center', className)}>
      <FileQuestion className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">No preview available.</p>
    </div>
  );
}

function UnsupportedState({
  type,
  id: _id,
  className,
}: {
  type: ArtifactTokenKey;
  id: string;
  className?: string;
}) {
  const label = artifactLabel(type, false);
  return (
    <div className={cn('flex flex-col items-center gap-2 px-6 py-16 text-center', className)}>
      <FileQuestion className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm text-foreground">Preview unavailable</p>
      <p className="max-w-sm text-xs text-muted-foreground">
        A rich preview for {label} artifacts isn’t wired up yet. Open the detail page to view this item.
      </p>
    </div>
  );
}
