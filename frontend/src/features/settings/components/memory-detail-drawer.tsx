/**
 * MemoryDetailDrawer — Sheet drawer showing full memory content and provenance.
 *
 * Phase 71: Right-side Sheet with content, properties, provenance, pin/forget actions.
 */

'use client';

import * as React from 'react';
import { Pin, PinOff, Trash2, ExternalLink } from 'lucide-react';
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
            <SheetHeader>
              <SheetTitle className="text-base">{detail.label}</SheetTitle>
              <SheetDescription className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">
                  {detail.nodeType.replace(/_/g, ' ')}
                </Badge>
                {detail.kind && (
                  <Badge variant="outline" className="text-xs">
                    {detail.kind}
                  </Badge>
                )}
                {detail.pinned && (
                  <Pin className="h-3 w-3 text-primary" aria-label="Pinned" />
                )}
              </SheetDescription>
            </SheetHeader>

            <ScrollArea className="flex-1 mt-4">
              <div className="space-y-5 pr-2">
                {/* Content */}
                <section>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Content
                  </h4>
                  <pre className="whitespace-pre-wrap text-sm text-foreground bg-muted/30 rounded-md p-3 max-h-[50vh] overflow-y-auto overflow-x-auto">
                    {detail.content.replace(/<!--[\s\S]*?-->/g, '').trim()}
                  </pre>
                </section>

                {/* Properties */}
                {Object.keys(detail.properties).length > 0 && (
                  <section>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                      Properties
                    </h4>
                    <table className="w-full rounded-md border text-sm">
                      <tbody>
                        {Object.entries(detail.properties).map(([key, value]) => (
                          <tr key={key} className="border-b last:border-b-0">
                            <th
                              scope="row"
                              className="min-w-[100px] max-w-[140px] shrink-0 px-3 py-1.5 text-left align-top font-mono text-xs font-normal text-muted-foreground"
                            >
                              {key}
                            </th>
                            <td className="px-3 py-1.5 text-xs text-foreground break-all">
                              {typeof value === 'string' ? value : JSON.stringify(value)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </section>
                )}

                {/* Provenance */}
                <section>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Provenance
                  </h4>
                  <div className="space-y-1 text-sm">
                    {detail.sourceType && (
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Source:</span>
                        <span className="text-foreground">
                          {detail.sourceLabel ?? detail.sourceType}
                        </span>
                        {detail.sourceUrl && (
                          <a
                            href={detail.sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline inline-flex items-center gap-0.5"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    )}
                    {detail.embeddingDim != null && (
                      <div>
                        <span className="text-muted-foreground">Embedding:</span>{' '}
                        <span className="font-mono text-xs">{detail.embeddingDim}d</span>
                      </div>
                    )}
                    <div>
                      <span className="text-muted-foreground">Created:</span>{' '}
                      {formatTimestamp(detail.createdAt)}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Updated:</span>{' '}
                      {formatTimestamp(detail.updatedAt)}
                    </div>
                  </div>
                </section>
              </div>
            </ScrollArea>

            {/* Actions */}
            <div className="flex items-center gap-2 border-t pt-3 mt-3">
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
