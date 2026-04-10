/**
 * MemoryDetailDrawer — Sheet drawer showing full memory content and provenance.
 *
 * Phase 71: Right-side Sheet with content, properties, provenance, pin/forget actions.
 */

'use client';

import * as React from 'react';
import { Pin, PinOff, Trash2, ExternalLink, FileText, Brain, MessageSquare, GitPullRequest, AlertCircle } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useMemoryDetail, usePinMemory, useForgetMemory } from '../hooks/use-ai-memory';
import { useQueryClient } from '@tanstack/react-query';

interface MemoryDetailDrawerProps {
  workspaceId: string;
  nodeId: string | null;
  open: boolean;
  onClose: () => void;
}

function DetailSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-4 w-64" />
    </div>
  );
}

function formatTimestamp(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso));
}

/** Strip markdown headings + HTML comments for cleaner display. */
function cleanContent(raw: string): string {
  return raw
    .replace(/<!--[\s\S]*?-->/g, '') // TipTap block IDs
    .replace(/^#{1,6}\s+/gm, '')     // markdown headings (## Foo → Foo)
    .trim();
}

/** Human-readable node type label + icon. */
const NODE_TYPE_LABELS: Record<string, { label: string; Icon: React.ElementType }> = {
  note_chunk: { label: 'Note excerpt', Icon: FileText },
  note: { label: 'Note', Icon: FileText },
  issue: { label: 'Issue', Icon: AlertCircle },
  decision: { label: 'Decision', Icon: Brain },
  agent_turn: { label: 'AI conversation', Icon: MessageSquare },
  user_correction: { label: 'Correction', Icon: AlertCircle },
  pr_review_finding: { label: 'PR review finding', Icon: GitPullRequest },
  learned_pattern: { label: 'Learned pattern', Icon: Brain },
};

function getTypeInfo(nodeType: string) {
  return NODE_TYPE_LABELS[nodeType] ?? { label: nodeType.replace(/_/g, ' '), Icon: FileText };
}

/** Properties we hide from the admin — internal plumbing, not useful. */
const HIDDEN_PROPERTIES = new Set([
  'chunk_index', 'heading_level', 'parent_note_id', 'parent_issue_id',
  'pinned', 'source_type', 'source_id', 'memory_type',
]);

export function MemoryDetailDrawer({
  workspaceId,
  nodeId,
  open,
  onClose,
}: MemoryDetailDrawerProps) {
  const { data: detail, isLoading } = useMemoryDetail(workspaceId, nodeId);
  const pinMutation = usePinMemory(workspaceId);
  const forgetMutation = useForgetMemory(workspaceId);
  const queryClient = useQueryClient();

  const handlePin = React.useCallback(() => {
    if (!nodeId) return;
    pinMutation.mutate(nodeId, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['memory-list'] });
        queryClient.invalidateQueries({ queryKey: ['memory-stats'] });
        queryClient.invalidateQueries({ queryKey: ['memory-detail', workspaceId, nodeId] });
      },
    });
  }, [nodeId, pinMutation, queryClient, workspaceId]);

  const handleForget = React.useCallback(() => {
    if (!nodeId) return;
    forgetMutation.mutate(nodeId, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['memory-list'] });
        queryClient.invalidateQueries({ queryKey: ['memory-stats'] });
        onClose();
      },
    });
  }, [nodeId, forgetMutation, queryClient, onClose]);

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" aria-label="Memory detail drawer">
        {isLoading || !detail ? (
          <>
            <SheetHeader>
              <SheetTitle className="sr-only">Loading memory detail</SheetTitle>
            </SheetHeader>
            <DetailSkeleton />
          </>
        ) : (
          <div className="flex h-full flex-col">
            {/* Header — SheetHeader provides its own p-4 */}
            {(() => {
              const typeInfo = getTypeInfo(detail.nodeType);
              return (
                <SheetHeader className="pb-0">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                      <typeInfo.Icon className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <SheetTitle className="text-base leading-tight">{detail.label}</SheetTitle>
                      <SheetDescription className="flex items-center gap-2 mt-1.5">
                        <Badge variant="secondary" className="text-xs">
                          {typeInfo.label}
                        </Badge>
                        {detail.kind && detail.kind !== 'raw' && (
                          <Badge variant="outline" className="text-xs">
                            {detail.kind}
                          </Badge>
                        )}
                        {detail.pinned && (
                          <Pin className="h-3 w-3 text-primary" aria-label="Pinned" />
                        )}
                      </SheetDescription>
                    </div>
                  </div>
                </SheetHeader>
              );
            })()}

            {/* Source attribution — sits inside the padded container */}
            <div className="px-5">
              {detail.sourceLabel && (
                <div className="flex items-center gap-2 mt-3 px-3 py-2.5 rounded-lg bg-muted/40 text-sm border border-border/50">
                  <span className="text-muted-foreground">From</span>
                  <span className="font-medium text-foreground truncate">{detail.sourceLabel}</span>
                  {detail.sourceUrl && (
                    <a
                      href={detail.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline inline-flex items-center gap-1 ml-auto shrink-0 text-xs"
                      aria-label={`Open ${detail.sourceLabel}`}
                    >
                      Open <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              )}
            </div>

            {/* Scrollable body — consistent horizontal padding */}
            <ScrollArea className="flex-1 mt-4">
              <div className="space-y-6 px-5 pb-4">
                {/* Content — cleaned and readable */}
                <section>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Content
                  </h4>
                  <div className="whitespace-pre-wrap text-sm text-foreground leading-relaxed rounded-lg bg-muted/20 p-4 max-h-[50vh] overflow-y-auto overflow-x-auto border border-border/30">
                    {cleanContent(detail.content)}
                  </div>
                </section>

                {/* Metadata — only user-relevant properties, collapsed by default */}
                {(() => {
                  const visibleProps = Object.entries(detail.properties).filter(
                    ([key]) => !HIDDEN_PROPERTIES.has(key)
                  );
                  if (visibleProps.length === 0) return null;
                  return (
                    <details className="group">
                      <summary className="text-xs font-semibold uppercase tracking-wider text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors">
                        Metadata ({visibleProps.length})
                      </summary>
                      <table className="w-full rounded-lg border text-sm mt-2">
                        <tbody>
                          {visibleProps.map(([key, value]) => (
                            <tr key={key} className="border-b last:border-b-0">
                              <th
                                scope="row"
                                className="min-w-[100px] max-w-[140px] shrink-0 px-3 py-2 text-left align-top font-mono text-xs font-normal text-muted-foreground"
                              >
                                {key}
                              </th>
                              <td className="px-3 py-2 text-xs text-foreground break-all">
                                {typeof value === 'string' ? value : JSON.stringify(value)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </details>
                  );
                })()}

                {/* Timeline — clean, minimal, with subtle top border */}
                <div className="space-y-1 border-t pt-4 text-xs text-muted-foreground">
                  <div>Created {formatTimestamp(detail.createdAt)}</div>
                  {detail.updatedAt !== detail.createdAt && (
                    <div>Updated {formatTimestamp(detail.updatedAt)}</div>
                  )}
                  {detail.embeddingDim != null && (
                    <div>{detail.embeddingDim}-dim embedding</div>
                  )}
                </div>
              </div>
            </ScrollArea>

            {/* Actions — pinned to bottom with consistent padding */}
            <div className="flex items-center gap-2 border-t px-5 py-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePin}
                disabled={pinMutation.isPending}
                className="gap-1"
                aria-label={detail.pinned ? 'Unpin this memory' : 'Pin this memory'}
              >
                {detail.pinned ? (
                  <>
                    <PinOff className="h-3.5 w-3.5" /> Unpin
                  </>
                ) : (
                  <>
                    <Pin className="h-3.5 w-3.5" /> Pin
                  </>
                )}
              </Button>

              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={forgetMutation.isPending}
                    className="gap-1"
                    aria-label="Forget this memory"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Forget
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Forget this memory?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently remove this memory from the workspace. This action
                      cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleForget}>Forget</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
