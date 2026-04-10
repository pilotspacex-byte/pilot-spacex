/**
 * MemoryBrowseTable — Paginated shadcn Table with row selection for memory browse.
 *
 * Phase 71: Columns: checkbox, type, kind, label, snippet, score (search only),
 * pinned, created. Pagination controls at bottom.
 */

'use client';

import * as React from 'react';
import { ChevronLeft, ChevronRight, Pin } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useMemoryList } from '../hooks/use-ai-memory';
import type { MemoryListParams, MemoryListItem } from '../hooks/use-ai-memory';

/** Human-readable node type labels for the table. */
const NODE_TYPE_DISPLAY: Record<string, string> = {
  note_chunk: 'Note excerpt',
  note: 'Note',
  issue: 'Issue',
  decision: 'Decision',
  agent_turn: 'AI conversation',
  user_correction: 'Correction',
  pr_review_finding: 'PR finding',
  learned_pattern: 'Pattern',
};

interface MemoryBrowseTableProps {
  workspaceId: string;
  params: MemoryListParams;
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onRowClick: (id: string) => void;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function TableSkeleton({ columns }: { columns: number }) {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: columns }).map((__, j) => (
            <TableCell key={j}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export function MemoryBrowseTable({
  workspaceId,
  params,
  selectedIds,
  onSelectionChange,
  onRowClick,
  offset,
  limit,
  onPageChange,
}: MemoryBrowseTableProps) {
  const { data, isLoading } = useMemoryList(workspaceId, params);
  const items = React.useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const hasNext = data?.hasNext ?? false;
  const showScore = !!params.q;

  const allOnPageSelected = items.length > 0 && items.every((item) => selectedIds.has(item.id));

  const handleSelectAll = React.useCallback(
    (checked: boolean | 'indeterminate') => {
      if (checked === true) {
        const next = new Set(selectedIds);
        items.forEach((item) => next.add(item.id));
        onSelectionChange(next);
      } else {
        const next = new Set(selectedIds);
        items.forEach((item) => next.delete(item.id));
        onSelectionChange(next);
      }
    },
    [items, selectedIds, onSelectionChange],
  );

  const handleSelectRow = React.useCallback(
    (id: string, checked: boolean | 'indeterminate') => {
      const next = new Set(selectedIds);
      if (checked === true) {
        next.add(id);
      } else {
        next.delete(id);
      }
      onSelectionChange(next);
    },
    [selectedIds, onSelectionChange],
  );

  const handleRowClick = React.useCallback(
    (item: MemoryListItem, e: React.MouseEvent | React.KeyboardEvent) => {
      // Don't open drawer when clicking checkbox
      if ((e.target as HTMLElement).closest('[role="checkbox"]')) return;
      onRowClick(item.id);
    },
    [onRowClick],
  );

  const handleRowKeyDown = React.useCallback(
    (item: MemoryListItem, e: React.KeyboardEvent<HTMLTableRowElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onRowClick(item.id);
        return;
      }
      if (e.key === ' ') {
        e.preventDefault();
        // Space toggles selection (like checkbox)
        const next = new Set(selectedIds);
        if (next.has(item.id)) {
          next.delete(item.id);
        } else {
          next.add(item.id);
        }
        onSelectionChange(next);
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextRow = (e.currentTarget as HTMLElement).nextElementSibling as HTMLElement | null;
        nextRow?.focus();
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevRow = (e.currentTarget as HTMLElement).previousElementSibling as HTMLElement | null;
        prevRow?.focus();
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        (e.currentTarget as HTMLElement).blur();
      }
    },
    [onRowClick, selectedIds, onSelectionChange],
  );

  const columnCount = showScore ? 7 : 6;
  const rangeStart = total > 0 ? offset + 1 : 0;
  const rangeEnd = Math.min(offset + limit, total);

  return (
    <div className="space-y-3">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <span className="sr-only">Selection</span>
                <Checkbox
                  checked={allOnPageSelected && items.length > 0 ? true : false}
                  onCheckedChange={handleSelectAll}
                  aria-label="Select all memories on this page"
                />
              </TableHead>
              <TableHead className="w-[140px]">Type</TableHead>
              <TableHead className="w-[200px]">Label</TableHead>
              <TableHead>Snippet</TableHead>
              {showScore && <TableHead className="w-[70px]">Score</TableHead>}
              <TableHead className="w-[50px]">
                <span className="sr-only">Pinned</span>
              </TableHead>
              <TableHead className="w-[100px]">Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableSkeleton columns={columnCount} />
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columnCount} className="h-32 text-center">
                  <div className="space-y-1.5">
                    <p className="text-sm font-medium text-foreground">
                      {params.q || params.type || params.kind || params.pinned
                        ? 'No matching memories'
                        : 'No memories yet'}
                    </p>
                    <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                      {params.q || params.type || params.kind || params.pinned
                        ? 'Try adjusting your search or filters to find what you\'re looking for.'
                        : 'Memories are created automatically when your team writes notes, resolves issues, or chats with Pilot. They\'ll appear here once available.'}
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow
                  key={item.id}
                  tabIndex={0}
                  className="cursor-pointer focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                  onClick={(e) => handleRowClick(item, e)}
                  onKeyDown={(e) => handleRowKeyDown(item, e)}
                  aria-selected={selectedIds.has(item.id)}
                  aria-label={`Memory: ${item.label || item.nodeType}`}
                  data-state={selectedIds.has(item.id) ? 'selected' : undefined}
                >
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(item.id)}
                      onCheckedChange={(checked) => handleSelectRow(item.id, checked)}
                      aria-label={`Select memory: ${item.label}`}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <Badge variant="secondary" className="text-xs whitespace-nowrap">
                        {NODE_TYPE_DISPLAY[item.nodeType] ?? item.nodeType.replace(/_/g, ' ')}
                      </Badge>
                      {item.kind && item.kind !== 'raw' && (
                        <Badge variant="outline" className="text-[10px] whitespace-nowrap">
                          {item.kind}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-medium truncate block max-w-[180px]" title={item.label}>
                      {item.label}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground line-clamp-1">
                      {item.contentSnippet
                        .replace(/<!--[\s\S]*?-->/g, '')
                        .replace(/^#{1,6}\s+/gm, '')
                        .trim() || '(empty)'}
                    </span>
                  </TableCell>
                  {showScore && (
                    <TableCell className="text-sm font-mono text-muted-foreground">
                      {item.score != null ? item.score.toFixed(2) : '-'}
                    </TableCell>
                  )}
                  <TableCell>
                    {item.pinned && (
                      <Pin className="h-3.5 w-3.5 text-primary" aria-label="Pinned" />
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatRelativeTime(item.createdAt)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Showing {rangeStart}-{rangeEnd} of {total}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={offset === 0}
            onClick={() => onPageChange(Math.max(0, offset - limit))}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasNext}
            onClick={() => onPageChange(offset + limit)}
            aria-label="Next page"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
