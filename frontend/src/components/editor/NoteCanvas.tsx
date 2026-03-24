'use client';

/**
 * NoteCanvas - Entry point for note editing.
 *
 * Phase 40 migration: Default export now routes to MonacoNoteEditor via
 * dynamic import (SSR disabled). The original TipTap-based NoteCanvasLayout
 * is preserved for rollback via the named `NoteCanvasLegacy` export.
 *
 * The NoteCanvasLayout (TipTap) includes ChatView, sidebar panels, metadata,
 * breadcrumbs, etc. MonacoNoteEditor is a focused editor component — the
 * surrounding chrome (header, sidebar, ChatView) remains in the page that
 * consumes this component.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react';
import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';
import type { GhostTextFetcher } from '@/features/editor/hooks/useMonacoGhostText';
import type { MemberFetcher } from '@/features/editor/hooks/useMonacoSlashCmd';

// Original TipTap-based exports (preserved for rollback and utilities)
export { extractFirstHeadingText } from './NoteCanvasEditor';
export type { NoteCanvasProps } from './NoteCanvasEditor';

// Legacy TipTap layout — keep for rollback during Phase 40 migration
export { NoteCanvasLayout as NoteCanvasLegacy } from './NoteCanvasLayout';

/** Error boundary for Monaco editor load failures. */
class EditorErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[NoteCanvas] Editor failed to load:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
          <p className="text-sm text-muted-foreground">
            Editor failed to load. Refresh the page to try again.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * MonacoNoteEditor loaded via dynamic import (SSR disabled).
 * Falls back to skeleton during load, shows error message on failure.
 */
const MonacoNoteEditor = dynamic(() => import('@/features/editor/MonacoNoteEditor'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

/**
 * NoteCanvasMonaco - Wrapper that maps NoteCanvasProps to MonacoNoteEditor props.
 *
 * Adapts the rich NoteCanvasProps interface to the simpler MonacoNoteEditor
 * props, handling the content serialization (JSONContent -> markdown string).
 */
interface NoteCanvasMonacoProps {
  noteId: string;
  initialContent?: string;
  onChange?: (content: string) => void;
  isReadOnly?: boolean;
  className?: string;
  /** Ghost text AI completion fetcher */
  ghostTextFetcher?: GhostTextFetcher;
  /** Workspace member fetcher for @ mentions */
  memberFetcher?: MemberFetcher;
}

function NoteCanvasMonaco({
  noteId,
  initialContent = '',
  onChange,
  isReadOnly = false,
  className,
  ghostTextFetcher,
  memberFetcher,
}: NoteCanvasMonacoProps) {
  return (
    <div className={className}>
      <EditorErrorBoundary>
        <MonacoNoteEditor
          noteId={noteId}
          initialContent={initialContent}
          onChange={onChange}
          isReadOnly={isReadOnly}
          ghostTextFetcher={ghostTextFetcher}
          memberFetcher={memberFetcher}
          className="h-full"
        />
      </EditorErrorBoundary>
    </div>
  );
}

// Phase 40 migration complete: Monaco is the default editor.
// Legacy TipTap layout available via NoteCanvasLegacy named export (line 25).
// Set NEXT_PUBLIC_EDITOR_ENGINE=tiptap to fall back to TipTap-based editor.
export { NoteCanvasMonaco };
export { NoteCanvasMonaco as NoteCanvas };

// Lazy-load legacy TipTap layout only when feature flag is set
const NoteCanvasLegacyDynamic = dynamic(
  () => import('./NoteCanvasLayout').then((mod) => ({ default: mod.NoteCanvasLayout })),
  { ssr: false, loading: () => <Skeleton className="h-full w-full" /> }
);

const DefaultExport =
  process.env.NEXT_PUBLIC_EDITOR_ENGINE === 'tiptap' ? NoteCanvasLegacyDynamic : NoteCanvasMonaco;

export default DefaultExport;
