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
  const items = data?.items ?? [];
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
    (item: MemoryListItem, e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onRowClick(item.id);
      }
    },
    [onRowClick],
  );

  const columnCount = showScore ? 8 : 7;
  const rangeStart = total > 0 ? offset + 1 : 0;
  const rangeEnd = Math.min(offset + limit, total);

  return (
    <div className="space-y-3">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={allOnPageSelected && items.length > 0 ? true : false}
                  onCheckedChange={handleSelectAll}
                  aria-label="Select all memories on this page"
                />
              </TableHead>
              <TableHead className="w-[120px]">Type</TableHead>
              <TableHead className="w-[80px]">Kind</TableHead>
              <TableHead className="w-[180px]">Label</TableHead>
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
                <TableCell colSpan={columnCount} className="h-24 text-center text-muted-foreground">
                  No memories found. Try adjusting your filters or search query.
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow
                  key={item.id}
                  tabIndex={0}
                  className="cursor-pointer"
                  onClick={(e) => handleRowClick(item, e)}
                  onKeyDown={(e) => handleRowKeyDown(item, e)}
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
                    <Badge variant="secondary" className="text-xs whitespace-nowrap">
                      {item.nodeType.replace(/_/g, ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {item.kind ?? '-'}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-medium truncate block max-w-[180px]" title={item.label}>
                      {item.label}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground line-clamp-1">
                      {item.contentSnippet}
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
