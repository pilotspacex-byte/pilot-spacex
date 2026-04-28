/**
 * ArtifactPeekDrawer — global right-side peek for any artifact.
 *
 * URL-driven (`?peek=&peekType=`). Mounted once at the workspace layout.
 * - 680px wide, 16px left-edge radius, 18% scrim.
 * - Esc closes; ⌘. escalates to split-pane focus.
 * - Header: lineage breadcrumb, type badge, short-form ID (click to copy),
 *   expand, pin (placeholder), more menu, close.
 *
 * See `.planning/phases/86-peek-drawer-split-pane-lineage/86-UI-SPEC.md` §2.
 */
'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { Copy, Maximize2, MoreHorizontal, Pin, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { copyToClipboard } from '@/lib/copy-context';
import { useArtifactPeekState } from '@/hooks/use-artifact-peek-state';
import { useArtifactQuery } from '@/hooks/use-artifact-query';
import { useViewport } from '@/hooks/useViewport';
import { trackEvent } from '@/lib/analytics';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ArtifactTypeBadge } from './ArtifactTypeBadge';
import { ArtifactRendererSwitch } from './ArtifactRendererSwitch';
import { LineageChip } from './LineageChip';
import { VersionHistoryChip } from './VersionHistoryChip';
import { SkillFilePreview } from '@/features/skills/components/SkillFilePreview';
import type { VersionHistoryEntry } from '@/features/ai/proposals/types';

function shortId(id: string): string {
  if (id.length <= 9) return id;
  return `${id.slice(0, 4)}…${id.slice(-4)}`;
}

export function ArtifactPeekDrawer() {
  const {
    peekId,
    peekType,
    isPeekOpen,
    isSkillFilePeek,
    skillFile,
    closePeek,
    escalate,
  } = useArtifactPeekState();
  const params = useParams<{ workspaceSlug?: string }>();
  const workspaceSlug = params?.workspaceSlug ?? '';
  // Phase 94 Plan 02 (MIG-03) — bottom-sheet variant @ <768px.
  const { peekMode } = useViewport();
  const isBottomSheet = peekMode === 'bottom-sheet';
  // Phase 91 — skill-file peeks use a separate body component (SkillFilePreview)
  // and do NOT participate in the artifact-resolution query. We still call
  // useArtifactQuery (with both args nulled when isSkillFilePeek) so the hook
  // ordering stays stable — TanStack Query short-circuits on null inputs.
  const { data } = useArtifactQuery(
    isPeekOpen && !isSkillFilePeek ? peekType : null,
    isPeekOpen && !isSkillFilePeek ? peekId : null,
  );

  // Phase 87.1 Plan 04 — emit `artifact_preview_opened` once per open for MD/HTML.
  // Effect re-fires when (peekId, peekType, isPeekOpen) changes, so close/re-open
  // emits a NEW event (per-open semantics, not per-mount).
  React.useEffect(() => {
    if (!isPeekOpen) return;
    if (isSkillFilePeek) return;
    if (peekType !== 'MD' && peekType !== 'HTML') return;
    if (!peekId) return;
    trackEvent('artifact_preview_opened', {
      format: peekType === 'MD' ? 'md' : 'html',
      artifactId: peekId,
    });
  }, [isPeekOpen, isSkillFilePeek, peekType, peekId]);

  // ⌘. → escalate
  React.useEffect(() => {
    if (!isPeekOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '.') {
        e.preventDefault();
        escalate();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isPeekOpen, escalate]);

  const handleCopyId = React.useCallback(async () => {
    if (!peekId) return;
    await copyToClipboard(peekId);
  }, [peekId]);

  const handleCopyLink = React.useCallback(async () => {
    if (typeof window === 'undefined') return;
    await copyToClipboard(window.location.href);
  }, []);

  const handlePin = React.useCallback(() => {
    // Phase 89 will persist pins.
    console.debug('[ArtifactPeekDrawer] Pin pressed (placeholder)', { peekId, peekType });
  }, [peekId, peekType]);

  const lineage = data?.lineage ?? null;

  // Phase 89 Plan 06 — pull versionNumber + versionHistory off the
  // artifact GET. ISSUE is wired in Plan 05. NOTE + file types fall
  // back to no chip (nothing to show yet).
  const versionInfo: { versionNumber: number; history: VersionHistoryEntry[] } | null =
    data?.issue?.versionNumber != null
      ? {
          versionNumber: data.issue.versionNumber,
          history: (data.issue.versionHistory ?? []) as VersionHistoryEntry[],
        }
      : null;

  return (
    <DialogPrimitive.Root
      open={isPeekOpen}
      onOpenChange={(open) => {
        if (!open) closePeek();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          data-testid="peek-drawer-overlay"
          className={cn(
            'fixed inset-0 z-50 bg-foreground/[0.18]',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0',
            'motion-reduce:animate-none motion-reduce:transition-none',
          )}
        />
        <DialogPrimitive.Content
          data-testid="peek-drawer-content"
          data-peek-mode={peekMode}
          aria-describedby={undefined}
          className={cn(
            'fixed z-50 flex flex-col bg-background shadow-xl',
            // Phase 94 Plan 02 (MIG-03) — branch on peekMode.
            isBottomSheet
              ? [
                  // Bottom-sheet (<768): full-width, slides up from bottom,
                  // 90vh max so the user can still see the page underneath
                  // and dismiss via tap-outside.
                  'inset-x-0 bottom-0 top-auto h-[90vh] w-full max-w-none',
                  'rounded-t-[16px] rounded-b-none border-t border-border',
                  'data-[state=open]:animate-in data-[state=closed]:animate-out',
                  'data-[state=open]:slide-in-from-bottom data-[state=closed]:slide-out-to-bottom',
                  'data-[state=open]:duration-250 data-[state=closed]:duration-200',
                  'ease-out',
                  'motion-reduce:data-[state=open]:fade-in-0 motion-reduce:data-[state=closed]:fade-out-0',
                  'motion-reduce:data-[state=open]:slide-in-from-bottom-0 motion-reduce:data-[state=closed]:slide-out-to-bottom-0',
                ]
              : [
                  // Side drawer (≥768): existing right-side behavior preserved.
                  'inset-y-0 right-0 h-full w-[680px] max-w-[100vw]',
                  'rounded-l-[16px] rounded-r-none border-l border-border',
                  'data-[state=open]:animate-in data-[state=closed]:animate-out',
                  'data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right',
                  'data-[state=open]:duration-250 data-[state=closed]:duration-200',
                  'ease-out',
                  'motion-reduce:data-[state=open]:fade-in-0 motion-reduce:data-[state=closed]:fade-out-0',
                  'motion-reduce:data-[state=open]:slide-in-from-right-0 motion-reduce:data-[state=closed]:slide-out-to-right-0',
                ],
          )}
        >
          <DialogPrimitive.Title className="sr-only">
            {isSkillFilePeek && skillFile
              ? `Skill file ${skillFile.path}`
              : (data?.title ??
                (peekType ? `${peekType} artifact` : 'Artifact preview'))}
          </DialogPrimitive.Title>

          {/* Header — 56px */}
          <header className="flex h-14 flex-shrink-0 items-center gap-2 border-b border-border px-4">
            {/* Phase 91 — skill-file branch: show SKILL chip + filename. */}
            {isSkillFilePeek && skillFile && (
              <>
                <ArtifactTypeBadge type="SKILL" />
                <span
                  className="font-mono text-[10px] font-semibold uppercase tracking-wider text-muted-foreground"
                  data-testid="peek-drawer-skill-slug"
                >
                  {skillFile.slug}
                </span>
                <span
                  className="truncate text-[13px] font-medium text-foreground"
                  data-testid="peek-drawer-skill-filename"
                >
                  {skillFile.path.split('/').pop() ?? skillFile.path}
                </span>
              </>
            )}

            {/* Entity-peek header — preserved verbatim, hidden for skill files. */}
            {!isSkillFilePeek && lineage?.sourceChatId && (
              <LineageChip
                sourceChatId={lineage.sourceChatId}
                sourceMessageId={lineage.sourceMessageId}
                firstSeenAt={lineage.firstSeenAt}
                workspaceSlug={workspaceSlug}
              />
            )}

            {!isSkillFilePeek && peekType && <ArtifactTypeBadge type={peekType} />}

            {!isSkillFilePeek && peekId && (
              <TooltipProvider delayDuration={300}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={handleCopyId}
                      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-xs text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label="Copy artifact ID"
                      data-testid="peek-drawer-id"
                    >
                      {shortId(peekId)}
                      <Copy className="h-3 w-3" aria-hidden="true" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    <span className="text-xs">Click to copy ID</span>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}

            {!isSkillFilePeek && versionInfo && (
              <VersionHistoryChip
                versionNumber={versionInfo.versionNumber}
                versionHistory={versionInfo.history}
              />
            )}

            <div className="ml-auto flex items-center gap-1">
              {/* Expand and Pin are entity-only — split-pane for files lands in Phase 92. */}
              {!isSkillFilePeek && (
                <>
                  <TooltipProvider delayDuration={300}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          onClick={escalate}
                          aria-label="Expand to focus view"
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          data-testid="peek-drawer-expand"
                        >
                          <Maximize2 className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom">
                        <span className="text-xs">Expand (⌘.)</span>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  <button
                    type="button"
                    onClick={handlePin}
                    aria-label="Pin artifact"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    data-testid="peek-drawer-pin"
                  >
                    <Pin className="h-4 w-4" aria-hidden="true" />
                  </button>
                </>
              )}

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    aria-label="More options"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    data-testid="peek-drawer-more"
                  >
                    <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onSelect={handleCopyLink}>Copy link</DropdownMenuItem>
                  {lineage?.sourceChatId && workspaceSlug && (
                    <DropdownMenuItem asChild>
                      <a
                        href={
                          lineage.sourceMessageId
                            ? `/${workspaceSlug}/chat/${lineage.sourceChatId}#msg-${lineage.sourceMessageId}`
                            : `/${workspaceSlug}/chat/${lineage.sourceChatId}`
                        }
                      >
                        View origin chat
                      </a>
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>

              <DialogPrimitive.Close asChild>
                <button
                  type="button"
                  aria-label="Close peek drawer"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  data-testid="peek-drawer-close"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </DialogPrimitive.Close>
            </div>
          </header>

          {/* Body — Phase 91 branch: skill-file preview vs entity-peek. */}
          <div className="flex-1 overflow-hidden">
            {isSkillFilePeek && skillFile ? (
              <SkillFilePreview slug={skillFile.slug} path={skillFile.path} />
            ) : peekType && peekId ? (
              <ArtifactRendererSwitch type={peekType} id={peekId} />
            ) : null}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
