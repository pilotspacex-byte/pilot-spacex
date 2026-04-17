'use client';

/**
 * PeekDrawer — universal right-side drawer for any v3 artifact type.
 *
 * Design spec: .planning/design.md v3 §Peek Drawer
 *
 * URL-driven: reads `?peek=<type>:<id>` via `usePeekParam`. Mount once in
 * the workspace layout and any page can trigger a peek by either:
 *   - clicking an ArtifactCard (which calls onPeek)
 *   - navigating to a URL with the peek query param (deep-link support)
 *
 * Body rendering is lazy — each body (NoteBody, IssueBody, FileBody, LinkBody)
 * is loaded on demand via `next/dynamic` so the drawer itself stays in the
 * route shell, but the 11 renderers are never bundled into the initial chunk.
 *
 * Critical constraint (see `.claude/rules/tiptap.md`): the issue body must NOT
 * be wrapped in `observer()`. It delegates to `IssueEditorContent` via the
 * existing `IssueNoteContext` bridge.
 */

import * as React from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { ArrowUpRight, AlertTriangle, Loader2 } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useWorkspace } from '@/components/workspace-guard';
import { cn } from '@/lib/utils';
import type { ArtifactType } from '../ArtifactCard';
import { resolveArtifactColor } from '../ArtifactCard';
import { usePeekParam } from './usePeekParam';

// ---------------------------------------------------------------------------
// Lazy bodies — isolate heavy renderer bundles from the drawer shell
// ---------------------------------------------------------------------------

const NoteBody = dynamic(() => import('./bodies/NoteBody').then((m) => ({ default: m.NoteBody })), {
  ssr: false,
  loading: () => <BodyLoading />,
});

const IssueBody = dynamic(
  () => import('./bodies/IssueBody').then((m) => ({ default: m.IssueBody })),
  { ssr: false, loading: () => <BodyLoading /> }
);

const FileBody = dynamic(() => import('./bodies/FileBody').then((m) => ({ default: m.FileBody })), {
  ssr: false,
  loading: () => <BodyLoading />,
});

const LinkBody = dynamic(() => import('./bodies/LinkBody').then((m) => ({ default: m.LinkBody })), {
  ssr: false,
  loading: () => <BodyLoading />,
});

// ---------------------------------------------------------------------------
// Shared UI
// ---------------------------------------------------------------------------

const TYPE_LABEL: Readonly<Record<ArtifactType, string>> = {
  NOTE: 'Note',
  ISSUE: 'Issue',
  SPEC: 'Spec',
  DECISION: 'Decision',
  MD: 'Markdown',
  HTML: 'HTML',
  CODE: 'Code',
  PDF: 'PDF',
  CSV: 'CSV',
  IMG: 'Image',
  PPTX: 'Presentation',
  LINK: 'Link',
};

function BodyLoading() {
  return (
    <div
      role="status"
      aria-label="Loading preview"
      className="flex h-full items-center justify-center py-12"
    >
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>
  );
}

function BodyError({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <AlertTriangle className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm text-muted-foreground max-w-xs">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Router — dispatches to the correct body based on `peekType`
// ---------------------------------------------------------------------------

function PeekBody({
  peekType,
  peekId,
  workspaceId,
  onClose,
}: {
  peekType: ArtifactType;
  peekId: string;
  workspaceId: string;
  onClose: () => void;
}) {
  switch (peekType) {
    case 'NOTE':
    case 'SPEC':
    case 'DECISION':
      return <NoteBody workspaceId={workspaceId} noteId={peekId} variant={peekType} />;
    case 'ISSUE':
      return <IssueBody workspaceId={workspaceId} issueId={peekId} onClose={onClose} />;
    case 'MD':
    case 'HTML':
    case 'CODE':
    case 'PDF':
    case 'CSV':
    case 'IMG':
    case 'PPTX':
      return <FileBody artifactId={peekId} peekType={peekType} />;
    case 'LINK':
      return <LinkBody url={peekId} />;
    default:
      return <BodyError message="Unsupported artifact type for peek drawer." />;
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function PeekDrawer() {
  const { isOpen, peekType, peekId, closePeek } = usePeekParam();
  const router = useRouter();
  const { workspace, workspaceSlug } = useWorkspace();

  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) closePeek();
    },
    [closePeek]
  );

  const handleExpand = React.useCallback(() => {
    if (!peekType || !peekId) return;
    let href: string | null = null;
    switch (peekType) {
      case 'NOTE':
      case 'SPEC':
      case 'DECISION':
        href = `/${workspaceSlug}/notes/${peekId}`;
        break;
      case 'ISSUE':
        href = `/${workspaceSlug}/issues/${peekId}`;
        break;
      default:
        href = null;
    }
    if (href) {
      closePeek();
      router.push(href);
    }
  }, [peekType, peekId, workspaceSlug, router, closePeek]);

  const canExpand =
    peekType !== null && peekType !== 'LINK' && peekType !== 'IMG' && peekType !== 'PDF';

  // Stable aria id — Radix requires labelledby/describedby to exist
  const titleId = React.useId();
  const descriptionId = React.useId();

  return (
    <Sheet open={isOpen} onOpenChange={handleOpenChange}>
      <SheetContent
        side="right"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className={cn(
          'flex flex-col gap-0 p-0',
          // Fluid width at desktop sizes; the Sheet primitive caps mobile to 3/4 viewport.
          'sm:max-w-none w-full md:w-[640px] lg:w-[780px] xl:w-[920px]'
        )}
      >
        <SheetHeader
          className={cn(
            'shrink-0 flex-row items-center gap-3 border-b border-border/70 px-5 py-3 bg-card'
          )}
        >
          {peekType ? (
            <Badge
              variant="secondary"
              className="text-[10px] font-semibold uppercase tracking-[0.08em]"
              style={{
                backgroundColor: `color-mix(in oklab, ${resolveArtifactColor(peekType)} 14%, transparent)`,
                color: resolveArtifactColor(peekType),
              }}
            >
              {TYPE_LABEL[peekType]}
            </Badge>
          ) : null}
          <SheetTitle
            id={titleId}
            className="flex-1 min-w-0 truncate text-sm font-medium text-foreground"
          >
            Peek
          </SheetTitle>
          <SheetDescription id={descriptionId} className="sr-only">
            Quick preview of the selected artifact.
          </SheetDescription>
          {canExpand ? (
            <Button
              size="sm"
              variant="ghost"
              className="shrink-0 text-xs"
              onClick={handleExpand}
              aria-label="Open full view"
            >
              <ArrowUpRight className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
              Full view
            </Button>
          ) : null}
        </SheetHeader>

        {/* Body — scrollable region. Suspense boundary isolates lazy imports
            from the Sheet primitive's portal tree so a suspended body does
            not unmount the drawer itself. */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {isOpen && peekType && peekId ? (
            <React.Suspense fallback={<BodyLoading />}>
              <PeekBody
                peekType={peekType}
                peekId={peekId}
                workspaceId={workspace.id}
                onClose={closePeek}
              />
            </React.Suspense>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
